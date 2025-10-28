import numpy as np
import requests
from services.question_service import analyze_question, fetch_company_info

def cosine_similarity(vec1, vec2):
    return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))

def query_wikidata(entity_label):
    query = f"""
    SELECT ?item ?itemLabel ?description WHERE {{
      ?item rdfs:label "{entity_label}"@en.
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
    }} LIMIT 5
    """
    r = requests.get("https://query.wikidata.org/sparql",
                     params={"query": query},
                     headers={"Accept": "application/sparql-results+json"})
    data = r.json()
    results = []
    for item in data["results"]["bindings"]:
        results.append({
            "label": item.get("itemLabel", {}).get("value"),
            "description": item.get("description", {}).get("value")
        })
    return results


def build_prompt(question: str, embeddings_model, chunk_vectors, metadata, similarity_threshold=0.6):
    query_vec = embeddings_model.encode(question)
    best_text, max_sim = "", 0.0

    if len(chunk_vectors) > 0:
        sims = [cosine_similarity(query_vec, c) for c in chunk_vectors]
        idx = int(np.argmax(sims))
        max_sim = sims[idx]
        best_text = metadata[idx].get("text_preview", "")

    context_parts = []

    if max_sim >= similarity_threshold and best_text:
        context_parts.append(best_text)
    else:
        is_related, company_name = analyze_question(question)
        company_info, _ = fetch_company_info(company_name) if is_related else (None, None)

        lod_text = ""
        # lod_results = query_wikidata(company_name or question)
        # for item in lod_results:
        #     label = item.get("label", "Unknown")
        #     desc = item.get("description", "")
        #     lod_text += f"{label}: {desc}\n"

        if company_info:
            context_parts.append(
                f"Company Information:\n"
                f"Name: {company_info.get('name', '')}\n"
                f"Type: {company_info.get('type', '')}\n"
                f"Address: {company_info.get('address', '')}\n"
                f"Business: {company_info.get('business', '')}\n"
                f"Established: {company_info.get('latestLegalRegistration', '')}"
            )
        if lod_text:
            context_parts.append(f"LOD supplement:\n{lod_text}")

    context = "\n\n".join(context_parts)
    return f"Refer to this knowledge: {context}\n\nUser Question: {question}\nAnswer:"
