import { lazy, Suspense, useState } from 'react'
import './App.css'
import { ingest, ask } from './api'
import ErrorBoundary from './ErrorBoundary'
const EmbeddingsView = lazy(() => import('./EmbeddingsView'))

function App() {
  const [ingestText, setIngestText] = useState('')
  const [source, setSource] = useState('')
  const [title, setTitle] = useState('')
  const [ingestStatus, setIngestStatus] = useState('')
  const [question, setQuestion] = useState('')
  const [answer, setAnswer] = useState('')
  const [sources, setSources] = useState<{source?: string; title?: string; snippet?: string}[]>([])
  const [file, setFile] = useState<File | null>(null)
  const [busy, setBusy] = useState(false)

  const onIngest = async () => {
    if (busy) return
    setBusy(true)
    setIngestStatus('Adding...')
    try {
      const res = await ingest(ingestText, source || undefined, title || undefined)
      setIngestStatus(`Added ${res.added_chunks} chunks.`)
    } catch (e) {
      setIngestStatus('Failed to ingest.')
    }
    setBusy(false)
  }

  const onUpload = async () => {
    if (busy) return
    if (!file) return
    if (file.size > 10 * 1024 * 1024) { setIngestStatus('File too large (>10MB)'); return }
    setBusy(true)
    setIngestStatus('Uploading...')
    try {
      const api = (import.meta as any).env?.VITE_API_URL || 'http://127.0.0.1:8000'
      const fd = new FormData()
      fd.append('file', file)
      fd.append('source', source)
      fd.append('title', title)
      const res = await fetch(`${api}/ingest-file`, { method: 'POST', body: fd })
      const data = await res.json()
      setIngestStatus(`Added ${data.added_chunks} chunks.`)
    } catch (e) {
      setIngestStatus('Upload failed.')
    }
    setBusy(false)
  }

  const onAsk = async () => {
    if (busy) return
    setBusy(true)
    setAnswer('Thinking...')
    setSources([])
    try {
      const res = await ask(question, 4)
      setAnswer(res.answer || '(no answer)')
      setSources(Array.isArray(res.sources) ? res.sources : [])
    } catch (e) {
      setAnswer('Error fetching answer.')
    }
    setBusy(false)
  }

  return (
    <div className="app">
      <h1>Ask & See</h1>
      <details style={{marginBottom: 16}} open>
        <summary>Embeddings Visualization</summary>
        <ErrorBoundary>
          <Suspense fallback={<div>Loading visualization...</div>}>
            <EmbeddingsView />
          </Suspense>
        </ErrorBoundary>
      </details>
      <div className="panel">
        <h2>Ingest</h2>
        <textarea value={ingestText} onChange={e=>setIngestText(e.target.value)} placeholder="Paste text to ingest..." rows={6} />
        <div className="row">
          <input value={source} onChange={e=>setSource(e.target.value)} placeholder="source (optional)" />
          <input value={title} onChange={e=>setTitle(e.target.value)} placeholder="title (optional)" />
          <button onClick={onIngest} disabled={busy}>Add to KB</button>
        </div>
        <div className="row">
          <input type="file" onChange={e=>setFile(e.target.files?.[0] || null)} />
          <button onClick={onUpload} disabled={busy}>Upload File</button>
        </div>
        <div className="status">{ingestStatus}</div>
      </div>

      <div className="panel">
        <h2>Ask</h2>
        <div className="row">
          <input value={question} onChange={e=>setQuestion(e.target.value)} placeholder="Ask a question..." />
          <button onClick={onAsk} disabled={busy}>Ask</button>
        </div>
        <div className="answer">{answer}</div>
        <div className="sources">
          {sources.map((s, i)=> (
            <div className="src" key={i}>[{s.title || s.source}] {s.snippet}</div>
          ))}
        </div>
      </div>
    </div>
  )
}

export default App
