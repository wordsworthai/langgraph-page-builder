import React from 'react'

function safeStringify(value, indent = null) {
  try {
    return JSON.stringify(value, null, indent)
  } catch (e) {
    return String(value)
  }
}

function GenericAiEvalCard({ evalResult, compact = false }) {
  if (!evalResult) {
    return (
      <div className="ai-eval-card ai-eval-empty">
        <div className="ai-eval-empty-icon">🔍</div>
        <p>No AI evaluation available</p>
      </div>
    )
  }

  const { output, status, model_name, prompt_version } = evalResult

  if (output?.parse_error) {
    return (
      <div className="ai-eval-card ai-eval-error">
        <div className="ai-eval-header">
          <span className="ai-eval-title">AI Evaluation</span>
          <span className="ai-eval-status error">Error</span>
        </div>
        <p className="ai-eval-error-msg">{output.reason || output.parse_error_reason || 'Failed to parse LLM response'}</p>
      </div>
    )
  }

  if (compact) {
    const avg = output?.average_score
    return (
      <div className="ai-eval-compact">
        <span className="score-badge small">{avg != null ? avg.toFixed(1) : 'N/A'}</span>
      </div>
    )
  }

  return (
    <div className="ai-eval-card">
      <div className="ai-eval-header">
        <span className="ai-eval-title">AI Evaluation</span>
        <div className="ai-eval-meta">
          {model_name && <span className="ai-eval-model">{model_name}</span>}
          {prompt_version && <span className="ai-eval-version">v{prompt_version}</span>}
          <span className={`ai-eval-status ${status}`}>{status}</span>
        </div>
      </div>
      <details className="full-output">
        <summary>View Raw JSON</summary>
        <pre>{safeStringify(evalResult, 2)}</pre>
      </details>
    </div>
  )
}

export default GenericAiEvalCard
