import React, { useEffect, useCallback } from 'react'

function safeStringify(value, indent = null) {
  try {
    return JSON.stringify(value, null, indent)
  } catch (e) {
    return String(value)
  }
}

function Modal({ open, title, content, onClose }) {
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
    <div className="modal active" onClick={(e) => e.target.className.includes('modal') && onClose()}>
      <div className="modal-content">
        <div className="modal-header">
          <h3>{title}</h3>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>
        <div className="modal-body">
          <pre>{safeStringify(content, 2)}</pre>
        </div>
      </div>
    </div>
  )
}

export default Modal
