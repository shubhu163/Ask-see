SHELL := /bin/bash

.PHONY: setup frontend backend run docker-build docker-run 

setup:
	python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt

frontend:
	cd frontend && npm ci && npm run build && rm -rf ../app/static/spa && mkdir -p ../app/static/spa && cp -R dist/* ../app/static/spa/

backend:
	uvicorn app.main:app --host 0.0.0.0 --port 8000

run: frontend backend

docker-build:
	docker build -t ask-and-see:latest .

docker-run:
	docker run --rm -p 8080:8080 -e GOOGLE_API_KEY -e GENERATOR_MODEL=gemini-2.5-flash-lite -e CHROMA_DIR=/data/chroma -v $$PWD/.chroma:/data/chroma ask-and-see:latest


clean:
	rm -rf .venv .chroma app/static/spa

