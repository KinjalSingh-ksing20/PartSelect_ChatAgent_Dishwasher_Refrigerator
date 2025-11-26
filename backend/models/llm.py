# backend/models/llm.py

import os
from dotenv import load_dotenv
from openai import OpenAI

# --- Observability ---
from observability.metrics import deepseek_calls_total, errors_total
from opentelemetry import trace
tracer = trace.get_tracer(__name__)

# -------------------------
# Load API keys + Create Client
# -------------------------
load_dotenv()

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

if not DEEPSEEK_API_KEY:
    raise RuntimeError("DEEPSEEK_API_KEY is missing from environment variables.")

client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url=DEEPSEEK_BASE_URL,
)

# -------------------------
# DeepSeek Chat Wrapper + Telemetry
# -------------------------
def deepseek_chat(system_prompt: str, user_prompt: str) -> str:
    deepseek_calls_total.inc()

    with tracer.start_as_current_span("deepseek.chat") as span:
        try:
            span.set_attribute("system_prompt_length", len(system_prompt))
            span.set_attribute("user_prompt_length", len(user_prompt))

            resp = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.2,
            )

            answer = resp.choices[0].message.content

            if not answer:
                return "I'm sorry, I couldn't generate a response at the moment."

            span.set_attribute("deepseek.response_length", len(answer))
            return answer

        except Exception as e:
            errors_total.labels("deepseek").inc()
            span.record_exception(e)
            raise
