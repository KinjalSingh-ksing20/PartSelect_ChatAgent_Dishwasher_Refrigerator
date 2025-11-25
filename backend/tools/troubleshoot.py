# backend/tools/troubleshoot.py

import os
import json
from typing import Any, Dict, List

from vectorstore.search import semantic_search

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
PARTS_PATH = os.path.join(DATA_DIR, "parts.json")


def _load_parts():
    with open(PARTS_PATH, "r") as f:
        return json.load(f)


def troubleshoot_issue(description: str) -> Dict[str, Any]:
    """
    Given a free-text problem description (e.g. "ice maker not working"),
    return a list of candidate parts + troubleshooting info.
    Uses a combination of symptom matching + semantic search.
    """
    desc = description.lower()
    parts = _load_parts()

    direct_hits: List[Dict[str, Any]] = []

    # 1) Symptom matching
    for p in parts:
        for symptom in p.get("symptoms", []):
            if symptom.lower() in desc or desc in symptom.lower():
                direct_hits.append(
                    {
                        "part_number": p.get("part_number"),
                        "name": p.get("name"),
                        "category": p.get("category"),
                        "matched_symptom": symptom,
                        "troubleshooting_texts": p.get("troubleshooting_texts", []),
                    }
                )
                break

    # 2) Semantic search as backup
    semantic_hits: List[Dict[str, Any]] = []
    try:
        hits = semantic_search(description, top_k=5)
        for h in hits:
            p = h["part"]
            semantic_hits.append(
                {
                    "part_number": p.get("part_number"),
                    "name": p.get("name"),
                    "category": p.get("category"),
                    "score": h["score"],
                    "troubleshooting_texts": p.get("troubleshooting_texts", []),
                }
            )
    except Exception as e:
        print(f"[TOOLS/troubleshoot] Semantic search failed: {e}")

    if not direct_hits and not semantic_hits:
        return {
            "matches": [],
            "message": "No troubleshooting guidance found for this description.",
        }

    return {
        "matches": {
            "symptom_matches": direct_hits,
            "semantic_matches": semantic_hits,
        },
        "message": "OK",
    }

