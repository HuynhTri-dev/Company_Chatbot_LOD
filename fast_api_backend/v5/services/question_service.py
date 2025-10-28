from services.extract_question import is_company_question, extract_company_name_ai
from services.search_company_ontology import get_company_info

def analyze_question(question: str):
    """Kiểm tra câu hỏi có liên quan công ty và trích tên"""
    is_related = is_company_question(question)
    company_name = extract_company_name_ai(question) if is_related else None
    return is_related, company_name


def fetch_company_info(company_name: str):
    """Truy vấn thông tin công ty từ Fuseki"""
    if not company_name:
        return None, None
    company_info, error = get_company_info(company_name)
    return company_info, error
