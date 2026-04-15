import React, { useState } from 'react'

function normalizeTrades(result) {
  if (!result || !result.success) return []
  if (Array.isArray(result.result)) return result.result
  return []
}

async function copyToClipboard(text) {
  try {
    await navigator.clipboard.writeText(text)
    return true
  } catch {
    return false
  }
}

function TradesCatalogResult({ result }) {
  const [copiedKey, setCopiedKey] = useState(null)
  const trades = normalizeTrades(result)

  const handleCopy = async (tradeKey) => {
    const ok = await copyToClipboard(tradeKey)
    if (ok) {
      setCopiedKey(tradeKey)
      setTimeout(() => setCopiedKey(null), 1500)
    }
  }

  const byCategory = trades.reduce((acc, t) => {
    const cat = t.parent_category || 'Other'
    if (!acc[cat]) acc[cat] = []
    acc[cat].push(t)
    return acc
  }, {})

  if (!trades.length) {
    return <div className="data-debug-empty">No trades found in catalog.</div>
  }

  return (
    <div className="trades-catalog-result">
      <div className="trades-catalog-trades">
        {Object.entries(byCategory).map(([category, items]) => (
          <div key={category} className="trades-catalog-category">
            <h4 className="trades-catalog-category-title">{category}</h4>
            <div className="trades-catalog-grid">
              {items.map((t) => (
                <div key={t.trade} className="trades-catalog-card">
                  <div className="trades-catalog-card-header">
                    <code className="trades-catalog-trade-key">{t.trade}</code>
                    <button
                      type="button"
                      className="trades-catalog-copy-btn"
                      onClick={() => handleCopy(t.trade)}
                      title="Copy trade key"
                    >
                      {copiedKey === t.trade ? 'Copied!' : 'Copy'}
                    </button>
                  </div>
                  {t.description && (
                    <p className="trades-catalog-description">{t.description}</p>
                  )}
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export default TradesCatalogResult
