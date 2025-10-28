import requests

API_BASE = "https://opendata.hochiminhcity.gov.vn/api/action/datastore/search.json"

def query_company_by_name(resource_id, company_name, limit=10):
    """
    Truy vấn thông tin công ty theo tên.
    
    :param resource_id: chuỗi resource_id của bộ dữ liệu trên portal.
    :param company_name: tên công ty cần tìm.
    :param limit: số bản ghi tối đa trả về (mặc định 10).
    :return: list các bản ghi (dictionaries) hoặc None nếu lỗi.
    """
    params = {
        "resource_id": "d154b956-610a-43d9-a981-482a7481767f",
        "filters[TenDN]": "TMA Crops",
        "limit": 5
    }

    try:
        resp = requests.get(API_BASE, params=params, timeout=101000)
        resp.raise_for_status()
        data = resp.json()
        if not data.get("success"):
            print("API trả về không thành công:", data)
            return None
        records = data["result"]["records"]
        return records
    except Exception as e:
        print("Lỗi khi gọi API:", e)
        return None

# Ví dụ sử dụng
if __name__ == "__main__":
    res_id = "d154b956-610a-43d9-a981-482a7481767f" 
    name = "TMA"
    results = query_company_by_name(res_id, name, limit=3)
    if results:
        for rec in results:
            print(rec)
