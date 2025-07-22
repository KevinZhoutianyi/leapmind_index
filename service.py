from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
import requests
from typing import Optional

# Config
MEILI_URL = os.getenv('MEILI_URL', 'http://localhost:7700')
MEILI_INDEX = os.getenv('MEILI_INDEX', 'documents')

app = FastAPI()

class Document(BaseModel):
    id: int
    title: Optional[str] = None
    content: str
    ad: Optional[str] = None

class SearchRequest(BaseModel):
    query: str
    top_k: int = 5
    semantic_ratio: float = 1.0  # 1.0 = pure semantic, 0.0 = pure keyword, 0.5 = hybrid

# Helper: Ensure Meilisearch index and embedder exists
def ensure_index_and_embedder():
    # Enable vector store experimental feature
    print('enable vector store experimental feature')
    requests.patch(f"{MEILI_URL}/experimental-features/", json={"vectorStore": True})
    # Create index if not exists
    resp = requests.get(f"{MEILI_URL}/indexes/{MEILI_INDEX}")
    if resp.status_code == 404:
        requests.post(f"{MEILI_URL}/indexes", json={"uid": MEILI_INDEX, "primaryKey": "id"})
    # Configure OpenAI embedder if not exists
    embedder_conf = {
        "default": {
            "source": "openAi",
            "model": "text-embedding-ada-002",  # Ensure this model name is correct for OpenAI API
            "apiKey": os.getenv('OPENAI_API_KEY'),  # This should be set in your environment variables
            "documentTemplate": "{{doc.content}}"  # Use `documentTemplate` instead of `inputTemplate`
        }
    }
    res=requests.patch(f"{MEILI_URL}/indexes/{MEILI_INDEX}/settings/embedders", json=embedder_conf)
    print('create embedder',res.text)

@app.post("/index")
def index_document(doc: Document):
    ensure_index_and_embedder()
    document = doc.dict()
    resp = requests.post(f"{MEILI_URL}/indexes/{MEILI_INDEX}/documents", json=[document])
    if resp.status_code not in (200, 202):
        raise HTTPException(status_code=500, detail=f"Meilisearch error: {resp.text}")
    return {"result": "indexed", "id": doc.id}

@app.post("/search")
def search_documents(req: SearchRequest):
    print('search_documents',req)
    ensure_index_and_embedder()
    resp = requests.get(f"{MEILI_URL}/indexes/{MEILI_INDEX}/settings")
    payload = {
        "q": req.query,
        "limit": req.top_k,
        "hybrid": {
            "semanticRatio": req.semantic_ratio,
            "embedder": "default"
        }
    }
    resp = requests.post(f"{MEILI_URL}/indexes/{MEILI_INDEX}/search", json=payload)
    if resp.status_code != 200:
        raise HTTPException(status_code=500, detail=f"Meilisearch error: {resp.text}")
    hits = resp.json().get("hits", [])
    return hits

@app.get("/")
def root():
    return {"message": "Meilisearch + OpenAI embedder (auto-embedding) service ready."}