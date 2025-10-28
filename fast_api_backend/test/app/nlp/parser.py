# Đây là base NLP parser (mẫu)
def parse_question(question: str) -> str:
    """
    Chuyển câu hỏi NL sang SPARQL query.
    Với MVP, chỉ trả về query mẫu hoặc dùng regex.
    """
    # TODO: tích hợp LLM / Rule-based mapping
    return """
    SELECT ?s ?p ?o
    WHERE {
        ?s ?p ?o .
    } LIMIT 5
    """
