import React, { useState, useEffect, useCallback } from 'react'

function SectionPickerModal({ open, onClose, onAddSection, config }) {
  const [sections, setSections] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const loadSections = useCallback(async () => {
    if (!config?.mongoUri) return
    setLoading(true)
    setError(null)
    try {
      const response = await fetch('/api/data/section-repo/sections', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          mongo_uri: config.mongoUri,
          query_filter: { status: 'ACTIVE', tag: 'smb' },
        }),
      })
      const data = await response.json()
      if (data.detail) throw new Error(data.detail)
      setSections(data.sections || [])
    } catch (err) {
      setError(err.message)
      setSections([])
    } finally {
      setLoading(false)
    }
  }, [config?.mongoUri])

  useEffect(() => {
    if (open) {
      loadSections()
    }
  }, [open, loadSections])

  useEffect(() => {
    if (!open) return
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [open, onClose])

  const handleAdd = (sectionId) => {
    onAddSection(sectionId)
    onClose()
  }

  if (!open) return null

  return (
    <div
      className="section-detail-modal-overlay"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div className="section-detail-modal section-picker-modal" onClick={(e) => e.stopPropagation()}>
        <div className="section-detail-modal-header">
          <h3 className="section-picker-modal-title">Add Section from Browser</h3>
          <button type="button" className="section-detail-modal-close" onClick={onClose}>
            Close
          </button>
        </div>
        <div className="section-picker-modal-body">
          {error && <div className="section-repo-error">{error}</div>}
          {loading ? (
            <div className="section-repo-loading">Loading sections...</div>
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
                  <div key={section.section_id} className="section-card section-card-with-actions">
                    {previewUrl && (
                      <div className="section-card-preview">
                        <img src={previewUrl} alt="" />
                      </div>
                    )}
                    <div className="section-card-body">
                      <div className="section-card-name">{displayName}</div>
                      <div className="section-card-id">{section.section_id}</div>
                      <div className="section-card-actions">
                        <button
                          type="button"
                          className="section-card-action section-card-action-primary"
                          onClick={() => handleAdd(section.section_id)}
                        >
                          Add
                        </button>
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default SectionPickerModal
