import pandas as pd
from rdflib import Graph, Namespace, Literal, RDF, XSD, URIRef
import requests

# ========================
# CONFIG
# ========================
EX = Namespace("http://example.com/company#")
FUSEKI_DATA_URL = "http://localhost:3030/companies/data"  # endpoint /data
EXCEL_PATH = "../data_excel/DoanhNghiepHCM.xlsx"
N_ROWS = 10 # số dòng đầu tiên để import

# ========================
# LOAD EXCEL
# ========================
df = pd.read_excel(EXCEL_PATH)
df = df.head(N_ROWS)

# ========================
# BUILD RDF GRAPH
# ========================
g = Graph()
g.bind("ex", EX)

for _, row in df.iterrows():
    company_uri = URIRef(f"http://example.com/company/{row['IdCompany']}")
    g.add((company_uri, RDF.type, EX.Company))

    def add_prop(predicate, value):
        if pd.notna(value):
            g.add((company_uri, predicate, Literal(str(value), datatype=XSD.string)))

    add_prop(EX.idCompany, row["IdCompany"])
    add_prop(EX.name, row["Name"])
    add_prop(EX.latestLegalRegistration, row["LatestLegalRegistration"])
    add_prop(EX.type, row["Type"])
    add_prop(EX.address, row["Address"])
    add_prop(EX.business, row["Business"])

ttl_data = g.serialize(format="turtle")

headers = {"Content-Type": "text/turtle"}

try:
    response = requests.post(FUSEKI_DATA_URL, data=ttl_data.encode("utf-8"), headers=headers)
    if response.status_code in [200, 201, 204]:
        print("✅ Dữ liệu RDF đã được nạp thành công vào Fuseki!")
    else:
        print(f"❌ Lỗi khi nạp dữ liệu: {response.status_code}\n{response.text}")
except Exception as e:
    print("❌ Không thể kết nối Fuseki:", e)
