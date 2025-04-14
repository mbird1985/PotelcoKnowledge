import os
import fitz  # PyMuPDF
from config import DOCUMENT_FOLDER

CHUNK_SIZE = 500  # Characters per chunk (adjustable)


def load_and_chunk_documents():
    all_chunks = []

    for filename in os.listdir(DOCUMENT_FOLDER):
        if not filename.lower().endswith((".pdf", ".txt")):
            continue

        filepath = os.path.join(DOCUMENT_FOLDER, filename)

        if filename.lower().endswith(".pdf"):
            chunks = parse_pdf(filepath, filename)
        else:
            chunks = parse_txt(filepath, filename)

        all_chunks.extend(chunks)

    return all_chunks


def parse_pdf(filepath, source):
    doc = fitz.open(filepath)
    chunks = []
    for page_number, page in enumerate(doc, start=1):
        text = page.get_text("text")
        page_chunks = chunk_text(text, CHUNK_SIZE)
        for i, chunk in enumerate(page_chunks):
            chunks.append({
                "text": chunk,
                "source": source,
                "page": page_number,
                "chunk_id": f"{source}_p{page_number}_c{i}"
            })
    return chunks


def parse_txt(filepath, source):
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()
    chunks = chunk_text(text, CHUNK_SIZE)
    return [
        {
            "text": chunk,
            "source": source,
            "page": None,
            "chunk_id": f"{source}_c{i}"
        }
        for i, chunk in enumerate(chunks)
    ]


def chunk_text(text, size):
    # Break into paragraphs, then further into fixed-size chunks
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks = []
    for para in paragraphs:
        while len(para) > size:
            split_at = para.rfind(" ", 0, size)
            if split_at == -1:
                split_at = size
            chunks.append(para[:split_at].strip())
            para = para[split_at:].strip()
        if para:
            chunks.append(para)
    return chunks
