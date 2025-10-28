import numpy as np

data = np.load("data/pdf_embeddings.npz", allow_pickle=True)
texts = data["texts"]
metadata = data["metadata"]

print(f"Tổng số chunk: {len(texts)}")
print("Ví dụ 1 chunk:")
print(texts[0][:1000])  # xem 500 ký tự đầu tiên
print("Metadata:", metadata[0])
