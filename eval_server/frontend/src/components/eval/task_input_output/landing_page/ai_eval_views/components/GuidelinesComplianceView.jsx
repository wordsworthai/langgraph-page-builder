import React from 'react'
import ComplianceCheckItem from './ComplianceCheckItem'

function GuidelinesComplianceView({ compliance }) {
  const { required = {}, recommended = {}, anti_patterns = {} } = compliance

  return (
    <div className="compliance-view">
      <div className="compliance-section">
        <div className="compliance-header required">
          <span>Required Sections</span>
          <span className="compliance-ratio">
            {required.passed ?? 0}/{required.total ?? 0}
          </span>
        </div>
        {required.checks?.length > 0 && (
          <div className="compliance-checks">
            {required.checks.map((check, idx) => (
              <ComplianceCheckItem key={idx} check={check} type="required" />
            ))}
          </div>
        )}
      </div>

      <div className="compliance-section">
        <div className="compliance-header recommended">
          <span>Recommended Sections</span>
          <span className="compliance-ratio">
            {recommended.present ?? 0}/{recommended.total ?? 0}
          </span>
        </div>
        {recommended.checks?.length > 0 && (
          <div className="compliance-checks">
            {recommended.checks.map((check, idx) => (
              <ComplianceCheckItem key={idx} check={check} type="recommended" />
            ))}
          </div>
        )}
      </div>

      <div className="compliance-section">
        <div className="compliance-header anti-patterns">
          <span>Anti-patterns</span>
          <span className="compliance-ratio violations">
            {anti_patterns.violations ?? 0} violations
          </span>
        </div>
        {anti_patterns.checks?.length > 0 && (
          <div className="compliance-checks">
            {anti_patterns.checks.map((check, idx) => (
              <ComplianceCheckItem key={idx} check={check} type="anti_pattern" />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default GuidelinesComplianceView
