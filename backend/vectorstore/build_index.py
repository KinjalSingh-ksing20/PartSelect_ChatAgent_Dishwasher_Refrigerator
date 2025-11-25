# backend/vectorstore/build_index.py

import json
import os
import faiss
import numpy as np
from tqdm import tqdm
from sentence_transformers import SentenceTransformer

# Load local embedding model (no API needed)
model = SentenceTransformer("all-MiniLM-L6-v2")

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "parts.json")
OUT_INDEX = os.path.join(os.path.dirname(__file__), "index.faiss")
OUT_META = os.path.join(os.path.dirname(__file__), "parts_metadata.json")


def embed_text(text: str):
    """Local embedding model — no API key, no errors."""
    return model.encode(text).tolist()


def combine_fields(item):
    """Turn a part into a single search-friendly text blob."""
    fields = [
        item.get("name") or "",
        item.get("description") or "",
        " ".join(item.get("compatible_models", [])),
        " ".join(item.get("symptoms", [])),
        " ".join(item.get("installation_texts", [])),
        " ".join(item.get("troubleshooting_texts", [])),
    ]
    return " ".join(fields)


def main():
    with open(DATA_PATH, "r") as f:
        parts = json.load(f)

    print(f"[INDEX] Loaded {len(parts)} parts")

    embeddings = []
    metadata = []

    for item in tqdm(parts, desc="Embedding"):
        text = combine_fields(item)
        vec = embed_text(text)
        embeddings.append(vec)
        metadata.append(item)

    # Convert to numpy
    matrix = np.array(embeddings).astype("float32")

    # Build FAISS index
    dim = len(embeddings[0])
    index = faiss.IndexFlatL2(dim)
    index.add(matrix)

    # Save index + metadata
    faiss.write_index(index, OUT_INDEX)

    with open(OUT_META, "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"[INDEX] Saved FAISS index → {OUT_INDEX}")
    print(f"[INDEX] Saved metadata → {OUT_META}")


if __name__ == "__main__":
    main()
