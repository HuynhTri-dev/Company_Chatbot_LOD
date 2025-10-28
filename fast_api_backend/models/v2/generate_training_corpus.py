# generate_training_corpus.py
# Usage:
#   python generate_training_corpus.py --input data/opendata_hcm_clean.csv --out data/opendata_training.jsonl

import argparse
import pandas as pd
import json

def make_text(row):
    parts = []
    if row.company_name_norm:
        parts.append(f"Tên doanh nghiệp: {row.company_name_norm}.")
    if row.company_type:
        parts.append(f"Loại hình: {row.company_type}.")
    if row.business_line:
        parts.append(f"Lĩnh vực hoạt động: {row.business_line}.")
    if row.address_norm:
        parts.append(f"Địa chỉ: {row.address_norm}.")
    if row.registration_date_norm:
        parts.append(f"Ngày đăng ký: {row.registration_date_norm}.")
    return " ".join(parts)

def main(args):
    df = pd.read_csv(args.input)
    df["text"] = df.apply(make_text, axis=1)
    
    with open(args.out, "w", encoding="utf-8") as f:
        for _, row in df.iterrows():
            record = {
                "id": row.tax_id,
                "text": row.text,
                "metadata": {
                    "company_name": row.company_name_norm,
                    "address": row.address_norm,
                    "industry": row.business_line
                }
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(f"Saved training corpus: {args.out} ({len(df)} records)")

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True)
    p.add_argument("--out", required=True)
    args = p.parse_args()
    main(args)
