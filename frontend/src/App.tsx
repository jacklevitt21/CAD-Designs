import { useState } from 'react'
import './App.css'
import { apiUrl, ApiError, generateFromText, regenerate, stepDownloadUrl } from './api'
import { ErrorBanner } from './components/ErrorBanner'
import { ParamsPanel } from './components/ParamsPanel'
import { PromptInput } from './components/PromptInput'
import { Viewer3D } from './components/Viewer3D'
import type { PartResponse } from './types'

type Status = 'idle' | 'generating' | 'regenerating' | 'ready'

function App() {
  const [status, setStatus] = useState<Status>('idle')
  const [part, setPart] = useState<PartResponse | null>(null)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [errorList, setErrorList] = useState<string[] | null>(null)

  async function handleGenerate(text: string) {
    setStatus('generating')
    setErrorMessage(null)
    setErrorList(null)
    try {
      const result = await generateFromText(text)
      setPart(result)
      setStatus('ready')
    } catch (err) {
      setStatus(part ? 'ready' : 'idle')
      if (err instanceof ApiError) {
        setErrorMessage(err.message)
        setErrorList(err.errors ?? null)
      } else {
        setErrorMessage('Something went wrong talking to the server.')
      }
    }
  }

  async function handleRegenerate(
    name: string | null,
    material: string | null,
    parameters: Record<string, unknown>,
  ) {
    if (!part) return
    setStatus('regenerating')
    setErrorMessage(null)
    setErrorList(null)
    try {
      const result = await regenerate(part.part_type, name, material, parameters)
      setPart(result)
      setStatus('ready')
    } catch (err) {
      setStatus('ready')
      if (err instanceof ApiError) {
        setErrorMessage(err.message)
        setErrorList(err.errors ?? null)
      } else {
        setErrorMessage('Something went wrong talking to the server.')
      }
    }
  }

  const isBusy = status === 'generating' || status === 'regenerating'

  return (
    <div className="app">
      <header className="app-header">
        <h1>Text-to-CAD</h1>
        <p>Describe a mechanical part in plain English — get a real parametric STEP file.</p>
      </header>

      <PromptInput onSubmit={handleGenerate} disabled={isBusy} />

      {errorMessage && (
        <ErrorBanner
          message={errorMessage}
          errors={errorList}
          onDismiss={() => {
            setErrorMessage(null)
            setErrorList(null)
          }}
        />
      )}

      {part && (
        <div className="workspace">
          <div className="viewer-pane">
            {status === 'generating' && (
              <div className="generating-overlay">
                <div className="spinner" />
                <span>Generating…</span>
              </div>
            )}
            <Viewer3D stlUrl={apiUrl(part.stl_url)} />
            <a className="download-btn" href={stepDownloadUrl(part.part_id)}>
              ⬇ Download STEP
            </a>
          </div>

          <ParamsPanel part={part} onRegenerate={handleRegenerate} isRegenerating={status === 'regenerating'} />
        </div>
      )}

      {!part && status === 'generating' && (
        <div className="generating-overlay standalone">
          <div className="spinner" />
          <span>Generating…</span>
        </div>
      )}
    </div>
  )
}

export default App
