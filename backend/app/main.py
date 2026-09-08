from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path
import uuid
import shutil

from .services.document_service import process_document
from .services.retrieval_service import ask_question, list_documents, delete_document

app = FastAPI(title="RuleLens API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = Path("data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

class AskRequest(BaseModel):
    question: str
    top_k: int = 5

@app.get("/api/health")
def health():
    return {"status": "ok", "service": "RuleLens API"}

@app.get("/api/documents")
def documents():
    return {"documents": list_documents()}

@app.post("/api/documents/upload")
async def upload_document(file: UploadFile = File(...)):
    allowed = {".pdf", ".txt", ".md"}
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in allowed:
        raise HTTPException(400, "Only PDF, TXT and Markdown files are supported.")

    document_id = str(uuid.uuid4())
    destination = UPLOAD_DIR / f"{document_id}{suffix}"

    with destination.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        result = process_document(destination, file.filename, document_id)
        return result
    except Exception as exc:
        if destination.exists():
            destination.unlink()
        raise HTTPException(500, f"Could not process document: {exc}")

@app.delete("/api/documents/{document_id}")
def remove_document(document_id: str):
    result = delete_document(document_id)
    if not result:
        raise HTTPException(404, "Document not found.")
    return {"success": True}

@app.post("/api/questions/ask")
def question(request: AskRequest):
    if not request.question.strip():
        raise HTTPException(400, "Question cannot be empty.")
    return ask_question(request.question.strip(), request.top_k)
