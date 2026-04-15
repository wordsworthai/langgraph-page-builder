import React from 'react'

function FeedbackNumberField({ category, value, onUpdate }) {
  const hasContent = value !== null && value !== undefined && value !== ''

  return (
    <div className="feedback-category">
      <label className="feedback-category-label">
        <span className="feedback-category-icon">{category.icon}</span>
        {category.label}
        {hasContent && <span className="feedback-has-content">●</span>}
      </label>
      <input
        type="number"
        value={value ?? ''}
        onChange={(e) => {
          const v = e.target.value
          onUpdate(v === '' ? null : Number(v))
        }}
        placeholder={category.placeholder}
        className="feedback-number"
      />
    </div>
  )
}

export default FeedbackNumberField
