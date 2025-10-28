# ingest_opendata_hcm.py
# Usage:
#   python ingest_opendata_hcm.py --input data/raw_opendata.xlsx --out data/opendata_hcm_clean.csv --sample 1000
#
import argparse
import pandas as pd
import re
from datetime import datetime

# normalization helpers
def normalize_company_name(name: str) -> str:
    if pd.isna(name):
        return ""
    s = str(name).strip()
    # common abbreviations -> canonical
    s = re.sub(r'\bCTY\b', 'Công ty', s, flags=re.IGNORECASE)
    s = re.sub(r'\bCP\b', 'Cổ phần', s, flags=re.IGNORECASE)
    s = re.sub(r'\bTNHH\b', 'Trách nhiệm hữu hạn', s, flags=re.IGNORECASE)
    s = s.replace('&', 'và')
    s = " ".join(s.split())
    return s

def normalize_address(addr: str) -> str:
    if pd.isna(addr):
        return ""
    s = str(addr).strip()
    s = s.replace("TP. HCM", "TP. Hồ Chí Minh")
    s = s.replace("TP HCM", "TP. Hồ Chí Minh")
    s = re.sub(r'\s+', ' ', s)
    return s

def parse_date(d):
    # try known formats, otherwise return original string
    if pd.isna(d): return ""
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(str(d), fmt).date().isoformat()
        except:
            pass
    return str(d)

def process_df(df: pd.DataFrame):
    # adapt column names (robust to different headers)
    col_map = {}
    lc = {c.lower(): c for c in df.columns}
    # common column keys in your sample: MaSoDN, TenDN, NgayCap, LoaiDN, DiaChi, NganhNghe
    for key in ["masodn","maso","mst","tax","masothue"]:
        if key in lc: col_map[lc[key]] = "tax_id"
    for key in ["tendn","company","name"]:
        if key in lc: col_map[lc[key]] = "company_name"
    for key in ["ngaycap","ngaydangky","registration_date","date"]:
        if key in lc: col_map[lc[key]] = "registration_date"
    for key in ["loaidn","loai"]:
        if key in lc: col_map[lc[key]] = "company_type"
    for key in ["diachi","address","addr"]:
        if key in lc: col_map[lc[key]] = "address"
    for key in ["nganhnghe","industry","business_line"]:
        if key in lc: col_map[lc[key]] = "business_line"

    df = df.rename(columns=col_map)
    # ensure basic columns exist
    for c in ["tax_id","company_name","registration_date","company_type","address","business_line"]:
        if c not in df.columns:
            df[c] = ""

    df["company_name_norm"] = df["company_name"].apply(normalize_company_name)
    df["address_norm"] = df["address"].apply(normalize_address)
    df["registration_date_norm"] = df["registration_date"].apply(parse_date)
    df["canonical_key"] = (df["company_name_norm"].fillna("") + " | " + df["tax_id"].astype(str).fillna("")).str.lower()
    return df[["tax_id","company_name","company_name_norm","registration_date","registration_date_norm","company_type","address","address_norm","business_line","canonical_key"]]

def main(args):
    # read excel - for big files use read_excel with chunksize via engine openpyxl is not streamable;
    # if very large, recommend converting to CSV externally and then use pandas.read_csv with chunksize.
    print("Reading input:", args.input)
    df = pd.read_excel(args.input, engine="openpyxl")
    print("Rows read:", len(df))
    df_clean = process_df(df)
    # optionally save a smaller sample for development
    if args.sample and args.sample > 0:
        df_clean_sample = df_clean.head(args.sample)
        df_clean_sample.to_csv(args.out.replace(".csv","_sample.csv"), index=False, encoding="utf-8-sig")
        print("Saved sample:", args.out.replace(".csv","_sample.csv"))
    df_clean.to_csv(args.out, index=False, encoding="utf-8-sig")
    print("Saved clean CSV:", args.out)

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--sample", type=int, default=1000, help="save a small sample for dev")
    args = p.parse_args()
    main(args)
