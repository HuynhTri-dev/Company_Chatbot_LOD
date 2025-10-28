import re
import requests
GPT_OSS_LOCAL_URL = "http://localhost:11434/api/generate"

def is_company_question(question: str) -> bool:
    q = question.lower().strip()
    company_keywords = [
        r"\bcông ty\b", r"\bdoanh nghiệp\b", r"\btập đoàn\b",
        r"\bfpt\b", r"\bvng\b", r"\btma\b", r"\bvinamilk\b", r"\bvin\b"
    ]
    # Các cụm ngữ pháp phổ biến
    patterns = [
        r"\b(là|thuộc|có|ở|đặt|trụ sở)\b.*(công ty|tập đoàn|doanh nghiệp)",
        r"(công ty|tập đoàn|doanh nghiệp)\b",
    ]
    if any(re.search(p, q) for p in company_keywords + patterns):
        return True
    return False

def extract_company_name_ai(question: str) -> str | None:
    payload = {
        "prompt": f"Trích xuất tên công ty (nếu có) từ câu hỏi sau: '{question}'. Nếu không có thì trả về 'None'.",
        "max_tokens": 32,
        "model": "gpt-oss:120b-cloud",
        "stream": False
    }
    try:
        res = requests.post(GPT_OSS_LOCAL_URL, json=payload, timeout=15)
        res.raise_for_status()
        text = res.json().get("response", "").strip()
        if text.lower() == "none" or not text:
            return None
        return text
    except Exception as e:
        print(f"[ERROR] Lỗi khi gọi GPT-OSS để trích xuất tên công ty: {e}", flush=True)
        return None
