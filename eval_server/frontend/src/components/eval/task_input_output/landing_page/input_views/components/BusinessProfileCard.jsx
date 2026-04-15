import React, { useState, useEffect } from 'react'

function BusinessProfileCard({ businessId, config }) {
  const [profile, setProfile] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!businessId) return

    const fetchProfile = async () => {
      setLoading(true)
      setError(null)
      try {
        const response = await fetch('/api/business-profile', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ business_id: businessId })
        })

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`)
        }

        const data = await response.json()
        if (data.business_profile) {
          setProfile(data.business_profile)
        }
      } catch (err) {
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }

    fetchProfile()
  }, [businessId])

  if (!businessId) return null

  if (loading) {
    return (
      <div className="input-card full-width">
        <label>Business Profile</label>
        <span>Loading...</span>
      </div>
    )
  }

  if (error) {
    return (
      <div className="input-card full-width">
        <label>Business Profile</label>
        <span style={{ color: 'var(--accent-red)' }}>Error: {error}</span>
      </div>
    )
  }

  if (!profile) return null

  // Build summary text for collapsed view
  const summaryParts = []
  if (profile.business_name) summaryParts.push(profile.business_name)
  if (profile.formatted_address) summaryParts.push(profile.formatted_address)
  if (profile.google_rating || profile.yelp_rating) {
    const ratings = []
    if (profile.google_rating) ratings.push(`Google: ${profile.google_rating}⭐`)
    if (profile.yelp_rating) ratings.push(`Yelp: ${profile.yelp_rating}⭐`)
    summaryParts.push(ratings.join(' | '))
  }
  const summaryText = summaryParts.join(' • ')

  return (
    <div className="input-card full-width business-profile-card">
      <label>Business Profile</label>
      <details className="business-profile-details">
        <summary className="business-profile-summary">
          {summaryText || 'View Business Profile'}
        </summary>
        <div className="business-profile-content">
          {profile.business_name && (
            <div className="profile-field">
              <strong>Name:</strong> {profile.business_name}
            </div>
          )}
          {profile.display_name && profile.display_name !== profile.business_name && (
            <div className="profile-field">
              <strong>Display Name:</strong> {profile.display_name}
            </div>
          )}
          {profile.tagline && (
            <div className="profile-field">
              <strong>Tagline:</strong> {profile.tagline}
            </div>
          )}
          {profile.description && (
            <div className="profile-field">
              <strong>Description:</strong> {profile.description}
            </div>
          )}
          {profile.industry && (
            <div className="profile-field">
              <strong>Industry:</strong> {profile.industry}
            </div>
          )}
          {profile.primary_category && (
            <div className="profile-field">
              <strong>Category:</strong> {profile.primary_category}
            </div>
          )}
          {profile.categories && profile.categories.length > 0 && (
            <div className="profile-field">
              <strong>Categories:</strong> {profile.categories.join(', ')}
            </div>
          )}
          {profile.formatted_address && (
            <div className="profile-field">
              <strong>Address:</strong> {profile.formatted_address}
            </div>
          )}
          {profile.phone && (
            <div className="profile-field">
              <strong>Phone:</strong> {profile.phone}
            </div>
          )}
          {profile.email && (
            <div className="profile-field">
              <strong>Email:</strong> {profile.email}
            </div>
          )}
          {profile.website_url && (
            <div className="profile-field">
              <strong>Website:</strong>{' '}
              <a href={profile.website_url} target="_blank" rel="noopener noreferrer">
                {profile.website_url}
              </a>
            </div>
          )}
          {profile.google_maps_url && (
            <div className="profile-field">
              <strong>Google Maps:</strong>{' '}
              <a href={profile.google_maps_url} target="_blank" rel="noopener noreferrer">
                View on Google Maps
              </a>
            </div>
          )}
          {profile.yelp_url && (
            <div className="profile-field">
              <strong>Yelp:</strong>{' '}
              <a href={profile.yelp_url} target="_blank" rel="noopener noreferrer">
                View on Yelp
              </a>
            </div>
          )}
          {(profile.google_rating || profile.yelp_rating) && (
            <div className="profile-field">
              <strong>Ratings:</strong>{' '}
              {profile.google_rating && (
                <span>Google: {profile.google_rating}⭐ ({profile.google_review_count || 0} reviews)</span>
              )}
              {profile.google_rating && profile.yelp_rating && ' | '}
              {profile.yelp_rating && (
                <span>Yelp: {profile.yelp_rating}⭐ ({profile.yelp_review_count || 0} reviews)</span>
              )}
            </div>
          )}
          {profile.services && profile.services.length > 0 && (
            <div className="profile-field">
              <strong>Services:</strong> {profile.services.join(', ')}
            </div>
          )}
          {profile.specialties && (
            <div className="profile-field">
              <strong>Specialties:</strong> {profile.specialties}
            </div>
          )}
          {profile.year_established && (
            <div className="profile-field">
              <strong>Established:</strong> {profile.year_established}
            </div>
          )}
        </div>
      </details>
    </div>
  )
}

export default BusinessProfileCard
