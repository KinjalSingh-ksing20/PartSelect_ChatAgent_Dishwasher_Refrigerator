import re

def clean_llm_text(text: str) -> str:
    """Remove markdown, bullets, headers, and excess formatting."""
    if not text:
        return ""

    # Remove markdown bold/italic
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"\*(.*?)\*", r"\1", text)

    # Remove headers
    text = re.sub(r"^#+\s*", "", text, flags=re.MULTILINE)

    # Remove horizontal rules
    text = re.sub(r"---+", "", text)

    # Remove bullet formatting
    text = re.sub(r"^\s*[-•]\s*", "", text, flags=re.MULTILINE)

    # Normalize line spacing
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()

