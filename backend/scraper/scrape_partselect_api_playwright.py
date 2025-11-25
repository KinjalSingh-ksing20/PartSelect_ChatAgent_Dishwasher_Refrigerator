# scraper/scrape_partselect_hybrid_api.py

from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import json
import os
import time
import random

BASE_URL = "https://www.partselect.com"
MAX_MODELS_PER_BRAND = 5
MAX_PARTS_PER_MODEL = 9999       # API gives all parts at once
NAV_TIMEOUT = 45000

def log(msg):
    print(f"[SCRAPER] {msg}")

def clean(x):
    if not x:
        return None
    return " ".join(x.split()).strip()

def load_brands():
    path = os.path.join(os.path.dirname(__file__), "brands.json")
    with open(path, "r") as f:
        return json.load(f)

###############################################################
# 🔥 STEALTH NAVIGATION
###############################################################
def safe_goto(page, url):
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=NAV_TIMEOUT)

        # human-like scroll
        for _ in range(4):
            page.mouse.wheel(0, random.randint(300, 800))
            time.sleep(random.uniform(0.3, 0.9))

        time.sleep(random.uniform(1.5, 2.8))
        return True

    except Exception as e:
        log(f"❌ Navigation failed: {url} → {e}")
        return False

def get_html(page):
    try:
        return page.evaluate("() => document.documentElement.innerHTML")
    except:
        return page.content()

###############################################################
# 🔥 Extract Models (works perfectly in your DOM scraper)
###############################################################
def extract_model_links(page, brand_url):
    log(f"▶ Brand: {brand_url}")

    if not safe_goto(page, brand_url):
        return []

    soup = BeautifulSoup(get_html(page), "lxml")

    models = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "/Models/" in href:
            full = urljoin(BASE_URL, href)
            if full not in models:
                models.append(full)

    limited = models[:MAX_MODELS_PER_BRAND]
    log(f"  → Found {len(models)} models, using {len(limited)}")

    return limited

###############################################################
# 🔥 Extract Model Number from URL for API use
###############################################################
def extract_model_number(model_url: str) -> str:
    # URL: https://www.partselect.com/Models/HDA3400G02BB/
    return model_url.rstrip("/").split("/")[-1]

###############################################################
# 🔥 Fetch Parts from API (no more part page scraping!)
###############################################################
def fetch_parts_from_api(page, model_number, category):
    api_url = f"https://www.partselect.com/api/ModelParts?modelNumber={model_number}"

    log(f"    → Fetching API for model {model_number}")

    response = page.request.get(api_url)

    if response.status != 200:
        log(f"    ❌ API error {response.status}")
        return []

    data = response.json()
    log(f"    → Retrieved {len(data)} parts")

    parts = []

    for p in data:
        parts.append({
            "category": category,
            "model_number": model_number,
            "part_number": p.get("partNumber"),
            "manufacturer_number": p.get("manufacturerNumber"),
            "name": p.get("name"),
            "price": p.get("price"),
            "image": p.get("image"),
            "summary": p.get("summary"),
            "symptoms": p.get("symptoms", []),
            "installation_texts": p.get("installation", []),
            "videos": p.get("videos", []),
            "raw": p        # keep all fields, useful for embeddings
        })

    return parts

###############################################################
# 🔥 MAIN: DOM navigation + API details
###############################################################
def main():
    start = time.time()
    brands = load_brands()
    all_parts = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"]
        )

        context = browser.new_context(
            viewport={"width": 1400, "height": 900},
            user_agent=(
                f"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_{random.randint(14,16)}_{random.randint(1,6)}) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                f"Chrome/{random.randint(120,125)}.0.{random.randint(1000,5000)}.{random.randint(100,300)} Safari/537.36"
            )
        )

        page = context.new_page()

        for category, brand_urls in brands.items():
            log("=======================================")
            log(f"SCRAPING CATEGORY: {category.upper()}")
            log("=======================================")

            for brand_url in brand_urls:
                model_links = extract_model_links(page, brand_url)

                for model_url in model_links:
                    model_number = extract_model_number(model_url)

                    # Only needed so cookies load properly before API call
                    safe_goto(page, model_url)

                    # Fetch ALL parts in one API call
                    parts = fetch_parts_from_api(page, model_number, category)
                    all_parts.extend(parts)

        browser.close()

    # Save
    out_path = os.path.join(os.path.dirname(__file__), "..", "data", "parts.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    with open(out_path, "w") as f:
        json.dump(all_parts, f, indent=2)

    log(f"✅ Saved {len(all_parts)} parts → {out_path}")
    log(f"⏱ Total scrape time: {time.time() - start:.1f} seconds")

if __name__ == "__main__":
    main()

