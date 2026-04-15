import React, { useState } from 'react'

function normalizePhotos(result) {
  if (!result || !result.success) return []
  const data = result.result
  if (!data) return []
  if (Array.isArray(data)) return data
  if (Array.isArray(data.items)) return data.items
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

function BusinessPhotosResult({ result }) {
  const [copiedUrl, setCopiedUrl] = useState(null)
  const photos = normalizePhotos(result)

  const handleCopyUrl = async (url) => {
    const ok = await copyToClipboard(url)
    if (ok) {
      setCopiedUrl(url)
      setTimeout(() => setCopiedUrl(null), 1500)
    }
  }

  if (!photos.length) {
    return <div className="data-debug-empty">No business photos found.</div>
  }

  return (
    <div className="business-photos-result">
      <div className="business-photos-grid">
        {photos.map((photo) => {
          const id = photo.photo_id || `photo_${photo.index ?? 0}`
          const url = photo.url || photo.image_url
          const dims = photo.width && photo.height ? `${photo.width}×${photo.height}` : null
          const copied = copiedUrl === url
          return (
            <div key={id} className="business-photo-card">
              <div className="business-photo-preview">
                {url ? (
                  <img
                    src={url}
                    alt=""
                    onError={(e) => {
                      e.target.style.display = 'none'
                      const fallback = e.target.nextSibling
                      if (fallback) fallback.style.display = 'flex'
                    }}
                  />
                ) : null}
                <div className="business-photo-fallback" style={{ display: url ? 'none' : 'flex' }}>
                  <span>No preview</span>
                </div>
              </div>
              <div className="business-photo-body">
                <code className="business-photo-id">{id}</code>
                <div className="business-photo-meta">
                  {dims && <span>{dims}</span>}
                  {photo.aspect_ratio != null && (
                    <span className="business-photo-aspect">AR: {Number(photo.aspect_ratio).toFixed(2)}</span>
                  )}
                  {photo.source && <span className="business-photo-source">{photo.source}</span>}
                </div>
                {url && (
                  <button
                    type="button"
                    className="business-photo-copy-btn"
                    onClick={() => handleCopyUrl(url)}
                    title="Copy URL"
                  >
                    {copied ? 'Copied!' : 'Copy URL'}
                  </button>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

export default BusinessPhotosResult
