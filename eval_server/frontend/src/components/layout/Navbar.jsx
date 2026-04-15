import React, { useState, useRef, useEffect } from 'react'

const MODES = [
  { value: 'checkpoint', label: 'Checkpoint Mode' },
  { value: 'eval', label: 'Eval Mode' },
  { value: 'metrics', label: 'Metrics' },
  { value: 'data', label: 'Data Explorer' }
]

const EXTRA_OPTIONS = [
  { value: 'code', label: 'Code' },
  { value: 'section_browser', label: 'Section Browser' },
  { value: 'curated_page_builder', label: 'Curated Page Builder' }
]

function Navbar({ mode, onModeChange, onOpenSettings }) {
  const [dropdownOpen, setDropdownOpen] = useState(false)
  const dropdownRef = useRef(null)

  useEffect(() => {
    function handleClickOutside(e) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setDropdownOpen(false)
      }
    }
    if (dropdownOpen) document.addEventListener('click', handleClickOutside)
    return () => document.removeEventListener('click', handleClickOutside)
  }, [dropdownOpen])

  const isExtraMode = EXTRA_OPTIONS.some(o => o.value === mode)

  return (
    <nav className="navbar">
      <div className="navbar-brand">
        <span className="navbar-logo">⚡</span>
        <span className="navbar-title">WWAI Eval</span>
      </div>

      <div className="navbar-tabs">
        {MODES.map(({ value, label }) => (
          <button
            key={value}
            className={`navbar-tab ${mode === value ? 'active' : ''}`}
            onClick={() => onModeChange(value)}
          >
            {label}
          </button>
        ))}
        <div className="navbar-dropdown" ref={dropdownRef}>
          <button
            className={`navbar-dropdown-trigger ${dropdownOpen || isExtraMode ? 'active' : ''}`}
            onClick={() => setDropdownOpen(!dropdownOpen)}
            title="More options"
          >
            ⋮
          </button>
          {dropdownOpen && (
            <div className="navbar-dropdown-menu">
              {EXTRA_OPTIONS.map(({ value, label }) => (
                <button
                  key={value}
                  className={`navbar-dropdown-item ${mode === value ? 'active' : ''}`}
                  onClick={() => {
                    onModeChange(value)
                    setDropdownOpen(false)
                  }}
                >
                  {label}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      <button
        className="navbar-settings-btn"
        onClick={onOpenSettings}
        title="Settings"
      >
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="12" r="3" />
          <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
        </svg>
      </button>
    </nav>
  )
}

export default Navbar
