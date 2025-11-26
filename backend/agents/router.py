from typing import Dict, Any

from tools.search_part import search_part
from tools.compatibility import check_compatibility
from tools.installation import get_installation_steps
from tools.troubleshoot import troubleshoot_issue

# --- Observability ---
from observability.metrics import agent_tool_invocations_total, errors_total
from opentelemetry import trace

tracer = trace.get_tracer(__name__)


class ToolRouter:
    """
    Tool routing with OpenTelemetry tracing + Prometheus metrics.
    """

    def route(self, intent: str, query: str, entities: Dict[str, Any]) -> Dict[str, Any]:
        intent = (intent or "").lower()

        with tracer.start_as_current_span(f"router.{intent}") as span:
            try:
                span.set_attribute("query", query)
                span.set_attribute("entities", str(entities))

                tool_name = None
                part_number = entities.get("part_number")
                model_number = entities.get("model_number")

                if intent == "installation":
                    tool_name = "installation"
                    agent_tool_invocations_total.labels(tool_name).inc()

                    return {
                        "tool": tool_name,
                        "output": get_installation_steps(part_number or query),
                    }
 
                if intent == "compatibility":
                    tool_name = "compatibility"
                    agent_tool_invocations_total.labels(tool_name).inc()

                    return {
                        "tool": tool_name,
                        "output": check_compatibility(part_number, model_number),
                    }

                if intent == "troubleshooting":
                    tool_name = "troubleshooting"
                    agent_tool_invocations_total.labels(tool_name).inc()

                    return {
                        "tool": tool_name,
                        "output": troubleshoot_issue(query),
                    }

                if intent == "product_lookup":
                    tool_name = "search_part"
                    agent_tool_invocations_total.labels(tool_name).inc()

                    return {
                        "tool": tool_name,
                        "output": search_part(query),
                    }

                # --- FALLBACK ---
                agent_tool_invocations_total.labels("none").inc()
                return {
                    "tool": None,
                    "output": "I’m not sure what tool to call for this query."
                }

            except Exception as e:
                errors_total.labels("tool_router").inc()
                span.record_exception(e)
                raise

