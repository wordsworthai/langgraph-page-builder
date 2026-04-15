import React, { useState, useEffect, useCallback } from 'react'

function safeStringify(value, indent = 2) {
  try {
    return JSON.stringify(value, null, indent)
  } catch (e) {
    return String(value)
  }
}

function TraceCard({ trace, index }) {
  const [expandedInput, setExpandedInput] = useState(false)
  const [expandedOutput, setExpandedOutput] = useState(false)
  const [expandedFormattedPrompt, setExpandedFormattedPrompt] = useState(false)

  const modelProvider = [trace.model, trace.provider].filter(Boolean).join(' · ')

  return (
    <div className="trace-card" style={{
      border: '1px solid var(--border-color)',
      borderRadius: 8,
      marginBottom: 12,
      overflow: 'hidden',
      background: 'var(--bg-secondary)',
    }}>
      <div style={{
        padding: '12px 16px',
        borderBottom: '1px solid var(--border-color)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: 8,
      }}>
        <div>
          <strong style={{ fontSize: 14 }}>{trace.prompt_name || trace.task_name || `Trace ${index + 1}`}</strong>
          {trace.task_name && trace.task_name !== trace.prompt_name && (
            <span style={{ marginLeft: 8, fontSize: 12, color: 'var(--text-secondary)' }}>
              ({trace.task_name})
            </span>
          )}
        </div>
        <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
          {modelProvider && <span>{modelProvider} · </span>}
          {(trace.input_tokens != null || trace.output_tokens != null) && (
            <span>
              {trace.input_tokens != null && `${trace.input_tokens.toLocaleString()} in`}
              {trace.input_tokens != null && trace.output_tokens != null && ' · '}
              {trace.output_tokens != null && `${trace.output_tokens.toLocaleString()} out`}
              {' · '}
            </span>
          )}
          {trace.duration_ms != null && `${trace.duration_ms}ms`}
          {trace.timestamp_iso && ` · ${trace.timestamp_iso}`}
        </div>
      </div>
      <div style={{ padding: 12 }}>
        {trace.formatted_prompt != null && (
          <div style={{ marginBottom: 8 }}>
            <button
              type="button"
              onClick={() => setExpandedFormattedPrompt(!expandedFormattedPrompt)}
              style={{
                background: 'none',
                border: 'none',
                cursor: 'pointer',
                padding: 4,
                fontSize: 12,
                color: 'var(--text-secondary)',
              }}
            >
              {expandedFormattedPrompt ? '▼' : '▶'} Formatted prompt
            </button>
            {expandedFormattedPrompt && (
              <pre style={{
                marginTop: 8,
                padding: 12,
                background: 'var(--bg-tertiary)',
                borderRadius: 6,
                overflow: 'auto',
                maxHeight: 300,
                fontSize: 12,
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-word',
              }}>
                {trace.formatted_prompt}
              </pre>
            )}
          </div>
        )}
        <div style={{ marginBottom: 8 }}>
          <button
            type="button"
            onClick={() => setExpandedInput(!expandedInput)}
            style={{
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              padding: 4,
              fontSize: 12,
              color: 'var(--text-secondary)',
            }}
          >
            {expandedInput ? '▼' : '▶'} Input
          </button>
          {expandedInput && (
            <pre style={{
              marginTop: 8,
              padding: 12,
              background: 'var(--bg-tertiary)',
              borderRadius: 6,
              overflow: 'auto',
              maxHeight: 300,
              fontSize: 12,
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
            }}>
              {safeStringify(trace.invoke_input)}
            </pre>
          )}
        </div>
        <div>
          <button
            type="button"
            onClick={() => setExpandedOutput(!expandedOutput)}
            style={{
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              padding: 4,
              fontSize: 12,
              color: 'var(--text-secondary)',
            }}
          >
            {expandedOutput ? '▼' : '▶'} Output
          </button>
          {expandedOutput && (
            <pre style={{
              marginTop: 8,
              padding: 12,
              background: 'var(--bg-tertiary)',
              borderRadius: 6,
              overflow: 'auto',
              maxHeight: 300,
              fontSize: 12,
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
            }}>
              {safeStringify(trace.result)}
            </pre>
          )}
        </div>
      </div>
    </div>
  )
}

export default function PromptTracesView({ generationVersionId, config }) {
  const [traces, setTraces] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const fetchTraces = useCallback(async () => {
    if (!generationVersionId) {
      setTraces([])
      return
    }
    setLoading(true)
    setError(null)
    try {
      const response = await fetch('/api/prompt-traces', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          mongo_uri: config?.mongoUri,
          db_name: config?.dbName,
          generation_version_id: generationVersionId,
        }),
      })
      const data = await response.json()
      if (data.detail) throw new Error(data.detail)
      setTraces(data.traces || [])
    } catch (err) {
      setError(err.message)
      setTraces([])
    } finally {
      setLoading(false)
    }
  }, [generationVersionId, config?.mongoUri, config?.dbName])

  useEffect(() => {
    fetchTraces()
  }, [fetchTraces])

  if (!generationVersionId) {
    return (
      <div className="prompt-traces-empty" style={{ padding: 24, textAlign: 'center', color: 'var(--text-secondary)' }}>
        Select a thread to view prompt traces
      </div>
    )
  }

  if (loading) {
    return (
      <div className="prompt-traces-loading" style={{ padding: 24, textAlign: 'center' }}>
        Loading prompt traces...
      </div>
    )
  }

  if (error) {
    return (
      <div className="prompt-traces-error" style={{ padding: 24, color: 'var(--error-color)' }}>
        Error: {error}
      </div>
    )
  }

  if (traces.length === 0) {
    return (
      <div className="prompt-traces-empty" style={{ padding: 24, textAlign: 'center', color: 'var(--text-secondary)' }}>
        No prompt traces found for this generation. Enable prompt tracing with WWAI_AGENT_ORCHESTRATION_ENABLE_PROMPT_TRACE=true.
      </div>
    )
  }

  return (
    <div className="prompt-traces-view" style={{ padding: 16, overflow: 'auto' }}>
      <div style={{ marginBottom: 16, fontSize: 14, color: 'var(--text-secondary)' }}>
        {traces.length} prompt call{traces.length !== 1 ? 's' : ''} for this generation
      </div>
      {traces.map((trace, idx) => (
        <TraceCard key={idx} trace={trace} index={idx} />
      ))}
    </div>
  )
}
