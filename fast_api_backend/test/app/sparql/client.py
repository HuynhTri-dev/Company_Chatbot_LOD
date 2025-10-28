from SPARQLWrapper import SPARQLWrapper, JSON
from app.config import SPARQL_ENDPOINT

sparql = SPARQLWrapper(SPARQL_ENDPOINT)

def query_sparql(query: str):
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    try:
        results = sparql.query().convert()
        # Trích xuất kết quả đơn giản
        answers = []
        for result in results["results"]["bindings"]:
            answers.append({k: v["value"] for k,v in result.items()})
        return answers
    except Exception as e:
        return {"error": str(e)}
