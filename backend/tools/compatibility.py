import os
import json
from typing import Any, Dict, Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
PARTS_PATH = os.path.join(DATA_DIR, "parts.json")


def _load_parts():
    with open(PARTS_PATH, "r") as f:
        return json.load(f)


def check_compatibility(
    part_number: Optional[str],
    model_number: Optional[str],
) -> Dict[str, Any]:
    """
    Check if a given part is compatible with a given model.

    Args:
        part_number: e.g. "PS11752778"
        model_number: e.g. "WDT780SAEM1"

    Returns:
        {
          "part_number": ...,
          "model_number": ...,
          "compatible": bool | None,
          "reason": str,
          "part": {...}  # when found
        }
    """
    if not part_number and not model_number:
        return {
            "part_number": None,
            "model_number": None,
            "compatible": None,
            "reason": "Missing both part number and model number.",
        }

    parts = _load_parts()

    # Normalize
    pn = part_number.upper() if part_number else None
    mn = model_number.upper() if model_number else None

    # Find the part
    part = None
    for p in parts:
        if pn and p.get("part_number", "").upper() == pn:
            part = p
            break

    # If no exact part match, try soft name search
    if not part and pn:
        for p in parts:
            if pn in p.get("name", "").upper():
                part = p
                break

    if not part:
        return {
            "part_number": pn,
            "model_number": mn,
            "compatible": None,
            "reason": "Part not found in catalog.",
        }

    comp_models = [m.upper() for m in part.get("compatible_models", [])]

    if not mn:
        return {
            "part_number": pn,
            "model_number": None,
            "compatible": None,
            "reason": "Model number not provided.",
            "part": part,
        }

    is_compatible = mn in comp_models

    if is_compatible:
        reason = f"Part {pn} is listed as compatible with model {mn}."
    else:
        reason = f"Model {mn} is NOT listed as compatible with part {pn}."

    return {
        "part_number": pn,
        "model_number": mn,
        "compatible": is_compatible,
        "reason": reason,
        "part": part,
    }

