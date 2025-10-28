from fastapi import FastAPI, Query, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import numpy as np
import json
import requests
import time

from sentence_transformers import SentenceTransformer
from services.pdf_service import upload_embeddings_pdf
from services.context_builder import build_prompt

# ============ Setup ============
app = FastAPI(title="Company Knowledge Chatbot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

embeddings_model = SentenceTransformer("all-MiniLM-L6-v2")
data = np.load("data/pdf_embeddings.npz", allow_pickle=True)
chunk_vectors = data["embeddings"]
metadata = data["metadata"]

GPT_OSS_LOCAL_URL = "http://localhost:11434/api/generate"

# ============ Routes ============

def stream_gpt_response(prompt: str):
    payload = {"prompt": prompt, "max_tokens": 512, "model": "gpt-oss:120b-cloud", "stream": True}
    try:
        with requests.post(GPT_OSS_LOCAL_URL, json=payload, stream=True, timeout=300) as r:
            r.raise_for_status()
            for line in r.iter_lines():
                if line:
                    try:
                        token = json.loads(line.decode("utf-8")).get("response", "")
                        if token:
                            yield f"data:{json.dumps({'token': token})}\n\n"
                    except json.JSONDecodeError:
                        continue
                time.sleep(0.005)
    except Exception as e:
        yield f"data:{json.dumps({'token': f'[Lỗi GPT-OSS]: {e}'})}\n\n"


@app.get("/ask_stream")
def ask_stream(question: str = Query(...)):
    prompt = build_prompt(question, embeddings_model, chunk_vectors, metadata, 0.6)
    print("Prompt", prompt)
    return StreamingResponse(stream_gpt_response(prompt), media_type="text/event-stream")

@app.post("/upload_pdf")
async def upload_pdf(file: UploadFile = File(...)):
    return await upload_embeddings_pdf(file)


