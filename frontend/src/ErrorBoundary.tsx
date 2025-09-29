import React from 'react'

type Props = { children: React.ReactNode }
type State = { hasError: boolean; message?: string }

export default class ErrorBoundary extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false }
  }

  static getDerivedStateFromError(err: unknown): State {
    const message = err instanceof Error ? err.message : 'Unknown error'
    return { hasError: true, message }
  }

  componentDidCatch(error: unknown) {
    // eslint-disable-next-line no-console
    console.error('Embeddings error:', error)
  }

  render(): React.ReactNode {
    if (this.state.hasError) {
      return (
        <div style={{ border: '1px solid #a33', background: '#300', color: '#fdd', padding: 12, borderRadius: 8 }}>
          <div style={{ fontWeight: 700, marginBottom: 6 }}>Embeddings Visualization failed to load</div>
          <div style={{ opacity: 0.8, fontSize: 14 }}>{this.state.message}</div>
        </div>
      )
    }
    return this.props.children
  }
}


