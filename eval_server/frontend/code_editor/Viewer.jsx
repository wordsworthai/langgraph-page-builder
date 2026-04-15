import React, { useState } from 'react'
import { Monitor, Smartphone } from 'lucide-react'
import StreamedPreview from '../html_preview/StreamedPreview'

function Viewer({ isSidebarCollapsed = false, customHtml }) {
  const [viewMode, setViewMode] = useState('desktop')

  return (
    <div
      style={{
        height: '100%',
        minHeight: 0,
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
      }}
    >
      <div
        style={{
          flexShrink: 0,
          display: 'flex',
          alignItems: 'center',
          gap: 4,
          padding: '8px 12px',
          borderBottom: '1px solid var(--border-color)',
          background: 'var(--bg-secondary)',
        }}
      >
        <button
          type="button"
          onClick={() => setViewMode('desktop')}
          aria-pressed={viewMode === 'desktop'}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            padding: '6px 12px',
            borderRadius: 6,
            border: '1px solid var(--border-color)',
            background: viewMode === 'desktop' ? 'var(--accent-blue)' : 'transparent',
            color: viewMode === 'desktop' ? 'white' : 'var(--text-secondary)',
            cursor: 'pointer',
            fontSize: 13,
          }}
        >
          <Monitor size={16} />
          Desktop
        </button>
        <button
          type="button"
          onClick={() => setViewMode('mobile')}
          aria-pressed={viewMode === 'mobile'}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            padding: '6px 12px',
            borderRadius: 6,
            border: '1px solid var(--border-color)',
            background: viewMode === 'mobile' ? 'var(--accent-blue)' : 'transparent',
            color: viewMode === 'mobile' ? 'white' : 'var(--text-secondary)',
            cursor: 'pointer',
            fontSize: 13,
          }}
        >
          <Smartphone size={16} />
          Mobile
        </button>
      </div>
      <div style={{ flex: 1, minHeight: 0, overflow: 'hidden' }}>
        <StreamedPreview
          viewMode={viewMode}
          isSidebarCollapsed={isSidebarCollapsed}
          customHtml={customHtml}
        />
      </div>
    </div>
  )
}

export default Viewer
