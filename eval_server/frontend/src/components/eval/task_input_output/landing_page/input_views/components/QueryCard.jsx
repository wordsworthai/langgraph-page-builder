import React from 'react'

function QueryCard({ query }) {
  if (!query) return null

  return (
    <div className="input-card">
      <label>Query</label>
      <span>{query}</span>
    </div>
  )
}

export default QueryCard
