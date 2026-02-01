import faiss
import pickle
from sentence_transformers import SentenceTransformer

# Load once (important for performance)
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

index = faiss.read_index("rag/faiss.index")
with open("rag/meta.pkl", "rb") as f:
    metadata = pickle.load(f)

def retrieve_knowledge(query, k=2):
    """
    Retrieve top-k relevant knowledge chunks for a query
    """
    query_embedding = embedding_model.encode([query])
    distances, indices = index.search(query_embedding, k)

    results = []
    for idx in indices[0]:
        results.append(metadata[idx]["source"])

    return results
    