import requests

def search_wikidata_entity(query, lang="vi"):
    """Dùng API Wikidata để tìm entity (Q-id)."""
    url = "https://www.wikidata.org/w/api.php"
    params = {
        "action": "wbsearchentities",
        "language": lang,
        "format": "json",
        "search": query
    }
    res = requests.get(url, params=params)
    results = res.json().get("search", [])
    if not results:
        return None
    return {
        "label": results[0]["label"],
        "id": results[0]["id"]
    }

def extract_entities(question: str):
    """Đơn giản: trích danh từ riêng và tìm entity tương ứng."""
    # V1: tìm từ khóa đơn (sau này có thể dùng spaCy/NER)
    keywords = [word for word in question.split() if word[0].isupper()]
    entities = []
    for kw in keywords:
        ent = search_wikidata_entity(kw)
        if ent:
            entities.append(ent)
    return entities

def retrieve_schema(entities):
    """Truy vấn schema (property) của entity đầu tiên."""
    if not entities:
        return []
    qid = entities[0]["id"]
    sparql = f"""
    SELECT DISTINCT ?property ?propertyLabel WHERE {{
      wd:{qid} ?p ?statement.
      ?property wikibase:claim ?p.
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "vi,en". }}
    }} LIMIT 50
    """
    url = "https://query.wikidata.org/sparql"
    headers = {"Accept": "application/sparql-results+json"}
    res = requests.get(url, params={"query": sparql}, headers=headers).json()

    props = []
    for row in res["results"]["bindings"]:
        props.append(f"{row['propertyLabel']['value']} ({row['property']['value'].split('/')[-1]})")
    return props
