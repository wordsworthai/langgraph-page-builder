import React from 'react'

function BusinessNameCard({ businessName }) {
  if (!businessName) return null

  return (
    <div className="input-card">
      <label>Business Name</label>
      <span>{businessName}</span>
    </div>
  )
}

export default BusinessNameCard
