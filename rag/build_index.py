import os
import faiss
import pickle
from sentence_transformers import SentenceTransformer

# Load embedding model
model = SentenceTransformer("all-MiniLM-L6-v2")

KNOWLEDGE_DIR = "knowledge"
INDEX_PATH = "rag/faiss.index"
META_PATH = "rag/meta.pkl"

documents = []
metadatas = []

# Read all text files
for filename in os.listdir(KNOWLEDGE_DIR):
    if filename.endswith(".txt"):
        path = os.path.join(KNOWLEDGE_DIR, filename)
        with open(path, "r", encoding="utf-8") as f:
            text = f.read().strip()
            if text:
                documents.append(text)
                metadatas.append({"source": filename})

print(f"Loaded {len(documents)} documents")

# Generate embeddings
embeddings = model.encode(documents)

# Create FAISS index
dimension = embeddings.shape[1]
index = faiss.IndexFlatL2(dimension)
index.add(embeddings)

# Save index and metadata
faiss.write_index(index, INDEX_PATH)
with open(META_PATH, "wb") as f:
    pickle.dump(metadatas, f)

print("FAISS index built and saved")
