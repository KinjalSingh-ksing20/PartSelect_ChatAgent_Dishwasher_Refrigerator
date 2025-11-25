from agents.intent_classifier import classify_intent

tests = [
    "How do I install this dishwasher motor?",
    "Will this filter fit my Samsung refrigerator?",
    "My dryer won't start, what should I do?",
    "Find me the part number for Whirlpool W12345",
]

for t in tests:
    print(t, "→", classify_intent(t))

