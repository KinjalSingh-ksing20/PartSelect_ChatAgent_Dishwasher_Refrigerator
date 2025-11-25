# scraper/scrape_partselect_async.py

import asyncio
import aiohttp
from aiohttp import ClientSession
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import json
import os
import time

BASE_URL = "https://www.partselect.com"

# Tuning knobs
MAX_CONCURRENT_REQUESTS = 10         # don't hammer the site
MAX_MODELS_PER_BRAND = 10            # per brand, per category
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0 Safari/537.36"
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_3_1) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,"
              "image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
    "Referer": "https://www.google.com/",
}


SEM = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)


def log(msg: str):
    print(f"[SCRAPER] {msg}")


async def fetch_html(session: ClientSession, url: str) -> str | None:
    """Fetch URL with retries, browser headers, and Cloudflare-friendly behavior."""
    async with SEM:
        for attempt in range(3):
            try:
                async with session.get(url, ssl=ssl_context, timeout=25) as resp:
                    if resp.status != 200:
                        log(f"Non-200 status {resp.status} for {url}")
                        await asyncio.sleep(1)
                        continue

                    text = await resp.text()

                    # Anti-Cloudflare rate-limiting
                    await asyncio.sleep(0.3)

                    return text

            except Exception as e:
                log(f"Error fetching {url} attempt {attempt+1}: {e}")
                await asyncio.sleep(1.5)

    return None



def parse_brand_links(category_html: str, category_path_fragment: str) -> list[str]:
    """
    From the Dishwasher/Refrigerator main category page, find brand links.
    We look for <a> whose href contains the category fragment.
    """
    soup = BeautifulSoup(category_html, "lxml")
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        # Example: "/Dishwasher-Parts/Whirlpool.htm"
        if category_path_fragment in href and href.endswith(".htm"):
            full = urljoin(BASE_URL, href)
            if full not in links:
                links.append(full)
    return links


def parse_model_links(brand_html: str) -> list[str]:
    """
    From a brand page, extract model links.
    Typically PartSelect model URLs look like: /Models/WDT780SAEM1/
    """
    soup = BeautifulSoup(brand_html, "lxml")
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "/Models/" in href:  # rough heuristic
            full = urljoin(BASE_URL, href)
            if full not in links:
                links.append(full)
    return links


