from models.llm import deepseek_chat

print(
    deepseek_chat(
        "You are a test system.",
        "Say hello in one short sentence."
    )
)

