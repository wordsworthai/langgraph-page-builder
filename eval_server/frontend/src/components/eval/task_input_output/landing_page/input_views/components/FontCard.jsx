import React from 'react'

function FontCard({ fontFamily }) {
  if (!fontFamily) return null

  return (
    <div className="input-card">
      <label>Font</label>
      <span style={{ fontFamily }}>{fontFamily}</span>
    </div>
  )
}

export default FontCard
