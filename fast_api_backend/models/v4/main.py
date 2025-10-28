from fastapi import FastAPI, Query
from rdflib import Graph, Namespace

app = FastAPI(title="Company Chatbot Ontology API")

# Load ontology RDF
g = Graph()
g.parse("data/company_ontology.ttl", format="turtle")
NS = Namespace("http://example.com/company#")

@app.get("/companies")
def get_companies(role: str = Query(..., description="Role of user: internal / public")):
    """
    Trả về danh sách công ty theo role
    """
    # SPARQL query theo accessLevel
    query = f"""
    PREFIX : <http://example.com/company#>
    SELECT ?id ?name ?industry ?address ?phone ?email ?ceo
    WHERE {{
        ?id a :Company ;
            :accessLevel "{role}" ;
            :name ?name ;
            :industry ?industry ;
            :address ?address ;
            :phone ?phone ;
            :email ?email ;
            :ceo ?ceo .
    }}
    """
    results = []
    for row in g.query(query):
        results.append({
            "id": str(row.id).replace(str(NS), ""),
            "name": str(row.name),
            "industry": str(row.industry),
            "address": str(row.address),
            "phone": str(row.phone),
            "email": str(row.email),
            "ceo": str(row.ceo)
        })
    
    return {"role": role, "companies": results}
