// Prefer explicit env; else in local dev (vite on 5173), talk to backend on 8000; else same-origin (Cloud Run)
export const envUrl = (import.meta as any).env?.VITE_API_URL as string | undefined;
let inferred = '';
try {
  const h = typeof window !== 'undefined' ? window.location.hostname : '';
  const p = typeof window !== 'undefined' ? window.location.port : '';
  const isLocalHost = h === 'localhost' || h === '127.0.0.1';
  if (isLocalHost && p && p !== '8000') {
    inferred = 'http://127.0.0.1:8000';
  }
} catch {}
export const API_URL = envUrl || inferred || '';

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

export async function clearDb() {
  const res = await fetch(`${API_URL}/clear`, { method: 'POST' });
  if (!res.ok) throw new Error('Clear failed');
  return res.json();
}

export async function uploadFile(file: File, source: string, title: string) {
  const fd = new FormData();
  fd.append('file', file);
  fd.append('source', source);
  fd.append('title', title);
  const res = await fetch(`${API_URL}/ingest-file`, { method: 'POST', body: fd });
  if (!res.ok) throw new Error('Upload failed');
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


