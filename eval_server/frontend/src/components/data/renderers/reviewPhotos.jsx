import React, { useState } from 'react'

function normalizeReviewPhotos(result) {
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

function ReviewPhotosResult({ result }) {
  const [copied, setCopied] = useState(null)
  const data = normalizeReviewPhotos(result)
  if (!data) return <div className="data-debug-empty">No review photos found.</div>

  const items = data.items || []
  const handleCopy = async (url) => {
    const ok = await copyToClipboard(url)
    if (ok) {
      setCopied(url)
      setTimeout(() => setCopied(null), 1500)
    }
  }

  return (
    <div className="review-photos-result">
      {data.reviews_with_photos != null && (
        <div className="review-photos-summary">{data.reviews_with_photos} reviews with photos</div>
      )}
      {items.length === 0 ? (
        <div className="data-debug-empty">No review photos returned.</div>
      ) : (
        <div className="review-photos-grid">
          {items.map((photo) => (
            <div key={photo.photo_id} className="review-photos-card">
              <div className="review-photos-preview">
                {photo.url ? (
                  <img
                    src={photo.url}
                    alt=""
                    onError={(e) => {
                      e.target.style.display = 'none'
                      const fb = e.target.nextSibling
                      if (fb) fb.style.display = 'flex'
                    }}
                  />
                ) : null}
                <div className="review-photos-fallback" style={{ display: photo.url ? 'none' : 'flex' }}>
                  No preview
                </div>
              </div>
              <div className="review-photos-body">
                {photo.reviewer_name && <div className="review-photos-reviewer">{photo.reviewer_name}</div>}
                {photo.review_rating != null && (
                  <span className="review-photos-rating">{photo.review_rating} ★</span>
                )}
                {photo.review_date && <span className="review-photos-date">{photo.review_date}</span>}
                {photo.url && (
                  <button
                    type="button"
                    className="review-photos-copy-btn"
                    onClick={() => handleCopy(photo.url)}
                  >
                    {copied === photo.url ? 'Copied!' : 'Copy URL'}
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default ReviewPhotosResult
