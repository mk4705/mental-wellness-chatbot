import os
import json
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

# CONFIG
KNOWLEDGE_FOLDER = "rag/knowledge"
INDEX_PATH = "rag/index.faiss"
METADATA_PATH = "rag/metadata.json"
CHUNK_SIZE = 300  # characters per chunk (simple version)
CHUNK_OVERLAP = 50

print("Loading embedding model...")
model = SentenceTransformer("all-MiniLM-L6-v2")

def chunk_text(text, chunk_size=300, overlap=50):
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks

all_chunks = []
metadata = []

print("Reading knowledge files...")

for filename in os.listdir(KNOWLEDGE_FOLDER):
    if filename.endswith(".txt"):
        filepath = os.path.join(KNOWLEDGE_FOLDER, filename)

        with open(filepath, "r", encoding="utf-8") as f:
            text = f.read()

        chunks = chunk_text(text, CHUNK_SIZE, CHUNK_OVERLAP)

        for chunk in chunks:
            all_chunks.append(chunk)
            metadata.append({
                "source": filename,
                "content": chunk
            })

print(f"Total chunks created: {len(all_chunks)}")

print("Generating embeddings...")
embeddings = model.encode(all_chunks, show_progress_bar=True)

embeddings = np.array(embeddings).astype("float32")

dimension = embeddings.shape[1]
index = faiss.IndexFlatL2(dimension)
index.add(embeddings)

print("Saving FAISS index...")
faiss.write_index(index, INDEX_PATH)

print("Saving metadata...")
with open(METADATA_PATH, "w", encoding="utf-8") as f:
    json.dump(metadata, f, indent=2)

print("Done! Hybrid RAG index built successfully.")