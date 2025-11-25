# backend/vectorstore/search.py

import os
import json
from typing import List, Dict, Any

import faiss
import numpy as np
from dotenv import load_dotenv
from openai import OpenAI

# --- Observability ---
from opentelemetry import trace
from observability.metrics import vector_search_total, errors_total

tracer = trace.get_tracer(__name__)

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INDEX_PATH = os.path.join(BASE_DIR, "index.faiss")
META_PATH = os.path.join(BASE_DIR, "parts_metadata.json")

_openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

_index = None
_metadata = None


def _load_index() -> bool:
    """Load FAISS index + metadata into memory once."""
    global _index, _metadata

    if _index is not None and _metadata is not None:
        return True

    if not os.path.exists(INDEX_PATH) or not os.path.exists(META_PATH):
        print("[VECTOR] Index or metadata missing.")
        return False

    _index = faiss.read_index(INDEX_PATH)

    with open(META_PATH, "r") as f:
        _metadata = json.load(f)

    print(f"[VECTOR] Loaded index with {len(_metadata)} parts.")
    return True


def _embed_query(text: str) -> np.ndarray:
    """Embed query using OpenAI text-embedding-3-small."""
    resp = _openai_client.embeddings.create(
        model="text-embedding-3-small",
        input=text,
    )
    vec = np.array(resp.data[0].embedding, dtype="float32")
    return vec.reshape(1, -1)


def semantic_search(query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """
    Vector search with:
    - Prometheus metrics
    - OpenTelemetry tracing
    - Error instrumentation
    """
    vector_search_total.inc()  # Prometheus counter

    with tracer.start_as_current_span("vectorstore.semantic_search") as span:
        try:
            span.set_attribute("query_length", len(query))

            if not _load_index():
                return []

            # Embed + search
            q_vec = _embed_query(query)
            distances, indices = _index.search(q_vec, top_k)

            # Build results
            results = []
            for dist, idx in zip(distances[0], indices[0]):
                if idx < 0 or idx >= len(_metadata):
                    continue

                part = _metadata[int(idx)]
                results.append({
                    "score": float(dist),
                    "part": part,
                })

            span.set_attribute("results_count", len(results))
            return results

        except Exception as e:
            errors_total.labels("vectorstore").inc()
            span.record_exception(e)
            raise

