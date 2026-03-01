import os
import json
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

# Paths
BASE_DIR = os.path.dirname(__file__)
INDEX_PATH = os.path.join(BASE_DIR, "index.faiss")
METADATA_PATH = os.path.join(BASE_DIR, "metadata.json")

# Load once at startup
print("Loading FAISS index...")
index = faiss.read_index(INDEX_PATH)

print("Loading metadata...")
with open(METADATA_PATH, "r", encoding="utf-8") as f:
    metadata = json.load(f)

print("Loading embedding model...")
model = SentenceTransformer("all-MiniLM-L6-v2")

def retrieve_knowledge(query, k=2):
    """
    Returns top-k most relevant knowledge chunks.
    """

    query_embedding = model.encode([query])
    query_embedding = np.array(query_embedding).astype("float32")

    distances, indices = index.search(query_embedding, k)

    results = []
    for idx in indices[0]:
        if idx < len(metadata):
            results.append(metadata[idx]["content"])

    return results