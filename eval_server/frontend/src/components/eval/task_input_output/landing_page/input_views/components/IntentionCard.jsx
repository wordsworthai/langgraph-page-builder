import React from 'react'

function IntentionCard({ intention }) {
  if (!intention) return null

  return (
    <div className="input-card">
      <label>Intention</label>
      <span>{intention}</span>
    </div>
  )
}

export default IntentionCard
