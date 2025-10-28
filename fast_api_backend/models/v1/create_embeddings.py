# create_embeddings.py
# Usage:
#   python create_embeddings.py --mapped data/opendata_hcm_mapped.csv --out data/embeddings_index.npz --backend sentence_transformers
#
import argparse
import pandas as pd
import numpy as np
from datetime import datetime

def build_text(row):
    parts = []
    if row.get("company_name"): parts.append(row.get("company_name"))
    if row.get("business_line"): parts.append(row.get("business_line"))
    if row.get("address"): parts.append(row.get("address"))
    return " | ".join(parts)

def main(args):
    df = pd.read_csv(args.mapped, encoding="utf-8-sig")
    df["doc_text"] = df.apply(build_text, axis=1)
    texts = df["doc_text"].fillna("").tolist()

    if args.backend == "sentence_transformers":
        from sentence_transformers import SentenceTransformer
        model_name = args.model or "all-MiniLM-L6-v2"
        model = SentenceTransformer(model_name)
        embeddings = model.encode(texts, show_progress_bar=True, convert_to_numpy=True)
    else:
        # fallback: TF-IDF dense vectors
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.preprocessing import normalize
        vec = TfidfVectorizer(ngram_range=(1,2), max_features=1024)
        X = vec.fit_transform(texts)
        embeddings = normalize(X.toarray(), norm='l2', axis=1)

    # save
    metadata = df.to_dict(orient="records")
    out_path = args.out
    np.savez_compressed(out_path, embeddings=embeddings, metadata=np.array(metadata, dtype=object))
    print("Saved embeddings:", out_path)

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--mapped", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--backend", choices=["sentence_transformers","tfidf"], default="sentence_transformers")
    p.add_argument("--model", default=None)
    args = p.parse_args()
    main(args)
