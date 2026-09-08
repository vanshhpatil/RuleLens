from pathlib import Path
import hashlib
import re
import fitz

from langchain_text_splitters import RecursiveCharacterTextSplitter
from .retrieval_service import get_vectorstore

def extract_pages(path: Path):
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        doc = fitz.open(path)
        return [(i + 1, page.get_text("text")) for i, page in enumerate(doc)]
    return [(1, path.read_text(encoding="utf-8", errors="ignore"))]

def clean_text(text: str):
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

def process_document(path: Path, original_name: str, document_id: str):
    pages = [(page, clean_text(text)) for page, text in extract_pages(path)]
    pages = [(p, t) for p, t in pages if t]

    if not pages:
        raise ValueError("No readable text was found.")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1100,
        chunk_overlap=150,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    texts, metadatas, ids = [], [], []
    for page_number, text in pages:
        chunks = splitter.split_text(text)
        for index, chunk in enumerate(chunks):
            chunk_id = hashlib.md5(
                f"{document_id}:{page_number}:{index}:{chunk}".encode()
            ).hexdigest()
            texts.append(chunk)
            metadatas.append({
                "document_id": document_id,
                "document_name": original_name,
                "page_number": page_number,
                "chunk_id": chunk_id,
            })
            ids.append(chunk_id)

    vectorstore = get_vectorstore()
    vectorstore.add_texts(texts=texts, metadatas=metadatas, ids=ids)

    return {
        "document_id": document_id,
        "filename": original_name,
        "chunks_created": len(texts),
        "pages": len(pages),
        "status": "processed",
    }
