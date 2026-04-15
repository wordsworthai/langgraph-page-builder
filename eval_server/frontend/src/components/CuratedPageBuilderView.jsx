import React, { useState, useEffect, useCallback } from 'react'
import { Monitor, Smartphone, ChevronUp, ChevronDown } from 'lucide-react'
import { toast } from 'react-toastify'
import SectionPickerModal from './SectionPickerModal'
import StreamedPreview from '../../html_preview/StreamedPreview'

function CuratedPageBuilderView({ config }) {
  const [curatedPages, setCuratedPages] = useState([])
  const [selectedPage, setSelectedPage] = useState(null)
  const [sectionIds, setSectionIds] = useState([])
  const [compiledHtml, setCompiledHtml] = useState('')
  const [loadingCompile, setLoadingCompile] = useState(false)
  const [loadingPages, setLoadingPages] = useState(true)
  const [loadingSave, setLoadingSave] = useState(false)
  const [sectionPickerOpen, setSectionPickerOpen] = useState(false)
  const [previewViewMode, setPreviewViewMode] = useState('desktop')
  const [newPagePath, setNewPagePath] = useState('')
  const [newPageTitle, setNewPageTitle] = useState('')
  const [newPageDescription, setNewPageDescription] = useState('')
  const [editedPageTitle, setEditedPageTitle] = useState('')
  const [editedPageDescription, setEditedPageDescription] = useState('')

  const loadCuratedPages = useCallback(async () => {
    setLoadingPages(true)
    try {
      const res = await fetch('/api/curated-pages')
      const data = await res.json()
      if (data.detail) throw new Error(data.detail)
      setCuratedPages(data.pages || [])
    } catch (err) {
      toast.error(err.message || 'Failed to load curated pages')
      setCuratedPages([])
    } finally {
      setLoadingPages(false)
    }
  }, [])

  useEffect(() => {
    loadCuratedPages()
  }, [loadCuratedPages])

  useEffect(() => {
    if (selectedPage) {
      setSectionIds(selectedPage.section_ids || [])
      setEditedPageTitle(selectedPage.page_title || '')
      setEditedPageDescription(selectedPage.page_description || '')
    } else {
      setSectionIds([])
    }
    setCompiledHtml('')
  }, [selectedPage])

  const handlePageSelect = (e) => {
    const value = e.target.value
    if (value === '__new__') {
      setSelectedPage(null)
    } else {
      const page = curatedPages.find((p) => p.page_path === value)
      setSelectedPage(page || null)
    }
  }

  const handleNewPage = () => {
    setSelectedPage(null)
    setSectionIds([])
    setCompiledHtml('')
    setNewPagePath('')
    setNewPageTitle('')
    setNewPageDescription('')
  }

  const handleSave = useCallback(async () => {
    const pagePath = selectedPage ? selectedPage.page_path : newPagePath.trim()
    const pageTitle = selectedPage ? editedPageTitle.trim() : newPageTitle.trim()
    const pageDescription = selectedPage
      ? editedPageDescription.trim()
      : newPageDescription.trim()

    if (!pagePath) {
      toast.error('Page path is required')
      return
    }

    setLoadingSave(true)
    try {
      const res = await fetch('/api/curated-pages/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          page_path: pagePath,
          page_title: pageTitle || pagePath,
          page_description: pageDescription || null,
          section_ids: sectionIds,
        }),
      })
      const data = await res.json()
      if (data.detail) throw new Error(data.detail)
      toast.success('Page saved successfully')
      await loadCuratedPages()
      if (!selectedPage) {
        setSelectedPage({
          page_path: pagePath,
          page_title: pageTitle || pagePath,
          page_description: pageDescription || null,
          section_ids: sectionIds,
        })
        setNewPagePath('')
        setNewPageTitle('')
        setNewPageDescription('')
      } else {
        setSelectedPage({
          ...selectedPage,
          page_title: pageTitle || pagePath,
          page_description: pageDescription || null,
          section_ids: sectionIds,
        })
      }
    } catch (err) {
      toast.error(err.message || 'Failed to save')
    } finally {
      setLoadingSave(false)
    }
  }, [selectedPage, newPagePath, newPageTitle, newPageDescription, editedPageTitle, editedPageDescription, sectionIds, loadCuratedPages])

  const handleMoveSection = (fromIndex, direction) => {
    const toIndex = direction === 'up' ? fromIndex - 1 : fromIndex + 1
    if (toIndex < 0 || toIndex >= sectionIds.length) return
    setSectionIds((prev) => {
      const next = [...prev]
      ;[next[fromIndex], next[toIndex]] = [next[toIndex], next[fromIndex]]
      return next
    })
  }

  const handleAddSection = (sectionId) => {
    setSectionIds((prev) => [...prev, sectionId])
    setSectionPickerOpen(false)
  }

  const handleDeleteSection = (index) => {
    setSectionIds((prev) => prev.filter((_, i) => i !== index))
  }

  const handleCompile = useCallback(async () => {
    setLoadingCompile(true)
    setCompiledHtml('')
    try {
      const res = await fetch('/api/sections/compile-batch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ section_ids: sectionIds }),
      })
      const data = await res.json()
      if (data.detail) throw new Error(data.detail)
      setCompiledHtml(data.compiled_html || '')
      toast.success('Compiled successfully')
    } catch (err) {
      toast.error(err.message || 'Compilation failed')
    } finally {
      setLoadingCompile(false)
    }
  }, [sectionIds])

  return (
    <main className="main full-width curated-page-builder">
      <div className="curated-page-builder-split">
        <div className="curated-page-builder-left">
          <div className="curated-page-builder-header">
            <div className="curated-page-builder-page-select">
              <label>
                <span>Page</span>
                <select
                  value={selectedPage ? selectedPage.page_path : '__new__'}
                  onChange={handlePageSelect}
                  disabled={loadingPages}
                >
                  <option value="__new__">New Page</option>
                  {curatedPages.map((p) => (
                    <option key={p.page_path} value={p.page_path}>
                      {p.page_title || p.page_path}
                    </option>
                  ))}
                </select>
              </label>
              <button
                type="button"
                className="curated-page-builder-btn curated-page-builder-btn-secondary"
                onClick={handleNewPage}
              >
                New Page
              </button>
            </div>
            {selectedPage ? (
              <div className="curated-page-builder-new-page-fields">
                <label className="curated-page-builder-field">
                  <span>Page path</span>
                  <input
                    type="text"
                    value={selectedPage.page_path || ''}
                    readOnly
                    className="curated-page-builder-input-readonly"
                  />
                </label>
                <label className="curated-page-builder-field">
                  <span>Page title</span>
                  <input
                    type="text"
                    value={editedPageTitle}
                    onChange={(e) => setEditedPageTitle(e.target.value)}
                    placeholder="Page title"
                  />
                </label>
                <label className="curated-page-builder-field">
                  <span>Page description</span>
                  <input
                    type="text"
                    value={editedPageDescription}
                    onChange={(e) => setEditedPageDescription(e.target.value)}
                    placeholder="Optional description"
                  />
                </label>
              </div>
            ) : (
              <div className="curated-page-builder-new-page-fields">
                <label className="curated-page-builder-field">
                  <span>Page path</span>
                  <input
                    type="text"
                    value={newPagePath}
                    onChange={(e) => setNewPagePath(e.target.value)}
                    placeholder="/about"
                  />
                </label>
                <label className="curated-page-builder-field">
                  <span>Page title</span>
                  <input
                    type="text"
                    value={newPageTitle}
                    onChange={(e) => setNewPageTitle(e.target.value)}
                    placeholder="About Us"
                  />
                </label>
                <label className="curated-page-builder-field">
                  <span>Page description</span>
                  <input
                    type="text"
                    value={newPageDescription}
                    onChange={(e) => setNewPageDescription(e.target.value)}
                    placeholder="Optional description"
                  />
                </label>
              </div>
            )}
          </div>

          <div className="curated-page-builder-actions">
            <button
              type="button"
              className="curated-page-builder-btn curated-page-builder-btn-primary"
              onClick={() => setSectionPickerOpen(true)}
            >
              Add Section
            </button>
            <button
              type="button"
              className="curated-page-builder-btn curated-page-builder-btn-primary"
              onClick={handleCompile}
              disabled={loadingCompile || sectionIds.length === 0}
            >
              {loadingCompile ? 'Compiling…' : 'Compile'}
            </button>
            <button
              type="button"
              className="curated-page-builder-btn curated-page-builder-btn-secondary"
              onClick={handleSave}
              disabled={
                loadingSave ||
                (selectedPage ? false : !newPagePath.trim())
              }
            >
              {loadingSave ? 'Saving…' : 'Save'}
            </button>
          </div>

          <div className="curated-page-builder-section-list">
            <h4 className="curated-page-builder-section-list-title">
              Sections ({sectionIds.length})
            </h4>
            {sectionIds.length === 0 ? (
              <div className="curated-page-builder-empty">
                No sections. Click &quot;Add Section&quot; to add from the browser.
              </div>
            ) : (
              <div className="curated-page-builder-section-cards">
                {sectionIds.map((sid, idx) => (
                  <div key={`${sid}-${idx}`} className="curated-page-builder-section-card">
                    <div className="curated-page-builder-section-card-move">
                      <button
                        type="button"
                        className="curated-page-builder-move-btn"
                        onClick={() => handleMoveSection(idx, 'up')}
                        disabled={idx === 0}
                        title="Move up"
                      >
                        <ChevronUp size={14} />
                      </button>
                      <button
                        type="button"
                        className="curated-page-builder-move-btn"
                        onClick={() => handleMoveSection(idx, 'down')}
                        disabled={idx === sectionIds.length - 1}
                        title="Move down"
                      >
                        <ChevronDown size={14} />
                      </button>
                    </div>
                    <span className="curated-page-builder-section-id">{sid}</span>
                    <button
                      type="button"
                      className="curated-page-builder-delete-btn"
                      onClick={() => handleDeleteSection(idx)}
                      title="Remove section"
                    >
                      ×
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="curated-page-builder-right">
          <div className="curated-page-builder-preview-header">
            <h4>HTML Preview</h4>
            {compiledHtml && (
              <div className="curated-page-builder-device-toggle">
                <button
                  type="button"
                  className={`curated-page-builder-device-btn ${previewViewMode === 'desktop' ? 'active' : ''}`}
                  onClick={() => setPreviewViewMode('desktop')}
                  aria-pressed={previewViewMode === 'desktop'}
                >
                  <Monitor size={16} />
                  Desktop
                </button>
                <button
                  type="button"
                  className={`curated-page-builder-device-btn ${previewViewMode === 'mobile' ? 'active' : ''}`}
                  onClick={() => setPreviewViewMode('mobile')}
                  aria-pressed={previewViewMode === 'mobile'}
                >
                  <Smartphone size={16} />
                  Mobile
                </button>
              </div>
            )}
          </div>
          <div className="curated-page-builder-preview">
            {compiledHtml ? (
              <StreamedPreview
                viewMode={previewViewMode}
                isSidebarCollapsed={false}
                customHtml={compiledHtml}
              />
            ) : (
              <div className="curated-page-builder-preview-placeholder">
                Click &quot;Compile&quot; to generate the HTML preview.
              </div>
            )}
          </div>
        </div>
      </div>

      <SectionPickerModal
        open={sectionPickerOpen}
        onClose={() => setSectionPickerOpen(false)}
        onAddSection={handleAddSection}
        config={config}
      />
    </main>
  )
}

export default CuratedPageBuilderView
