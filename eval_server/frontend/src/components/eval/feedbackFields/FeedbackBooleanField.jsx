import React from 'react'

function FeedbackBooleanField({ category, value, onUpdate }) {
  return (
    <div className="feedback-category feedback-boolean">
      <label className="feedback-category-label feedback-checkbox-label">
        <input
          type="checkbox"
          checked={value === true}
          onChange={(e) => onUpdate(e.target.checked)}
          className="feedback-checkbox"
        />
        <span className="feedback-category-icon">{category.icon}</span>
        {category.label}
      </label>
    </div>
  )
}

export default FeedbackBooleanField
