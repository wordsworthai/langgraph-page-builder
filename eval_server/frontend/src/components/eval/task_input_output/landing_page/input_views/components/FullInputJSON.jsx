import React from 'react'

function safeStringify(value, indent = null) {
  try {
    return JSON.stringify(value, null, indent)
  } catch (e) {
    return String(value)
  }
}

function FullInputJSON({ fullInput }) {
  if (!fullInput) return null

  return (
    <details className="full-input">
      <summary>View Full Input JSON</summary>
      <pre>{safeStringify(fullInput, 2)}</pre>
    </details>
  )
}

export default FullInputJSON
