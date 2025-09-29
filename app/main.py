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


# Load .env from project root and let .env override existing envs in this process
project_root = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=project_root / ".env", override=True)
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

# Optional React SPA (Embeddings visualization) served at /spa
spa_dir = static_dir / "spa"

@app.get("/spa")
def serve_spa():
    index_file = spa_dir / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    raise HTTPException(status_code=404, detail="SPA not found")

# The Vite build expects /assets and /vite.svg at root
if (spa_dir / "assets").exists():
    app.mount("/assets", StaticFiles(directory=str(spa_dir / "assets")), name="assets")

@app.get("/vite.svg")
def vite_svg():
    svg = spa_dir / "vite.svg"
    if svg.exists():
        return FileResponse(str(svg))
    raise HTTPException(status_code=404, detail="vite.svg not found")

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "").strip()
CHROMA_DIR = os.getenv("CHROMA_DIR", ".chroma").strip()
GENERATOR_MODEL = os.getenv("GENERATOR_MODEL", "gemma-2-2b-it").strip()

if not GOOGLE_API_KEY:
    raise RuntimeError(
        "GOOGLE_API_KEY is missing. Fill it in .env or set the env var before starting the server."
    )
rag = RAGService(
    persist_dir=CHROMA_DIR,
    google_api_key=GOOGLE_API_KEY,
    generator_model=GENERATOR_MODEL,
)


@app.get("/health")
def health():
    return {"ok": True}

@app.get("/")
def root_redirect():
    # Serve SPA as the single UI
    return RedirectResponse(url="/spa")

@app.get("/ui")
def serve_ui():
    # Back-compat: redirect old /ui to SPA
    return RedirectResponse(url="/spa")


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


@app.post("/clear")
def clear():
    ok = rag.clear()
    return {"ok": bool(ok)}

