import pandas as pd
import PyPDF2
import json
import requests
from rdflib import Graph, Literal, RDF, XSD, Namespace, URIRef
import re

# -------------------------- Namespace --------------------------
EX = Namespace("http://example.org/company#")

# -------------------------- Load JSON Mapping --------------------------
with open("mapping.json") as f:
    mapping = json.load(f)

# -------------------------- JSON -> RDF --------------------------
def json_to_rdf(entity_type, data, g=None, subject_uri=None):
    if g is None:
        g = Graph()
    class_ns = EX[entity_type]

    if subject_uri is None:
        subject_uri = EX[f"{entity_type}_{data.get('businessCode', data.get('name','id'))}"]

    g.add((subject_uri, RDF.type, class_ns))

    for prop, prop_info in mapping[entity_type]["properties"].items():
        json_path = prop_info["jsonPath"].strip("$.{}")
        value = data.get(json_path)

        if prop_info["type"].startswith("xsd:") and value is not None:
            g.add((subject_uri, EX[prop], Literal(value, datatype=getattr(XSD, prop_info["type"].split(":")[1]))))

        elif prop_info["type"] == "object" and value:
            obj_class = prop_info["class"]
            obj_uri = EX[f"{obj_class}_{value.get('name', 'id')}"]
            g.add((subject_uri, EX[prop], obj_uri))
            json_to_rdf(obj_class, value, g, obj_uri)

        elif prop_info["type"] == "objectArray" and value:
            obj_class = prop_info["class"]
            for item in value:
                obj_uri = EX[f"{obj_class}_{item.get('name', 'id')}"]
                g.add((subject_uri, EX[prop], obj_uri))
                json_to_rdf(obj_class, item, g, obj_uri)

    return g

# -------------------------- Read Excel / CSV --------------------------
def read_excel(file_path):
    df = pd.read_excel(file_path)
    return df.to_dict(orient="records")

def read_csv(file_path):
    df = pd.read_csv(file_path)
    return df.to_dict(orient="records")

# -------------------------- Read JSON --------------------------
def read_json(file_path):
    with open(file_path) as f:
        return json.load(f)

# -------------------------- Read PDF --------------------------
def read_pdf(file_path):
    text = ""
    with open(file_path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            text += page.extract_text() + "\n"
    # --- Simple parser to JSON (customize per PDF structure) ---
    data_list = []
    companies = re.split(r"\nCompany Name:", text)
    for company_text in companies[1:]:
        company = {}
        lines = company_text.splitlines()
        company["name"] = lines[0].strip()
        # parse more fields like businessCode, headquarters, etc.
        for line in lines[1:]:
            if line.startswith("Business Code:"):
                company["businessCode"] = line.split(":", 1)[1].strip()
            elif line.startswith("Headquarters:"):
                company["headquarters"] = line.split(":", 1)[1].strip()
        data_list.append(company)
    return data_list

# -------------------------- Generate RDF --------------------------
def generate_rdf(data_list, entity_type="Company", output_file="output.ttl"):
    g = Graph()
    for item in data_list:
        g = json_to_rdf(entity_type, item, g)
    g.serialize(output_file, format="turtle")
    print(f"RDF saved to {output_file}")
    return g

# -------------------------- Upload to Fuseki --------------------------
def upload_to_fuseki(rdf_file, fuseki_url):
    with open(rdf_file, "rb") as f:
        headers = {"Content-Type": "text/turtle"}
        r = requests.post(fuseki_url, data=f, headers=headers)
    print(f"Upload status: {r.status_code} {r.text}")

# -------------------------- Main Example --------------------------
if __name__ == "__main__":
    # --- Choose your source ---
    source_type = "excel"  # excel / csv / json / pdf
    source_file = "companies.xlsx"

    if source_type == "excel":
        data = read_excel(source_file)
    elif source_type == "csv":
        data = read_csv(source_file)
    elif source_type == "json":
        data = read_json(source_file)
    elif source_type == "pdf":
        data = read_pdf(source_file)
    else:
        data = []

    rdf_file = "companies.ttl"
    g = generate_rdf(data, "Company", rdf_file)

    # --- Upload to Fuseki ---
    FUSEKI_URL = "http://localhost:3030/your_dataset/data"
    upload_to_fuseki(rdf_file, FUSEKI_URL)
