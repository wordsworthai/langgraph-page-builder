import React, { useState, useCallback, useEffect } from 'react'
import CodeEditor from './CodeEditor'
import Viewer from './Viewer'

const MIN_PANEL_WIDTH = 200
const DIVIDER_WIDTH = 6
const DEFAULT_LEFT_RATIO = 0.5

function TwoPanelLayout({ leftPanel, rightPanel, defaultLeftRatio = DEFAULT_LEFT_RATIO, initialSectionId }) {
  const [leftWidth, setLeftWidth] = useState(null)
  const [isResizing, setIsResizing] = useState(false)
  const containerRef = React.useRef(null)

  const effectiveLeftWidth =
    leftWidth ?? (typeof window !== 'undefined' ? window.innerWidth * defaultLeftRatio : 400)

  const handleMouseDown = useCallback((e) => {
    e.preventDefault()
    setIsResizing(true)
  }, [])

  useEffect(() => {
    if (!isResizing) return

    const handleMouseMove = (e) => {
      if (!containerRef.current) return
      const containerRect = containerRef.current.getBoundingClientRect()
      const newLeft = e.clientX - containerRect.left
      const clamped = Math.max(
        MIN_PANEL_WIDTH,
        Math.min(containerRect.width - DIVIDER_WIDTH - MIN_PANEL_WIDTH, newLeft)
      )
      setLeftWidth(clamped)
    }

    const handleMouseUp = () => {
      setIsResizing(false)
    }

    document.addEventListener('mousemove', handleMouseMove)
    document.addEventListener('mouseup', handleMouseUp)
    document.body.style.cursor = 'col-resize'
    document.body.style.userSelect = 'none'

    return () => {
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
    }
  }, [isResizing])

  const leftContent = leftPanel ?? <CodeEditor initialSectionId={initialSectionId} />
  const rightContent = rightPanel ?? <Viewer />

  return (
    <div
      ref={containerRef}
      className="two-panel-layout"
      style={{
        display: 'flex',
        flex: 1,
        minHeight: 0,
        overflow: 'hidden',
      }}
    >
      <div
        className="two-panel-left"
        style={{
          flex: `0 0 ${effectiveLeftWidth}px`,
          minWidth: MIN_PANEL_WIDTH,
          overflow: 'auto',
          background: 'var(--bg-secondary)',
          borderRight: `1px solid var(--border-color)`,
        }}
      >
        {leftContent}
      </div>
      <div
        role="separator"
        aria-orientation="vertical"
        className="two-panel-divider"
        onMouseDown={handleMouseDown}
        style={{
          width: DIVIDER_WIDTH,
          flexShrink: 0,
          cursor: 'col-resize',
          background: isResizing ? 'var(--accent-blue)' : 'var(--border-color)',
          opacity: isResizing ? 0.8 : 1,
        }}
      />
      <div
        className="two-panel-right"
        style={{
          flex: 1,
          minWidth: MIN_PANEL_WIDTH,
          overflow: 'auto',
          background: 'var(--bg-secondary)',
        }}
      >
        {rightContent}
      </div>
    </div>
  )
}

export default TwoPanelLayout
