import React from 'react'

interface Props   { children: React.ReactNode }
interface State   { error: Error | null }

export class ErrorBoundary extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { error: null }
  }

  static getDerivedStateFromError(error: Error): State {
    return { error }
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error('[ErrorBoundary]', error, info)
  }

  render() {
    if (this.state.error) {
      return (
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          minHeight: '100vh',
          gap: '16px',
          fontFamily: 'var(--mono)',
          color: 'var(--danger-text)',
          padding: '40px',
          textAlign: 'center',
        }}>
          <div style={{ fontSize: 32 }}>✕</div>
          <p style={{ fontSize: 14, fontWeight: 600 }}>Something went wrong</p>
          <p style={{
            fontSize: 12,
            color: 'var(--text2)',
            maxWidth: 480,
            lineHeight: 1.7,
          }}>
            {this.state.error.message}
          </p>
          <button
            style={{
              fontFamily: 'var(--mono)',
              fontSize: 12,
              padding: '8px 18px',
              border: '0.5px solid var(--border2)',
              borderRadius: 6,
              background: 'transparent',
              cursor: 'pointer',
              color: 'var(--text)',
            }}
            onClick={() => this.setState({ error: null })}
          >
            Try again
          </button>
        </div>
      )
    }
    return this.props.children
  }
}
