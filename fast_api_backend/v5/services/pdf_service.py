import os
import time
import numpy as np
import shutil
from fastapi import UploadFile
from sentence_transformers import SentenceTransformer
from data.create_embeddings_pdf_folder import extract_text_from_pdf, split_into_sections

# ------------------ Setup đường dẫn ------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "../data")
PDF_DIR = os.path.join(BASE_DIR, "../data_pdf")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(PDF_DIR, exist_ok=True)

EMBED_FILE = os.path.normpath(os.path.join(DATA_DIR, "pdf_embeddings.npz"))
MODEL_NAME = "all-MiniLM-L6-v2"

embeddings_model = SentenceTransformer(MODEL_NAME)

# ------------------ Upload và xử lý ------------------
async def upload_embeddings_pdf(file: UploadFile):
    try:
        print("[DEBUG] Start upload:", file.filename)
        print("[DEBUG] BASE_DIR:", BASE_DIR)
        print("[DEBUG] DATA_DIR:", DATA_DIR)
        print("[DEBUG] PDF_DIR:", PDF_DIR)
        print("[DEBUG] EMBED_FILE:", EMBED_FILE)

        # --- Lưu file tạm thời ---
        timestamp = int(time.time())
        temp_path = os.path.join(PDF_DIR, f"temp_{timestamp}_{file.filename}")
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        print("[INFO] File đã lưu tạm tại:", temp_path)

        # --- Đọc văn bản từ PDF ---
        text = extract_text_from_pdf(temp_path)
        print("[DEBUG] Độ dài text:", len(text))
        print("[DEBUG] Mẫu nội dung:", text[:300])

        if not text.strip():
            os.remove(temp_path)
            print("[WARN] PDF không có nội dung văn bản (có thể là ảnh scan).")
            return {"error": "PDF không có nội dung văn bản."}

        # --- Cắt nhỏ theo section ---
        sections = split_into_sections(text)
        all_texts, new_metadata = [], []
        for idx, sec in enumerate(sections):
            combined = f"{sec['title']}\n{sec['content']}"
            all_texts.append(combined)
            new_metadata.append({
                "source": file.filename,
                "section_id": idx,
                "section_title": sec["title"],
                "text_preview": sec["content"][:200],
            })

        print(f"[INFO] Tổng số section trích được: {len(all_texts)}")

        # --- Tạo embedding ---
        new_embeds = embeddings_model.encode(
            all_texts, show_progress_bar=True, convert_to_numpy=True
        )
        print("[INFO] Embeddings shape:", new_embeds.shape)

        # --- Gộp dữ liệu cũ nếu có ---
        if os.path.exists(EMBED_FILE):
            existing = np.load(EMBED_FILE, allow_pickle=True)
            old_embeddings = existing["embeddings"]
            old_metadata = existing["metadata"]
            old_texts = existing["texts"]
            print("[INFO] File embeddings cũ đã được tải:", len(old_metadata))

            merged_embeddings = np.concatenate([old_embeddings, new_embeds])
            merged_metadata = np.concatenate([old_metadata, np.array(new_metadata, dtype=object)])
            merged_texts = np.concatenate([old_texts, np.array(all_texts, dtype=object)])
        else:
            merged_embeddings = new_embeds
            merged_metadata = np.array(new_metadata, dtype=object)
            merged_texts = np.array(all_texts, dtype=object)

        # --- Lưu file embeddings ---
        np.savez_compressed(
            EMBED_FILE,
            embeddings=merged_embeddings,
            metadata=merged_metadata,
            texts=merged_texts
        )

        # --- Kiểm tra file thật sự được tạo ---
        if os.path.exists(EMBED_FILE):
            print(f"[SUCCESS] File embeddings đã được lưu: {EMBED_FILE}")
            size = os.path.getsize(EMBED_FILE) / 1024
            print(f"[INFO] Kích thước file: {size:.2f} KB")
        else:
            print("[ERROR] Không thấy file embeddings được lưu!")

        return {
            "message": "Upload và cập nhật embeddings thành công.",
            "pdf_path": temp_path,
            "new_sections": len(all_texts),
            "total_after_update": len(merged_metadata)
        }

    except Exception as e:
        print("[ERROR]", str(e))
        return {"error": str(e)}
