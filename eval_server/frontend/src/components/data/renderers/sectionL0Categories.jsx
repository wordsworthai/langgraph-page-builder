import React, { useState } from 'react'

function normalizeL0Categories(result) {
  if (!result || !result.success) return []
  if (Array.isArray(result.result)) return result.result
  return []
}

async function copyToClipboard(text) {
  try {
    await navigator.clipboard.writeText(text)
    return true
  } catch {
    return false
  }
}

function SectionL0CategoriesResult({ result }) {
  const [copiedKey, setCopiedKey] = useState(null)
  const categories = normalizeL0Categories(result)

  const handleCopy = async (item, field) => {
    const text = field === 'name' ? (item.name || item.original_l0) : (item.l0_key || item.name)
    const ok = await copyToClipboard(text)
    if (ok) {
      setCopiedKey(`${item.l0_key || item.name}-${field}`)
      setTimeout(() => setCopiedKey(null), 1500)
    }
  }

  if (!categories.length) {
    return <div className="data-debug-empty">No L0 categories returned.</div>
  }

  return (
    <div className="section-l0-categories">
      <p className="section-l0-categories-hint">
        Copy name or l0_key to use as <code>l0_category</code> filter in Section Catalog (By L0).
      </p>
      <div className="section-l0-categories-grid">
        {categories.map((item, idx) => {
          const name = item.name || item.original_l0 || item.l0_key
          const key = item.l0_key || item.name
          const count = item.count ?? '-'
          const id = item.l0_key || key || String(idx)
          const nameCopied = copiedKey === `${id}-name`
          const keyCopied = copiedKey === `${id}-key`
          return (
            <div key={key} className="section-l0-category-card">
              <div className="section-l0-category-header">
                <span className="section-l0-category-name">{name}</span>
                <span className="section-l0-category-count">{count} sections</span>
              </div>
              <div className="section-l0-category-meta">
                <code className="section-l0-category-key">{key}</code>
              </div>
              <div className="section-l0-category-actions">
                <button
                  type="button"
                  className="section-l0-copy-btn"
                  onClick={() => handleCopy(item, 'name')}
                  title="Copy name for l0_category filter"
                >
                  {nameCopied ? 'Copied!' : 'Copy name'}
                </button>
                {key !== name && (
                  <button
                    type="button"
                    className="section-l0-copy-btn"
                    onClick={() => handleCopy(item, 'key')}
                    title="Copy l0_key for l0_category filter"
                  >
                    {keyCopied ? 'Copied!' : 'Copy l0_key'}
                  </button>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

export default SectionL0CategoriesResult
