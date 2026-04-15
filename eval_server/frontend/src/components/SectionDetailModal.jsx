import React, { useState, useEffect, useCallback, useRef } from 'react'
import { ChevronLeft, ChevronRight, ExternalLink } from 'lucide-react'
import { toast } from 'react-toastify'

function SectionDetailModal({ open, onClose, sections = [], initialIndex = 0, config, onNavigateToCode }) {
  const [section, setSection] = useState(null)
  const [loading, setLoading] = useState(false)
  const [semanticTags, setSemanticTags] = useState([])
  const [newTagInput, setNewTagInput] = useState('')
  const [saving, setSaving] = useState(false)
  const [statusUpdating, setStatusUpdating] = useState(false)
  const [index, setIndex] = useState(initialIndex)
  const prevOpenRef = useRef(false)

  const sectionId = sections[index]?.section_id
  const total = sections.length

  useEffect(() => {
    if (open && !prevOpenRef.current) {
      setIndex(initialIndex)
    }
    prevOpenRef.current = open
  }, [open, initialIndex])

  const fetchSection = useCallback(async () => {
    if (!sectionId || !config?.mongoUri) return
    setLoading(true)
    try {
      const res = await fetch('/api/data/section-repo/sections/get-by-id', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          mongo_uri: config.mongoUri,
          section_id: sectionId,
        }),
      })
      const data = await res.json()
      if (data.detail) throw new Error(data.detail)
      setSection(data.section || null)
      setSemanticTags(data.section?.semantic_tags || [])
    } catch (err) {
      toast.error(err.message || 'Failed to load section')
      setSection(null)
      setSemanticTags([])
    } finally {
      setLoading(false)
    }
  }, [sectionId, config?.mongoUri])

  useEffect(() => {
    if (open && sectionId) {
      fetchSection()
    }
  }, [open, sectionId, fetchSection])

  useEffect(() => {
    if (!open) return
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [open, onClose])

  const handlePrev = () => {
    if (index > 0) setIndex(index - 1)
  }

  const handleNext = () => {
    if (index < total - 1) setIndex(index + 1)
  }

  const handleAddTag = () => {
    const tag = newTagInput.trim()
    if (!tag || semanticTags.includes(tag)) return
    setSemanticTags([...semanticTags, tag])
    setNewTagInput('')
  }

  const handleRemoveTag = (tagToRemove) => {
    setSemanticTags(semanticTags.filter((t) => t !== tagToRemove))
  }

  const handleToggleStatus = async () => {
    if (!sectionId || !config?.mongoUri) return
    const currentStatus = section?.status || 'ACTIVE'
    const newStatus = currentStatus === 'ACTIVE' ? 'NOT-ACTIVE' : 'ACTIVE'
    const actionLabel = newStatus === 'ACTIVE' ? 'ACTIVE' : 'NOT-ACTIVE'
    if (!window.confirm(`Set section to ${actionLabel}?`)) return
    setStatusUpdating(true)
    try {
      const res = await fetch('/api/data/section-repo/sections/update-status', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          mongo_uri: config.mongoUri,
          section_id: sectionId,
          status: newStatus,
        }),
      })
      const data = await res.json()
      if (data.detail) throw new Error(data.detail)
      setSection((prev) => (prev ? { ...prev, status: newStatus } : null))
      toast.success(`Status set to ${actionLabel}`)
    } catch (err) {
      toast.error(err.message || 'Failed to update status')
    } finally {
      setStatusUpdating(false)
    }
  }

  const handleSaveTags = async () => {
    if (!sectionId || !config?.mongoUri) return
    setSaving(true)
    try {
      const res = await fetch('/api/data/section-repo/sections/update-semantic-tags', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          mongo_uri: config.mongoUri,
          section_id: sectionId,
          semantic_tags: semanticTags,
        }),
      })
      const data = await res.json()
      if (data.detail) throw new Error(data.detail)
      toast.success('Semantic tags updated')
    } catch (err) {
      toast.error(err.message || 'Failed to update semantic tags')
    } finally {
      setSaving(false)
    }
  }

  if (!open) return null

  return (
    <div
      className="section-detail-modal-overlay"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div className="section-detail-modal" onClick={(e) => e.stopPropagation()}>
        <div className="section-detail-modal-header">
          <div className="section-detail-modal-nav">
            <button
              type="button"
              className="section-detail-modal-nav-btn"
              onClick={handlePrev}
              disabled={index <= 0}
            >
              Prev
            </button>
            <span className="section-detail-modal-title">
              Section {index + 1} of {total}
            </span>
            <button
              type="button"
              className="section-detail-modal-nav-btn"
              onClick={handleNext}
              disabled={index >= total - 1}
            >
              Next
            </button>
          </div>
          <button type="button" className="section-detail-modal-close" onClick={onClose}>
            Close
          </button>
        </div>

        <div className={`section-detail-modal-body ${total > 1 ? 'section-detail-modal-body-with-arrows' : ''}`}>
          {total > 1 && (
            <>
              <button
                type="button"
                className="section-detail-modal-arrow section-detail-modal-arrow-left"
                onClick={handlePrev}
                disabled={index <= 0}
                aria-label="Previous section"
              >
                <ChevronLeft size={28} />
              </button>
              <button
                type="button"
                className="section-detail-modal-arrow section-detail-modal-arrow-right"
                onClick={handleNext}
                disabled={index >= total - 1}
                aria-label="Next section"
              >
                <ChevronRight size={28} />
              </button>
            </>
          )}
          {loading ? (
            <div className="section-detail-modal-loading">Loading section...</div>
          ) : section ? (
            <div className="section-detail-modal-layout">
              {section.desktop_image_url && (
                <div className="section-detail-modal-preview">
                  <img src={section.desktop_image_url} alt="" />
                </div>
              )}
              <div className="section-detail-modal-right">
                <div className="section-detail-modal-details">
                <div className="section-detail-modal-field">
                  <span className="section-detail-modal-label">Section ID</span>
                  <div className="section-detail-modal-id-row">
                    <code className="section-detail-modal-value">{section.section_id || section._id}</code>
                    {onNavigateToCode && (
                      <button
                        type="button"
                        className="section-detail-modal-open-code-link"
                        onClick={() => onNavigateToCode(section.section_id || section._id)}
                      >
                        <ExternalLink size={14} />
                        Open in code editor
                      </button>
                    )}
                  </div>
                </div>
                <div className="section-detail-modal-field">
                  <span className="section-detail-modal-label">Status</span>
                  <div className="section-detail-modal-status-row">
                    <span className="section-detail-modal-value">{section.status || 'ACTIVE'}</span>
                    <button
                      type="button"
                      className="section-detail-modal-status-btn"
                      onClick={handleToggleStatus}
                      disabled={statusUpdating}
                    >
                      {(section.status || 'ACTIVE') === 'ACTIVE' ? 'Set NOT-ACTIVE' : 'Set Active'}
                    </button>
                  </div>
                </div>
                <div className="section-detail-modal-field">
                  <span className="section-detail-modal-label">Tag</span>
                  <span className="section-detail-modal-value">{section.tag || '—'}</span>
                </div>
                <div className="section-detail-modal-field">
                  <span className="section-detail-modal-label">L0 / L1</span>
                  <span className="section-detail-modal-value">
                    {section.section_l0 || '—'} / {section.section_l1 || '—'}
                  </span>
                </div>
                {section.section_label && (
                  <div className="section-detail-modal-field">
                    <span className="section-detail-modal-label">Label</span>
                    <span className="section-detail-modal-value">{section.section_label}</span>
                  </div>
                )}
                </div>

                <div className="section-detail-modal-tags">
                <h3 className="section-detail-modal-tags-title">Semantic tags</h3>
                <div className="section-detail-modal-tags-list">
                  {semanticTags.map((tag) => (
                    <span key={tag} className="section-detail-modal-tag-chip">
                      {tag}
                      <button
                        type="button"
                        className="section-detail-modal-tag-remove"
                        onClick={() => handleRemoveTag(tag)}
                        aria-label={`Remove ${tag}`}
                      >
                        ×
                      </button>
                    </span>
                  ))}
                </div>
                <div className="section-detail-modal-tags-add">
                  <input
                    type="text"
                    value={newTagInput}
                    onChange={(e) => setNewTagInput(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), handleAddTag())}
                    placeholder="Add tag"
                    className="section-detail-modal-tags-input"
                  />
                  <button
                    type="button"
                    className="section-detail-modal-tags-add-btn"
                    onClick={handleAddTag}
                  >
                    Add
                  </button>
                </div>
                <button
                  type="button"
                  className="section-detail-modal-save"
                  onClick={handleSaveTags}
                  disabled={saving}
                >
                  {saving ? 'Saving...' : 'Save'}
                </button>
                </div>
              </div>
            </div>
          ) : (
            <div className="section-detail-modal-loading">No section data</div>
          )}
        </div>
      </div>
    </div>
  )
}

export default SectionDetailModal
