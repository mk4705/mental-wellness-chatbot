import os
import json
import faiss
import numpy as np
import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

INDEX_PATH = os.path.join(BASE_DIR, "index.faiss")
META_PATH = os.path.join(BASE_DIR, "metadata.json")

# Load FAISS index once
index = faiss.read_index(INDEX_PATH)

# Load metadata once
with open(META_PATH, "r", encoding="utf-8") as f:
    metadata = json.load(f)

HF_API_KEY = os.getenv("HF_API_KEY")

EMBEDDING_API_URL = "https://api-inference.huggingface.co/pipeline/feature-extraction/sentence-transformers/all-MiniLM-L6-v2"

headers = {
    "Authorization": f"Bearer {HF_API_KEY}"
}


def embed_query(text):
    response = requests.post(
        EMBEDDING_API_URL,
        headers=headers,
        json={"inputs": text}
    )

    if response.status_code != 200:
        raise RuntimeError("HF embedding API failed")

    embedding = response.json()

    # Convert to numpy array
    return np.array(embedding, dtype="float32")


def retrieve_knowledge(query, k=2):
    query_vector = embed_query(query)

    # FAISS expects 2D array
    query_vector = np.expand_dims(query_vector, axis=0)

    distances, indices = index.search(query_vector, k)

    results = []
    for idx in indices[0]:
        if idx < len(metadata):
            results.append(metadata[idx])

    return results