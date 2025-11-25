# backend/agents/intent_classifier.py

from models.llm import deepseek_chat

INTENTS = ["installation", "compatibility", "troubleshooting", "product_lookup"]

SYSTEM_PROMPT = """
You are an intent classification model for a PartSelect Chat Agent.
Your job is to classify the user's query into EXACTLY ONE of the following categories:

1. installation  → when user wants installation steps or guidance
2. compatibility → when user asks "will this part fit?", "is this compatible?"
3. troubleshooting → when user describes a problem and wants a fix
4. product_lookup → when user wants to search/identify a part

RULES:
- Return ONLY the category word. No sentences.
- Never explain yourself.
- Never output anything except one of the four labels.
"""

def classify_intent(user_message: str) -> str:
    """
    Sends user query to DeepSeek and returns a clean intent label.
    """
    raw = deepseek_chat(
        SYSTEM_PROMPT,
        user_message
    )

    cleaned = raw.strip().lower()

    # safety: map common variations to correct label
    if "install" in cleaned:
        return "installation"
    if "fit" in cleaned or "compatible" in cleaned or "compatibility" in cleaned:
        return "compatibility"
    if "not working" in cleaned or "won't start" in cleaned or "trouble" in cleaned:
        return "troubleshooting"

    # if DeepSeek returned an exact label:
    if cleaned in INTENTS:
        return cleaned

    # fallback
    return "product_lookup"

