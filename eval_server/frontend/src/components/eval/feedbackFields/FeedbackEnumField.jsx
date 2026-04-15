import React from 'react'

function FeedbackEnumField({ category, value, onUpdate }) {
  const options = category.options || []
  const hasContent = value !== null && value !== undefined && value !== ''

  return (
    <div className="feedback-category">
      <label className="feedback-category-label">
        <span className="feedback-category-icon">{category.icon}</span>
        {category.label}
        {hasContent && <span className="feedback-has-content">●</span>}
      </label>
      <select
        value={value ?? ''}
        onChange={(e) => onUpdate(e.target.value)}
        className="feedback-select"
      >
        <option value="">Select...</option>
        {options.map(opt => (
          <option key={opt} value={opt}>{opt}</option>
        ))}
      </select>
    </div>
  )
}

export default FeedbackEnumField
