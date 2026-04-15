import React from 'react'

function normalizeProfile(result) {
  if (!result || !result.success) return null
  return result.result
}

function formatAddress(addr) {
  if (!addr || typeof addr !== 'object') return null
  const parts = [addr.street, addr.city, addr.state, addr.zip].filter(Boolean)
  return parts.length ? parts.join(', ') : null
}

function BusinessProfileResult({ result }) {
  const data = normalizeProfile(result)
  if (!data) return <div className="data-debug-empty">No business profile found.</div>

  const addr = formatAddress(data.address) || data.formatted_address
  const hours = data.hours
  const coords = data.coordinates

  return (
    <div className="business-profile-result">
      <div className="business-profile-section">
        <h4 className="business-profile-label">Business</h4>
        <div className="business-profile-identity">
          <div className="business-profile-name">{data.display_name || data.business_name}</div>
          {data.tagline && <p className="business-profile-tagline">{data.tagline}</p>}
          {data.description && <p className="business-profile-desc">{data.description}</p>}
        </div>
      </div>

      {(data.primary_category || (data.categories && data.categories.length)) && (
        <div className="business-profile-section">
          <h4 className="business-profile-label">Categories</h4>
          <div className="business-profile-tags">
            {data.primary_category && <span className="business-profile-tag">{data.primary_category}</span>}
            {data.industry && <span className="business-profile-tag">{data.industry}</span>}
            {(data.categories || []).map((c, i) => (
              <span key={i} className="business-profile-tag">{c}</span>
            ))}
          </div>
        </div>
      )}

      {(data.phone || data.email || data.website_url) && (
        <div className="business-profile-section">
          <h4 className="business-profile-label">Contact</h4>
          <div className="business-profile-contact">
            {data.phone && <div>Phone: {data.phone}</div>}
            {data.email && <div>Email: {data.email}</div>}
            {data.website_url && <div><a href={data.website_url} target="_blank" rel="noreferrer">Website</a></div>}
          </div>
        </div>
      )}

      {addr && (
        <div className="business-profile-section">
          <h4 className="business-profile-label">Address</h4>
          <div>{addr}</div>
          {coords && <code className="business-profile-coords">{coords.lat}, {coords.lng}</code>}
        </div>
      )}

      {(data.google_rating != null || data.yelp_rating != null) && (
        <div className="business-profile-section">
          <h4 className="business-profile-label">Ratings</h4>
          <div className="business-profile-ratings">
            {data.google_rating != null && (
              <span>Google: {data.google_rating} ({data.google_review_count ?? 0} reviews)</span>
            )}
            {data.yelp_rating != null && (
              <span>Yelp: {data.yelp_rating} ({data.yelp_review_count ?? 0} reviews)</span>
            )}
          </div>
        </div>
      )}

      {hours && hours.length > 0 && (
        <div className="business-profile-section">
          <h4 className="business-profile-label">Hours</h4>
          <ul className="business-profile-hours">
            {hours.map((h, i) => (
              <li key={i}>{h.day}: {h.hours}</li>
            ))}
          </ul>
        </div>
      )}

      {data.services && data.services.length > 0 && (
        <div className="business-profile-section">
          <h4 className="business-profile-label">Services</h4>
          <ul className="business-profile-list">{data.services.map((s, i) => <li key={i}>{s}</li>)}</ul>
        </div>
      )}
    </div>
  )
}

export default BusinessProfileResult
