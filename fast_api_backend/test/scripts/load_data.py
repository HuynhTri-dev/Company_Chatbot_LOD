from rdflib import Graph

def load_triples(file_path: str, sparql_endpoint: str):
    g = Graph()
    g.parse(file_path, format="ttl")
    # TODO: push to SPARQL endpoint (có thể dùng Fuseki REST API)
    print(f"Loaded {len(g)} triples to {sparql_endpoint}")

if __name__ == "__main__":
    load_triples("../data/example_triples.ttl", "http://localhost:3030/company_kg")
