import React, { useState } from 'react'

function normalizeMediaAssets(result) {
  if (!result || !result.success) return null
  return result.result
}

function getMediaSrc(item) {
  const lookup = item.lookup_object
  if (!lookup) return null
  if (lookup.src) return lookup.src
  if (lookup.preview_image?.url) return lookup.preview_image.url
  const srcs = lookup.sources
  if (srcs && srcs[0]?.url) return srcs[0].url
  return null
}

async function copyToClipboard(text) {
  try {
    await navigator.clipboard.writeText(text)
    return true
  } catch {
    return false
  }
}

function MediaAssetsResult({ result }) {
  const [copied, setCopied] = useState(null)
  const data = normalizeMediaAssets(result)
  if (!data) return <div className="data-debug-empty">No media assets found.</div>

  const items = data.items || []
  const handleCopy = async (url) => {
    const ok = await copyToClipboard(url)
    if (ok) {
      setCopied(url)
      setTimeout(() => setCopied(null), 1500)
    }
  }

  return (
    <div className="media-assets-result">
      <div className="media-assets-summary">
        {data.images_count != null && <span>{data.images_count} images</span>}
        {data.videos_count != null && <span>{data.videos_count} videos</span>}
      </div>
      {items.length === 0 ? (
        <div className="data-debug-empty">No media items returned.</div>
      ) : (
        <div className="media-assets-grid">
          {items.map((item) => {
            const src = getMediaSrc(item)
            const isVideo = item.media_type === 'video'
            const lookup = item.lookup_object || {}
            return (
              <div key={item.media_id} className="media-assets-card">
                <div className="media-assets-preview">
                  {src && !isVideo ? (
                    <img
                      src={src}
                      alt={lookup.alt || ''}
                      onError={(e) => {
                        e.target.style.display = 'none'
                        const fb = e.target.nextSibling
                        if (fb) fb.style.display = 'flex'
                      }}
                    />
                  ) : isVideo && (lookup.preview_image?.url || src) ? (
                    <img src={lookup.preview_image?.url || src} alt="" />
                  ) : null}
                  <div className="media-assets-fallback" style={{ display: src ? 'none' : 'flex' }}>
                    {isVideo ? 'Video' : 'No preview'}
                  </div>
                </div>
                <div className="media-assets-body">
                  <code className="media-assets-id">{item.media_id}</code>
                  <div className="media-assets-meta">
                    <span>{item.media_type}</span>
                    <span>{item.source}</span>
                    {lookup.width && lookup.height && (
                      <span>{lookup.width}×{lookup.height}</span>
                    )}
                  </div>
                  {src && (
                    <button
                      type="button"
                      className="media-assets-copy-btn"
                      onClick={() => handleCopy(src)}
                    >
                      {copied === src ? 'Copied!' : 'Copy URL'}
                    </button>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

export default MediaAssetsResult
