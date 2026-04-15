import React from 'react'

function normalizeTradeClassification(result) {
  if (!result || !result.success) return null
  return result.result
}

function TradeClassificationResult({ result }) {
  const data = normalizeTradeClassification(result)

  if (!data) {
    return <div className="data-debug-empty">No trade classification found for this business.</div>
  }

  const {
    business_id,
    assigned_trades = [],
    business_summary,
    classified_at,
    google_types = [],
    yelp_categories,
  } = data

  return (
    <div className="trade-classification-result">
      <div className="trade-classification-section">
        <h4 className="trade-classification-label">Business ID</h4>
        <code className="trade-classification-value">{business_id}</code>
      </div>

      {business_summary && (
        <div className="trade-classification-section">
          <h4 className="trade-classification-label">Business Summary</h4>
          <p className="trade-classification-summary">{business_summary}</p>
        </div>
      )}

      {classified_at && (
        <div className="trade-classification-section">
          <h4 className="trade-classification-label">Classified At</h4>
          <span className="trade-classification-value">{classified_at}</span>
        </div>
      )}

      {assigned_trades.length > 0 && (
        <div className="trade-classification-section">
          <h4 className="trade-classification-label">Assigned Trades</h4>
          <div className="trade-classification-trades">
            {assigned_trades.map((t, idx) => (
              <div key={idx} className="trade-classification-trade-card">
                <div className="trade-classification-trade-header">
                  <span className="trade-classification-trade-name">{t.trade}</span>
                  {t.confidence && (
                    <span className={`trade-classification-confidence trade-classification-confidence-${t.confidence}`}>
                      {t.confidence}
                    </span>
                  )}
                </div>
                {t.parent_category && (
                  <div className="trade-classification-trade-meta">
                    Parent: {t.parent_category}
                  </div>
                )}
                {t.reasoning && (
                  <p className="trade-classification-trade-reasoning">{t.reasoning}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {google_types && google_types.length > 0 && (
        <div className="trade-classification-section">
          <h4 className="trade-classification-label">Google Types</h4>
          <div className="trade-classification-tags">
            {google_types.map((t, idx) => (
              <span key={idx} className="trade-classification-tag">{t}</span>
            ))}
          </div>
        </div>
      )}

      {yelp_categories && (
        <div className="trade-classification-section">
          <h4 className="trade-classification-label">Yelp Categories</h4>
          <span className="trade-classification-value">{String(yelp_categories)}</span>
        </div>
      )}
    </div>
  )
}

export default TradeClassificationResult
