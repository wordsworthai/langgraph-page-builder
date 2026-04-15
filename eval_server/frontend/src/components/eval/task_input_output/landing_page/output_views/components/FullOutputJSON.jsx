import React from 'react'

function safeStringify(value, indent = null) {
  try {
    return JSON.stringify(value, null, indent)
  } catch (e) {
    return String(value)
  }
}

function FullOutputJSON({ output }) {
  if (!output) return null

  return (
    <details className="full-output">
      <summary>View Output JSON</summary>
      <pre>{safeStringify(output, 2)}</pre>
    </details>
  )
}

export default FullOutputJSON
