import os
import json
from typing import List, Dict, Any

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

# --- Observability ---
from opentelemetry import trace
from observability.metrics import vector_search_total, errors_total

tracer = trace.get_tracer(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(__file__))

INDEX_PATH = os.path.join(BASE_DIR, "vectorstore", "index.faiss")
META_PATH = os.path.join(BASE_DIR, "vectorstore", "parts_metadata.json")

_index = None
_metadata = None
_model = SentenceTransformer("all-MiniLM-L6-v2")


def _load_index() -> bool:
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
    vec = _model.encode([text])
    return np.array(vec).astype("float32")


def semantic_search(query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    vector_search_total.inc()

    with tracer.start_as_current_span("vectorstore.semantic_search") as span:
        try:
            span.set_attribute("query_length", len(query))

            if not _load_index():
                return []

            q_vec = _embed_query(query)
            distances, indices = _index.search(q_vec, top_k)

            results = []
            for dist, idx in zip(distances[0], indices[0]):
                if idx < 0 or idx >= len(_metadata):
                    continue

                part = _metadata[int(idx)]
                results.append(part)

            span.set_attribute("results_count", len(results))
            return results

        except Exception as e:
            errors_total.labels("vectorstore").inc()
            span.record_exception(e)
            raise
