import React from 'react'
import BusinessNameCard from './components/BusinessNameCard'
import QueryCard from './components/QueryCard'
import IntentionCard from './components/IntentionCard'
import ToneCard from './components/ToneCard'
import PaletteCard from './components/PaletteCard'
import FontCard from './components/FontCard'
import BusinessProfileCard from './components/BusinessProfileCard'
import FullInputJSON from './components/FullInputJSON'

function SectionCoverageInput({ summary, businessId, fullInput, config }) {
  const presetInput = fullInput?.preset_sections_input || fullInput
  const sectionIds = presetInput?.section_ids || []
  const wc = presetInput?.website_context || {}
  const bc = presetInput?.brand_context || {}

  const effectiveSummary = {
    ...summary,
    website_intention: summary.website_intention ?? wc.website_intention,
    website_tone: summary.website_tone ?? wc.website_tone,
    palette: summary.palette ?? bc.palette,
    font_family: summary.font_family ?? bc.font_family,
  }

  return (
    <div className="eval-section input-section">
      <h3>📥 Input</h3>
      <div className="input-cards">
        {sectionIds.length > 0 && (
          <div className="input-card full-width">
            <label>Section IDs</label>
            <span>{sectionIds.join(', ')}</span>
          </div>
        )}
        <BusinessNameCard businessName={effectiveSummary.business_name || presetInput?.business_name} />
        <QueryCard query={effectiveSummary.query || presetInput?.generic_context?.query} />
        {businessId && <BusinessProfileCard businessId={businessId} config={config} />}
        <IntentionCard intention={effectiveSummary.website_intention} />
        <ToneCard tone={effectiveSummary.website_tone} />
        <PaletteCard palette={effectiveSummary.palette} />
        <FontCard fontFamily={effectiveSummary.font_family} />
      </div>
      <FullInputJSON fullInput={fullInput} />
    </div>
  )
}

export default SectionCoverageInput
