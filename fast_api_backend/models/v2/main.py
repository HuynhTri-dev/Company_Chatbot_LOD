from fastapi import FastAPI, File, UploadFile, Query
from fastapi.middleware.cors import CORSMiddleware
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import json, os

app = FastAPI()

# Cấu hình CORS để frontend (localhost:5173 hoặc 3000) có thể gọi API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # có thể thay bằng "http://localhost:5173"
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_DIR = "data"
UPLOAD_DIR = "uploads"
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)

MODEL = SentenceTransformer("all-MiniLM-L6-v2")


# ================== 1️⃣ UPLOAD FILE ==================
@app.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
    """Nhận file JSONL chứa dữ liệu text để tạo embeddings"""
    save_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(save_path, "wb") as f:
        f.write(await file.read())

    # Đọc file JSONL
    texts, ids = [], []
    with open(save_path, "r", encoding="utf-8") as f:
        for line in f:
            item = json.loads(line)
            texts.append(item["text"])
            ids.append(item["id"])

    # Tạo embeddings
    embeddings = MODEL.encode(texts)
    np.savez(os.path.join(DATA_DIR, "opendata_embeddings.npz"), ids=ids, embeddings=embeddings)

    return {"message": "Upload & embedding thành công", "num_chunks": len(texts)}


# ================== 2️⃣ UPDATE / FINE-TUNE GIẢ ==================
@app.post("/update/")
async def update_file(file: UploadFile = File(...)):
    """Fake fine-tune: chỉ ghi nhận thêm embeddings mới vào file"""
    save_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(save_path, "wb") as f:
        f.write(await file.read())

    data = np.load(os.path.join(DATA_DIR, "opendata_embeddings.npz"), allow_pickle=True)
    ids = list(data["ids"])
    embeddings = list(data["embeddings"])

    with open(save_path, "r", encoding="utf-8") as f:
        for line in f:
            item = json.loads(line)
            ids.append(item["id"])
            embeddings.append(MODEL.encode(item["text"]))

    np.savez(os.path.join(DATA_DIR, "opendata_embeddings.npz"), ids=ids, embeddings=embeddings)
    return {"message": "Fine-tune (cập nhật) thành công", "num_chunks": len(ids)}


# ================== ASK / SEARCH ==================
@app.get("/ask/")
async def ask(q: str = Query(...), top_k: int = 5):
    """Nhận câu hỏi và trả về top_k kết quả tương tự"""
    data_file = os.path.join(DATA_DIR, "opendata_embeddings.npz")
    if not os.path.exists(data_file):
        return {"answer": "Chưa có dữ liệu embeddings. Vui lòng upload trước."}

    data = np.load(data_file, allow_pickle=True)
    ids = data["ids"]
    texts = data["texts"]
    embeddings = data["embeddings"]

    q_emb = MODEL.encode([q])
    sims = cosine_similarity(q_emb, embeddings)[0]
    top_idx = sims.argsort()[-top_k:][::-1]

    results = [
        {
            "id": str(ids[i]),
            "similarity": round(float(sims[i]), 3),
            "text": texts[i],
        }
        for i in top_idx
    ]

    answer = "\n\n".join([
        f"({i+1}) {r['text']}  [sim={r['similarity']}]"
        for i, r in enumerate(results)
    ])
    return {"answer": answer, "results": results}