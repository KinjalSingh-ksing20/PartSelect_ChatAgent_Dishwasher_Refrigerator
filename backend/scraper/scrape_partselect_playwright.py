import asyncio
import json
import os
import time
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

BASE_URL = "https://www.partselect.com"

# Safety knobs – you can tune these
MAX_BRANDS_PER_CATEGORY = 10        # per category (dishwasher / refrigerator)
MAX_MODELS_PER_BRAND = 10          # per brand
MAX_PARTS_PER_MODEL = 200          # safety cap per model

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_3_1) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


def log(msg: str) -> None:
    print(f"[SCRAPER] {msg}")


# ----------- HTML PARSERS (BeautifulSoup) ----------- #

def parse_brand_links(category_html: str) -> list[str]:
    """
    From category page HTML (Dishwasher-Parts.htm, Refrigerator-Parts.htm),
    extract brand URLs.

    On PartSelect, brands are shown under a section roughly like:

        <div id="ps-brands">
            <a href="/Dishwasher-Parts/Whirlpool.htm">Whirlpool</a> ...

    We target #ps-brands a
    """
    soup = BeautifulSoup(category_html, "lxml")
    brand_section = soup.find(id="ps-brands")
    if not brand_section:
        # fallback: try anything that smells like a brand link
        links = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "Dishwasher-Parts" in href or "Refrigerator-Parts" in href:
                full = urljoin(BASE_URL, href)
                if full not in links:
                    links.append(full)
        return links

    links = []
    for a in brand_section.find_all("a", href=True):
        full = urljoin(BASE_URL, a["href"])
        if full not in links:
            links.append(full)
    return links


def parse_model_links(brand_html: str) -> list[str]:
    """
    From a brand page, extract model URLs.

    Model URLs usually look like: /Models/WDT780SAEM1/
    We use a heuristic: any <a> where href contains "/Models/".
    """
    soup = BeautifulSoup(brand_html, "lxml")
    links: list[str] = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "/Models/" in href:
            full = urljoin(BASE_URL, href)
            if full not in links:
                links.append(full)
    return links


def parse_part_links(model_html: str) -> list[str]:
    """
    From a model page, extract part URLs.

    Part URLs usually look like:
      /PS11752778-Whirlpool-WPW10613606-Door-Bin.htm

    We use heuristic: href contains "PS" and ends with ".htm".
    """
    soup = BeautifulSoup(model_html, "lxml")
    links: list[str] = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "PS" in href and href.endswith(".htm"):
            full = urljoin(BASE_URL, href)
            if full not in links:
                links.append(full)
    return links


def clean(text: str | None) -> str | None:
    if not text:
        return None
    return " ".join(text.split()).strip()


def parse_part_detail(part_html: str, url: str, category: str) -> dict:
    """
    Turn one part page into a structured dict the LLM can use.

    We try to capture:
      - part name
      - part number (PSxxxxx)
      - description
      - price
      - compatible models
      - symptoms / fixes
      - installation text
      - troubleshooting text
    """
    soup = BeautifulSoup(part_html, "lxml")

    # Title
    title_tag = soup.find("h1")
    name = clean(title_tag.text) if title_tag else None

    # Part number – multiple strategies
    part_number = None

    # Strategy 1: look for labels like "Part Number:" or "PartSelect Number:"
    text_candidates = soup.find_all(
        string=lambda t: t and ("Part Number" in t or "PartSelect Number" in t)
    )
    for t in text_candidates:
        parent = t.parent
        # often structure is: <span>Part Number:</span><span>PS11752778</span>
        if parent and parent.find_next("span"):
            part_number = clean(parent.find_next("span").get_text())
            if part_number:
                break

    # Strategy 2: fall back to URL pattern like "/PS11752778-Whirlpool-..."
    if not part_number:
        last = url.split("/")[-1]
        if last.startswith("PS"):
            part_number = last.split("-")[0]

    # Description – many product pages have a description div
    desc = None
    desc_div = (
        soup.find(id="product-description")
        or soup.find("div", class_="product-description")
        or soup.find("div", class_="ps-product-description")
    )
    if desc_div:
        desc = clean(desc_div.get_text(" ", strip=True))

    # Price
    price = None
    price_tag = soup.find("span", class_="price")
    if price_tag:
        price = clean(price_tag.get_text())

    # Compatible models (often a list)
    compatible_models: list[str] = []
    cross_ref = (
        soup.find(id="modelCrossReferences")
        or soup.find(id="modelCrossReference")
        or soup.find("div", class_="model-cross-reference")
    )
    if cross_ref:
        for li in cross_ref.find_all("li"):
            txt = clean(li.get_text())
            if txt:
                compatible_models.append(txt)

    # Symptoms / fixes
    symptoms: list[str] = []
    fixes_section = (
        soup.find("div", class_="fixes")
        or soup.find("ul", class_="fixes")
        or soup.find("div", class_="ps-fixes")
    )
    if fixes_section:
        for li in fixes_section.find_all("li"):
            txt = clean(li.get_text())
            if txt:
                symptoms.append(txt)

    # Installation & troubleshooting text: look for headings with keywords
    installation_texts: list[str] = []
    troubleshooting_texts: list[str] = []

    for header in soup.find_all(["h2", "h3", "h4"]):
        header_text = header.get_text(strip=True).lower()

        # Helper: collect paragraph-like siblings until next header
        def collect_block(start_tag):
            block = []
            sib = start_tag.find_next_sibling()
            while sib and sib.name not in ["h2", "h3", "h4"]:
                txt = clean(sib.get_text(" ", strip=True))
                if txt:
                    block.append(txt)
                sib = sib.find_next_sibling()
            return " ".join(block) if block else None

        if "install" in header_text:
            block = collect_block(header)
            if block:
                installation_texts.append(block)

        if (
            "troubleshoot" in header_text
            or "problem" in header_text
            or "not working" in header_text
            or "won't" in header_text
        ):
            block = collect_block(header)
            if block:
                troubleshooting_texts.append(block)

    return {
        "url": url,
        "category": category,  # "dishwasher" or "refrigerator"
        "name": name,
        "part_number": part_number,
        "description": desc,
        "price": price,
        "compatible_models": compatible_models,
        "symptoms": symptoms,
        "installation_texts": installation_texts,
        "troubleshooting_texts": troubleshooting_texts,
    }


