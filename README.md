## Ask & See — Explainable RAG Chatbot

Ask questions, get answers, and see a live 2D/3D map of your knowledge base (Google embeddings + PCA).

### 1) Prereqs
- Python 3.11
- Ollama running locally (for generation)
- A Google API key for `models/text-embedding-004`

### 2) Setup
```
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
export GOOGLE_API_KEY="YOUR_KEY"
export OLLAMA_BASE_URL="http://127.0.0.1:11434"
export OLLAMA_MODEL="llama3.2:3b-instruct"
export CHROMA_DIR=".chroma"
```

Start Ollama in another terminal and pull a small model:
```
ollama serve
ollama pull llama3.2:3b-instruct
```

### 3) Build frontend once (served by FastAPI)
```
cd frontend
npm ci
npm run build
rm -rf ../app/static/* && cp -R dist/* ../app/static/
cd ..
```

### 4) Run backend
```
uvicorn app.main:app --host 0.0.0.0 --port 8000
```
Open http://127.0.0.1:8000/ui

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
- The React app is bundled into `app/static/` and served by FastAPI.


