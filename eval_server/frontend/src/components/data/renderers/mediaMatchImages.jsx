import React, { useState } from 'react'

function normalizeMatchResult(result) {
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

function MediaMatchImagesResult({ result }) {
  const [copied, setCopied] = useState(null)
  const data = normalizeMatchResult(result)
  if (!data) return <div className="data-debug-empty">No match result.</div>

  const results = data.results || []
  const handleCopy = async (url) => {
    const ok = await copyToClipboard(url)
    if (ok) {
      setCopied(url)
      setTimeout(() => setCopied(null), 1500)
    }
  }

  return (
    <div className="media-match-result">
      <div className="media-match-summary">
        {data.matched_count} / {data.total_slots} matched
        {data.unmatched_count > 0 && ` · ${data.unmatched_count} unmatched`}
      </div>
      <div className="media-match-slots">
        {results.map((r, idx) => {
          const img = r.shopify_image
          const meta = r.match_metadata
          const slotId = r.slot_identity?.element_id || r.slot_identity?.block_type || `Slot ${idx + 1}`
          const src = img?.src
          return (
            <div key={idx} className="media-match-card">
              <div className="media-match-card-header">
                <span className="media-match-slot-id">{slotId}</span>
                {meta && (
                  <span className={`media-match-tier media-match-tier-${(meta.quality_tier || '').toLowerCase()}`}>
                    {meta.quality_tier}
                  </span>
                )}
              </div>
              <div className="media-match-preview">
                {src ? (
                  <img
                    src={src}
                    alt={img?.alt || ''}
                    onError={(e) => {
                      e.target.style.display = 'none'
                      const fb = e.target.nextSibling
                      if (fb) fb.style.display = 'flex'
                    }}
                  />
                ) : null}
                <div className="media-match-fallback" style={{ display: src ? 'none' : 'flex' }}>
                  No match
                </div>
              </div>
              <div className="media-match-body">
                {img && (
                  <>
                    <code className="media-match-id">{img.id}</code>
                    {img.width && img.height && (
                      <span className="media-match-dims">{img.width}×{img.height}</span>
                    )}
                    {meta && (
                      <div className="media-match-meta">
                        Source: {meta.source} · Score: {meta.fit_score?.toFixed(2)}
                      </div>
                    )}
                    {src && (
                      <button
                        type="button"
                        className="media-match-copy-btn"
                        onClick={() => handleCopy(src)}
                      >
                        {copied === src ? 'Copied!' : 'Copy URL'}
                      </button>
                    )}
                  </>
                )}
                {!img && <span className="media-match-no-match">No image matched for this slot</span>}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

export default MediaMatchImagesResult
