import os
import json
from pathlib import Path
from collections import defaultdict

from dotenv import load_dotenv

load_dotenv()

import chromadb
from langchain_chroma import Chroma
from langchain_google_genai import (
    ChatGoogleGenerativeAI,
    GoogleGenerativeAIEmbeddings,
)


PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIRECTORY", "./chroma_db")
COLLECTION = "rulelens_documents"


def get_embeddings():
    return GoogleGenerativeAIEmbeddings(
        model=os.getenv("EMBEDDING_MODEL", "gemini-embedding-001")
    )


def get_vectorstore():
    Path(PERSIST_DIR).mkdir(parents=True, exist_ok=True)

    return Chroma(
        collection_name=COLLECTION,
        persist_directory=PERSIST_DIR,
        embedding_function=get_embeddings(),
    )


def list_documents():
    client = chromadb.PersistentClient(path=PERSIST_DIR)

    try:
        collection = client.get_collection(COLLECTION)
    except Exception:
        return []

    data = collection.get(include=["metadatas"])

    grouped = defaultdict(
        lambda: {
            "chunks": 0,
            "filename": "",
            "pages": set(),
        }
    )

    for metadata in data.get("metadatas", []):
        if not metadata:
            continue

        did = metadata["document_id"]

        grouped[did]["chunks"] += 1
        grouped[did]["filename"] = metadata["document_name"]
        grouped[did]["pages"].add(
            metadata.get("page_number", 1)
        )

    return [
        {
            "document_id": did,
            "filename": item["filename"],
            "chunks": item["chunks"],
            "pages": len(item["pages"]),
            "status": "processed",
        }
        for did, item in grouped.items()
    ]


def delete_document(document_id: str):
    client = chromadb.PersistentClient(path=PERSIST_DIR)

    try:
        collection = client.get_collection(COLLECTION)
    except Exception:
        return False

    found = collection.get(
        where={"document_id": document_id}
    )

    ids = found.get("ids", [])

    if not ids:
        return False

    collection.delete(ids=ids)

    return True


def _llm():
    return ChatGoogleGenerativeAI(
        model=os.getenv(
            "LLM_MODEL",
            "gemini-3.1-flash-lite",
        ),
        temperature=0,
    )


