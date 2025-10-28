from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import re, json, requests
from typing import Any, Dict, Optional, Tuple
from fastapi.middleware.cors import CORSMiddleware

# ------------------ CONFIG ------------------
KG_NS = "http://example.org/ontology/"
FUSEKI_URL = "http://localhost:3030/company_kg"
LLAMA_API_URL = "http://localhost:11434/api/generate"

CLASS_MAP = {
    "sản phẩm": f"<{KG_NS}Product>",
    "nhân sự": f"<{KG_NS}Person>",
    "công ty": f"<{KG_NS}Organization>",
}

PREDICATE_MAP = {
    "bảo hành": f"<{KG_NS}hasWarranty>",
    "giá": f"<{KG_NS}hasPrice>",
    "tính năng": f"<{KG_NS}hasFeature>",
    "được sản xuất bởi": f"<{KG_NS}manufacturedBy>",
    "nhà cung cấp": f"<{KG_NS}supplier>",
    "mã": f"<{KG_NS}code>",
    "loại": f"<{KG_NS}type>",
}

# ------------------ UTILS ------------------
def normalize_text(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip())

def find_number_and_unit(text: str) -> Optional[Tuple[str, str]]:
    m = re.search(r"(\d+)\s*(tháng|năm|ngày|vnd|đ|đồng|%)?", text, re.I)
    if m:
        return (m.group(1), (m.group(2) or "").strip())
    return None

# ------------------ SIMPLE NER ------------------
class DummyNER:
    def extract(self, text):
        ents = []
        if "nestle" in text.lower() or "nestlé" in text.lower():
            ents.append({"text": "Nestlé", "label": "ORG"})
        return ents

# ------------------ PARSER ------------------
class QuestionParser:
    def __init__(self, ner_extractor):
        self.ner = ner_extractor

    def parse(self, question: str) -> Dict[str, Any]:
        q = normalize_text(question.lower())
        out = {"raw": question, "intent": None, "classes": [], "attributes": [], "entities": [], "filters": []}

        if re.search(r"\b(bao nhiêu|số lượng|count|có bao nhiêu)\b", q):
            out["intent"] = "count"
        elif re.search(r"\b(có|liệu)\b.*\b(không|ko|\?)", q):
            out["intent"] = "yesno"
        else:
            out["intent"] = "find"

        for kw in CLASS_MAP:
            if re.search(r"\b" + re.escape(kw) + r"\b", q):
                out["classes"].append(kw)
        for kw in PREDICATE_MAP:
            if re.search(r"\b" + re.escape(kw) + r"\b", q):
                out["attributes"].append(kw)

        ents = self.ner.extract(question)
        out["entities"] = ents

        num_unit = find_number_and_unit(question)
        if num_unit:
            num, unit = num_unit
            if out["attributes"]:
                for attr in out["attributes"]:
                    out["filters"].append((attr, "=", f"{num} {unit}".strip()))
            else:
                out["filters"].append(("value", "=", f"{num} {unit}".strip()))

        for e in ents:
            out["filters"].append((e.get("label", "ENTITY"), "=", e.get("text")))

        return out

# ------------------ SPARQL BUILDER ------------------
class SPARQLBuilder:
    def __init__(self):
        self.prefix = (
            f"PREFIX ex: <{KG_NS}>\n"
            "PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>\n"
        )

    def _literal(self, v: str) -> str:
        if re.match(r"^\d+$", v):
            return v
        return f"\"{v.replace('\"', '\\\"')}\""

    def build(self, parsed: Dict[str, Any]) -> str:
        subj, label = "?s", "?sLabel"
        where = []

        if parsed["classes"]:
            cls_uri = CLASS_MAP.get(parsed["classes"][0])
            if cls_uri:
                where.append(f"{subj} a {cls_uri} .")

        for (attr, op, val) in parsed["filters"]:
            pred = PREDICATE_MAP.get(attr)
            if pred:
                where.append(f"{subj} {pred} {self._literal(val)} .")

        for attr_kw in parsed["attributes"]:
            pred = PREDICATE_MAP.get(attr_kw)
            if pred:
                where.append(f"OPTIONAL {{ {subj} {pred} ?attr_{attr_kw} . }}")

        where.append(f"OPTIONAL {{ {subj} rdfs:label {label} . }}")
        where_str = "\n  ".join(where)
        query_type = parsed["intent"]

        if query_type == "count":
            return self.prefix + f"\nSELECT (COUNT(DISTINCT {subj}) AS ?count) WHERE {{\n  {where_str}\n}}"
        else:
            return self.prefix + f"\nSELECT DISTINCT {subj} {label} WHERE {{\n  {where_str}\n}} LIMIT 10"

# ------------------ FUSEKI CLIENT ------------------
class FusekiClient:
    def __init__(self, base_url: str):
        self.query_url = base_url.rstrip("/") + "/query"

    def query(self, sparql: str):
        print("\n[DEBUG] SPARQL Query:\n", sparql)
        r = requests.post(
            self.query_url,
            data={"query": sparql},
            headers={"Accept": "application/sparql-results+json"}
        )
        if not r.ok:
            print("[ERROR] Fuseki response:", r.text)
            r.raise_for_status()
        data = r.json()
        print("[DEBUG] Fuseki result keys:", list(data.keys()))
        return data

# ------------------ LLAMA CLIENT ------------------
class LlamaClient:
    def __init__(self, api_url: str):
        self.url = api_url

    def ask(self, context: str, question: str) -> str:
        prompt = f"""Ngữ cảnh dữ liệu:
{context}

Câu hỏi của người dùng:
{question}

Hãy trả lời ngắn gọn và tự nhiên bằng tiếng Việt, dựa trên dữ liệu trên."""
        resp = requests.post(
            self.url,
            json={"model": "llama3.1:8b", "prompt": prompt, "stream": False},
            timeout=60
        )
        print("[DEBUG] Llama response code:", resp.status_code)
        try:
            j = resp.json()
        except Exception:
            print("[ERROR] Không parse được JSON từ Llama:", resp.text)
            return "Không thể hiểu phản hồi từ Llama."

        # Ollama thường trả về {"response": "..."} hoặc {"message": "..."}
        answer = j.get("response") or j.get("message") or str(j)
        return answer.strip()

# ------------------ FASTAPI APP ------------------
app = FastAPI(title="Knowledge RAG API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ner = DummyNER()
parser = QuestionParser(ner)
builder = SPARQLBuilder()
fuseki = FusekiClient(FUSEKI_URL)
llama = LlamaClient(LLAMA_API_URL)

class AskRequest(BaseModel):
    question: str

@app.post("/ask")
def ask(req: AskRequest):
    try:
        parsed = parser.parse(req.question)
        sparql = builder.build(parsed)
        fuseki_data = fuseki.query(sparql)

        context = json.dumps(fuseki_data, ensure_ascii=False)
        answer = llama.ask(context, req.question)

        return {
            "parsed": parsed,
            "sparql": sparql,
            "fuseki_results": fuseki_data,
            "llama_answer": answer
        }
    except Exception as e:
        print("[EXCEPTION]", e)
        raise HTTPException(status_code=500, detail=str(e))
