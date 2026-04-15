import React, { useState, useEffect, useCallback } from 'react'
import { toast } from 'react-toastify'
import SectionDetailModal from './SectionDetailModal'

function SectionBrowserView({ config, onNavigateToCode }) {
  const [tags, setTags] = useState([])
  const [semanticTags, setSemanticTags] = useState([])
  const [detailModalOpen, setDetailModalOpen] = useState(false)
  const [detailModalIndex, setDetailModalIndex] = useState(0)
  const [statuses, setStatuses] = useState([])
  const [categories, setCategories] = useState([])
  const [sections, setSections] = useState([])
  const [selectedTag, setSelectedTag] = useState('smb')
  const [selectedStatus, setSelectedStatus] = useState('ACTIVE')
  const [selectedSemanticTag, setSelectedSemanticTag] = useState('all')
  const [selectedL0, setSelectedL0] = useState(null)
  const [selectedL1, setSelectedL1] = useState(null)
  const [loadingDistinct, setLoadingDistinct] = useState(false)
  const [loadingCategories, setLoadingCategories] = useState(false)
  const [loadingSections, setLoadingSections] = useState(false)
  const [error, setError] = useState(null)

  const queryFilter = useCallback(() => {
    const q = {}
    if (selectedTag && selectedTag !== 'all') q.tag = selectedTag
    if (selectedStatus && selectedStatus !== 'all') q.status = selectedStatus
    if (selectedSemanticTag && selectedSemanticTag !== 'all') q.semantic_tags = selectedSemanticTag
    return Object.keys(q).length ? q : { status: 'ACTIVE', tag: 'smb' }
  }, [selectedTag, selectedStatus, selectedSemanticTag])

  const loadDistinct = useCallback(async () => {
    setLoadingDistinct(true)
    setError(null)
    try {
      const [tagsRes, statusesRes, semanticTagsRes] = await Promise.all([
        fetch('/api/data/section-repo/distinct', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ mongo_uri: config.mongoUri, field: 'tag' }),
        }),
        fetch('/api/data/section-repo/distinct', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ mongo_uri: config.mongoUri, field: 'status' }),
        }),
        fetch('/api/data/section-repo/distinct', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ mongo_uri: config.mongoUri, field: 'semantic_tags' }),
        }),
      ])
      const tagsData = await tagsRes.json()
      const statusesData = await statusesRes.json()
      const semanticTagsData = await semanticTagsRes.json()
      if (tagsData.detail) throw new Error(tagsData.detail)
      if (statusesData.detail) throw new Error(statusesData.detail)
      if (semanticTagsData.detail) throw new Error(semanticTagsData.detail)
      setTags(tagsData.values || [])
      setStatuses(statusesData.values || [])
      setSemanticTags(semanticTagsData.values || [])
    } catch (err) {
      setError(err.message)
      setTags([])
      setStatuses([])
      setSemanticTags([])
    } finally {
      setLoadingDistinct(false)
    }
  }, [config.mongoUri])

  const loadCategories = useCallback(async () => {
    setLoadingCategories(true)
    setError(null)
    try {
      const response = await fetch('/api/data/section-repo/categories', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          mongo_uri: config.mongoUri,
          query_filter: queryFilter(),
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
  }, [config.mongoUri, queryFilter])

  const loadSections = useCallback(async () => {
    setLoadingSections(true)
    setError(null)
    try {
      const response = await fetch('/api/data/section-repo/sections', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          mongo_uri: config.mongoUri,
          query_filter: queryFilter(),
          l0_category: selectedL0 ? (selectedL0.original_l0 || selectedL0.name) : undefined,
          l1_category: selectedL1 || undefined,
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
  }, [config.mongoUri, queryFilter, selectedL0, selectedL1])

  useEffect(() => {
    loadDistinct()
  }, [loadDistinct])

  useEffect(() => {
    loadCategories()
  }, [loadCategories])

  useEffect(() => {
    loadSections()
  }, [loadSections])

  useEffect(() => {
    setSelectedL0(null)
    setSelectedL1(null)
  }, [selectedTag, selectedStatus, selectedSemanticTag])

  const l1Options = [...new Set(sections.map((s) => s.section_l1).filter(Boolean))].sort()

  const handleToggleStatus = async (section) => {
    const currentStatus = section.status || 'ACTIVE'
    const newStatus = currentStatus === 'ACTIVE' ? 'NOT-ACTIVE' : 'ACTIVE'
    const actionLabel = newStatus === 'ACTIVE' ? 'ACTIVE' : 'NOT-ACTIVE'
    if (!window.confirm(`Set section "${section.section_id}" to ${actionLabel}?`)) return
    try {
      const res = await fetch('/api/data/section-repo/sections/update-status', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          mongo_uri: config.mongoUri,
          section_id: section.section_id,
          status: newStatus,
        }),
      })
      const data = await res.json()
      if (data.detail) throw new Error(data.detail)
      toast.success(`Section set to ${actionLabel}`)
      loadSections()
      loadCategories()
    } catch (err) {
      toast.error(err.message || 'Failed to update section')
    }
  }

  return (
    <main className="main full-width">
      <div className="section-browser">
        <div className="section-browser-toolbar">
          <div className="section-browser-filters">
            <label className="section-browser-filter">
              <span>Tag</span>
              <select
                value={selectedTag}
                onChange={(e) => setSelectedTag(e.target.value)}
                disabled={loadingDistinct}
              >
                <option value="all">All</option>
                {tags.map((t) => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>
            </label>
            <label className="section-browser-filter">
              <span>Status</span>
              <select
                value={selectedStatus}
                onChange={(e) => setSelectedStatus(e.target.value)}
                disabled={loadingDistinct}
              >
                <option value="all">All</option>
                {statuses.map((s) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </label>
            <label className="section-browser-filter">
              <span>Semantic Tags</span>
              <select
                value={selectedSemanticTag}
                onChange={(e) => setSelectedSemanticTag(e.target.value)}
                disabled={loadingDistinct}
              >
                <option value="all">All</option>
                {semanticTags.map((t) => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>
            </label>
            <label className="section-browser-filter">
              <span>L0</span>
              <select
                value={selectedL0 ? selectedL0.l0_key : 'all'}
                onChange={(e) => {
                  const val = e.target.value
                  setSelectedL0(val === 'all' ? null : categories.find((c) => c.l0_key === val) || null)
                }}
                disabled={loadingCategories}
              >
                <option value="all">All</option>
                {categories.map((c) => (
                  <option key={c.l0_key} value={c.l0_key}>{c.name || c.l0_key}</option>
                ))}
              </select>
            </label>
            <label className="section-browser-filter">
              <span>L1</span>
              <select
                value={selectedL1 || 'all'}
                onChange={(e) => setSelectedL1(e.target.value === 'all' ? null : e.target.value)}
              >
                <option value="all">All</option>
                {l1Options.map((l1) => (
                  <option key={l1} value={l1}>{l1}</option>
                ))}
              </select>
            </label>
          </div>
          <span className="section-browser-count">
            {loadingSections ? '…' : `${sections.length} section${sections.length === 1 ? '' : 's'}`}
          </span>
          <button
            type="button"
            className="section-browser-refresh"
            onClick={() => loadSections()}
            disabled={loadingSections}
          >
            Refresh
          </button>
        </div>

        <div className="section-browser-content">
          {error && (
            <div className="section-repo-error">{error}</div>
          )}
          {loadingSections ? (
            <div className="section-repo-loading">Loading sections...</div>
          ) : sections.length === 0 ? (
            <div className="section-repo-empty">No sections found</div>
          ) : (
            <div className="section-repo-grid">
              {sections.map((section, idx) => {
                const displayName = section.section_l1
                  ? `${section.section_l0 || ''} - ${section.section_l1}`
                  : section.section_l0 || section.section_id
                const previewUrl = section.desktop_image_url
                const openDetailModal = () => {
                  setDetailModalIndex(idx)
                  setDetailModalOpen(true)
                }
                return (
                  <div key={section.section_id} className="section-card section-card-with-actions">
                    {previewUrl && (
                      <div
                        className="section-card-preview section-card-preview-clickable"
                        onClick={openDetailModal}
                        onKeyDown={(e) => e.key === 'Enter' && openDetailModal()}
                        role="button"
                        tabIndex={0}
                      >
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
                          onClick={() => onNavigateToCode(section.section_id)}
                        >
                          View Code
                        </button>
                        <button
                          type="button"
                          className="section-card-action section-card-action-secondary"
                          onClick={openDetailModal}
                        >
                          View Details
                        </button>
                        <button
                          type="button"
                          className="section-card-action section-card-action-secondary"
                          onClick={() => handleToggleStatus(section)}
                        >
                          {(section.status || 'ACTIVE') === 'ACTIVE' ? 'Set NOT-ACTIVE' : 'Set Active'}
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

      <SectionDetailModal
        open={detailModalOpen}
        onClose={() => setDetailModalOpen(false)}
        sections={sections}
        initialIndex={detailModalIndex}
        config={config}
        onNavigateToCode={onNavigateToCode}
      />
    </main>
  )
}

export default SectionBrowserView
