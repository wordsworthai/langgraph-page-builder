import React from 'react'
import ScoreBadge from './ScoreBadge'

function TemplateScoreCard({ templateScore, isExpanded, onToggle, isBest }) {
  const { template_index, score, reasoning, strengths = [], weaknesses = [] } = templateScore

  return (
    <div className={`template-score-card ${isBest ? 'best' : ''}`}>
      <div className="template-score-header" onClick={onToggle}>
        <div className="template-info">
          <span className="template-name">Template #{template_index + 1}</span>
          {isBest && <span className="best-badge">★ Best</span>}
        </div>
        <ScoreBadge score={score} size="medium" />
      </div>

      {isExpanded && (
        <div className="template-score-details">
          {reasoning && (
            <div className="detail-section">
              <div className="detail-label">Reasoning</div>
              <p className="detail-text">{reasoning}</p>
            </div>
          )}
          {strengths.length > 0 && (
            <div className="detail-section">
              <div className="detail-label strengths">✓ Strengths</div>
              <ul className="detail-list">
                {strengths.map((s, i) => <li key={i}>{s}</li>)}
              </ul>
            </div>
          )}
          {weaknesses.length > 0 && (
            <div className="detail-section">
              <div className="detail-label weaknesses">✗ Weaknesses</div>
              <ul className="detail-list">
                {weaknesses.map((w, i) => <li key={i}>{w}</li>)}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default TemplateScoreCard
