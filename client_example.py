import requests
import time
import csv
import random

# === Batch crawl, summarize, index, and search from targetcustomer.csv ===
print("\n=== Batch crawl, summarize, index, and search from targetcustomer.csv ===\n")

csv_path = "targetcustomer.csv"
websites = []
with open(csv_path, newline='', encoding='utf-8') as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        url = row['独立站网址'].strip()
        if url and url.startswith('http'):
            websites.append(url)

# User input for number of sites to crawl+index and crawl+search
try:
    n_index = int(input("How many websites to crawl and index? (default 5): ") or 5)
except Exception:
    n_index = 5
try:
    n_search = int(input("How many websites to crawl and search? (default 2): ") or 2)
except Exception:
    n_search = 2

if n_index + n_search > len(websites):
    print(f"Not enough websites in CSV, using max available: {len(websites)}")
    n_index = min(n_index, len(websites))
    n_search = min(n_search, len(websites) - n_index)

# Randomize order
random.shuffle(websites)

# 1. Crawl, summarize, and index
for idx, url in enumerate(websites[:n_index]):
    print(f"\nCrawling and summarizing: {url}")
    try:
        resp = requests.post("http://localhost:8000/crawl_markdown", json={"url": url}, timeout=180)
        if resp.status_code == 200:
            summary = resp.json().get("summary")
            print(f"Summary: {summary[:200]}...")
            # Index to Meilisearch
            doc = {
                "id": 2000 + idx,
                "title": url,
                "content": summary
            }
            idx_resp = requests.post("http://localhost:8000/index", json=doc)
            print("Index response:", idx_resp.json())
            time.sleep(1)
        else:
            print(f"Failed to crawl {url}: {resp.status_code} {resp.text}")
    except Exception as e:
        print(f"Exception for {url}: {e}")

# 2. Crawl, summarize, and search
for idx, url in enumerate(websites[n_index:n_index+n_search]):
    print(f"\nCrawling and searching for: {url}")
    try:
        resp = requests.post("http://localhost:8000/crawl_markdown", json={"url": url}, timeout=180)
        if resp.status_code == 200:
            summary = resp.json().get("summary")
            print(f"Summary: {summary[:200]}...")
            # Search in Meilisearch using the summary as query (embedding search)
            search_payload = {
                "query": summary,
                "top_k": 3,
                "semantic_ratio": 1.0
            }
            search_resp = requests.post("http://localhost:8000/search", json=search_payload)
            if search_resp.status_code == 200:
                hits = search_resp.json()
                print("Search results:")
                for i, hit in enumerate(hits, 1):
                    print(f"[{i}] id={hit.get('id')} | url={hit.get('title')}\n"
                          f"    semanticScore: {hit.get('_semanticScore')}\n"
                          f"    内容摘要：{hit.get('content','')[:80]}...\n")
            else:
                print(f"Search failed: {search_resp.status_code} {search_resp.text}")
        else:
            print(f"Failed to crawl {url}: {resp.status_code} {resp.text}")
    except Exception as e:
        print(f"Exception for {url}: {e}")
