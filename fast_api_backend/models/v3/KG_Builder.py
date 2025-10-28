"""
KG_Builder_ontology.py
Build Knowledge Graph for company chatbot based on predefined ontology
"""
import argparse, re
from pathlib import Path
from typing import List, Tuple, Dict, Any

# Text extraction
import pdfplumber, docx, requests
from bs4 import BeautifulSoup

# NLP
import spacy
from transformers import pipeline

# RDF
from rdflib import Graph, URIRef, Literal, Namespace, RDF, RDFS, XSD

from googletrans import Translator

# --------------------------- Text extraction ---------------------------
def extract_text_from_pdf(path: str) -> str:
    texts = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            texts.append(page.extract_text() or "")
    return "\n".join(texts)

def extract_text_from_docx(path: str) -> str:
    doc = docx.Document(path)
    texts = [p.text for p in doc.paragraphs if p.text]
    return "\n".join(texts)

def extract_text_from_html(path_or_url: str) -> str:
    if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
        r = requests.get(path_or_url)
        html = r.text
    else:
        html = Path(path_or_url).read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "html.parser")
    for s in soup(["script", "style"]):
        s.decompose()
    return soup.get_text(separator="\n")

def load_files_from_folder(folder: str) -> Dict[str, str]:
    texts = {}
    patterns = ["**/*.pdf", "**/*.docx", "**/*.html", "**/*.htm", "**/*.txt"]
    p = Path(folder)
    for pat in patterns:
        for f in p.glob(pat):
            try:
                if f.suffix.lower() == ".pdf":
                    texts[str(f)] = extract_text_from_pdf(str(f))
                elif f.suffix.lower() == ".docx":
                    texts[str(f)] = extract_text_from_docx(str(f))
                elif f.suffix.lower() in [".html", ".htm"]:
                    texts[str(f)] = extract_text_from_html(str(f))
                elif f.suffix.lower() == ".txt":
                    texts[str(f)] = f.read_text(encoding="utf-8")
            except Exception as e:
                print(f"Lỗi đọc file {f}: {e}")
    return texts

def clean_text(text: str) -> str:
    text = text.replace('\r','\n')
    text = re.sub(r'\s{2,}', ' ', text)
    text = re.sub(r'\n{2,}', '\n\n', text)
    text = re.sub(r'[\x00-\x1F\x7F]', ' ', text)
    return text.strip()

# --------------------------- NER extractor ---------------------------
class NERExtractor:
    def __init__(self, spacy_model: str = None):
        self.spacy_nlp = None
        self.hf_ner = None
        if spacy_model:
            try:
                self.spacy_nlp = spacy.load(spacy_model)
            except Exception as e:
                print(f"Không load được spaCy {spacy_model}: {e}")
        self.hf_model_name = "xlm-roberta-large-finetuned-conll03-english"
    
    def extract(self, text: str) -> List[Dict[str, Any]]:
        ents = []
        if self.spacy_nlp:
            doc = self.spacy_nlp(text)
            for e in doc.ents:
                ents.append({"text": e.text, "label": e.label_})
            return ents
        if self.hf_ner is None:
            try:
                self.hf_ner = pipeline("ner", model=self.hf_model_name, aggregation_strategy="simple")
            except:
                return []
        res = self.hf_ner(text)
        for r in res:
            ents.append({"text": r.get("word", r.get("entity_group")), "label": r.get("entity_group")})
        return ents

# --------------------------- Relation extraction ---------------------------
def extract_relations_rule_based(text: str) -> List[Tuple[str,str,str]]:
    triples = []
    sents = re.split(r'[\n\.!?]+', text)
    for sent in sents:
        sent = sent.strip()
        if not sent: continue
        # Product có giá
        m = re.search(r"(Sản phẩm .+?) có (giá|bảo hành|hoàn trả) (.+)", sent)
        if m:
            triples.append((m.group(1), m.group(2), m.group(3)))
            continue
        # X thuộc Y
        m = re.search(r"(.+?) thuộc (.+)", sent)
        if m:
            triples.append((m.group(1), "belongsTo", m.group(2)))
    return triples

# --------------------------- RDF generation ---------------------------
def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'\s+', '_', text)
    return text.strip('_')

def build_rdf_graph(triples: List[Tuple[str,str,str]]) -> Graph:
    EX = Namespace("http://example.org/ontology/")
    g = Graph()
    g.bind("ex", EX)

    entity_map = {}  # entity text -> URI

    for s,p,o in triples:
        # Mapping entity type based on predicate or label
        def map_class(text, predicate):
            pred = predicate.lower()
            if "sản phẩm" in text.lower(): return EX.Product
            if "công ty" in text.lower() in text.lower(): return EX.Organization
            if "dịch vụ" in text.lower() in text.lower(): return EX.Service
            if "khu vực" in text.lower() in text.lower() or "hcm" in text.lower(): return EX.Region
            if pred in ["bảo hành","hoàn trả","refund","giá"]: return EX.Policy
            return EX.Entity

        for ent in [s,o]:
            if ent not in entity_map:
                uri = EX[slugify(ent)]
                entity_map[ent] = uri
                g.add((uri, RDF.type, map_class(ent, p)))
                g.add((uri, RDFS.label, Literal(ent)))

        s_uri = entity_map[s]
        o_uri = entity_map[o]

        # predicate: object literal if price/duration else URI
        if p.lower() in ["giá","bảo hành","hoàn trả"]:
            g.add((s_uri, EX[slugify(p)], Literal(o)))
        else:
            g.add((s_uri, EX[slugify(p)], o_uri))
    return g

# --------------------------- Push to Fuseki ---------------------------
def push_to_fuseki(turtle_text: str, fuseki_url: str):
    data_url = fuseki_url.rstrip('/') + '/data'
    headers = {"Content-Type": "text/turtle; charset=utf-8"}
    r = requests.post(data_url, data=turtle_text.encode('utf-8'), headers=headers)
    if r.status_code in (200,201,204):
        print("✅ Đã đẩy RDF lên Fuseki thành công.")
    else:
        print("❌ Lỗi push Fuseki:", r.status_code,r.text)

# --------------------------- Main ---------------------------
def process_folder(folder: str, out_file: str, spacy_model: str=None, fuseki: str=None):
    files = load_files_from_folder(folder)
    print(f"Tìm thấy {len(files)} file.")
    ner = NERExtractor(spacy_model=spacy_model)
    all_triples = []

    for path, text in files.items():
        text = clean_text(text)
        triples_rule = extract_relations_rule_based(text)
        all_triples.extend(triples_rule)
        ents = ner.extract(text[:20000])
        for e in ents:
            all_triples.append((e['text'],'is_a',e.get('label','Entity')))

    uniq = list(dict.fromkeys(all_triples))
    g = build_rdf_graph(uniq)
    ttl = g.serialize(format='turtle')
    Path(out_file).write_text(ttl,encoding='utf-8')
    print(f"Lưu RDF vào {out_file}")
    if fuseki:
        push_to_fuseki(ttl,fuseki)

# --------------------------- CLI ---------------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input','-i',required=True)
    parser.add_argument('--out','-o','kg_output.ttl')
    parser.add_argument('--spacy')
    parser.add_argument('--fuseki')
    args = parser.parse_args()
    process_folder(args.input,args.out,spacy_model=args.spacy,fuseki=args.fuseki)

if __name__=='__main__':
    main()
