import React, { useState, useEffect, useRef, useCallback } from 'react'
import CodeEditorMain from './monaco/CodeEditorMain'
import { sectionMappingToSectionData, sectionDataToSectionMapping } from './utils/sectionDataMapper'
import { usePreviewContext } from './PreviewContext'

function CodeEditor({ initialSectionId }) {
  const [sectionId, setSectionId] = useState(initialSectionId || '')
  const [loadSource, setLoadSource] = useState('auto') // 'auto' | 'original' | 'staging' - auto prefers staging if exists
  const [loadedSectionId, setLoadedSectionId] = useState('')
  const [sectionDataByVariant, setSectionDataByVariant] = useState({}) // { original?, staging?, boilerplate? }
  const [activeVariant, setActiveVariant] = useState(null) // 'original' | 'staging' | 'boilerplate'
  const [stagingExists, setStagingExists] = useState(false) // true when we loaded from staging
  const [loading, setLoading] = useState(false)
  const [switchingLoading, setSwitchingLoading] = useState(false)
  const [error, setError] = useState(null)
  const initialLoadDone = useRef(false)
  const { setCompiledHtml } = usePreviewContext() || {}

  const sectionData = activeVariant && sectionDataByVariant[activeVariant] ? sectionDataByVariant[activeVariant] : null

  useEffect(() => {
    if (initialSectionId?.trim() && !initialLoadDone.current) {
      initialLoadDone.current = true
      setSectionId(initialSectionId)
      handleLoad(initialSectionId, 'auto')
    }
  }, [initialSectionId])

  const fetchVariant = useCallback(async (id, variant) => {
    if (variant === 'original') {
      const res = await fetch('/api/sections/template', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ section_id: id }),
      })
      if (!res.ok) {
        const errBody = await res.json().catch(() => ({}))
        throw new Error(errBody.detail || `Request failed: ${res.status}`)
      }
      return sectionMappingToSectionData(await res.json())
    }
    if (variant === 'staging') {
      const res = await fetch('/api/sections/staging/get', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ section_id: id }),
      })
      if (!res.ok) {
        const errBody = await res.json().catch(() => ({}))
        throw new Error(errBody.detail || `Request failed: ${res.status}`)
      }
      return sectionMappingToSectionData(await res.json())
    }
    if (variant === 'boilerplate') {
      const res = await fetch('/api/sections/boilerplate/get', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ section_id: id }),
      })
      if (!res.ok) {
        const errBody = await res.json().catch(() => ({}))
        throw new Error(errBody.detail || `Request failed: ${res.status}`)
      }
      return sectionMappingToSectionData(await res.json())
    }
    throw new Error(`Unknown variant: ${variant}`)
  }, [])

  const handleLoad = async (idOverride, sourceOverride) => {
    const id = (idOverride ?? sectionId).trim()
    const source = sourceOverride ?? loadSource
    if (!id) {
      setError('Please enter a section ID')
      return
    }
    setError(null)
    setLoading(true)
    try {
      let sectionMapping
      let from

      if (source === 'auto') {
        const stagingRes = await fetch('/api/sections/staging/get', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ section_id: id }),
        })
        if (stagingRes.ok) {
          sectionMapping = await stagingRes.json()
          from = 'staging'
          setStagingExists(true)
        } else {
          const templateRes = await fetch('/api/sections/template', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ section_id: id }),
          })
          if (!templateRes.ok) {
            const errBody = await templateRes.json().catch(() => ({}))
            throw new Error(errBody.detail || `Request failed: ${templateRes.status}`)
          }
          sectionMapping = await templateRes.json()
          from = 'original'
          setStagingExists(false)
        }
      } else if (source === 'staging') {
        const res = await fetch('/api/sections/staging/get', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ section_id: id }),
        })
        if (!res.ok) {
          const errBody = await res.json().catch(() => ({}))
          throw new Error(errBody.detail || `Request failed: ${res.status}`)
        }
        sectionMapping = await res.json()
        from = 'staging'
        setStagingExists(true)
      } else {
        const res = await fetch('/api/sections/template', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ section_id: id }),
        })
        if (!res.ok) {
          const errBody = await res.json().catch(() => ({}))
          throw new Error(errBody.detail || `Request failed: ${res.status}`)
        }
        sectionMapping = await res.json()
        from = 'original'
        setStagingExists(false)
      }

      const data = sectionMappingToSectionData(sectionMapping)
      setSectionDataByVariant((prev) => ({ ...prev, [from]: data }))
      setActiveVariant(from)
      setLoadedSectionId(id)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load section')
      setSectionDataByVariant({})
      setActiveVariant(null)
      setLoadedSectionId('')
    } finally {
      setLoading(false)
    }
  }

  const handleSwitchVariant = useCallback(
    async (variant) => {
      if (!loadedSectionId || variant === activeVariant) return
      if (sectionDataByVariant[variant]) {
        setActiveVariant(variant)
        return
      }
      setSwitchingLoading(true)
      setError(null)
      try {
        const data = await fetchVariant(loadedSectionId, variant)
        setSectionDataByVariant((prev) => ({ ...prev, [variant]: data }))
        setActiveVariant(variant)
        if (variant === 'staging') setStagingExists(true)
      } catch (e) {
        setError(e instanceof Error ? e.message : `Failed to load ${variant}`)
      } finally {
        setSwitchingLoading(false)
      }
    },
    [loadedSectionId, activeVariant, sectionDataByVariant, fetchVariant]
  )

  const handleClear = () => {
    setSectionDataByVariant({})
    setActiveVariant(null)
    setError(null)
    setLoadedSectionId('')
  }

  const handleSave = useCallback(async (updatedSectionData) => {
    if (!loadedSectionId) return
    const sectionMapping = sectionDataToSectionMapping(updatedSectionData)
    const res = await fetch('/api/sections/staging/save', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ section_id: loadedSectionId, section_mapping: sectionMapping }),
    })
    if (!res.ok) {
      const errBody = await res.json().catch(() => ({}))
      throw new Error(errBody.detail || `Save failed: ${res.status}`)
    }
    setSectionDataByVariant((prev) => ({ ...prev, staging: updatedSectionData }))
    setStagingExists(true)
  }, [loadedSectionId])

  const handleDiscardDraft = useCallback(async () => {
    if (!loadedSectionId) return
    if (!window.confirm('Discard draft and reload from original? This cannot be undone.')) return
    try {
      const res = await fetch('/api/sections/staging/delete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ section_id: loadedSectionId }),
      })
      if (!res.ok) {
        const errBody = await res.json().catch(() => ({}))
        throw new Error(errBody.detail || `Delete failed: ${res.status}`)
      }
      await handleLoad(loadedSectionId, 'original')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to discard draft')
    }
  }, [loadedSectionId])

  const handlePromoteToMainSuccess = useCallback(() => {
    setSectionDataByVariant((prev) => {
      const next = { ...prev }
      delete next.staging
      return next
    })
    setStagingExists(false)
    if (activeVariant === 'staging') {
      setActiveVariant('original')
      fetchVariant(loadedSectionId, 'original').then((data) => {
        setSectionDataByVariant((prev) => ({ ...prev, original: data }))
      })
    }
  }, [activeVariant, loadedSectionId, fetchVariant])

  if (sectionData) {
    return (
      <div style={{ height: '100%', display: 'flex', flexDirection: 'column', minHeight: 0 }}>
        <CodeEditorMain
          sectionData={sectionData}
          sectionId={loadedSectionId}
          activeVariant={activeVariant}
          stagingExists={stagingExists}
          onSwitchVariant={handleSwitchVariant}
          switchingLoading={switchingLoading}
          onClear={handleClear}
          setCompiledHtml={setCompiledHtml}
          onSave={handleSave}
          onDiscardDraft={activeVariant === 'staging' ? handleDiscardDraft : undefined}
          onPromoteToMainSuccess={handlePromoteToMainSuccess}
        />
      </div>
    )
  }

  return (
    <div
      style={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        padding: 16,
      }}
    >
      <div
        style={{
          fontSize: 12,
          fontWeight: 600,
          color: 'var(--text-secondary)',
          textTransform: 'uppercase',
          letterSpacing: '0.05em',
          marginBottom: 12,
        }}
      >
        Code Editor
      </div>
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          gap: 12,
          maxWidth: 400,
        }}
      >
        <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, color: 'var(--text-secondary)' }}>
            <span>Load from:</span>
            <select
              value={loadSource}
              onChange={(e) => setLoadSource(e.target.value)}
              disabled={loading}
              style={{
                padding: '4px 8px',
                fontSize: 13,
                background: 'var(--bg-tertiary)',
                border: '1px solid var(--border-color)',
                borderRadius: 4,
                color: 'var(--text-primary)',
              }}
            >
              <option value="auto">Auto (prefer staging)</option>
              <option value="original">Original</option>
              <option value="staging">Staging</option>
            </select>
          </label>
          <input
            type="text"
            placeholder="Enter section ID"
            value={sectionId}
            onChange={(e) => setSectionId(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleLoad()}
            disabled={loading}
            style={{
              flex: 1,
              padding: '8px 12px',
              fontSize: 14,
              background: 'var(--bg-tertiary)',
              border: '1px solid var(--border-color)',
              borderRadius: 4,
              color: 'var(--text-primary)',
            }}
          />
          <button
            type="button"
            onClick={() => handleLoad()}
            disabled={loading}
            style={{
              padding: '8px 16px',
              fontSize: 14,
              fontWeight: 600,
              cursor: loading ? 'not-allowed' : 'pointer',
              background: 'var(--accent-blue)',
              border: 'none',
              borderRadius: 4,
              color: 'white',
            }}
          >
            {loading ? 'Loading…' : 'Load'}
          </button>
        </div>
        {error && (
          <div
            style={{
              padding: 8,
              fontSize: 13,
              color: 'var(--text-error, #f85149)',
              background: 'var(--bg-error, rgba(248, 81, 73, 0.15))',
              borderRadius: 4,
            }}
          >
            {error}
          </div>
        )}
        <p style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
          Enter a section ID from the developer hub to load and edit its section code in the Monaco editor.
        </p>
      </div>
    </div>
  )
}

export default CodeEditor
