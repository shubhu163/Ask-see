import os
from typing import List

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, FileResponse
from pathlib import Path
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import io
import requests
from pypdf import PdfReader
import docx

from app.core.rag import RAGService
from app.schemas import IngestItem, AskPayload


load_dotenv()
app = FastAPI(title="Polyglot FAQ Chat")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

static_dir = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "").strip()
CHROMA_DIR = os.getenv("CHROMA_DIR", ".chroma").strip()
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b-instruct").strip()
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").strip()

if not GOOGLE_API_KEY:
    raise RuntimeError(
        "GOOGLE_API_KEY is missing. Fill it in .env or set the env var before starting the server."
    )
rag = RAGService(
    persist_dir=CHROMA_DIR,
    google_api_key=GOOGLE_API_KEY,
    ollama_model=OLLAMA_MODEL,
    ollama_base_url=OLLAMA_BASE_URL,
)


@app.get("/health")
def health():
    return {"ok": True}

@app.get("/")
def root_redirect():
    return RedirectResponse(url="/ui")

@app.get("/ui")
def serve_ui():
    index_file = static_dir / "index.html"
    return FileResponse(str(index_file))


def _fetch_url_text(url: str) -> str:
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    ctype = r.headers.get("content-type", "")
    if "html" in ctype:
        soup = BeautifulSoup(r.text, "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        return soup.get_text(separator="\n")
    return r.text


@app.post("/ingest")
def ingest(items: List[IngestItem]):
    docs = []
    for it in items:
        content = (it.text or "").strip()
        if not content and it.url:
            try:
                content = _fetch_url_text(it.url)
            except Exception:
                continue
        if content:
            docs.append({"text": content, "source": it.source or "user", "title": it.title or ""})
    added = rag.ingest(docs)
    return {"added_chunks": added}


MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10MB


@app.post("/ingest-file")
async def ingest_file(file: UploadFile = File(...), source: str = Form("upload"), title: str = Form("")):
    content = ""
    try:
        # size guard (reads stream in memory; for huge files use tempfile + stream)
        blob = await file.read()
        if len(blob) > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail="File too large (>10MB)")
        name = file.filename.lower()
        if file.filename.lower().endswith((".pdf",)):
            reader = PdfReader(io.BytesIO(blob))
            pages = [page.extract_text() or "" for page in reader.pages]
            content = "\n\n".join(pages)
        elif file.filename.lower().endswith((".docx",)):
            with open("/tmp/_docx_upload.docx", "wb") as f:
                f.write(blob)
            document = docx.Document("/tmp/_docx_upload.docx")
            content = "\n".join([p.text for p in document.paragraphs])
        else:
            content = blob.decode(errors="ignore")
    except Exception:
        content = ""
    if not content.strip():
        return {"added_chunks": 0}
    added = rag.ingest([{"text": content, "source": source or "upload", "title": title or file.filename}])
    return {"added_chunks": added}

@app.post("/ask")
def ask(payload: AskPayload):
    return rag.ask(payload.question, payload.k)


@app.get("/embeddings")
def embeddings(limit: int = 500, offset: int = 0):
    return rag.list_embeddings(limit=limit, offset=offset)

