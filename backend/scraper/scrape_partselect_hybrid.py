# scraper/scrape_partselect_hybrid.py

import asyncio
import json
import os
import time
from playwright.async_api import async_playwright
import aiohttp

BASE_API_URL = "https://www.partselect.com"
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
OUT_PATH = os.path.join(DATA_DIR, "parts.json")

os.makedirs(DATA_DIR, exist_ok=True)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_3_1) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://www.partselect.com/",
}

MAX_MODELS_PER_BRAND = 10


def log(msg):
    print(f"[SCRAPER] {msg}")


# -------------------------------------------------------------
# 1. JSON API ENDPOINTS
# -------------------------------------------------------------

async def api_get(session, url):
    async with session.get(url, headers=HEADERS, timeout=20) as resp:
        if resp.status != 200:
            log(f"❌ API error {resp.status} → {url}")
            return None
        return await resp.json()


async def fetch_brands(session, appliance_id):
    url = f"{BASE_API_URL}/Category/ApplianceTypeBrands?applianceTypeId={appliance_id}"
    return await api_get(session, url)


async def fetch_models(session, brand_id):
    url = f"{BASE_API_URL}/Category/BrandModels?brandId={brand_id}"
    return await api_get(session, url)


async def fetch_parts_for_model(session, model_id):
    url = f"{BASE_API_URL}/Model/ModelParts?modelId={model_id}"
    return await api_get(session, url)


# -------------------------------------------------------------
# 2. PLAYWRIGHT DETAIL SCRAPING
# -------------------------------------------------------------

async def scrape_part_detail(page, url):
    """Extract title, description, price, symptoms, installation, troubleshooting."""
    try:
        await page.goto(url, timeout=30000)
        await page.wait_for_load_state("networkidle")
    except:
        return None

    data = {"url": url}

    async def get_text(selector):
        try:
            el = await page.query_selector(selector)
            if el:
                txt = (await el.inner_text()).strip()
                return " ".join(txt.split())
        except:
            pass
        return None

    # Title
    data["name"] = await get_text("h1")

    # Price
    data["price"] = await get_text(".price")

    # Description block
    data["description"] = await get_text("#product-description") or await get_text(".product-description")

    # Symptoms list
    symptoms = []
    items = await page.query_selector_all(".fixes li")
    for li in items:
        txt = (await li.inner_text()).strip()
        symptoms.append(txt)
    data["symptoms"] = symptoms

    # Installation & troubleshooting text (collect from headings)
    html = await page.content()

    install_sections = []
    trouble_sections = []

    for section_type, bucket in [
        ("install", install_sections),
        ("troubleshoot", trouble_sections),
        ("problem", trouble_sections),
    ]:
        # crude text search
        if section_type in html.lower():
            bucket.append(section_type)

    data["installation_texts"] = install_sections
    data["troubleshooting_texts"] = trouble_sections

    return data


# -------------------------------------------------------------
# 3. MAIN SCRAPER — HYBRID PIPELINE
# -------------------------------------------------------------

async def scrape_category(session, pw, category_name, appliance_id):
    """Scrape brands → models → parts using JSON API, details using Playwright."""
    log(f"▶ Scraping category: {category_name}")

    brands = await fetch_brands(session, appliance_id)
    if not brands:
        log("❌ No brands found.")
        return []

    total_parts = []

    browser = await pw.chromium.launch(headless=True)
    page = await browser.new_page()

    for brand in brands:
        brand_id = brand["BrandId"]
        brand_name = brand["Name"]

        log(f"  - Brand: {brand_name}")

        models = await fetch_models(session, brand_id)
        if not models:
            continue

        models = models[:MAX_MODELS_PER_BRAND]

        for model in models:
            model_id = model["ModelId"]
            model_name = model["Name"]

            log(f"    → Model: {model_name}")

            parts_json = await fetch_parts_for_model(session, model_id)
            if not parts_json:
                continue

            for part in parts_json:
                part_number = part.get("PartNumber")
                part_name = part.get("Name")
                part_url = BASE_API_URL + part.get("Url", "")

                log(f"      • Part {part_number}: {part_name}")

                # Basic metadata
                part_record = {
                    "category": category_name,
                    "brand": brand_name,
                    "model": model_name,
                    "part_number": part_number,
                    "name": part_name,
                    "url": part_url,
                }

                # Scrape detail with Playwright
                detail = await scrape_part_detail(page, part_url)
                if detail:
                    part_record.update(detail)

                total_parts.append(part_record)

    await browser.close()
    return total_parts


# -------------------------------------------------------------
# 4. ENTRY POINT
# -------------------------------------------------------------

async def main():
    start = time.time()

    async with aiohttp.ClientSession(headers=HEADERS) as session:
        async with async_playwright() as pw:
            all_parts = []

            # Dishwasher = applianceTypeId 1
            dishwasher_parts = await scrape_category(
                session, pw, "dishwasher", appliance_id=1
            )
            all_parts.extend(dishwasher_parts)

            # Refrigerator = applianceTypeId 2
            refrigerator_parts = await scrape_category(
                session, pw, "refrigerator", appliance_id=2
            )
            all_parts.extend(refrigerator_parts)

    with open(OUT_PATH, "w") as f:
        json.dump(all_parts, f, indent=2)

    log(f"✅ Saved {len(all_parts)} parts → {OUT_PATH}")
    log(f"⏱ Total scrape time: {time.time() - start:.2f} seconds")


if __name__ == "__main__":
    asyncio.run(main())

