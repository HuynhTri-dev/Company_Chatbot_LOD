import requests
import json

def build_sparql_prompt(question: str, entities: list, schema_context: list) -> str:
    """
    Sinh prompt SPARQL hoàn chỉnh cho LLaMA / Ollama,
    có hỗ trợ auto-add ví dụ mẫu khi gặp property phổ biến.
    """
    entity_str = ", ".join([f"{e['label']} ({e['id']})" for e in entities]) if entities else "Không rõ"
    schema_str = "\n".join(schema_context) if schema_context else "Chưa có schema cụ thể."

    # Các ví dụ few-shot gợi ý thêm nếu liên quan
    examples = ""

    q_lower = question.lower()
    props_text = " ".join(schema_context).lower()

    if any(x in q_lower or x in props_text for x in ["gdp", "tổng sản phẩm", "kinh tế", "p2131"]):
        examples += """
    # Ví dụ: GDP của Việt Nam năm 2020
    PREFIX wd: <http://www.wikidata.org/entity/>
    PREFIX wdt: <http://www.wikidata.org/prop/direct/>
    PREFIX p: <http://www.wikidata.org/prop/>
    PREFIX ps: <http://www.wikidata.org/prop/statement/>
    PREFIX pq: <http://www.wikidata.org/prop/qualifier/>

    SELECT ?gdp ?year WHERE {
    wd:Q881 p:P2131 ?statement.
    ?statement ps:P2131 ?gdp;
                pq:P585 ?year.
    FILTER(YEAR(?year) = 2020)
    }
    """

        if any(x in q_lower or x in props_text for x in ["dân số", "population", "p1082"]):
            examples += """
    # Ví dụ: Dân số của Việt Nam
    PREFIX wd: <http://www.wikidata.org/entity/>
    PREFIX wdt: <http://www.wikidata.org/prop/direct/>

    SELECT ?population WHERE {
    wd:Q881 wdt:P1082 ?population.
    }
    """

        if any(x in q_lower or x in props_text for x in ["diện tích", "area", "p2046"]):
            examples += """
    # Ví dụ: Diện tích của Việt Nam
    PREFIX wd: <http://www.wikidata.org/entity/>
    PREFIX wdt: <http://www.wikidata.org/prop/direct/>

    SELECT ?area WHERE {
    wd:Q881 wdt:P2046 ?area.
    }
    """

        if any(x in q_lower or x in props_text for x in ["thủ đô", "capital", "p36"]):
            examples += """
    # Ví dụ: Thủ đô của Việt Nam
    PREFIX wd: <http://www.wikidata.org/entity/>
    PREFIX wdt: <http://www.wikidata.org/prop/direct/>

    SELECT ?capitalLabel WHERE {
    wd:Q881 wdt:P36 ?capital.
    SERVICE wikibase:label { bd:serviceParam wikibase:language "vi,en". }
    }
    """

        if any(x in q_lower or x in props_text for x in ["sáng lập", "founder", "p112"]):
            examples += """
    # Ví dụ: Người sáng lập của một công ty
    PREFIX wd: <http://www.wikidata.org/entity/>
    PREFIX wdt: <http://www.wikidata.org/prop/direct/>

    SELECT ?founderLabel WHERE {
    wd:Q95 wdt:P112 ?founder.
    SERVICE wikibase:label { bd:serviceParam wikibase:language "vi,en". }
    }
    """

        # Prompt chính xác cú pháp + hướng dẫn mô hình
        base_prompt = f"""
    Bạn là một trình sinh truy vấn SPARQL chính xác cho cơ sở tri thức Wikidata.

    ### Ngữ cảnh:
    - Entity chính (chủ thể): {entity_str}
    - Danh sách property (được phép sử dụng):
    {schema_str}

    ### Câu hỏi người dùng:
    {question}

    ### Quy tắc sinh SPARQL:
    1. Chỉ sinh truy vấn SPARQL chuẩn 1.1, tương thích endpoint https://query.wikidata.org/sparql.
    2. Luôn khai báo prefix theo đúng chuẩn:
    PREFIX wd: <http://www.wikidata.org/entity/>
    PREFIX wdt: <http://www.wikidata.org/prop/direct/>
    PREFIX p: <http://www.wikidata.org/prop/>
    PREFIX ps: <http://www.wikidata.org/prop/statement/>
    PREFIX pq: <http://www.wikidata.org/prop/qualifier/>
    3. Không viết sai prefix (ví dụ: không có 'wdt:/P2131', 'wd:/Q881/', 'psv:').
    4. Nếu hỏi về dữ liệu theo năm, hãy dùng qualifier pq:P585 và FILTER(YEAR(...)).
    5. Biến kết quả phải rõ ràng (?gdp, ?population, ?area, ?capital...).
    6. Không thêm markdown, không giải thích — chỉ output SPARQL thuần túy.

    ### Ví dụ truy vấn chuẩn:
    {examples if examples else '(Không có ví dụ cụ thể, hãy sinh trực tiếp dựa trên schema.)'}
    """

    return base_prompt.strip()


def generate_sparql(question: str, entities: list, schema_context: list) -> str:
    prompt = build_sparql_prompt(question=question, entities=entities, schema_context=schema_context)

    url = "http://localhost:11434/api/generate"
    payload = {
        "model": "llama3.1:8b",
        "prompt": prompt,
        "stream": False  # không stream để nhận JSON gọn
    }

    try:
        response = requests.post(url, json=payload, timeout=60)
        if response.status_code != 200:
            return f"[ERROR] HTTP {response.status_code}: {response.text}"

        data = response.json()
        return data.get("response", "").strip() or "[EMPTY RESPONSE]"

    except requests.exceptions.ConnectionError:
        return "[ERROR] Không kết nối được Ollama API (chạy `ollama serve` trước)."
    except Exception as e:
        return f"[EXCEPTION] {e}"


if __name__ == "__main__":
    entities = [{"label": "Việt Nam", "id": "Q881"}]
    schema = [
        "P1082: population",
        "P2131: GDP",
        "P17: country",
    ]
    question = "GDP của Việt Nam năm 2020 là bao nhiêu?"
    
    print("=== Kết quả SPARQL ===")
    print(generate_sparql(question, entities, schema))