# ----------- PLAYWRIGHT HELPERS ----------- #

async def get_html(page, url: str, wait_selector: str | None = None) -> str | None:
    """
    Navigate to `url`, wait for network + optional selector, then return page HTML.
    """
    try:
        await page.goto(url, wait_until="networkidle", timeout=30000)
    except Exception as e:
        log(f"Error navigating to {url}: {e}")
        return None

    if wait_selector:
        try:
            await page.wait_for_selector(wait_selector, timeout=5000)
        except Exception:
            # It's okay if we time out; some pages may not have this selector
            pass

    try:
        html = await page.content()
        return html
    except Exception as e:
        log(f"Error getting content from {url}: {e}")
        return None


# ----------- SCRAPING LOGIC ----------- #

async def scrape_category(page, cat_name: str, cat_url: str) -> list[dict]:
    """
    Scrape one category (dishwasher or refrigerator):
      - get brand links
      - for each brand, get up to N models
      - for each model, get part links
      - for each part, scrape details
    """
    log(f"Scraping category: {cat_name} ({cat_url})")

    category_html = await get_html(page, cat_url, wait_selector="#ps-brands a")
    if not category_html:
        log(f"Failed to load category page: {cat_url}")
        return []

    brand_links = parse_brand_links(category_html)
    if not brand_links:
        log(f"No brand links found in {cat_name} category")
        return []

    # Limit how many brands we take
    brand_links = brand_links[:MAX_BRANDS_PER_CATEGORY]
    log(f"Found {len(brand_links)} brand links for {cat_name} (capped at {MAX_BRANDS_PER_CATEGORY})")

    all_model_links: list[str] = []

    for brand_url in brand_links:
        log(f"  Brand: {brand_url}")
        brand_html = await get_html(page, brand_url, wait_selector="a[href*='/Models/']")
        if not brand_html:
            log(f"    Failed to load brand page: {brand_url}")
            continue

        model_links = parse_model_links(brand_html)
        if not model_links:
            log(f"    No models found for brand: {brand_url}")
            continue

        model_links = model_links[:MAX_MODELS_PER_BRAND]
        log(f"    Models found (capped at {MAX_MODELS_PER_BRAND}): {len(model_links)}")
        all_model_links.extend(model_links)

    # Deduplicate models
    all_model_links = list(dict.fromkeys(all_model_links))
    log(f"Total unique models for {cat_name}: {len(all_model_links)}")

    # For each model, get part URLs
    part_urls: set[str] = set()

    for model_url in all_model_links:
        log(f"    Scraping model: {model_url}")
        model_html = await get_html(page, model_url, wait_selector="a[href*='PS'][href$='.htm']")
        if not model_html:
            log(f"      Failed to load model page: {model_url}")
            continue

        model_part_links = parse_part_links(model_html)
        if not model_part_links:
            log(f"      No part links found on model page: {model_url}")
            continue

        # safety limit per model
        model_part_links = model_part_links[:MAX_PARTS_PER_MODEL]
        log(f"      Found {len(model_part_links)} part links on model page")
        for p_url in model_part_links:
            part_urls.add(p_url)

    log(f"Total unique part URLs for {cat_name}: {len(part_urls)}")

    # Now scrape part details (sequential to be polite)
    parts: list[dict] = []
    count = 0
    total = len(part_urls)

    for p_url in part_urls:
        count += 1
        log(f"    [{count}/{total}] Scraping part: {p_url}")
        part_html = await get_html(page, p_url, wait_selector="h1")
        if not part_html:
            log(f"      Failed to load part page: {p_url}")
            continue

        try:
            part_data = parse_part_detail(part_html, p_url, category=cat_name)
            if part_data.get("part_number") or part_data.get("name"):
                parts.append(part_data)
        except Exception as e:
            log(f"      Error parsing part page {p_url}: {e}")
            continue

    log(f"Successfully parsed {len(parts)} parts for category {cat_name}")
    return parts


async def main():
    start = time.time()
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=USER_AGENT,
        )
        page = await context.new_page()

        categories = {
            "dishwasher": "https://www.partselect.com/Dishwasher-Parts.htm",
            "refrigerator": "https://www.partselect.com/Refrigerator-Parts.htm",
        }

        all_parts: list[dict] = []

        for cat_name, cat_url in categories.items():
            cat_parts = await scrape_category(page, cat_name, cat_url)
            all_parts.extend(cat_parts)

        await browser.close()

    # Save to ../data/parts.json
    data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    os.makedirs(data_dir, exist_ok=True)
    out_path = os.path.join(data_dir, "parts.json")

    with open(out_path, "w") as f:
        json.dump(all_parts, f, indent=2)

    log(f"Saved {len(all_parts)} parts to {out_path}")
    log(f"Scrape completed in {time.time() - start:.2f} seconds")


if __name__ == "__main__":
    asyncio.run(main())
