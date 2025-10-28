# query_demo.py
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

def search(query, embeddings_file, top_k=5):
    data = np.load(embeddings_file, allow_pickle=True)
    ids = data["ids"]
    embeddings = data["embeddings"]
    model = SentenceTransformer("all-MiniLM-L6-v2")
    q_emb = model.encode([query])
    sims = cosine_similarity(q_emb, embeddings)[0]
    top_idx = sims.argsort()[-top_k:][::-1]
    for i in top_idx:
        print(f"{ids[i]}: similarity={sims[i]:.3f}")

if __name__ == "__main__":
    search("công ty sản xuất phần mềm ở quận 1", "data/opendata_embeddings.npz")
