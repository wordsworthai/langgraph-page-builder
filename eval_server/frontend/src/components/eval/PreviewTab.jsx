import React, { useState, useRef, useEffect, useCallback } from 'react'
import { DEVICE_PRESETS } from './constants'

function PreviewTab({ output, previewDevice, onDeviceChange }) {
  const previewContainerRef = useRef(null)
  const [previewScale, setPreviewScale] = useState(1)

  const calculatePreviewScale = useCallback(() => {
    if (!previewContainerRef.current) return
    
    const container = previewContainerRef.current
    const containerWidth = container.clientWidth - 48
    const containerHeight = container.clientHeight - 100
    
    const device = DEVICE_PRESETS[previewDevice]
    const scaleX = containerWidth / device.width
    const scaleY = containerHeight / device.height
    const scale = Math.min(scaleX, scaleY, 1)
    
    setPreviewScale(scale)
  }, [previewDevice])

  useEffect(() => {
    calculatePreviewScale()
    window.addEventListener('resize', calculatePreviewScale)
    return () => window.removeEventListener('resize', calculatePreviewScale)
  }, [calculatePreviewScale])

  useEffect(() => {
    setTimeout(calculatePreviewScale, 100)
  }, [calculatePreviewScale])

  const device = DEVICE_PRESETS[previewDevice]
  const scaledWidth = device.width * previewScale
  const scaledHeight = device.height * previewScale
  const previewUrl = output?.s3_url ?? output?.html_url

  return (
    <div className="eval-preview-fullscreen" ref={previewContainerRef}>
      {previewUrl ? (
        <>
          <div className="preview-toolbar">
            <div className="preview-toolbar-left">
              <div className="device-switcher">
                {Object.entries(DEVICE_PRESETS).map(([key, preset]) => (
                  <button
                    key={key}
                    className={`device-btn ${previewDevice === key ? 'active' : ''}`}
                    onClick={() => onDeviceChange(key)}
                  >
                    {preset.label}
                  </button>
                ))}
              </div>
              <span className="preview-dimensions">
                {device.width} × {device.height} @ {Math.round(previewScale * 100)}%
              </span>
            </div>
            <a href={previewUrl} target="_blank" rel="noopener noreferrer">
              Open in new tab ↗
            </a>
          </div>
          <div className="preview-viewport">
            <div
              className={`preview-device-frame ${previewDevice}`}
              style={{ width: scaledWidth, height: scaledHeight }}
            >
              <iframe
                src={previewUrl}
                title="Generated HTML Preview"
                sandbox="allow-scripts allow-same-origin"
                style={{
                  width: device.width,
                  height: device.height,
                  transform: `scale(${previewScale})`,
                  transformOrigin: 'top left'
                }}
              />
            </div>
          </div>
        </>
      ) : (
        <div className="no-preview">
          <div className="icon">🚫</div>
          <p>No HTML output available to preview</p>
        </div>
      )}
    </div>
  )
}

export default PreviewTab
