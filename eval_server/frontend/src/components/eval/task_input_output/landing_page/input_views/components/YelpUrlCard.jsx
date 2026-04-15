import React from 'react'

function YelpUrlCard({ yelpUrl }) {
  if (!yelpUrl) return null

  return (
    <div className="input-card full-width">
      <label>Yelp URL</label>
      <a href={yelpUrl} target="_blank" rel="noopener noreferrer">
        {yelpUrl}
      </a>
    </div>
  )
}

export default YelpUrlCard
