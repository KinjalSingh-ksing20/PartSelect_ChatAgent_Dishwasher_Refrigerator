import json
import os
import faiss
import numpy as np
from tqdm import tqdm
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("all-MiniLM-L6-v2")

DATA_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data", "full_catalog.json"
)

OUT_INDEX = os.path.join(os.path.dirname(__file__), "index.faiss")
OUT_META = os.path.join(os.path.dirname(__file__), "parts_metadata.json")


def embed_text(text: str):
    return model.encode(text).tolist()


def combine_fields(item):
    """Combine rich schema fields into a single semantic embedding blob."""
    fields = [
        item.get("name", ""),
        item.get("brand", ""),
        item.get("category", ""),
        item.get("description", ""),
        " ".join(item.get("symptoms_vector", [])),
        item.get("installation_guide_markdown", ""),
        item.get("troubleshooting_tips", ""),
        " ".join(item.get("compatible_models", [])),
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

   
    matrix = np.array(embeddings).astype("float32")

    #  FAISS index
    dim = matrix.shape[1]
    index = faiss.IndexFlatL2(dim)
    index.add(matrix)

    # index + metadata
    faiss.write_index(index, OUT_INDEX)

    with open(OUT_META, "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"[INDEX] Saved FAISS index → {OUT_INDEX}")
    print(f"[INDEX] Saved metadata → {OUT_META}")


if __name__ == "__main__":
    main()
