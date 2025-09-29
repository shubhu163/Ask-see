## Ask & See — Explainable RAG Chatbot

Ask questions, get answers, and see a live 2D/3D map of your knowledge base (Google embeddings + PCA).

### 1) Prereqs
- Python 3.11
- A Google API key for `models/text-embedding-004`

### 2) Setup
```
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
export GOOGLE_API_KEY="YOUR_KEY"
export GENERATOR_MODEL="gemma-2-2b-it"  # optional; default is gemma-2-2b-it
export CHROMA_DIR=".chroma"             # optional; default is .chroma
```

The app uses Google Generative AI for both embeddings and generation; no local model needed.

### 3) Build frontend once (served by FastAPI as SPA)
```
cd frontend
npm ci
npm run build
rm -rf ../app/static/spa && mkdir -p ../app/static/spa && cp -R dist/* ../app/static/spa/
cd ..
```

### 4) Run backend
```
uvicorn app.main:app --host 0.0.0.0 --port 8000
```
Open http://127.0.0.1:8000/spa

### 5) Demo flow
1. Ingest 2+ snippets (Ingest panel) → Refresh in Embeddings Visualization.
2. Toggle 2D/3D, hover points for titles/snippets.
3. Ask questions; answers include cited sources.

### API quick test
```
curl -X POST http://127.0.0.1:8000/ingest -H "Content-Type: application/json" -d '[
  {"text":"RAG combines a vector store and a generator.", "source":"demo", "title":"RAG Basics"}
]'

curl -X POST http://127.0.0.1:8000/ask -H "Content-Type: application/json" -d '{"question":"What is RAG?", "k":4}'
```

### Notes
- Chroma persists under `.chroma/`; delete it to reset the KB.
- The React SPA is bundled into `app/static/spa/` and served by FastAPI at `/spa`.


