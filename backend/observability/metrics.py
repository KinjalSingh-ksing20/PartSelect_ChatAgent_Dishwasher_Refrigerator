# backend/observability/metrics.py

from prometheus_client import Counter, Histogram

# ---- Counters ----

deepseek_calls_total = Counter(
    "deepseek_calls_total",
    "Total number of DeepSeek LLM calls",
)

vector_search_total = Counter(
    "vector_search_total",
    "Total number of FAISS semantic searches",
)

agent_tool_invocations_total = Counter(
    "agent_tool_invocations_total",
    "Total number of tool invocations by the agent",
    ["tool_name"],  # label
)

errors_total = Counter(
    "errors_total",
    "Total number of backend errors",
    ["type"],  # type of error (deepseek, vectorstore, tool, agent)
)

# ---- Histograms ----

request_latency_seconds = Histogram(
    "request_latency_seconds",
    "Request latency for /chat",
    buckets=[0.05, 0.1, 0.2, 0.5, 1, 3, 5],
)