def parse_part_links(model_html: str) -> list[str]:
    """
    From a model page, get part URLs.
    Part URLs usually look like /PS11752778-Whirlpool-WPW10613606-Door-Bin.htm
    We'll look for 'PS' + '.htm' patterns.
    """
    soup = BeautifulSoup(model_html, "lxml")
    links = []
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
    Parse one part page into a structured dict.
    This heavily depends on the site layout; adjust selectors if needed.
    """
    soup = BeautifulSoup(part_html, "lxml")

    # Title / name
    title_tag = soup.find("h1")
    name = clean(title_tag.text) if title_tag else None

    # Part number (often visible as PSxxxxx or shown in a 'Part Number' field)
    part_number = None
    # Try to find something like "Part Number: PS11752778"
    possible_labels = soup.find_all(text=lambda t: t and "Part Number" in t)
    if possible_labels:
        # Take the next sibling text if possible
        label = possible_labels[0]
        if label.parent and label.parent.find_next("span"):
            part_number = clean(label.parent.find_next("span").text)

    # Fallback: try to extract PSxxxxx from URL
    if not part_number:
        # e.g. https://www.partselect.com/PS11752778-Whirlpool-...
        segments = url.split("/")
        last = segments[-1]
        if last.startswith("PS"):
            part_number = last.split("-")[0]

    # Description: look for a product description container
    desc = None
    desc_div = soup.find(id="product-description") or soup.find("div", class_="product-description")
    if desc_div:
        desc = clean(desc_div.text)

    # Price (optional)
    price = None
    price_tag = soup.find("span", class_="price")
    if price_tag:
        price = clean(price_tag.text)

    # Compatible models: many sites have a cross-reference list
    compatible_models = []
    cross_ref = soup.find(id="modelCrossReferences") or soup.find(id="modelCrossReference")
    if cross_ref:
        for li in cross_ref.find_all("li"):
            txt = clean(li.text)
            if txt:
                compatible_models.append(txt)

    # Symptoms / “Part fixes” (if present)
    symptoms = []
    fixes_section = soup.find("div", class_="fixes") or soup.find("ul", class_="fixes")
    if fixes_section:
        for li in fixes_section.find_all("li"):
            txt = clean(li.text)
            if txt:
                symptoms.append(txt)

    # Installation / troubleshooting text: we'll search for headings that contain "Install" or "Troubleshoot"
    installation_texts = []
    troubleshooting_texts = []

    for header in soup.find_all(["h2", "h3", "h4"]):
        header_text = header.get_text(strip=True).lower()
        content_block = []
        if "install" in header_text:
            # collect following siblings until next header
            sib = header.find_next_sibling()
            while sib and sib.name not in ["h2", "h3", "h4"]:
                txt = clean(sib.get_text(" ", strip=True))
                if txt:
                    content_block.append(txt)
                sib = sib.find_next_sibling()
            if content_block:
                installation_texts.append(" ".join(content_block))

        if "troubleshoot" in header_text or "problem" in header_text or "not working" in header_text:
            sib = header.find_next_sibling()
            while sib and sib.name not in ["h2", "h3", "h4"]:
                txt = clean(sib.get_text(" ", strip=True))
                if txt:
                    content_block.append(txt)
                sib = sib.find_next_sibling()
            if content_block:
                troubleshooting_texts.append(" ".join(content_block))

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


async def scrape_part_page(session: ClientSession, url: str, category: str) -> dict | None:
    html = await fetch_html(session, url)
    if not html:
        return None
    try:
        return parse_part_detail(html, url, category)
    except Exception as e:
        log(f"Error parsing part page {url}: {e}")
        return None


async def scrape_model_page(session: ClientSession, url: str) -> list[str]:
    html = await fetch_html(session, url)
    if not html:
        return []
    return parse_part_links(html)


async def scrape_brand_models(session: ClientSession, brand_url: str, max_models: int) -> list[str]:
    html = await fetch_html(session, brand_url)
    if not html:
        return []
    model_links = parse_model_links(html)
    # Limit how many models per brand we take
    limited = model_links[:max_models]
    log(f"{brand_url} → {len(limited)} model(s) (out of {len(model_links)})")
    return limited


async def scrape_category(session: ClientSession, cat_name: str, cat_url: str) -> list[dict]:
    """
    Scrape one category (dishwasher or refrigerator):
      - get brand links
      - for each brand, get up to N models
      - for each model, get all part links
      - for each part link, scrape detailed data
    """
    log(f"Scraping category: {cat_name} ({cat_url})")
    cat_html = await fetch_html(session, cat_url)
    if not cat_html:
        log(f"Failed to fetch category page: {cat_url}")
        return []

    # Category path fragment to find brands
    if "Dishwasher" in cat_url:
        frag = "Dishwasher-Parts"
    else:
        frag = "Refrigerator-Parts"

    brand_links = parse_brand_links(cat_html, frag)
    log(f"Found {len(brand_links)} brand links in {cat_name} category")

    all_model_links: list[str] = []

    # Scrape models for each brand (sequentially to stay polite)
    for brand_url in brand_links:
        models = await scrape_brand_models(session, brand_url, MAX_MODELS_PER_BRAND)
        all_model_links.extend(models)

    all_model_links = list(dict.fromkeys(all_model_links))  # dedupe while preserving order
    log(f"Total unique models for {cat_name}: {len(all_model_links)}")

    # For each model, get part links (we can do this concurrently)
    part_urls: set[str] = set()

    async def model_worker(model_url: str):
        parts = await scrape_model_page(session, model_url)
        for p in parts:
            part_urls.add(p)

    await asyncio.gather(*(model_worker(m) for m in all_model_links))
    log(f"Total unique part URLs for {cat_name}: {len(part_urls)}")

    # Now scrape each part detail concurrently
    tasks = [
        scrape_part_page(session, url, category=cat_name)
        for url in part_urls
    ]
    results = await asyncio.gather(*tasks)

    parts = [r for r in results if r is not None]
    log(f"Successfully parsed {len(parts)} parts for category {cat_name}")
    return parts


import ssl

ssl_context = ssl.create_default_context()
ssl_context.set_ciphers("DEFAULT@SECLEVEL=1")

async def main():
    start = time.time()
    async with aiohttp.ClientSession(headers=HEADERS,connector=aiohttp.TCPConnector(ssl=ssl_context)) as session:
        categories = {
            "dishwasher": "https://www.partselect.com/Dishwasher-Parts.htm",
            "refrigerator": "https://www.partselect.com/Refrigerator-Parts.htm",
        }

        all_parts: list[dict] = []

        for cat_name, cat_url in categories.items():
            parts = await scrape_category(session, cat_name, cat_url)
            all_parts.extend(parts)

    # Save to ../data/parts.json
    data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    os.makedirs(data_dir, exist_ok=True)
    out_path = os.path.join(data_dir, "parts.json")

    with open(out_path, "w") as f:
        json.dump(all_parts, f, indent=2)

    log(f"Saved {len(all_parts)} parts to {out_path}")
    log(f"Total scrape time: {time.time() - start:.1f} seconds")


if __name__ == "__main__":
    asyncio.run(main())

