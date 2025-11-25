
import re
from typing import Dict, Optional


def extract_entities(text: str) -> Dict[str, Optional[str]]:
    """
    Very lightweight entity extractor.

    - part_number: things like PS11752778 (starts with PS + digits)
    - model_number: typical appliance model codes like WDT780SAEM1, LFX28968ST, etc.

    Returns:
        {"part_number": str | None, "model_number": str | None}
    """
    if not text:
        return {"part_number": None, "model_number": None}

    up = text.upper()

    # Find part number: first token starting with PS + digits
    part_number = None
    tokens = re.findall(r"\b[A-Z0-9\-]+\b", up)
    for tok in tokens:
        if tok.startswith("PS") and any(ch.isdigit() for ch in tok[2:]):
            part_number = tok
            break

    # Find model number: first long alphanumeric token NOT starting with PS
    model_number = None
    for tok in tokens:
        if tok == part_number:
            continue
        # heuristic: length >= 6 (e.g. WDT780SAEM1, LFX28968ST)
        if len(tok) >= 6 and any(ch.isdigit() for ch in tok) and any(ch.isalpha() for ch in tok):
            model_number = tok
            break

    return {"part_number": part_number, "model_number": model_number}
