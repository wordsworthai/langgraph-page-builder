import React from 'react'
import { TASK_CONFIG } from '../../../constants'
import { getRunDisplayInfo } from '../converters/runUtils'
import GenericInput from './GenericInput'
import TemplateSelectionInput from './TemplateSelectionInput'
import LandingPageInput from './LandingPageInput'
import SectionCoverageInput from './SectionCoverageInput'

function LandingPageInputSection({ input, taskType, config, run }) {
  if (!input || !input.summary) return null

  const effectiveTaskType = TASK_CONFIG.normalizeTaskType(taskType)
  const { businessId: runBusinessId, websiteIntention: runIntention } = getRunDisplayInfo(run)
  const taskDetails = run?.task_details || {}
  const summary = {
    ...input.summary,
    website_intention: input.summary.website_intention ?? runIntention ?? taskDetails.website_intention,
    website_tone: input.summary.website_tone ?? taskDetails.website_tone,
  }
  const businessId = input.full?.business_id ?? runBusinessId ?? null
  const props = { summary, businessId, fullInput: input.full, config }

  if (effectiveTaskType === 'template_selection') {
    return <TemplateSelectionInput {...props} />
  }
  if (effectiveTaskType === 'landing_page') {
    return <LandingPageInput {...props} />
  }
  if (effectiveTaskType === 'section_coverage' || effectiveTaskType === 'color_palette' || effectiveTaskType === 'curated_pages') {
    return <SectionCoverageInput {...props} />
  }

  return <GenericInput {...props} />
}

export default LandingPageInputSection
