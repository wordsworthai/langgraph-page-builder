import React from 'react'

function safeStringify(value, indent = null) {
  try {
    return JSON.stringify(value, null, indent)
  } catch (e) {
    return String(value)
  }
}

function OutputCard({ label, value, isCollapsible = false, fullWidth = false, summary }) {
  if (!value) return null

  const cardClass = `output-card ${fullWidth ? 'full-width' : ''}`

  if (isCollapsible) {
    return (
      <div className={cardClass}>
        <label>{label}</label>
        <details>
          <summary>{summary || `View ${label}`}</summary>
          <pre>{safeStringify(value, 2)}</pre>
        </details>
      </div>
    )
  }

  return (
    <div className={cardClass}>
      <label>{label}</label>
      <span>{typeof value === 'object' ? safeStringify(value, 2) : value}</span>
    </div>
  )
}

export default OutputCard
