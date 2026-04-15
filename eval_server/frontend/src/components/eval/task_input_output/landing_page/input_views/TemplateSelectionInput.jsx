import React from 'react'
import BusinessNameCard from './components/BusinessNameCard'
import QueryCard from './components/QueryCard'
import IntentionCard from './components/IntentionCard'
import ToneCard from './components/ToneCard'
import PaletteCard from './components/PaletteCard'
import FontCard from './components/FontCard'
import BusinessProfileCard from './components/BusinessProfileCard'
import FullInputJSON from './components/FullInputJSON'

function TemplateSelectionInput({ summary, businessId, fullInput, config }) {
  return (
    <div className="eval-section input-section">
      <h3>📥 Input</h3>
      <div className="input-cards">
        <BusinessNameCard businessName={summary.business_name} />
        <QueryCard query={summary.query} />
        {businessId && <BusinessProfileCard businessId={businessId} config={config} />}
        <IntentionCard intention={summary.website_intention} />
        <ToneCard tone={summary.website_tone} />
        <PaletteCard palette={summary.palette} />
        <FontCard fontFamily={summary.font_family} />
      </div>
      <FullInputJSON fullInput={fullInput} />
    </div>
  )
}

export default TemplateSelectionInput
