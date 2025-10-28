# generate_embeddings.py
# Usage:
#   python generate_embeddings.py --input data/opendata_training.jsonl --out data/opendata_embeddings.npz

import argparse
import json
import numpy as np
from tqdm import tqdm
from sentence_transformers import SentenceTransformer

def main(args):
    model = SentenceTransformer("all-MiniLM-L6-v2")
    texts, ids = [], []
    
    with open(args.input, "r", encoding="utf-8") as f:
        for line in f:
            item = json.loads(line)
            texts.append(item["text"])
            ids.append(item["id"])
    
    embeddings = model.encode(texts, show_progress_bar=True, convert_to_numpy=True)
    np.savez(args.out, ids=ids, texts=texts, embeddings=embeddings)
    print(f"Saved embeddings: {args.out}, shape={embeddings.shape}")

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True)
    p.add_argument("--out", required=True)
    args = p.parse_args()
    main(args)
