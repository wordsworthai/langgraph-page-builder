import React from 'react'

function normalizeReviews(result) {
  if (!result || !result.success) return null
  return result.result
}

function formatDate(ts) {
  if (!ts) return null
  try {
    const d = typeof ts === 'string' ? new Date(ts) : ts
    return isNaN(d.getTime()) ? ts : d.toLocaleDateString()
  } catch {
    return String(ts)
  }
}

function ReviewsResult({ result }) {
  const data = normalizeReviews(result)
  if (!data) return <div className="data-debug-empty">No reviews found.</div>

  const reviews = data.reviews || []

  return (
    <div className="reviews-result">
      {data.average_rating != null && (
        <div className="reviews-result-summary">
          Average: {data.average_rating} · {reviews.length} reviews
          {data.review_providers?.length ? ` · ${data.review_providers.join(', ')}` : ''}
        </div>
      )}
      {reviews.length === 0 ? (
        <div className="data-debug-empty">No reviews returned.</div>
      ) : (
        <div className="reviews-result-list">
          {reviews.map((r, i) => (
            <div key={i} className="reviews-result-card">
              <div className="reviews-result-header">
                {r.rating != null && (
                  <span className="reviews-result-rating">{r.rating} ★</span>
                )}
                {r.author && <span className="reviews-result-author">{r.author}</span>}
                {r.review_timestamp && (
                  <span className="reviews-result-date">{formatDate(r.review_timestamp)}</span>
                )}
                {r.review_provider && (
                  <span className="reviews-result-provider">{r.review_provider}</span>
                )}
              </div>
              {r.title && <div className="reviews-result-title">{r.title}</div>}
              <p className="reviews-result-body">{r.body}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default ReviewsResult
