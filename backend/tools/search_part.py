# backend/tools/search_part.py

import os
import json
from typing import Any, Dict

from vectorstore.search import semantic_search

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")  # backend/data
PARTS_PATH = os.path.join(DATA_DIR, "parts.json")


def _load_parts():
    with open(PARTS_PATH, "r") as f:
        return json.load(f)


def search_part(query: str) -> Dict[str, Any]:
    """
    Hybrid product lookup:
      1) Try semantic FAISS search
      2) Fallback to simple JSON scan by name / part_number
    """
    # 1. Semantic search
    try:
        hits = semantic_search(query, top_k=3)
        if hits:
            return {
                "mode": "semantic",
                "matches": [
                    {
                        "score": h["score"],
                        **h["part"],
                    }
                    for h in hits
                ],
            }
    except Exception as e:
        print(f"[TOOLS/search_part] Semantic search failed: {e}")

    # 2. Fallback – simple scan
    parts = _load_parts()
    q = query.lower()

    exact_part = None
    candidates = []

    for p in parts:
        if p.get("part_number", "").lower() == q:
            exact_part = p
            break
        if q in p.get("name", "").lower():
            candidates.append(p)

    if exact_part:
        return {
            "mode": "exact_part_number",
            "matches": [exact_part],
        }

    if candidates:
        return {
            "mode": "name_contains",
            "matches": candidates,
        }

    return {
        "mode": "none",
        "matches": [],
        "message": "No matching part found.",
    }

