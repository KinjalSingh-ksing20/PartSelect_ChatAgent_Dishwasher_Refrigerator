# scraper/scrape_partselect_dom.py

from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import json
import os
import time
import random

BASE_URL = "https://www.partselect.com"
MAX_MODELS_PER_BRAND = 5      # safe, fast
MAX_PARTS_PER_MODEL = 10      # prevents 1000+ pages
NAV_TIMEOUT = 45000           # 45s (site can be slow)

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
# 🔥 Stealth Navigation Wrapper (Prevents 403 + 30s timeout)
###############################################################
def safe_goto(page, url):
    try:
        page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=NAV_TIMEOUT
        )
        # scroll to trigger lazy loads + appear human
        for _ in range(5):
            page.mouse.wheel(0, random.randint(300, 800))
            time.sleep(random.uniform(0.4, 0.9))

        # random realistic user delay
        time.sleep(random.uniform(1.8, 3.5))
        return True
    except Exception as e:
        log(f"❌ Navigation failed: {url} → {e}")
        return False

def get_html(page):
    """JS extraction works even when .content() is blocked."""
    try:
        return page.evaluate("() => document.documentElement.innerHTML")
    except:
        return page.content()

###############################################################
# 🔥 Extract Models
###############################################################
def extract_model_links(page, brand_url):
    log(f"▶ Brand: {brand_url}")

    if not safe_goto(page, brand_url):
        log("  → Failed to open brand page.")
        return []

    html = get_html(page)
    soup = BeautifulSoup(html, "lxml")

    # Model URLs look like: /Models/XXXX/
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
# 🔥 Extract Parts on Model Page
###############################################################
def extract_part_links(page, model_url):
    log(f"  ▶ Model: {model_url}")

    if not safe_goto(page, model_url):
        log("    → Failed to open model page.")
        return []

    html = get_html(page)
    soup = BeautifulSoup(html, "lxml")

    parts = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.startswith("/PS") and href.endswith(".htm"):
            full = urljoin(BASE_URL, href)
            if full not in parts:
                parts.append(full)

    log(f"    → Found {len(parts)} parts")
    return parts

###############################################################
# 🔥 Parse Part Detail Page
###############################################################
def parse_part_detail(page, part_url, category):
    log(f"    ▶ Part page: {part_url}")

    if not safe_goto(page, part_url):
        log("      → Failed to load part page")
        return None

    html = get_html(page)
    soup = BeautifulSoup(html, "lxml")

    name = clean(soup.find("h1").text if soup.find("h1") else None)
    part_number = part_url.split("/")[-1].split("-")[0]

    # Description
    desc_tag = soup.find("div", id="product-description")
    description = clean(desc_tag.get_text(" ", strip=True)) if desc_tag else None

    # Price
    price_tag = soup.find("span", class_="price")
    price = clean(price_tag.text) if price_tag else None

    return {
        "url": part_url,
        "category": category,
        "name": name,
        "part_number": part_number,
        "description": description,
        "price": price,
        "compatible_models": [],
        "installation_texts": [],
        "troubleshooting_texts": []
    }

###############################################################
# 🔥 Main Scraper Logic
###############################################################
def main():
    start = time.time()
    brands = load_brands()
    all_parts = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox"
            ]
        )

        context = browser.new_context(
            viewport={"width": 1400, "height": 900},
            user_agent=(
                f"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_{random.randint(14, 15)}_{random.randint(1, 6)}) "
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
                    part_links = extract_part_links(page, model_url)

                    # Limit parts per model
                    for part_url in part_links[:MAX_PARTS_PER_MODEL]:
                        detail = parse_part_detail(page, part_url, category)
                        if detail:
                            all_parts.append(detail)

        browser.close()

    # Save output
    out_path = os.path.join(os.path.dirname(__file__), "..", "data", "parts.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    with open(out_path, "w") as f:
        json.dump(all_parts, f, indent=2)

    log(f"✅ Saved {len(all_parts)} parts → {out_path}")
    log(f"⏱ Total scrape time: {time.time() - start:.1f} seconds")

if __name__ == "__main__":
    main()
