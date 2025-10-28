import pandas as pd
from rdflib import Graph, Namespace, Literal, RDF, XSD, URIRef

# ===== Khai báo namespace =====
EX = Namespace("http://example.com/company#")

# ===== Đọc file Excel =====
df = pd.read_excel("../data_excel/DoanhNghiepHCM.xlsx")  # đổi tên nếu cần
df = df.head(11)  # lấy 11 dòng đầu (dòng 1 là tiêu đề)

# ===== Tạo graph RDF =====
g = Graph()
g.bind("ex", EX)

for _, row in df.iterrows():
    company_uri = URIRef(f"http://example.com/company/{row['IdCompany']}")
    g.add((company_uri, RDF.type, EX.Company))

    if not pd.isna(row["IdCompany"]):
        g.add((company_uri, EX.idCompany, Literal(str(row["IdCompany"]), datatype=XSD.string)))
    if not pd.isna(row["Name"]):
        g.add((company_uri, EX.name, Literal(row["Name"], datatype=XSD.string)))
    if not pd.isna(row["LatestLegalRegistration"]):
        g.add((company_uri, EX.latestLegalRegistration, Literal(str(row["LatestLegalRegistration"]), datatype=XSD.string)))
    if not pd.isna(row["Type"]):
        g.add((company_uri, EX.type, Literal(row["Type"], datatype=XSD.string)))
    if not pd.isna(row["Address"]):
        g.add((company_uri, EX.address, Literal(row["Address"], datatype=XSD.string)))
    if not pd.isna(row["Business"]):
        g.add((company_uri, EX.business, Literal(row["Business"], datatype=XSD.string)))

# ===== Xuất file RDF/Turtle =====
g.serialize(destination="companies_sample.ttl", format="turtle")
print("✅ Exported 10 companies → companies_sample.ttl")
