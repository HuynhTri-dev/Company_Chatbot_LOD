import requests

FUSEKI_QUERY_URL = "http://localhost:3030/companies/query"  # endpoint SPARQL

def get_company_info(company_name: str):
    """
    Lấy thông tin công ty từ Fuseki bằng SPARQL Query.
    Trả về dict: { name, type, address, business, dateStart }
    """
    query = f"""
    PREFIX ex: <http://example.com/company#>
    SELECT ?id ?name ?type ?address ?business ?latestLegal
    WHERE {{
        ?company a ex:Company ;
                 ex:name ?name ;
                 ex:idCompany ?id ;
                 ex:type ?type ;
                 ex:address ?address ;
                 ex:business ?business ;
                 ex:latestLegalRegistration ?latestLegal .
        FILTER(CONTAINS(LCASE(?name), LCASE("{company_name}")))
    }}
    LIMIT 1
    """

    headers = {"Accept": "application/sparql-results+json"}
    try:
        response = requests.get(FUSEKI_QUERY_URL, params={"query": query}, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()

        bindings = data.get("results", {}).get("bindings", [])
        if not bindings:
            return None, "Không có dữ liệu công ty"

        row = bindings[0]
        company_info = {
            "name": row.get("name", {}).get("value", ""),
            "type": row.get("type", {}).get("value", ""),
            "address": row.get("address", {}).get("value", ""),
            "business": row.get("business", {}).get("value", ""),
            "dateStart": row.get("dateStart", {}).get("value", "")
        }
        return company_info, None
    except Exception as e:
        return None, f"Lỗi khi truy vấn Fuseki: {e}"
