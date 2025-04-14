import faiss
import numpy as np
import pickle
from sentence_transformers import SentenceTransformer
from services.document_loader import load_and_chunk_documents
from services.logging_service import log_audit  # Add this if logging is desired

# Where we store the index + metadata
INDEX_FILE = "vector_index/faiss.index"
META_FILE = "vector_index/meta.pkl"

# Load embedding model (local, fast)
model = SentenceTransformer("all-MiniLM-L6-v2")

def build_vector_index():
    print("🔄 Loading and chunking documents...")
    chunks = load_and_chunk_documents()

    texts = [chunk["text"] for chunk in chunks]
    embeddings = model.encode(texts, show_progress_bar=True, convert_to_numpy=True)

    index = faiss.IndexFlatL2(embeddings.shape[1])
    index.add(embeddings)

    # Save index with error handling
    try:
        faiss.write_index(index, INDEX_FILE)
        with open(META_FILE, "wb") as f:
            pickle.dump(chunks, f)
        print(f"✅ Indexed {len(chunks)} chunks.")
        log_audit(None, "build_vector_index", {"chunk_count": len(chunks)})  # Optional
    except Exception as e:
        print(f"❌ Failed to save index: {e}")
        raise

def semantic_search(query, top_k=5):
    try:
        index = faiss.read_index(INDEX_FILE)
        with open(META_FILE, "rb") as f:
            metadata = pickle.load(f)
    except Exception as e:
        print(f"❌ Failed to load index/metadata: {e}")
        return []

    query_vec = model.encode([query], convert_to_numpy=True)
    D, I = index.search(query_vec, top_k)

    results = [metadata[i] for i in I[0] if i < len(metadata)]  # Guard against index out of bounds
    return results