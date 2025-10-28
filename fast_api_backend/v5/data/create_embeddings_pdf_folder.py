import os
import re
import numpy as np
from PyPDF2 import PdfReader
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

# =========================== Cấu hình mặc định ===========================
DEFAULT_PDF_DIR = "data_pdf"
DEFAULT_OUT_FILE = "pdf_embeddings.npz"
DEFAULT_MODEL = "all-MiniLM-L6-v2"


def extract_text_from_pdf(file_path):
    reader = PdfReader(file_path)
    text = ""
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"
    return text


def split_into_sections(text):
    """
    Tách text thành các section theo tiêu đề hoặc mục lớn.
    Heuristic: dòng bắt đầu bằng số, hoặc từ viết hoa, hoặc chứa từ "Mục", "Điều", "Chương", "Phần", "Section".
    """
    lines = text.splitlines()
    sections = []
    current_section = ""
    current_title = "Untitled"

    title_pattern = re.compile(r"^(Mục|Điều|Chương|Phần|Section|\d+[\.\)]|[A-Z\s]{4,})")

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # Nếu dòng có vẻ là tiêu đề mới
        if title_pattern.match(stripped):
            if current_section:
                sections.append({"title": current_title, "content": current_section.strip()})
            current_title = stripped
            current_section = ""
        else:
            current_section += stripped + " "

    if current_section:
        sections.append({"title": current_title, "content": current_section.strip()})

    return sections


def main():
    pdf_dir = DEFAULT_PDF_DIR
    out_path = DEFAULT_OUT_FILE
    model_name = DEFAULT_MODEL

    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    pdf_files = [f for f in os.listdir(pdf_dir) if f.lower().endswith(".pdf")]
    if not pdf_files:
        print(f"[ERROR] Không tìm thấy PDF trong thư mục '{pdf_dir}'")
        return

    all_texts = []
    metadata = []

    for pdf_file in pdf_files:
        pdf_path = os.path.join(pdf_dir, pdf_file)
        text = extract_text_from_pdf(pdf_path)
        sections = split_into_sections(text)

        for idx, sec in enumerate(sections):
            combined_text = f"{sec['title']}\n{sec['content']}"
            all_texts.append(combined_text)
            metadata.append({
                "source": pdf_file,
                "section_id": idx,
                "section_title": sec["title"],
                "text_preview": sec["content"][:200]
            })

    print(f"\n✅ Tổng cộng {len(all_texts)} mục được trích xuất từ {len(pdf_files)} PDF.")

    model = SentenceTransformer(model_name)
    embeddings = model.encode(all_texts, show_progress_bar=True, convert_to_numpy=True)

    np.savez_compressed(out_path,
                        embeddings=embeddings,
                        metadata=np.array(metadata, dtype=object),
                        texts=np.array(all_texts, dtype=object))



if __name__ == "__main__":
    main()
