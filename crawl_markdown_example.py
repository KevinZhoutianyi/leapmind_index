import sys
import requests

def main():
    if len(sys.argv) < 2:
        print(f"Usage: python {sys.argv[0]} <url>")
        sys.exit(1)
    url = sys.argv[1]
    api_url = "http://localhost:8000/crawl_markdown"
    try:
        resp = requests.post(api_url, json={"url": url}, timeout=120)
        if resp.status_code == 200:
            data = resp.json()
            summary = data.get("summary")
            markdown = data.get("markdown")
            if summary:
                print("--- SUMMARY ---")
                print(summary)
            else:
                print("No summary returned.")
            if markdown:
                print("\n--- WEBSITE CONTENT (MARKDOWN) ---")
                print(markdown[:50])
            else:
                print("No website content (markdown) returned.")
        else:
            print(f"Error: {resp.status_code} {resp.text}")
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    main() 