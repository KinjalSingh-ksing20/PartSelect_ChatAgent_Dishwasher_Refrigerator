# backend/tools/installation.py

import os
import json
from typing import List, Dict, Any, Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
PARTS_PATH = os.path.join(DATA_DIR, "parts.json")


def _load_parts():
    with open(PARTS_PATH, "r") as f:
        return json.load(f)


def _find_part(part_number_or_query: str) -> Optional[Dict[str, Any]]:
    q = part_number_or_query.upper()
    parts = _load_parts()

    # 1. Exact by part_number
    for p in parts:
        if p.get("part_number", "").upper() == q:
            return p

    # 2. Contains in name
    for p in parts:
        if q in p.get("name", "").upper():
            return p

    return None


def get_installation_steps(part_number_or_query: str) -> Dict[str, Any]:
    """
    Return structured installation steps for a given part.
    """
    part = _find_part(part_number_or_query)

    if not part:
        return {
            "part": None,
            "steps": [],
            "message": "No installation information found for this part.",
        }

    steps: List[str] = part.get("installation_texts", []) or []

    return {
        "part": {
            "part_number": part.get("part_number"),
            "name": part.get("name"),
            "category": part.get("category"),
        },
        "steps": steps,
        "message": "OK" if steps else "No explicit installation steps stored for this part.",
    }