def ask_question(question: str, top_k: int = 5):
    store = get_vectorstore()

    results = store.similarity_search_with_relevance_scores(
        question,
        k=top_k,
    )

    evidence = [
        (doc, score)
        for doc, score in results
        if score
        >= float(
            os.getenv(
                "RELEVANCE_THRESHOLD",
                "0.35",
            )
        )
    ]

    if not evidence:
        return {
            "status": "INSUFFICIENT_INFORMATION",
            "answer": (
                "The uploaded documents do not contain "
                "enough relevant information to answer "
                "this question."
            ),
            "summary": (
                "No sufficiently relevant evidence was retrieved."
            ),
            "conflict_detected": False,
            "conflict_type": "none",
            "conflict_explanation": None,
            "sources": [],
            "evidence": [],
        }

    evidence_text = "\n\n".join(
        f"[SOURCE {i + 1}]\n"
        f"Document: {doc.metadata.get('document_name')}\n"
        f"Page: {doc.metadata.get('page_number')}\n"
        f"Text: {doc.page_content}"
        for i, (doc, _) in enumerate(evidence)
    )

    system = """You are RuleLens, a conflict-aware policy document assistant.

Answer ONLY from the supplied evidence.

Never invent rules, facts, citations, or page numbers.

Classify the evidence as:

- ANSWERED: enough evidence gives a clear answer.
- CONFLICT: genuinely contradictory applicable rules remain and cannot be resolved by an exception or override.
- INSUFFICIENT_INFORMATION: evidence does not contain enough information.

Important:

An exception or override is NOT automatically a conflict.

If one rule explicitly applies to a special case, explain it as an exception.

Return valid JSON only with:

{
  "status": "ANSWERED|CONFLICT|INSUFFICIENT_INFORMATION",
  "answer": "...",
  "summary": "...",
  "conflict_detected": true|false,
  "conflict_type": "contradiction|exception|none",
  "conflict_explanation": "..." or null,
  "used_source_indexes": [1,2]
}
"""

    prompt = (
        f"{system}\n\n"
        f"USER QUESTION:\n{question}\n\n"
        f"EVIDENCE:\n{evidence_text}"
    )

    response = _llm().invoke(prompt)

    content = response.content

    if isinstance(content, list):
        raw = "".join(
            item.get("text", "")
            if isinstance(item, dict)
            else str(item)
            for item in content
        ).strip()
    else:
        raw = str(content).strip()

    try:
        parsed = json.loads(raw)

    except json.JSONDecodeError:
        parsed = {
            "status": "ANSWERED",
            "answer": raw,
            "summary": (
                "Answer generated from retrieved evidence."
            ),
            "conflict_detected": False,
            "conflict_type": "none",
            "conflict_explanation": None,
            "used_source_indexes": list(
                range(1, len(evidence) + 1)
            ),
        }

    used = (
        parsed.get("used_source_indexes")
        or list(range(1, len(evidence) + 1))
    )

    used = [
        i
        for i in used
        if isinstance(i, int)
        and 1 <= i <= len(evidence)
    ]

    sources = []
    evidence_out = []

    for i in used:
        doc, score = evidence[i - 1]
        meta = doc.metadata

        sources.append(
            {
                "document": meta.get("document_name"),
                "page": meta.get("page_number"),
                "section": meta.get("section"),
                "relevance": round(float(score), 3),
            }
        )

        evidence_out.append(
            {
                "text": doc.page_content,
                "document": meta.get("document_name"),
                "page": meta.get("page_number"),
                "relevance": round(float(score), 3),
            }
        )

    return {
        "status": parsed.get(
            "status",
            "ANSWERED",
        ),
        "answer": parsed.get(
            "answer",
            "",
        ),
        "summary": parsed.get(
            "summary",
            "",
        ),
        "conflict_detected": bool(
            parsed.get(
                "conflict_detected",
                False,
            )
        ),
        "conflict_type": parsed.get(
            "conflict_type",
            "none",
        ),
        "conflict_explanation": parsed.get(
            "conflict_explanation"
        ),
        "sources": sources,
        "evidence": evidence_out,
    }
# import os
# from pathlib import Path
# from collections import defaultdict
# from dotenv import load_dotenv

# load_dotenv()

# import chromadb
# from langchain_chroma import Chroma
# from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings

# PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIRECTORY", "./chroma_db")
# COLLECTION = "rulelens_documents"

# def get_embeddings():
#     return GoogleGenerativeAIEmbeddings(
#         model=os.getenv("EMBEDDING_MODEL", "gemini-embedding-001")
#     )

# def get_vectorstore():
#     Path(PERSIST_DIR).mkdir(parents=True, exist_ok=True)
#     return Chroma(
#         collection_name=COLLECTION,
#         persist_directory=PERSIST_DIR,
#         embedding_function=get_embeddings(),
#     )

# def list_documents():
#     client = chromadb.PersistentClient(path=PERSIST_DIR)
#     try:
#         collection = client.get_collection(COLLECTION)
#     except Exception:
#         return []

#     data = collection.get(include=["metadatas"])
#     grouped = defaultdict(lambda: {"chunks": 0, "filename": "", "pages": set()})
#     for metadata in data.get("metadatas", []):
#         if not metadata:
#             continue
#         did = metadata["document_id"]
#         grouped[did]["chunks"] += 1
#         grouped[did]["filename"] = metadata["document_name"]
#         grouped[did]["pages"].add(metadata.get("page_number", 1))

#     return [
#         {
#             "document_id": did,
#             "filename": item["filename"],
#             "chunks": item["chunks"],
#             "pages": len(item["pages"]),
#             "status": "processed",
#         }
#         for did, item in grouped.items()
#     ]

# def delete_document(document_id: str):
#     client = chromadb.PersistentClient(path=PERSIST_DIR)
#     try:
#         collection = client.get_collection(COLLECTION)
#     except Exception:
#         return False

#     found = collection.get(where={"document_id": document_id})
#     ids = found.get("ids", [])
#     if not ids:
#         return False
#     collection.delete(ids=ids)
#     return True

# def _llm():
#     return ChatGoogleGenerativeAI(
#         model=os.getenv("LLM_MODEL", "gemini-3.1-flash-lite"),
#         temperature=0,
#     )

