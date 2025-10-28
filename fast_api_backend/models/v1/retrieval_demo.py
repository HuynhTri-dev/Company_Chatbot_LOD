# retrieval_demo.py
# Usage:
#   python retrieval_demo.py --emb data/embeddings_index.npz --query "công ty nghiên cứu AI quận 9" --topk 5
import argparse
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer

def load_index(path):
    data = np.load(path, allow_pickle=True)
    embeddings = data['embeddings']
    metadata = data['metadata']
    return embeddings, metadata

def embed_query(query, model_name="all-MiniLM-L6-v2"):
    model = SentenceTransformer(model_name)
    v = model.encode([query], convert_to_numpy=True)
    return v

def main(args):
    embeddings, metadata = load_index(args.emb)
    qvec = embed_query(args.query)
    sims = cosine_similarity(qvec, embeddings)[0]
    idxs = sims.argsort()[::-1][:args.topk]
    for rank, i in enumerate(idxs, start=1):
        meta = metadata[i].item() if hasattr(metadata[i], 'item') else metadata[i]
        print(f"Rank {rank} (score={sims[i]:.4f}): {meta.get('company_name')} | tax:{meta.get('tax_id')} | qid:{meta.get('wikidata_qid')}")
        print("  Address:", meta.get("address"))
        print("  Business line:", meta.get("business_line"))
        print()

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--emb", required=True)
    p.add_argument("--query", required=True)
    p.add_argument("--topk", type=int, default=5)
    args = p.parse_args()
    main(args)
