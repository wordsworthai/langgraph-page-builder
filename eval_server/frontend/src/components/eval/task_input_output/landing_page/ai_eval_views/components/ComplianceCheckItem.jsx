import React from 'react'

function ComplianceCheckItem({ check, type }) {
  const { l0, pattern, severity, present_in_templates, violated_in_templates } = check

  if (type === 'required' || type === 'recommended') {
    const presentArr = present_in_templates || []
    return (
      <div className="compliance-check-item">
        <span className="check-name">{l0}</span>
        <div className="template-indicators">
          {presentArr.map((present, idx) => (
            <span
              key={idx}
              className={`template-indicator ${present ? 'present' : 'missing'}`}
              title={`Template ${idx + 1}: ${present ? 'Present' : 'Missing'}`}
            >
              {idx + 1}
            </span>
          ))}
        </div>
      </div>
    )
  }

  if (type === 'anti_pattern') {
    const violatedArr = violated_in_templates || []
    const hasViolation = violatedArr.some(v => v)
    return (
      <div className={`compliance-check-item ${hasViolation ? 'violated' : ''}`}>
        <span className="check-name">
          {pattern}
          {severity && <span className={`severity-badge ${severity}`}>{severity}</span>}
        </span>
        <div className="template-indicators">
          {violatedArr.map((violated, idx) => (
            <span
              key={idx}
              className={`template-indicator ${violated ? 'violated' : 'ok'}`}
              title={`Template ${idx + 1}: ${violated ? 'Violated' : 'OK'}`}
            >
              {idx + 1}
            </span>
          ))}
        </div>
      </div>
    )
  }

  return null
}

export default ComplianceCheckItem
