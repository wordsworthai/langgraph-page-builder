import React, { useState, useEffect, useCallback } from 'react'

function SectionRepoTab({ config }) {
  const [categories, setCategories] = useState([])
  const [sections, setSections] = useState([])
  const [selectedL0, setSelectedL0] = useState(null)
  const [loadingCategories, setLoadingCategories] = useState(false)
  const [loadingSections, setLoadingSections] = useState(false)
  const [error, setError] = useState(null)

  const loadCategories = useCallback(async () => {
    setLoadingCategories(true)
    setError(null)
    try {
      const response = await fetch('/api/data/section-repo/categories', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          mongo_uri: config.mongoUri,
        }),
      })
      const data = await response.json()
      if (data.detail) throw new Error(data.detail)
      setCategories(data.categories || [])
    } catch (err) {
      setError(err.message)
      setCategories([])
    } finally {
      setLoadingCategories(false)
    }
  }, [config.mongoUri])

  const loadSections = useCallback(async (l0Category) => {
    setLoadingSections(true)
    setError(null)
    try {
      const response = await fetch('/api/data/section-repo/sections', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          mongo_uri: config.mongoUri,
          l0_category: l0Category || undefined,
        }),
      })
      const data = await response.json()
      if (data.detail) throw new Error(data.detail)
      setSections(data.sections || [])
    } catch (err) {
      setError(err.message)
      setSections([])
    } finally {
      setLoadingSections(false)
    }
  }, [config.mongoUri])

  useEffect(() => {
    loadCategories()
  }, [loadCategories])

  useEffect(() => {
    loadSections(selectedL0 ? (selectedL0.original_l0 || selectedL0.name) : null)
  }, [selectedL0, loadSections])

  const handleSelectL0 = (cat) => {
    setSelectedL0(selectedL0?.l0_key === cat.l0_key ? null : cat)
  }

  return (
    <div className="section-repo-layout">
      <div className="section-repo-sidebar">
        <div className="section-repo-sidebar-header">
          <h3>L0 Categories</h3>
        </div>
        {loadingCategories ? (
          <div className="section-repo-loading">Loading categories...</div>
        ) : error ? (
          <div className="section-repo-error">{error}</div>
        ) : categories.length === 0 ? (
          <div className="section-repo-empty">No categories found</div>
        ) : (
          <div className="section-repo-category-list">
            <button
              className={`section-repo-category-item ${!selectedL0 ? 'active' : ''}`}
              onClick={() => setSelectedL0(null)}
            >
              All
            </button>
            {categories.map((cat) => (
              <button
                key={cat.l0_key}
                className={`section-repo-category-item ${selectedL0?.l0_key === cat.l0_key ? 'active' : ''}`}
                onClick={() => handleSelectL0(cat)}
              >
                <span className="category-name">{cat.name || cat.l0_key}</span>
                <span className="category-count">{cat.count}</span>
              </button>
            ))}
          </div>
        )}
      </div>
      <div className="section-repo-content">
        <div className="section-repo-content-header">
          <h3>{selectedL0 ? `${selectedL0.name} sections` : 'All sections'}</h3>
        </div>
        {loadingSections ? (
          <div className="section-repo-loading">Loading sections...</div>
        ) : error && sections.length === 0 ? (
          <div className="section-repo-error">{error}</div>
        ) : sections.length === 0 ? (
          <div className="section-repo-empty">No sections found</div>
        ) : (
          <div className="section-repo-grid">
            {sections.map((section) => {
              const displayName = section.section_l1
                ? `${section.section_l0 || ''} - ${section.section_l1}`
                : section.section_l0 || section.section_id
              const previewUrl = section.desktop_image_url
              return (
                <div key={section.section_id} className="section-card">
                  {previewUrl && (
                    <div className="section-card-preview">
                      <img src={previewUrl} alt="" />
                    </div>
                  )}
                  <div className="section-card-body">
                    <div className="section-card-name">{displayName}</div>
                    <div className="section-card-id">{section.section_id}</div>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}

export default SectionRepoTab
