import React from 'react'

function PaletteCard({ palette }) {
  if (!palette) return null

  return (
    <div className="input-card">
      <label>Palette</label>
      <div className="color-swatches">
        {Object.entries(palette).map(([key, value]) =>
          typeof value === 'string' && value.startsWith('#') && (
            <div key={key} className="swatch" title={`${key}: ${value}`}>
              <div className="swatch-color" style={{ backgroundColor: value }} />
              <span>{key}</span>
            </div>
          )
        )}
      </div>
    </div>
  )
}

export default PaletteCard
