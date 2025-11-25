from agents.router import route_to_tool

tests = [
    "How do I install this dishwasher motor?",
    "Will this water filter fit my Samsung fridge?",
    "My dryer is not heating, what should I check?",
    "Find me the part number for Whirlpool W12345"
]

for t in tests:
    intent = "installation" if "install" in t.lower() else \
             "compatibility" if "fit" in t.lower() else \
             "troubleshooting" if "not" in t.lower() else \
             "product_lookup"

    result = route_to_tool(intent, t)
    print("\nQuery:", t)
    print("→ Tool:", result["tool"])
    print("→ Output:", result["output"])

