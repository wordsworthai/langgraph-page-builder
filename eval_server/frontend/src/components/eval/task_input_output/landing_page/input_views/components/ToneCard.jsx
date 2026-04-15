import React from 'react'

function ToneCard({ tone }) {
  if (!tone) return null

  return (
    <div className="input-card">
      <label>Tone</label>
      <span>{tone}</span>
    </div>
  )
}

export default ToneCard
