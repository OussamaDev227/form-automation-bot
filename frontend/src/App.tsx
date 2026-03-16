import React from 'react'
import { Dashboard }      from './pages/Dashboard'
import { ErrorBoundary }  from './components/ErrorBoundary'

const App: React.FC = () => (
  <ErrorBoundary>
    <Dashboard />
  </ErrorBoundary>
)

export default App
