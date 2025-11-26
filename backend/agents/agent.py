from typing import Dict, Any, Optional
import re
import uuid

from vectorstore.search import semantic_search
from models.llm import deepseek_chat
from memory.session_store import get_session, update_session
from utils.response_formatter import clean_llm_text

#Observability 
from observability.metrics import (
    request_latency_seconds,
    errors_total,
    agent_tool_invocations_total,
)

from opentelemetry import trace

tracer = trace.get_tracer(__name__)


from data.catalog_registry import (
    KNOWN_BRANDS,
    KNOWN_PART_NUMBERS,
    KNOWN_MODELS,
    KNOWN_SYMPTOMS,
)

# SUPPORTED & BLOCKED APPLIANCES 
SUPPORTED_APPLIANCE_KEYWORDS = [
    "dishwasher", "dish washer",
    "refrigerator", "fridge", "freezer",
    "ice maker", "icemaker"
]

OUT_OF_SCOPE_APPLIANCES = [
    "microwave", "oven", "range",
    "washer", "dryer", "stove", "cooktop"
]


#ENTITY EXTRACTION UTILS 

def _extract_brand(q: str) -> Optional[str]:
    q_lower = q.lower()
    for brand in KNOWN_BRANDS:
        if brand in q_lower:
            return brand.title()
    return None


def _extract_appliance(q: str) -> Optional[str]:
    if any(x in q for x in ["dishwasher", "dish washer"]):
        return "dishwasher"
    if any(x in q for x in ["refrigerator", "fridge", "freezer", "ice maker", "icemaker"]):
        return "refrigerator"
    return None


def _extract_model(q: str) -> Optional[str]:
    q_upper = q.upper()
    for model in KNOWN_MODELS:
        if model in q_upper:
            return model
    return None


def _extract_part_number(q: str) -> Optional[str]:
    for part in KNOWN_PART_NUMBERS:
        if part.lower() in q.lower():
            return part
    return None


def _extract_symptom(q: str) -> Optional[str]:
    q_lower = q.lower()
    for symptom in KNOWN_SYMPTOMS:
        if symptom in q_lower:
            return symptom
    return None


def _wants_installation(q: str) -> bool:
    return any(w in q for w in ["install", "installation", "replace"])


def _wants_compatibility(q: str) -> bool:
    return any(w in q for w in ["compatible", "fit", "work with"])


def _user_doesnt_know_model(q: str) -> bool:
    return any(x in q for x in ["i don't know", "dont know", "not sure", "no idea"])


# CORE AGENT CONTROLLER

