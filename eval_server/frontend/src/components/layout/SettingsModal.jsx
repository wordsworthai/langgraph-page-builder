import React, { useEffect, useCallback } from 'react'

function SettingsModal({ open, config, onConfigChange, onClose }) {
  const handleKeyDown = useCallback((e) => {
    if (e.key === 'Escape') {
      onClose()
    }
  }, [onClose])

  useEffect(() => {
    if (open) {
      document.addEventListener('keydown', handleKeyDown)
      return () => document.removeEventListener('keydown', handleKeyDown)
    }
  }, [open, handleKeyDown])

  if (!open) return null

  return (
    <div
      className="modal active settings-modal"
      onClick={(e) => e.target.className.includes('modal') && onClose()}
    >
      <div className="modal-content">
        <div className="modal-header">
          <h3>Settings</h3>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>
        <div className="modal-body settings-modal-body">
          <div className="config-group">
            <label>MongoDB URI</label>
            <input
              type="text"
              value={config?.mongoUri ?? ''}
              onChange={(e) => onConfigChange(prev => ({ ...prev, mongoUri: e.target.value }))}
              placeholder="mongodb://localhost:27020"
            />
          </div>
          <div className="config-group">
            <label>Database Name</label>
            <input
              type="text"
              value={config?.dbName ?? ''}
              onChange={(e) => onConfigChange(prev => ({ ...prev, dbName: e.target.value }))}
              placeholder="checkpointing_db"
            />
          </div>
        </div>
      </div>
    </div>
  )
}

export default SettingsModal