# def ask_question(question: str, top_k: int = 5):
#     store = get_vectorstore()
#     results = store.similarity_search_with_relevance_scores(question, k=top_k)

#     # Keep only useful evidence. Chroma relevance scores vary by embedding setup;
#     # this threshold is intentionally conservative for an MVP.
#     evidence = [
#         (doc, score) for doc, score in results
#         if score >= float(os.getenv("RELEVANCE_THRESHOLD", "0.35"))
#     ]

#     if not evidence:
#         return {
#             "status": "INSUFFICIENT_INFORMATION",
#             "answer": "The uploaded documents do not contain enough relevant information to answer this question.",
#             "summary": "No sufficiently relevant evidence was retrieved.",
#             "conflict_detected": False,
#             "conflict_type": "none",
#             "conflict_explanation": None,
#             "sources": [],
#             "evidence": [],
#         }

#     evidence_text = "\n\n".join(
#         f"[SOURCE {i+1}]\n"
#         f"Document: {doc.metadata.get('document_name')}\n"
#         f"Page: {doc.metadata.get('page_number')}\n"
#         f"Text: {doc.page_content}"
#         for i, (doc, _) in enumerate(evidence)
#     )

#     system = """You are RuleLens, a conflict-aware policy document assistant.
# Answer ONLY from the supplied evidence. Never invent rules, facts, citations, or page numbers.

# Classify the evidence as:
# - ANSWERED: enough evidence gives a clear answer.
# - CONFLICT: genuinely contradictory applicable rules remain and cannot be resolved by an exception/override.
# - INSUFFICIENT_INFORMATION: evidence does not contain enough information.

# Important:
# An exception or override is NOT automatically a conflict. If one rule explicitly applies to a special case, explain it as an exception.

# Return valid JSON only with:
# {
#   "status": "ANSWERED|CONFLICT|INSUFFICIENT_INFORMATION",
#   "answer": "...",
#   "summary": "...",
#   "conflict_detected": true|false,
#   "conflict_type": "contradiction|exception|none",
#   "conflict_explanation": "..." or null,
#   "used_source_indexes": [1,2]
# }
# """

#     prompt = f"{system}\n\nUSER QUESTION:\n{question}\n\nEVIDENCE:\n{evidence_text}"
#         response = _llm().invoke(prompt)
#     content = response.content

#     if isinstance(content, list):
#         raw = "".join(
#             item.get("text", "") if isinstance(item, dict) else str(item)
#             for item in content
#         ).strip()
#     else:
#         raw = str(content).strip()

#     import json

#     try:
#         parsed = json.loads(raw)
#     except json.JSONDecodeError:
#         parsed = {
#             "status": "ANSWERED",
#             "answer": raw,
#             "summary": "Answer generated from retrieved evidence.",
#             "conflict_detected": False,
#             "conflict_type": "none",
#             "conflict_explanation": None,
#             "used_source_indexes": list(range(1, len(evidence) + 1)),
#         }

#     used = parsed.get("used_source_indexes") or list(range(1, len(evidence) + 1))
#     used = [
#         i for i in used
#         if isinstance(i, int) and 1 <= i <= len(evidence)
#     ]

#     sources, evidence_out = [], []

#     for i in used:
#         doc, score = evidence[i - 1]
#         meta = doc.metadata

#         sources.append({
#             "document": meta.get("document_name"),
#             "page": meta.get("page_number"),
#             "section": meta.get("section"),
#             "relevance": round(float(score), 3),
#         })

#         evidence_out.append({
#             "text": doc.page_content,
#             "document": meta.get("document_name"),
#             "page": meta.get("page_number"),
#             "relevance": round(float(score), 3),
#         })

#     return {
#         "status": parsed.get("status", "ANSWERED"),
#         "answer": parsed.get("answer", ""),
#         "summary": parsed.get("summary", ""),
#         "conflict_detected": bool(parsed.get("conflict_detected", False)),
#         "conflict_type": parsed.get("conflict_type", "none"),
#         "conflict_explanation": parsed.get("conflict_explanation"),
#         "sources": sources,
#         "evidence": evidence_out,
#     }