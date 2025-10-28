from rdflib import Graph, Literal, RDF, URIRef, Namespace
from rdflib.namespace import XSD
import requests

# Namespace cho công ty
NS = Namespace("http://example.com/company#")

# Fuseki endpoint
FUSEKI_URL = "http://localhost:3030/TMA_Company/data?graph=http://example.com/company"
def create_tma_company_ontology():
    g = Graph()

    # Tạo class Company
    Company = URIRef(NS.Company)

    # Các thuộc tính dữ liệu
    properties = {
        "name": XSD.string,
        "industry": XSD.string,
        "address": XSD.string,
        "phone": XSD.string,
        "email": XSD.string,
        "ceo": XSD.string,
        "accessLevel": XSD.string  # internal / public
    }

    # Dữ liệu công ty TMA Tech Group
    companies = [
        {
            "id": "TMA_Tech_Group",
            "name": "TMA Tech Group",
            "industry": "Software & IT Services",
            "address": "Khu Công nghệ cao, Quận 9, TP.HCM, Vietnam",
            "phone": "+84 28 1234 5678",
            "email": "contact@tma.com.vn",
            "ceo": "Nguyen Van A",
            "accessLevel": "internal"
        }
    ]

    # Thêm triples vào graph
    for c in companies:
        company_uri = URIRef(NS[c["id"]])
        g.add((company_uri, RDF.type, Company))
        for prop, datatype in properties.items():
            g.add((company_uri, NS[prop], Literal(c[prop], datatype=datatype)))

    # Serialize graph ra Turtle string
    ttl_data = g.serialize(format="turtle").decode("utf-8") if isinstance(g.serialize(format="turtle"), bytes) else g.serialize(format="turtle")

    # Đẩy lên Fuseki bằng HTTP PUT (Graph Store Protocol)
    headers = {"Content-Type": "text/turtle"}
    response = requests.post(FUSEKI_URL, data=ttl_data, headers=headers)
    if response.status_code in [200, 201, 204]:
        print("Upload ontology TMA Tech Group thành công vào Fuseki dataset TMA_Company")
    else:
        print("Lỗi khi upload:", response.status_code, response.text)

    return g

if __name__ == "__main__":
    create_tma_company_ontology()
