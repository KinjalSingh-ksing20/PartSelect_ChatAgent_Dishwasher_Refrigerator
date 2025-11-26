import json
from pathlib import Path
from typing import Set

CATALOG_PATH = Path(__file__).parent / "full_catalog.json"

KNOWN_BRANDS: Set[str] = set()
KNOWN_PART_NUMBERS: Set[str] = set()
KNOWN_MODELS: Set[str] = set()
KNOWN_SYMPTOMS: Set[str] = set()


def load_catalog_registry():
    global KNOWN_BRANDS, KNOWN_PART_NUMBERS, KNOWN_MODELS, KNOWN_SYMPTOMS

    if not CATALOG_PATH.exists():
        raise RuntimeError(f"Catalog file not found: {CATALOG_PATH}")

    with open(CATALOG_PATH, "r", encoding="utf-8") as f:
        catalog = json.load(f)

    for item in catalog:
        
        if item.get("brand"):
            KNOWN_BRANDS.add(item["brand"].lower())

        if item.get("id"):
            KNOWN_PART_NUMBERS.add(item["id"].upper())

        for m in item.get("compatible_models", []):
            KNOWN_MODELS.add(m.upper())

        for s in item.get("symptoms_vector", []):
            KNOWN_SYMPTOMS.add(s.lower())

    print(f"[CATALOG] Brands: {len(KNOWN_BRANDS)}")
    print(f"[CATALOG] Part Numbers: {len(KNOWN_PART_NUMBERS)}")
    print(f"[CATALOG] Models: {len(KNOWN_MODELS)}")
    print(f"[CATALOG] Symptoms: {len(KNOWN_SYMPTOMS)}")

