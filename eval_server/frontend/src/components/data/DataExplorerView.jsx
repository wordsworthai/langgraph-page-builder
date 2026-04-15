import React, { useEffect, useMemo, useState } from 'react'
import DataDebugRunner from './DataDebugRunner'

function DataDebugTabList({ targets, activeTab, onTabChange, collapsed, onToggleCollapsed }) {
  const byCategory = useMemo(() => {
    return targets.reduce((acc, target) => {
      const key = target.category || 'Other'
      if (!acc[key]) acc[key] = []
      acc[key].push(target)
      return acc
    }, {})
  }, [targets])

  return (
    <div className={`data-debug-tab-list ${collapsed ? 'collapsed' : ''}`}>
      <div className="data-debug-tab-toolbar">
        <button
          className="panel-collapse-btn"
          onClick={onToggleCollapsed}
          title={collapsed ? 'Expand catalog' : 'Collapse catalog'}
        >
          {collapsed ? '»' : '«'}
        </button>
      </div>
      {collapsed ? null : (
        <>
      {Object.entries(byCategory).map(([category, entries]) => (
        <div key={category} className="data-debug-tab-group">
          <div className="data-debug-tab-category">{category}</div>
          {entries.map((target) => (
            <button
              key={target.target}
              className={`data-debug-tab-item ${activeTab === target.target ? 'active' : ''}`}
              onClick={() => onTabChange(target.target)}
            >
              {target.label}
              {target.external_call ? ' *' : ''}
            </button>
          ))}
        </div>
      ))}
        </>
      )}
    </div>
  )
}

function DataExplorerView({ config, activeTab, onTabChange }) {
  const [catalog, setCatalog] = useState([])
  const [allowExternal, setAllowExternal] = useState(false)
  const [catalogError, setCatalogError] = useState(null)
  const [isCatalogCollapsed, setIsCatalogCollapsed] = useState(false)

  useEffect(() => {
    let cancelled = false

    const loadCatalog = async () => {
      try {
        const response = await fetch('/api/data/debug/catalog')
        const payload = await response.json()
        if (!response.ok) {
          throw new Error(payload?.detail || `Failed to load catalog (${response.status})`)
        }
        if (!cancelled && Array.isArray(payload.targets) && payload.targets.length > 0) {
          setCatalog(payload.targets)
          setCatalogError(null)
        } else if (!cancelled) {
          setCatalog([])
          setCatalogError('Catalog is empty')
        }
      } catch (err) {
        if (!cancelled) {
          setCatalogError(err.message)
          setCatalog([])
        }
      }
    }

    loadCatalog()
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    if (!catalog.length) return
    const selectedExists = catalog.some((target) => target.target === activeTab)
    if (!selectedExists) {
      onTabChange(catalog[0].target)
    }
  }, [catalog, activeTab, onTabChange])

  const selectedTarget = useMemo(
    () => catalog.find((target) => target.target === activeTab) || catalog[0],
    [catalog, activeTab]
  )

  return (
    <div className="data-explorer">
      <div className="data-explorer-header">
        <h2>Data Explorer</h2>
        {catalogError && <div className="data-debug-catalog-error">Catalog fallback: {catalogError}</div>}
      </div>
      <div className="data-explorer-content">
        {catalog.length === 0 ? (
          <div className="data-debug-main">
            <div className="data-debug-empty">
              No debug targets available. Ensure backend catalog endpoint is reachable.
            </div>
          </div>
        ) : (
          <div className={`data-debug-layout ${isCatalogCollapsed ? 'catalog-collapsed' : ''}`}>
            <DataDebugTabList
              targets={catalog}
              activeTab={activeTab}
              onTabChange={onTabChange}
              collapsed={isCatalogCollapsed}
              onToggleCollapsed={() => setIsCatalogCollapsed((prev) => !prev)}
            />
            <div className="data-debug-main">
              {selectedTarget && (
                <DataDebugRunner
                  target={selectedTarget}
                  allowExternal={allowExternal}
                  onAllowExternalChange={setAllowExternal}
                  config={config}
                />
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default DataExplorerView
