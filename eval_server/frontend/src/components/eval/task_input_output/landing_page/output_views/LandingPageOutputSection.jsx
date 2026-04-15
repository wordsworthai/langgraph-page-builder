import React from 'react'
import { TASK_CONFIG } from '../../../constants'
import GenericOutput from './GenericOutput'
import TemplateSelectionOutput from './TemplateSelectionOutput'
import LandingPageOutput from './LandingPageOutput'
import SectionCoverageOutput from './SectionCoverageOutput'

function LandingPageOutputSection({ output, taskType, hasHtmlPreview, onViewPreview }) {
  if (!output) return null

  const effectiveTaskType = TASK_CONFIG.normalizeTaskType(taskType)
  const showPreview = hasHtmlPreview ?? TASK_CONFIG.hasHtmlPreview(taskType)

  if (effectiveTaskType === 'template_selection') {
    return (
      <TemplateSelectionOutput
        output={output}
        hasHtmlPreview={showPreview}
        onViewPreview={onViewPreview}
      />
    )
  }
  if (effectiveTaskType === 'landing_page') {
    return (
      <LandingPageOutput
        output={output}
        hasHtmlPreview={showPreview}
        onViewPreview={onViewPreview}
      />
    )
  }
  if (effectiveTaskType === 'section_coverage' || effectiveTaskType === 'color_palette' || effectiveTaskType === 'curated_pages') {
    return (
      <SectionCoverageOutput
        output={output}
        hasHtmlPreview={showPreview}
        onViewPreview={onViewPreview}
      />
    )
  }

  return (
    <GenericOutput
      output={output}
      hasHtmlPreview={showPreview}
      onViewPreview={onViewPreview}
    />
  )
}

export default LandingPageOutputSection
