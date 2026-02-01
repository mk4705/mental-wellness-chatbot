import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

# Globals (lazy-loaded)
_model = None
_index = None
_memory_texts = []

DIMENSION = 384


def get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def get_index():
    global _index
    if _index is None:
        _index = faiss.IndexFlatL2(DIMENSION)
    return _index


def add_to_memory(text: str):
    model = get_model()
    index = get_index()

    embedding = model.encode([text])
    index.add(np.array(embedding))
    _memory_texts.append(text)


def retrieve_memory(query: str, k: int = 2):
    if len(_memory_texts) == 0:
        return []

    model = get_model()
    index = get_index()

    query_embedding = model.encode([query])
    distances, indices = index.search(np.array(query_embedding), k)

    return [
        _memory_texts[i]
        for i in indices[0]
        if i < len(_memory_texts)
    ]
