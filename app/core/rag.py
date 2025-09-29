import os
import shutil
from pathlib import Path
from typing import List, Dict, Any

from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.vectorstores import Chroma
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.prompts import PromptTemplate
from langchain.chains import RetrievalQA


RAG_PROMPT = PromptTemplate.from_template(
    "You are a helpful assistant. Use the provided context to answer the question.\n"
    "- Cite sources by listing their titles at the end as [Sources: title1; title2].\n"
    "- If unsure, say you don't know.\n"
    "- Answer in the SAME LANGUAGE as the question.\n\n"
    "Context:\n{context}\n\nQuestion: {question}\nAnswer:"
)


class RAGService:
    def __init__(
        self,
        persist_dir: str,
        google_api_key: str,
        generator_model: str = "gemma-2-2b-it",
    ):
        # Remember persist directory for maintenance operations (e.g., clear)
        self.persist_dir = persist_dir
        os.environ["GOOGLE_API_KEY"] = google_api_key

        # Google embeddings (remote)
        self.embeddings = GoogleGenerativeAIEmbeddings(
            model="models/text-embedding-004",
            google_api_key=google_api_key,
        )

        # Vector store (disk persisted)
        self.vs = Chroma(
            collection_name="docs",
            embedding_function=self.embeddings,
            persist_directory=persist_dir,
        )

        # Chunker
        # Bigger chunks reduce number of embeddings → faster ingestion
        self.splitter = RecursiveCharacterTextSplitter(chunk_size=1200, chunk_overlap=100)

        # Generator backend: Google Generative AI (Gemma/Gemini via API key)
        self.llm = ChatGoogleGenerativeAI(
            model=generator_model,
            google_api_key=google_api_key,
            temperature=0.2,
        )

        # QA chain
        self.qa = RetrievalQA.from_chain_type(
            llm=self.llm,
            retriever=self.vs.as_retriever(search_type="mmr", search_kwargs={"k": 8, "fetch_k": 20, "lambda_mult": 0.5}),
            chain_type="stuff",
            return_source_documents=True,
            chain_type_kwargs={"prompt": RAG_PROMPT},
        )

    def ingest(self, docs: List[Dict[str, Any]]) -> int:
        texts, metas = [], []
        for d in docs:
            content = (d.get("text") or "").strip()
            if not content:
                continue
            for chunk in self.splitter.split_text(content):
                texts.append(chunk)
                metas.append({
                    "source": d.get("source", "user"),
                    "title": d.get("title", ""),
                })
        if not texts:
            return 0
        self.vs.add_texts(texts, metas)
        # Note: With Chroma >=0.4, persistence is automatic; calling persist() is harmless but deprecated.
        try:
            self.vs.persist()
        except Exception:
            pass
        return len(texts)

    def ask(self, question: str, k: int = 4) -> Dict[str, Any]:
        # Adjust MMR top-k on the fly
        try:
            self.qa.retriever.search_kwargs["k"] = max(1, int(k))
        except Exception:
            pass
        result = self.qa.invoke({"query": question})
        # Deduplicate by (title, source, snippet) to avoid repeated chunks
        seen = set()
        sources = []
        for d in result.get("source_documents", []):
            md = d.metadata or {}
            item = {
                "source": md.get("source", ""),
                "title": md.get("title", ""),
                "snippet": (d.page_content or "")[:300],
            }
            key = (item["title"], item["source"], item["snippet"]) 
            if key in seen:
                continue
            seen.add(key)
            sources.append(item)
        return {
            "answer": (result.get("result") or "").strip(),
            "sources": sources,
        }


    def list_embeddings(self, limit: int = 500, offset: int = 0) -> Dict[str, Any]:
        """Return raw embeddings with basic metadata for visualization."""
        try:
            # Access underlying Chroma collection to retrieve embeddings
            col = getattr(self.vs, "_collection", None)
            if col is None:
                return {"items": [], "total": 0}
            data = {}
            try:
                data = col.get(
                    include=["embeddings", "metadatas", "documents", "ids"],
                    limit=limit,
                    offset=offset,
                )
            except Exception:
                # chroma API versions differ; we'll fallback below
                data = {"ids": [], "embeddings": [], "metadatas": [], "documents": []}
            total = 0
            try:
                total = int(col.count())
            except Exception:
                total = len((data.get("ids", []) or []))

            ids = (data.get("ids", []) or [])
            embs = (data.get("embeddings", []) or [])
            metas = (data.get("metadatas", []) or [])
            docs = (data.get("documents", []) or [])

            # If nothing returned (or embeddings missing), try peek + compute embeddings on the fly
            if not ids:
                try:
                    peek = col.peek(limit=limit)
                    ids = (peek.get("ids", []) or [])
                    metas = (peek.get("metadatas", []) or [])
                    docs = (peek.get("documents", []) or [])
                except Exception:
                    ids, metas, docs = [], [], []

            if ids and (not embs or len(embs) != len(ids)):
                try:
                    # Compute embeddings client-side for visualization if server didn't return them
                    embs = self.embeddings.embed_documents(docs)
                except Exception:
                    embs = []

            items = []
            for i in range(min(len(ids), len(embs))):
                md = metas[i] or {}
                txt = (docs[i] or "")
                items.append({
                    "id": ids[i],
                    "embedding": embs[i],
                    "title": md.get("title", ""),
                    "source": md.get("source", ""),
                    "text": txt[:200],
                })
            return {"items": items, "total": total, "limit": limit, "offset": offset}
        except Exception:
            # Be conservative: if anything fails, return empty to avoid breaking UI
            return {"items": [], "total": 0, "limit": limit, "offset": offset}


    def clear(self) -> bool:
        """Clear all stored embeddings/documents from the vector store.

        Tries collection-wide delete; falls back to resetting the client and
        finally deleting the on-disk persistence directory.
        """
        # Preferred: drop the collection and recreate vector store + retriever
        try:
            collection = getattr(self.vs, "_collection", None)
            client = getattr(self.vs, "_client", None)
            name = None
            try:
                name = getattr(collection, "name", None) or "docs"
            except Exception:
                name = "docs"

            if client is not None and name:
                try:
                    client.delete_collection(name)
                except Exception:
                    # Fall back to deleting by ids
                    try:
                        data = collection.get(include=["ids"])  # type: ignore[attr-defined]
                        ids = (data.get("ids", []) or [])
                        if ids:
                            collection.delete(ids=ids)  # type: ignore[attr-defined]
                    except Exception:
                        pass

            # Recreate an empty vector store and QA chain so retriever is fresh
            self.vs = Chroma(
                collection_name="docs",
                embedding_function=self.embeddings,
                persist_directory=self.persist_dir,
            )
            self.qa = RetrievalQA.from_chain_type(
                llm=self.llm,
                retriever=self.vs.as_retriever(search_kwargs={"k": 4}),
                chain_type="stuff",
                return_source_documents=True,
                chain_type_kwargs={"prompt": RAG_PROMPT},
            )
            try:
                self.vs.persist()
            except Exception:
                pass
            return True
        except Exception:
            pass

        # Last resort: wipe the persistence directory on disk and rebuild
        try:
            p = Path(self.persist_dir).resolve()
            if p.exists():
                shutil.rmtree(str(p), ignore_errors=True)
            p.mkdir(parents=True, exist_ok=True)
            self.vs = Chroma(
                collection_name="docs",
                embedding_function=self.embeddings,
                persist_directory=self.persist_dir,
            )
            self.qa = RetrievalQA.from_chain_type(
                llm=self.llm,
                retriever=self.vs.as_retriever(search_kwargs={"k": 4}),
                chain_type="stuff",
                return_source_documents=True,
                chain_type_kwargs={"prompt": RAG_PROMPT},
            )
            return True
        except Exception:
            return False

