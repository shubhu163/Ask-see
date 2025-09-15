## Polyglot FAQ Chat

End-to-end RAG app using FastAPI + LangChain + Google embeddings + Hugging Face.

### 1) Setup
```
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
cp env.example .env
# Fill GOOGLE_API_KEY and HUGGINGFACEHUB_API_TOKEN in .env
```

### 2) Run
```
uvicorn app.main:app --reload --port 8000
```

### 3) Test
```
curl -X POST http://localhost:8000/ingest -H "Content-Type: application/json" -d '[
  {"text":"FastAPI is a modern web framework for building APIs with Python.", "source":"notes", "title":"fastapi"}
]'

curl -X POST http://localhost:8000/ask -H "Content-Type: application/json" -d '{"question":"FastAPI क्या है?", "k":4}'
```

### 4) Docker
```
docker build -t polyglot-faq-chat .
docker run -p 8000:8000 --env-file .env -v $(pwd)/.chroma:/app/.chroma polyglot-faq-chat
```

### Env vars
- GOOGLE_API_KEY
- CHROMA_DIR (default .chroma)
- OLLAMA_MODEL (default llama3.1:8b-instruct)
- OLLAMA_BASE_URL (default http://127.0.0.1:11434)

### Use Ollama locally
1) Install: `brew install --cask ollama`
2) Start app (Ollama daemon)
3) Pull a model: `ollama pull llama3.1:8b-instruct`
4) Run API and test as below


