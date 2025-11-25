import asyncio
import aiohttp
import json
import os
import time
from bs4 import BeautifulSoup

BASE_URL = "https://www.partselect.com"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json,text/html,*/*"
}

def log(msg):
    print(f"[SCRAPER] {msg}")

async def fetch(session, url):
    async with session.get(url, headers=HEADERS) as resp:
        if resp.status != 200:
            log(f"❌ {resp.status} → {url}")
            return None
        if "application/json" in resp.headers.get("Content-Type", ""):
            return await resp.json()
        return await resp.text()

async def scrape_model_parts(session, model_number, category):
    """Call hidden API endpoint → JSON list of parts."""
    api_url = f"https://www.partselect.com/api/ModelParts?modelNumber={model_number}"
    data = await fetch(session, api_url)
    if not data:
        return []

    results = []
    for p in data:
        results.append({
            "category": category,
            "model": model_number,
            "part_number": p.get("partNumber"),
            "manufacturer_number": p.get("manufacturerNumber"),
            "name": p.get("name"),
            "price": p.get("price"),
            "image": p.get("image"),
            "summary": p.get("summary"),
            "symptoms": p.get("symptoms", []),
            "installation_texts": p.get("installation", []),
            "videos": p.get("videos", [])
        })

    log(f"  → {len(results)} parts for {model_number}")
    return results

async def main():
    start = time.time()
    out = []

    models = [
        "HDA3400G02BB",
        "WDT730PAHZ0",
        "FGHD2465NF1A",
        "LDF6920ST",
        # add 30–40 more popular models
    ]

    async with aiohttp.ClientSession() as session:
        for m in models:
            parts = await scrape_model_parts(session, m, category="dishwasher")
            out.extend(parts)

    # save dataset
    out_path = os.path.join(os.path.dirname(__file__), "..", "data", "parts.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    with open(out_path, "w") as f:
        json.dump(out, f, indent=2)

    log(f"✅ Saved {len(out)} parts → {out_path}")
    log(f"⏱ Done in {time.time() - start:.1f} seconds")

if __name__ == "__main__":
    asyncio.run(main())

