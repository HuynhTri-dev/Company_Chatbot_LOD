# wikidata_mapper.py
# Usage: python wikidata_mapper.py --clean data/opendata_hcm_clean.csv --out data/opendata_hcm_mapped.csv
# This script queries Wikidata; requires internet.
import argparse
import pandas as pd
import requests
import time
from rapidfuzz import fuzz, process

WIKIDATA_SPARQL = "https://query.wikidata.org/sparql"
WIKIDATA_SEARCH_API = "https://www.wikidata.org/w/api.php"

# HEADERS = {"User-Agent": "OmniMerMapper/0.1 (your_email@example.com)"}

def query_by_literal_value(literal_value, limit=10):
    # Generic SPARQL: look for any statement whose value string equals provided literal
    q = f"""
    SELECT ?item ?itemLabel ?p ?val WHERE {{
      ?item ?p ?val .
      FILTER(str(?val) = "{literal_value}")
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "vi,en". }}
    }}
    LIMIT {limit}
    """
    r = requests.get(WIKIDATA_SPARQL, params={"query": q, "format": "json"}, timeout=30)
    r.raise_for_status()
    return r.json().get("results", {}).get("bindings", [])

def search_by_label(label, limit=10):
    # Use wikidata search API (fulltext)
    params = {"action":"wbsearchentities","format":"json","language":"vi","search":label,"limit":limit}
    r = requests.get(WIKIDATA_SEARCH_API, params=params, headers=HEADERS, timeout=20)
    r.raise_for_status()
    return r.json().get("search", [])

def get_entity_claims(qid):
    # fetch basic claims to check country (P17) and instance of (P31)
    params = {"action":"wbgetentities","ids": qid, "format":"json", "props":"claims|labels"}
    r = requests.get(WIKIDATA_SEARCH_API, params=params, headers=HEADERS, timeout=20)
    r.raise_for_status()
    return r.json().get("entities", {}).get(qid, {})

def is_vietnam_company(entity):
    # check P17 (country) == Q881 and P31 instance-of contains company classes
    claims = entity.get("claims", {})
    # quick country check
    if "P17" in claims:
        for c in claims["P17"]:
            mainsnak = c.get("mainsnak", {})
            datavalue = mainsnak.get("datavalue")
            if datavalue and datavalue.get("value", {}).get("id") == "Q881":
                return True
    return False

def map_row(row):
    tax = str(row.get("tax_id","")).strip()
    name = str(row.get("company_name_norm","")).strip()
    result = {"tax_id":tax, "company_name":name, "wikidata_qid": "", "match_type":"", "match_score":0, "wikidata_label":""}
    # 1) try literal search by tax id
    if tax:
        try:
            bindings = query_by_literal_value(tax, limit=20)
            for b in bindings:
                qid = b["item"]["value"].split("/")[-1]
                # quick entity check for Vietnam/company
                ent = get_entity_claims(qid)
                if is_vietnam_company(ent):
                    result.update({"wikidata_qid": qid, "match_type":"tax_literal", "match_score":100, "wikidata_label": ent.get("labels",{}).get("vi", {}).get("value","")})
                    return result
            # if any binding found but not country-match, keep as candidate (take first)
            if bindings:
                qid = bindings[0]["item"]["value"].split("/")[-1]
                ent = get_entity_claims(qid)
                result.update({"wikidata_qid": qid, "match_type":"tax_literal_nonVN", "match_score":80, "wikidata_label": ent.get("labels",{}).get("vi",{}).get("value","")})
                return result
        except Exception as e:
            print("SPARQL tax lookup error:", e)
            time.sleep(1)

    # 2) fallback: search by label using API
    if name:
        try:
            candidates = search_by_label(name, limit=10)
            # rank by fuzzy score between candidate label and name; prefer that have P17=Q881
            best = None
            best_score = 0
            for c in candidates:
                qid = c.get("id")
                label = c.get("label","")
                score = fuzz.token_sort_ratio(name, label)
                if score < 60:  # threshold
                    continue
                ent = get_entity_claims(qid)
                v = is_vietnam_company(ent)
                bonus = 20 if v else 0
                final_score = score + bonus
                if final_score > best_score:
                    best_score = final_score
                    best = (qid, label, v, final_score)
            if best:
                result.update({"wikidata_qid": best[0], "match_type":"label_fuzzy", "match_score": best[3], "wikidata_label": best[1]})
                return result
        except Exception as e:
            print("Label search error:", e)
            time.sleep(1)

    # no match
    return result

def main(args):
    df = pd.read_csv(args.clean, encoding="utf-8-sig")
    outputs = []
    total = len(df)
    for i,row in df.iterrows():
        out = map_row(row)
        out_row = {**row.to_dict(), **out}
        outputs.append(out_row)
        if (i+1) % 50 == 0:
            print(f"Processed {i+1}/{total}")
        # rate limit (be polite)
        time.sleep(0.1)
    df_out = pd.DataFrame(outputs)
    df_out.to_csv(args.out, index=False, encoding="utf-8-sig")
    print("Saved mapped file:", args.out)

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--clean", required=True, help="clean CSV from ingest step")
    p.add_argument("--out", required=True)
    args = p.parse_args()
    main(args)
