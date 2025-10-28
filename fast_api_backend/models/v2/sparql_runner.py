from SPARQLWrapper import SPARQLWrapper, JSON

def run_sparql(query):
    """Thực thi SPARQL và trả JSON kết quả."""
    try:
        sparql = SPARQLWrapper("https://query.wikidata.org/sparql")
        sparql.setQuery(query)
        sparql.setReturnFormat(JSON)
        results = sparql.query().convert()

        if not results["results"]["bindings"]:
            return "Không có kết quả phù hợp."
        # Lấy giá trị đầu tiên
        first_row = results["results"]["bindings"][0]
        return {k: v["value"] for k, v in first_row.items()}    
    except Exception as e:
        return {"error": str(e)}
