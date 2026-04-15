import React, { useState } from 'react'
import ScoreBadge from './components/ScoreBadge'
import TemplateScoreCard from './components/TemplateScoreCard'
import GuidelinesComplianceView from './components/GuidelinesComplianceView'

function TemplateSelectionAiEvalCard({ evalResult, compact = false }) {
  const [expandedTemplate, setExpandedTemplate] = useState(null)
  const [showCompliance, setShowCompliance] = useState(false)

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

  const {
    template_scores = [],
    average_score,
    compliance_score,
    guidelines_compliance = {},
    best_template_index,
    overall_assessment,
  } = output || {}

  if (compact) {
    return (
      <div className="ai-eval-compact">
        <ScoreBadge score={average_score} size="small" />
        {compliance_score != null && (
          <span className="compliance-mini" title="Compliance Score">
            C: {compliance_score.toFixed(1)}
          </span>
        )}
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

      <div className="ai-eval-scores-row">
        <div className="ai-eval-score-block">
          <div className="score-label">Average Score</div>
          <ScoreBadge score={average_score} size="large" />
        </div>
        <div className="ai-eval-score-block">
          <div className="score-label">Compliance</div>
          <ScoreBadge score={compliance_score} size="large" type="compliance" />
        </div>
        {best_template_index != null && (
          <div className="ai-eval-score-block">
            <div className="score-label">Best Template</div>
            <div className="best-template-badge">#{best_template_index + 1}</div>
          </div>
        )}
      </div>

      {overall_assessment && (
        <div className="ai-eval-assessment">
          <div className="assessment-label">Overall Assessment</div>
          <p className="assessment-text">{overall_assessment}</p>
        </div>
      )}

      {template_scores.length > 0 && (
        <div className="ai-eval-section">
          <div className="section-header">
            <span>Template Scores</span>
          </div>
          <div className="template-scores-grid">
            {template_scores.map((ts, idx) => (
              <TemplateScoreCard
                key={idx}
                templateScore={ts}
                isExpanded={expandedTemplate === idx}
                onToggle={() => setExpandedTemplate(expandedTemplate === idx ? null : idx)}
                isBest={best_template_index === ts.template_index}
              />
            ))}
          </div>
        </div>
      )}

      {Object.keys(guidelines_compliance).length > 0 && (
        <div className="ai-eval-section">
          <div
            className="section-header clickable"
            onClick={() => setShowCompliance(!showCompliance)}
          >
            <span>Guidelines Compliance</span>
            <span className="toggle-icon">{showCompliance ? '▼' : '▶'}</span>
          </div>
          {showCompliance && (
            <GuidelinesComplianceView compliance={guidelines_compliance} />
          )}
        </div>
      )}
    </div>
  )
}

export default TemplateSelectionAiEvalCard
