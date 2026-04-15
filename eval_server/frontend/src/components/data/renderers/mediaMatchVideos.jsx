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

function MediaMatchVideosResult({ result }) {
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
          const vid = r.shopify_video
          const meta = r.match_metadata
          const slotId = r.slot_identity?.element_id || r.slot_identity?.block_type || `Slot ${idx + 1}`
          const previewUrl = vid?.preview_image?.src || vid?.preview_image?.url
          const firstSource = vid?.sources?.[0]
          const sourceUrl = firstSource?.url
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
                {previewUrl ? (
                  <img
                    src={previewUrl}
                    alt={vid?.alt || ''}
                    onError={(e) => {
                      e.target.style.display = 'none'
                      const fb = e.target.nextSibling
                      if (fb) fb.style.display = 'flex'
                    }}
                  />
                ) : null}
                <div className="media-match-fallback" style={{ display: previewUrl ? 'none' : 'flex' }}>
                  Video
                </div>
              </div>
              <div className="media-match-body">
                {vid && (
                  <>
                    <code className="media-match-id">{vid.id}</code>
                    {vid.filename && <span className="media-match-filename">{vid.filename}</span>}
                    {meta && (
                      <div className="media-match-meta">
                        Source: {meta.source} · Score: {meta.fit_score?.toFixed(2)}
                      </div>
                    )}
                    {sourceUrl && (
                      <button
                        type="button"
                        className="media-match-copy-btn"
                        onClick={() => handleCopy(sourceUrl)}
                      >
                        {copied === sourceUrl ? 'Copied!' : 'Copy URL'}
                      </button>
                    )}
                  </>
                )}
                {!vid && <span className="media-match-no-match">No video matched for this slot</span>}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

export default MediaMatchVideosResult
