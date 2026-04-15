import React from 'react'

function ScoreBadge({ score, size = 'medium', type = 'score' }) {
  if (score == null) {
    return <span className={`score-badge ${size} na`}>N/A</span>
  }

  let colorClass = 'low'
  if (score >= 7) colorClass = 'high'
  else if (score >= 4) colorClass = 'medium'

  return (
    <span className={`score-badge ${size} ${colorClass} ${type}`}>
      {score.toFixed(1)}
    </span>
  )
}

export default ScoreBadge
