# Leapmind Index Service

This service provides a simple API to index and search markdown (or any text) content using Meilisearch with OpenAI-powered semantic search.

## Requirements
- Python 3.7+
- Meilisearch v1.6+ running (with vector store enabled and master key set)
- OpenAI API key (for Meilisearch to generate embeddings)

## Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Start Meilisearch with a master key:**
   ```bash
   ./meilisearch --http-addr '0.0.0.0:7700'
   ```

3. **Set your OpenAI API key in the environment:**
   ```bash
   export OPENAI_API_KEY="sk-..."  # your real OpenAI key
   ```

4. **Run the API service:**
   ```bash
   uvicorn service:app --reload --host 0.0.0.0 --port 8000
   ```

## How it Works

- **/index**: Adds a document (id, title, content, ad) to Meilisearch. The FastAPI service configures Meilisearch to use the OpenAI embedder. Meilisearch will automatically call OpenAI to generate an embedding for the content and store it in its vector store.
- **/search**: Accepts a query and performs a hybrid (semantic + keyword) search using Meilisearch's built-in vector search. You can control the balance between semantic and keyword search with the `semantic_ratio` parameter.
- **No local database is used**: All data and embeddings are stored in Meilisearch.

## API Usage

### Index Document
- **POST** `/index`
- **Body:**
  ```json
  {
    "id": 1,
    "title": "AI-Powered Search Guide",
    "content": "This guide explains how to use AI-powered search with Meilisearch.",
    "ad": "Try our AI search!"
  }
  ```
- **Response:**
  ```json
  { "result": "indexed", "id": 1 }
  ```

### Search Document
- **POST** `/search`
- **Body:**
  ```json
  {
    "query": "How to use AI search?",
    "top_k": 3,
    "semantic_ratio": 1.0
  }
  ```
- **Response:**
  ```json
  [
    { "id": 1, "title": "AI-Powered Search Guide", "content": "...", "ad": "Try our AI search!", ... }
  ]
  ```