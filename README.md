# RuleLens

Conflict-aware RAG for policy and rulebook documents.

## Stack
- Next.js + TypeScript + Tailwind
- FastAPI + Python
- LangChain
- PyMuPDF
- ChromaDB
- OpenAI embeddings + LLM

## Run locally

### Backend
```bash
cd backend
python -m venv venv
# Windows PowerShell:
.env\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
# Add OPENAI_API_KEY to .env
uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
copy .env.example .env.local
npm run dev
```

Open http://localhost:3000

## RAG flow

Document → extraction → chunking → embeddings → ChromaDB → semantic retrieval → conflict/exception analysis → grounded LLM answer → sources/evidence.

## GitHub

Never commit `.env`, API keys, `venv`, uploads, or `chroma_db`.
