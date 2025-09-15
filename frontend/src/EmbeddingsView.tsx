import { useEffect, useMemo, useRef, useState } from 'react'
import Plot from 'react-plotly.js'
import { PCA as PCAClass } from 'ml-pca'
import { fetchEmbeddings, type EmbeddingItem } from './api'

export default function EmbeddingsView() {
  const [items, setItems] = useState<EmbeddingItem[]>([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [dims, setDims] = useState(2)
  const [limit, setLimit] = useState(300)
  const plotRef = useRef<HTMLDivElement | null>(null)
  const canvasRef = useRef<HTMLCanvasElement | null>(null)
  const [useFallback, setUseFallback] = useState(false)
  const validCount = useMemo(() => items.filter(i => Array.isArray(i.embedding) && i.embedding.length >= 2 && i.embedding.every(n => Number.isFinite(n))).length, [items])

  useEffect(() => {
    const run = async () => {
      setLoading(true)
      setError('')
      try {
        const res = await fetchEmbeddings(limit, 0)
        setItems(res.items || [])
      } catch (e: any) {
        setError(e?.message || 'Failed to load embeddings')
      }
      setLoading(false)
    }
    run()
  }, [limit])

  const plotData = useMemo(() => {
    const valid = items.filter(i => Array.isArray(i.embedding) && i.embedding.length >= 2 && i.embedding.every(n => Number.isFinite(n)))
    if (valid.length < 2) return null
    const matrix = valid.map(i => i.embedding)
    if (!matrix.length || !matrix[0] || matrix[0].length < 2) return null
    const pca = new (PCAClass as any)(matrix, { center: true, scale: false })
    const k = dims === 3 ? 3 : 2
    let transformed = pca.predict(matrix, { nComponents: k }).to2DArray()
    // Fallback if PCA produced invalid values or collapsed variance
    const flat = transformed.flat() as number[]
    const hasBad = flat.some((v: number) => !Number.isFinite(v))
    const spreadX = Math.max(...transformed.map((r: number[]) => r[0])) - Math.min(...transformed.map((r: number[]) => r[0]))
    const spreadY = Math.max(...transformed.map((r: number[]) => r[1])) - Math.min(...transformed.map((r: number[]) => r[1]))
    if (hasBad || spreadX === 0 || spreadY === 0) {
      transformed = matrix.map((r: number[]) => [r[0], r[1], 0])
    }
    const hover = valid.map(i => `${(i.title || i.source || '').trim()}` + (i.text ? `\n${i.text}` : ''))
    const xs = transformed.map((r: number[]) => r[0])
    const ys = transformed.map((r: number[]) => r[1])
    const minX = Math.min(...xs), maxX = Math.max(...xs)
    const minY = Math.min(...ys), maxY = Math.max(...ys)
    const padX = (maxX - minX || 1) * 0.1
    const padY = (maxY - minY || 1) * 0.1
    if (k === 3) {
      return ({
        traces: ([{
          x: xs,
          y: ys,
          z: transformed.map((r: number[]) => r[2]),
          text: hover,
          mode: 'markers',
          type: 'scatter3d',
          marker: { size: 4, opacity: 0.85, color: '#8bb0ff' },
          name: 'embeddings'
        }] as any),
        layout: { scene: { xaxis: { range: [minX - padX, maxX + padX] }, yaxis: { range: [minY - padY, maxY + padY] } } }
      })
    }
    return ({
      traces: ([{
        x: xs,
        y: ys,
        text: hover,
        mode: 'markers',
        type: 'scatter',
        marker: { size: 6, opacity: 0.9, color: '#8bb0ff' },
        name: 'embeddings'
      }] as any),
      layout: { xaxis: { range: [minX - padX, maxX + padX] }, yaxis: { range: [minY - padY, maxY + padY] } }
    })
  }, [items, dims])

  const layoutBase = useMemo(() => ({
    title: `Embeddings (PCA) — ${items.length} points`,
    margin: { l: 10, r: 10, t: 30, b: 30 },
    paper_bgcolor: 'rgba(0,0,0,0)',
    plot_bgcolor: '#0e1540',
    font: { color: '#cfd6ff' },
  } as any), [items.length])

  // Canvas fallback renderer (2D only)
  useEffect(() => {
    if (!useFallback || !plotData || dims !== 2) return
    const c = canvasRef.current
    if (!c) return
    const ctx = c.getContext('2d')
    if (!ctx) return
    const xs = (plotData as any).traces[0].x as number[]
    const ys = (plotData as any).traces[0].y as number[]
    const w = c.clientWidth || 800
    const h = c.clientHeight || 400
    c.width = w
    c.height = h
    const minX = Math.min(...xs), maxX = Math.max(...xs)
    const minY = Math.min(...ys), maxY = Math.max(...ys)
    const sx = (x: number) => (x - minX) / (maxX - minX || 1) * (w - 20) + 10
    const sy = (y: number) => h - ((y - minY) / (maxY - minY || 1) * (h - 20) + 10)
    ctx.clearRect(0, 0, w, h)
    ctx.fillStyle = '#0e1540'
    ctx.fillRect(0, 0, w, h)
    ctx.fillStyle = '#8bb0ff'
    for (let i = 0; i < xs.length; i++) {
      const x = sx(xs[i])
      const y = sy(ys[i])
      ctx.beginPath()
      ctx.arc(x, y, 3, 0, Math.PI * 2)
      ctx.fill()
    }
  }, [useFallback, plotData, dims])

  return (
    <div style={{ border: '1px solid #ddd', padding: 12, borderRadius: 8 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
        <span style={{ fontWeight: 600 }}>View:</span>
        <button onClick={() => setDims(2)} disabled={dims===2}>2D</button>
        <button onClick={() => setDims(3)} disabled={dims===3}>3D</button>
        <span style={{ marginLeft: 12 }}>Limit:</span>
        <select value={limit} onChange={e=>setLimit(parseInt(e.target.value))}>
          <option value={200}>200</option>
          <option value={300}>300</option>
          <option value={500}>500</option>
          <option value={800}>800</option>
        </select>
        <button onClick={() => setLimit(l => l)} title="Refresh" style={{ marginLeft: 8 }}>Refresh</button>
        <span style={{ color: '#666' }}>Google model: text-embedding-004</span>
        <span style={{ marginLeft: 'auto', color: '#888' }}>points: {validCount}</span>
      </div>
      {loading ? <div>Loading embeddings...</div> : null}
      {error ? <div style={{ color: 'crimson' }}>{error}</div> : null}
      {validCount < 2 && !loading ? (
        <div style={{ padding: 8, color: '#888' }}>Add more text or increase Limit to see the plot (need at least 2 points).</div>
      ) : null}
      {useFallback && dims === 2 ? (
        <div style={{ width: '100%', height: 400 }}>
          <div style={{ color: '#ffdf8b', marginBottom: 6 }}>Plotly failed; showing canvas fallback.</div>
          <canvas ref={canvasRef} style={{ width: '100%', height: 360, display: 'block' }} />
        </div>
      ) : plotData ? (
        <Plot
          data={(plotData as any).traces}
          layout={{
            ...layoutBase,
            ...(plotData as any).layout,
            ...(dims === 3 ? { scene: { xaxis: { title: 'PC1' }, yaxis: { title: 'PC2' }, zaxis: { title: 'PC3' } } } : {}),
            ...(dims === 2 ? { xaxis: { title: 'PC1', color: '#cfd6ff', tickcolor: '#cfd6ff', zerolinecolor: '#445', gridcolor: '#223', ...((plotData as any).layout?.xaxis || {}) }, yaxis: { title: 'PC2', color: '#cfd6ff', tickcolor: '#cfd6ff', zerolinecolor: '#445', gridcolor: '#223', ...((plotData as any).layout?.yaxis || {}) } } : {}),
          }}
          config={{ responsive: true, displaylogo: false }}
          style={{ width: '100%', height: 400 }}
          useResizeHandler
        />
      ) : (
        <div ref={plotRef} style={{ width: '100%', height: 400 }} />
      )}
    </div>
  )
}


