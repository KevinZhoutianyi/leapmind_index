from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
import requests
from typing import Optional
import asyncio
import openai

# Add crawl4ai imports
from crawl4ai.async_webcrawler import AsyncWebCrawler, CrawlerRunConfig

# Config
MEILI_URL = os.getenv('MEILI_URL', 'http://localhost:7700')
MEILI_INDEX = os.getenv('MEILI_INDEX', 'documents')
print(MEILI_INDEX)
app = FastAPI()
print('openaikey',os.getenv('OPENAI_API_KEY'))
@app.on_event("startup")
def on_startup():
    ensure_index_and_embedder()

class Document(BaseModel):
    id: int
    title: Optional[str] = None
    content: str
    ad: Optional[str] = None

class SearchRequest(BaseModel):
    query: str
    top_k: int = 5
    semantic_ratio: float = 1.0  # 1.0 = pure semantic, 0.0 = pure keyword, 0.5 = hybrid

class CrawlRequest(BaseModel):
    url: str

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
            "model": "text-embedding-3-small",  # Ensure this model name is correct for OpenAI API
            "apiKey": os.getenv('OPENAI_API_KEY'),  # This should be set in your environment variables
            "documentTemplate": "{{doc.content}}"  # Use `documentTemplate` instead of `inputTemplate`
        }
    }
    res=requests.patch(f"{MEILI_URL}/indexes/{MEILI_INDEX}/settings/embedders", json=embedder_conf)
    print('create embedder',res.text)

@app.post("/index")
def index_document(doc: Document):
    document = doc.dict()
    print("Sending to Meilisearch:", document)
    resp = requests.post(f"{MEILI_URL}/indexes/{MEILI_INDEX}/documents", json=[document])
    print("Meilisearch response:", resp.status_code, resp.text)
    if resp.status_code not in (200, 202):
        raise HTTPException(status_code=500, detail=f"Meilisearch error: {resp.text}")
    return {"result": "indexed", "id": doc.id}

@app.post("/search")
def search_documents(req: SearchRequest):
    print('search_documents',req)
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

@app.post("/documents/clear")
def clear_documents():
    """Clear all documents in the Meilisearch index. Use with caution!"""
    resp = requests.delete(f"{MEILI_URL}/indexes/{MEILI_INDEX}/documents")
    if resp.status_code not in (200, 202):
        raise HTTPException(status_code=500, detail=f"Meilisearch error: {resp.text}")
    return {"result": "index cleared"}

@app.post("/crawl_markdown")
async def crawl_markdown(req: CrawlRequest):
    """Crawl a website, summarize its content in ~500 words using GPT-4o, and return the summary."""
    try:
        async with AsyncWebCrawler() as crawler:
            result = await crawler.arun(url=req.url)
            if isinstance(result, list) and result:
                crawl_result = result[0]
            elif hasattr(result, 'markdown'):
                crawl_result = result
            else:
                raise HTTPException(status_code=500, detail="Crawl4ai did not return a valid result.")
            markdown = getattr(crawl_result, 'markdown', None)
            if not markdown:
                raise HTTPException(status_code=500, detail="No markdown content returned from crawl4ai.")

        # Detect if the content is mostly Chinese
        def is_mostly_chinese(text, threshold=0.3):
            chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
            return chinese_chars / max(1, len(text)) > threshold

        if is_mostly_chinese(markdown):
            prompt = (
                "你是一位资深的市场营销文案专家。请先根据内容或网址推断产品类型，并以'产品类型：<类型>'开头，然后将以下网站内容总结为约200字的中文广告文案，突出产品或服务的独特卖点、优势和吸引力，语言要生动有说服力，适合用于广告或市场推广。不要包含免责声明或与任务无关的说明，只输出高质量的中文广告文案。\n\n" + markdown[:12000]
            )
        else:
            prompt = (
                "You are an expert marketing copywriter. First, infer the product type from the website or content and start the summary with 'Product: <type>'. Then, summarize the following website content in about 200 words, creating a compelling and engaging summary suitable for use in advertisements or marketing materials. Highlight the unique selling points, benefits, and features that would attract potential customers. Make the summary persuasive, clear, and appealing, using energetic and positive language. Do not include disclaimers or meta commentary. Return only the ad-style summary in fluent, natural English.\n\n" + markdown[:12000]
            )

        # Summarize with OpenAI GPT-4o
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise HTTPException(status_code=500, detail="OPENAI_API_KEY not set in environment.")
        client = openai.OpenAI(api_key=api_key)
        
        response = await asyncio.to_thread(
            client.chat.completions.create,
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000,
            temperature=0.5,
        )
        summary = response.choices[0].message.content.strip()
        # Check for invalid summary
        if not summary or any(x in summary.lower() for x in ["i'm sorry", "i can\'t", "i cannot", "please provide", "cannot provide", "not able to", "unable to"]):
            raise HTTPException(status_code=500, detail="Failed to generate a valid summary for this website.")
        return {"summary": summary, "markdown": markdown}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Crawl4ai or OpenAI error: {str(e)}")

@app.get("/")
def root():
    return {"message": "Meilisearch + OpenAI embedder (auto-embedding) service ready."}