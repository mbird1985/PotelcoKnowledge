from services.vector_indexer import semantic_search
from services.ollama_llm import call_ollama


def generate_rag_response(query):
    # 1. Retrieve relevant chunks
    top_chunks = semantic_search(query, top_k=5)

    # 2. Build context prompt with citations
    context_blocks = []
    citations = []

    for i, chunk in enumerate(top_chunks):
        label = f"[{i + 1}] {chunk['source']} page {chunk.get('page', 'N/A')}"
        context_blocks.append(f"{label}:\n{chunk['text']}")
        citations.append(f"{label} → /documents/view/{chunk['source']}")

    context_prompt = "\n\n".join(context_blocks)

    full_prompt = f"""
You are a helpful assistant. Use the information below to answer the user's question.

Context:
{context_prompt}

Question: {query}
Answer:"""

    # 3. Call local LLaMA3 via Ollama
    raw_response = call_ollama(full_prompt)

    # 4. Append sources
    answer = f"{raw_response.strip()}\n\nSources:\n" + "\n".join(citations)
    return answer