class AgentController:

    @request_latency_seconds.time()
    async def handle_chat(self, query: str, session_id: str | None = None) -> Dict[str, Any]:
        with tracer.start_as_current_span("agent.handle_chat") as span:
            try:
                if not session_id:
                    session_id = str(uuid.uuid4())

                q = query.lower().strip()
                span.set_attribute("query_length", len(query))

                
                # 1) SESSION MEMORY
                session = get_session(session_id)

                part_number = _extract_part_number(q)
                model_number = _extract_model(q) or session.get("model_number")
                brand = _extract_brand(q) or session.get("brand")
                appliance = _extract_appliance(q) or session.get("appliance")
                symptom = _extract_symptom(q) or session.get("symptom")
                issue_text = query.strip() or session.get("issue_text")

                update_session(
                    session_id,
                    {
                        "model_number": model_number,
                        "brand": brand,
                        "appliance": appliance,
                        "symptom": symptom,
                        "issue_text": issue_text,
                    },
                )

                # 2) HARD SCOPE GUARDRAIL 
                mentions_supported_appliance = any(w in q for w in SUPPORTED_APPLIANCE_KEYWORDS)
                mentions_out_of_scope = any(w in q for w in OUT_OF_SCOPE_APPLIANCES)

                mentions_brand = any(b.lower() in q for b in KNOWN_BRANDS)
                mentions_part_number = any(p.lower() in q for p in KNOWN_PART_NUMBERS)
                mentions_model = any(m.lower() in q for m in KNOWN_MODELS)
                mentions_symptom = any(s.lower() in q for s in KNOWN_SYMPTOMS)

                # --- Final In-Scope Decision (Multi-Signal) ---

                in_scope = any([
                    mentions_supported_appliance,
                    mentions_brand,
                    mentions_part_number,
                    mentions_model,
                    mentions_symptom,
                ])

                if (mentions_out_of_scope and not in_scope) or not in_scope:
                    return {
                        "session_id": session_id,
                        "intent": "out_of_scope",
                        "entities": {},
                        "tool_used": None,
                        "tool_output": [],
                        "answer": (
                            "I specialize in refrigerator and dishwasher parts only, "
                            "including troubleshooting, installation, compatibility, and ordering. "
                            "If you have a question about a refrigerator or dishwasher, "
                            "I can help you with that."
                        ),
                    }

                
                # 3) INSTALLATION FLOW
                if part_number and _wants_installation(q):
                    results = semantic_search(part_number, top_k=1)

                    if not results:
                        return {
                            "session_id": session_id,
                            "intent": "install_generic",
                            "entities": {"part_number": part_number},
                            "tool_used": "FAISS",
                            "tool_output": [],
                            "answer": (
                                "I could not find exact installation steps for this part. "
                                "Here is a safe general approach:\n"
                                "1. Disconnect power and water.\n"
                                "2. Remove access panels.\n"
                                "3. Remove old part.\n"
                                "4. Install new part.\n"
                                "5. Reassemble and restore power.\n\n"
                                "If you share the model number, I can be more precise."
                            ),
                        }

                    part = results[0]

                    system_prompt = """
You are a PartSelect installation expert.
Use ONLY the provided data.
Do NOT use markdown.
Give clean numbered steps.
Include a short safety warning at the top.
"""
                    user_prompt = f"Install using only this data:\n{part}"

                    raw_answer = deepseek_chat(system_prompt, user_prompt)
                    answer = clean_llm_text(raw_answer)
                    agent_tool_invocations_total.labels("installation").inc()

                    return {
                        "session_id": session_id,
                        "intent": "installation",
                        "entities": {
                            "part_number": part["part_number"],
                            "model_number": model_number,
                            "brand": part.get("brand"),
                            "appliance": appliance,
                        },
                        "tool_used": "FAISS + DeepSeek",
                        "tool_output": results,
                        "answer": answer,
                    }

                
                # 4) COMPATIBILITY FLOW
                if part_number and model_number and _wants_compatibility(q):
                    results = semantic_search(part_number, top_k=1)

                    if not results:
                        agent_tool_invocations_total.labels("compatibility").inc()
                        return {
                            "session_id": session_id,
                            "intent": "compatibility_unknown",
                            "entities": {"part_number": part_number, "model_number": model_number},
                            "tool_used": "FAISS",
                            "tool_output": [],
                            "answer": (
                                f"I could not find part {part_number} for model {model_number}. "
                                "Compatibility cannot be confirmed."
                            ),
                        }

                    part = results[0]
                    compatible = model_number in part.get("compatible_models", [])
                    agent_tool_invocations_total.labels("compatibility").inc()

                    return {
                        "session_id": session_id,
                        "intent": "compatibility_yes" if compatible else "compatibility_no",
                        "entities": {"part_number": part["part_number"], "model_number": model_number},
                        "tool_used": "FAISS",
                        "tool_output": [part],
                        "answer": (
                            "This part is listed as compatible."
                            if compatible else
                            "This part is NOT listed as compatible for your model."
                        ),
                    }

                
                # 5) MODEL UNKNOWN → BRAND + SYMPTOM SEARCH 
                if _user_doesnt_know_model(q):
                    search_query = " ".join(
                        [x for x in [brand, appliance, symptom, issue_text] if x]
                    )

                    results = semantic_search(search_query, top_k=4)

                    if results:
                        context = "\n".join(
                            f"{p['name']} — {p.get('symptoms_vector', [])}" for p in results
                        )

                        system_prompt = """
You are a PartSelect appliance troubleshooting expert.
User does NOT know the model.
Use ONLY the provided data.
Give safe general guidance.
Do NOT guarantee compatibility.
"""

                        user_prompt = f"User issue:\n{query}\n\nCatalog data:\n{context}"

                        raw_answer = deepseek_chat(system_prompt, user_prompt)
                        answer = clean_llm_text(raw_answer)
                        agent_tool_invocations_total.labels("recommendation").inc()

                        return {
                            "session_id": session_id,
                            "intent": "brand_symptom_guidance",
                            "entities": {"brand": brand, "appliance": appliance},
                            "tool_used": "FAISS + DeepSeek",
                            "tool_output": results,
                            "answer": answer,
                        }

         
                # 6) NORMAL RAG FLOW
                results = semantic_search(query, top_k=4)

                if not results:
                    return {
                        "session_id": session_id,
                        "intent": "generic_guidance",
                        "entities": {
                            "model_number": model_number,
                            "brand": brand,
                            "appliance": appliance,
                        },
                        "tool_used": "FAISS",
                        "tool_output": [],
                        "answer": (
                            "I could not find a strong catalog match. "
                            "Please verify your model number or describe symptoms in more detail."
                        ),
                    }

                context = "\n".join(str(p) for p in results)

                system_prompt = """
You are a professional PartSelect expert.
Use ONLY catalog data.
Never invent prices or models.
Give clear reasoning and recommend at most 3 parts.
"""

                user_prompt = f"User issue:\n{query}\n\nCatalog data:\n{context}"

                raw_answer = deepseek_chat(system_prompt, user_prompt)
                answer = clean_llm_text(raw_answer)

                return {
                    "session_id": session_id,
                    "intent": "product_recommendation",
                    "entities": {
                        "model_number": model_number,
                        "brand": brand,
                        "appliance": appliance,
                    },
                    "tool_used": "FAISS + DeepSeek",
                    "tool_output": results,
                    "answer": answer,
                }

            except Exception as e:
                errors_total.labels("agent").inc()
                span.record_exception(e)
                return {
                    "session_id": session_id,
                    "intent": "error",
                    "entities": {},
                    "tool_used": None,
                    "tool_output": [],
                    "answer": "Something went wrong while processing your request. Please try again.",
                }
