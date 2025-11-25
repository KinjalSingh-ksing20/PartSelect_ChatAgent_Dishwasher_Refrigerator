# backend/agents/agent.py

from typing import Dict, Any

from agents.intent_classifier import classify_intent
from agents.router import ToolRouter
from tools.entities import extract_entities
from models.llm import deepseek_chat

# --- Observability ---
from observability.metrics import request_latency_seconds, errors_total
from opentelemetry import trace

tracer = trace.get_tracer(__name__)


class AgentController:
    """
    Core agent orchestration with OpenTelemetry tracing + Prometheus metrics.
    """

    def __init__(self):
        self.router = ToolRouter()

    @request_latency_seconds.time()   # <-- Prometheus latency measurement
    async def handle_chat(self, query: str) -> Dict[str, Any]:
        with tracer.start_as_current_span("agent.handle_chat") as span:
            try:
                span.set_attribute("query_length", len(query))

                # -------------------------
                # 1. Entity Extraction
                # -------------------------
                entities = extract_entities(query)
                span.set_attribute("entities", str(entities))

                # -------------------------
                # 2. Intent Classification
                # -------------------------
                intent = classify_intent(query)
                span.set_attribute("intent", intent)

                # -------------------------
                # 3. Tool Router
                # -------------------------
                tool_result = self.router.route(intent, query, entities)
                span.set_attribute("tool_used", tool_result["tool"])

                # -------------------------
                # 4. Final DeepSeek Answer
                # -------------------------
                system_prompt = """
                You are a support assistant for the PartSelect e-commerce site.

                RULES:
                - Only answer questions about dishwasher and refrigerator parts.
                - Use the provided tool output as ground truth.
                - Be concise and accurate.
                """

                user_prompt = f"""
                User query: {query}
                Intent: {intent}
                Entities: {entities}

                Tool used: {tool_result["tool"]}
                Tool output: {tool_result["output"]}
                """

                answer = deepseek_chat(system_prompt, user_prompt)

                return {
                    "intent": intent,
                    "entities": entities,
                    "tool_used": tool_result["tool"],
                    "tool_output": tool_result["output"],
                    "answer": answer,
                }

            except Exception as e:
                errors_total.labels("agent").inc()  # <-- Prometheus error counter
                span.record_exception(e)            # <-- OTel
                raise

