import React, { useState } from 'react'

function normalizeLogos(result) {
  if (!result || !result.success) return null
  return result.result
}

async function copyToClipboard(text) {
  try {
    await navigator.clipboard.writeText(text)
    return true
  } catch {
    return false
  }
}

function LogosResult({ result }) {
  const [copied, setCopied] = useState(null)
  const data = normalizeLogos(result)
  if (!data) return <div className="data-debug-empty">No logo data found.</div>

  const logos = data.all_logos || (data.primary_logo ? [data.primary_logo] : [])

  const handleCopy = async (url) => {
    const ok = await copyToClipboard(url)
    if (ok) {
      setCopied(url)
      setTimeout(() => setCopied(null), 1500)
    }
  }

  return (
    <div className="logos-result">
      {data.matched_trades && data.matched_trades.length > 0 && (
        <div className="logos-result-section">
          <h4 className="logos-result-label">Matched Trades</h4>
          <div className="logos-result-tags">
            {data.matched_trades.map((t, i) => (
              <span key={i} className="logos-result-tag">{t}</span>
            ))}
          </div>
        </div>
      )}
      {data.has_logo === false && logos.length === 0 && (
        <div className="data-debug-empty">No logos matched for this business.</div>
      )}
      {logos.length > 0 && (
        <div className="logos-result-section">
          <h4 className="logos-result-label">Logos ({logos.length})</h4>
          <div className="logos-result-grid">
            {logos.map((logo) => {
              const url = logo.url
              const isPrimary = data.primary_logo && logo.logo_id === data.primary_logo.logo_id
              return (
                <div key={logo.logo_id} className={`logos-result-card ${isPrimary ? 'primary' : ''}`}>
                  <div className="logos-result-preview">
                    {url ? (
                      <img
                        src={url}
                        alt=""
                        onError={(e) => {
                          e.target.style.display = 'none'
                          const fb = e.target.nextSibling
                          if (fb) fb.style.display = 'flex'
                        }}
                      />
                    ) : null}
                    <div className="logos-result-fallback" style={{ display: url ? 'none' : 'flex' }}>
                      No preview
                    </div>
                  </div>
                  <div className="logos-result-body">
                    <code className="logos-result-id">{logo.logo_id}</code>
                    <div className="logos-result-meta">
                      {logo.trade_type && <span>{logo.trade_type}</span>}
                      {logo.source && <span>{logo.source}</span>}
                      {logo.width && logo.height && <span>{logo.width}×{logo.height}</span>}
                    </div>
                    {url && (
                      <button
                        type="button"
                        className="logos-result-copy-btn"
                        onClick={() => handleCopy(url)}
                      >
                        {copied === url ? 'Copied!' : 'Copy URL'}
                      </button>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}

export default LogosResult
