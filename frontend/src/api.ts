const API_URL = (import.meta as any).env?.VITE_API_URL || 'http://127.0.0.1:8000';

export async function ingest(text: string, source?: string, title?: string) {
  const res = await fetch(`${API_URL}/ingest`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify([{ text, source, title }])
  });
  if (!res.ok) throw new Error('Ingest failed');
  return res.json();
}

export async function ask(question: string, k = 4) {
  const res = await fetch(`${API_URL}/ask`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, k })
  });
  if (!res.ok) throw new Error('Ask failed');
  return res.json();
}


export interface EmbeddingItem {
  id: string;
  embedding: number[];
  title?: string;
  source?: string;
  text?: string;
}

export async function fetchEmbeddings(limit = 500, offset = 0): Promise<{ items: EmbeddingItem[]; total: number; limit: number; offset: number; }> {
  const res = await fetch(`${API_URL}/embeddings?limit=${limit}&offset=${offset}`);
  if (!res.ok) throw new Error('Embeddings fetch failed');
  return res.json();
}


