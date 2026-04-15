import React, { useEffect, useMemo, useState } from 'react'
import { renderDataDebugResult } from './renderers'
import { generateDataDebugArgs } from './arg_generators'

function prettyJson(value) {
  return JSON.stringify(value ?? {}, null, 2)
}

function DataDebugSafetyBanner({ allowExternal, onToggle }) {
  return (
    <div className={`data-debug-safety ${allowExternal ? 'external-enabled' : ''}`}>
      <div className="data-debug-safety-copy">
        <strong>Safety Mode:</strong> {allowExternal ? 'External calls enabled' : 'Readonly mode (DB-backed only)'}
      </div>
      <label className="data-debug-toggle">
        <input type="checkbox" checked={allowExternal} onChange={(e) => onToggle(e.target.checked)} />
        <span>Enable External Calls (cost/network)</span>
      </label>
    </div>
  )
}

function DataDebugResultPanel({ target, result, runError }) {
  const [viewMode, setViewMode] = useState('ui')

  if (!result && !runError) {
    return <div className="data-debug-empty">Run a target to inspect output.</div>
  }

  if (runError) {
    return <div className="data-debug-error">{runError}</div>
  }

  const renderedResult = renderDataDebugResult({ target, result })
  const hasCustomUi = Boolean(renderedResult)

  return (
    <div className="data-debug-result">
      <div className="data-debug-result-meta">
        <span className={result.success ? 'ok' : 'bad'}>{result.success ? 'Success' : 'Failed'}</span>
        <span>{result.target}</span>
        <span>{result?.meta?.elapsed_ms ?? 0} ms</span>
      </div>
      {hasCustomUi && (
        <div className="data-debug-view-toggle view-toggle">
          <button
            type="button"
            className={`toggle-btn ${viewMode === 'ui' ? 'active' : ''}`}
            onClick={() => setViewMode('ui')}
          >
            UI
          </button>
          <button
            type="button"
            className={`toggle-btn ${viewMode === 'json' ? 'active' : ''}`}
            onClick={() => setViewMode('json')}
          >
            JSON
          </button>
        </div>
      )}
      {hasCustomUi ? (
        viewMode === 'ui' ? (
          <div className="data-debug-rendered-result">{renderedResult}</div>
        ) : (
          <pre>{prettyJson(result)}</pre>
        )
      ) : (
        <pre>{prettyJson(result)}</pre>
      )}
    </div>
  )
}

function DataDebugRunner({ target, allowExternal, onAllowExternalChange, config }) {
  const [argsText, setArgsText] = useState(prettyJson(target?.sample_args || {}))
  const [result, setResult] = useState(null)
  const [runError, setRunError] = useState(null)
  const [running, setRunning] = useState(false)

  const targetHeader = useMemo(() => {
    if (!target) return 'No target selected'
    return `${target.label} (${target.target})`
  }, [target])

  useEffect(() => {
    setArgsText(prettyJson(target?.sample_args || {}))
    setResult(null)
    setRunError(null)
  }, [target?.target])

  const handleRun = async () => {
    if (!target) return
    let parsedArgs = {}
    try {
      parsedArgs = argsText ? JSON.parse(argsText) : {}
    } catch (err) {
      setRunError(`Invalid JSON args: ${err.message}`)
      return
    }

    setRunning(true)
    setRunError(null)
    setResult(null)

    try {
      const response = await fetch('/api/data/debug/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          target: target.target,
          args: { ...parsedArgs, mongo_uri: config?.mongoUri || undefined },
          allow_external: allowExternal,
        }),
      })

      const payload = await response.json()
      if (!response.ok) {
        throw new Error(payload?.detail || `Request failed (${response.status})`)
      }
      setResult(payload)
    } catch (err) {
      setRunError(err.message)
    } finally {
      setRunning(false)
    }
  }

  const handleGenerateExample = () => {
    const nextArgs = generateDataDebugArgs({
      target,
      sampleArgs: target?.sample_args || {},
    })
    setArgsText(prettyJson(nextArgs))
    setRunError(null)
  }

  return (
    <div className="data-debug-runner">
      <DataDebugSafetyBanner allowExternal={allowExternal} onToggle={onAllowExternalChange} />

      <div className="data-debug-target-header">
        <h3>{targetHeader}</h3>
        {target?.description && <p>{target.description}</p>}
      </div>

      <div className="data-debug-controls">
        <label>Args (JSON)</label>
        <textarea value={argsText} onChange={(e) => setArgsText(e.target.value)} spellCheck={false} />
        <div className="data-debug-actions">
          <button className="btn-secondary" onClick={handleGenerateExample} disabled={running}>
            Generate Example
          </button>
          <button className="btn" onClick={handleRun} disabled={running}>
            {running ? 'Running...' : 'Run Target'}
          </button>
        </div>
      </div>

      <DataDebugResultPanel target={target} result={result} runError={runError} />
    </div>
  )
}

export default DataDebugRunner

