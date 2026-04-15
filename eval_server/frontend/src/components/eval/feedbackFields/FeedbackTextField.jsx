import React from 'react'

function FeedbackTextField({ category, value, onUpdate }) {
  const hasContent = value !== null && value !== undefined && value !== ''

  return (
    <div className="feedback-category">
      <label className="feedback-category-label">
        <span className="feedback-category-icon">{category.icon}</span>
        {category.label}
        {hasContent && <span className="feedback-has-content">●</span>}
      </label>
      <textarea
        value={value || ''}
        onChange={(e) => onUpdate(e.target.value)}
        placeholder={category.placeholder}
        rows={2}
      />
    </div>
  )
}

export default FeedbackTextField
