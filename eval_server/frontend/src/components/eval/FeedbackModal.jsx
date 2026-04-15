import React from 'react'
import AIEvalResultCard from './AIEvalResultCard'
import {
  FeedbackBooleanField,
  FeedbackEnumField,
  FeedbackTextField,
  FeedbackNumberField
} from './feedbackFields'

const FIELD_BY_TYPE = {
  boolean: FeedbackBooleanField,
  enum: FeedbackEnumField,
  number: FeedbackNumberField,
  text: FeedbackTextField
}

function FeedbackModal({
  open,
  onClose,
  threadId,
  feedback,
  feedbackType,
  feedbackSaved,
  feedbackSaving,
  taxonomy,
  taskType,
  onUpdateField,
  onSave,
  hasFeedbackContent,
  aiEvalResult,
  aiEvalLoading,
  aiEvalCollapsed,
  onAiEvalToggle
}) {
  const categories = (taxonomy?.categories?.filter(c => c.active) ?? []).sort(
    (a, b) => (a.order ?? 0) - (b.order ?? 0)
  )
  const mostlyBoolean = categories.filter(c => c.value_type === 'boolean').length > categories.length / 2
  const modalLayoutClass = mostlyBoolean ? 'feedback-modal-compact' : 'feedback-modal-large'

  if (!open) return null

  return (
    <div className="feedback-overlay" onClick={onClose}>
      <div
        className={`feedback-modal ${modalLayoutClass}`}
        onClick={e => e.stopPropagation()}
      >
        <div className="feedback-header">
          <h3>Feedback for this Example</h3>
          <div className="feedback-header-meta">
            <span className="feedback-thread">Thread: {threadId?.substring(0, 16)}...</span>
            {feedbackSaved && <span className="feedback-status saved">✓ Saved</span>}
          </div>
          <button className="feedback-close" onClick={onClose}>×</button>
        </div>

        <div className="feedback-modal-content">
          <div className="feedback-body feedback-categories">
            {categories.length === 0 ? (
              <div className="feedback-empty-state">
                {taxonomy === null && taskType
                  ? 'Loading feedback options…'
                  : 'No feedback categories available for this task type.'}
              </div>
            ) : (
              categories.map(category => {
                const Field = FIELD_BY_TYPE[category.value_type] ?? FeedbackTextField
                return (
                  <Field
                    key={category.key}
                    category={category}
                    value={feedback[category.key]}
                    onUpdate={(v) => onUpdateField(category.key, v)}
                  />
                )
              })
            )}
          </div>

          <div className="feedback-ai-collapsible">
            <button
              type="button"
              className="feedback-ai-toggle"
              onClick={onAiEvalToggle}
            >
              <span className="feedback-ai-chevron">{aiEvalCollapsed ? '▶' : '▼'}</span>
              AI Evaluation
              {aiEvalCollapsed && aiEvalResult?.output?.average_score != null && (
                <span className="feedback-ai-badge">Avg: {aiEvalResult.output.average_score}</span>
              )}
            </button>
            {!aiEvalCollapsed && (
              <div className="feedback-ai-section">
                {aiEvalLoading ? (
                  <div className="feedback-ai-loading">Loading…</div>
                ) : aiEvalResult ? (
                  <AIEvalResultCard evalResult={aiEvalResult} taskType={taskType} compact={false} />
                ) : (
                  <div className="feedback-ai-empty">No AI evaluation for this run.</div>
                )}
              </div>
            )}
          </div>
        </div>

        <div className="feedback-footer">
          <button className="btn-secondary" onClick={onClose}>
            Cancel
          </button>
          <button
            className="btn-primary"
            onClick={onSave}
            disabled={feedbackSaving || !hasFeedbackContent}
          >
            {feedbackSaving ? 'Saving...' : 'Save Feedback'}
          </button>
        </div>
      </div>
    </div>
  )
}

export default FeedbackModal
