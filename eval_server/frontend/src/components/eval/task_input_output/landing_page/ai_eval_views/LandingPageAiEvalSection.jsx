import React from 'react'
import { TASK_CONFIG } from '../../../constants'
import TemplateSelectionAiEvalCard from './TemplateSelectionAiEvalCard'
import GenericAiEvalCard from './GenericAiEvalCard'

function hasTemplateStructure(result) {
  const output = result?.output
  return output && (
    Array.isArray(output.template_scores) && output.template_scores.length > 0 ||
    (output.guidelines_compliance && Object.keys(output.guidelines_compliance).length > 0)
  )
}

function LandingPageAiEvalSection({ evalResult, taskType, compact = false }) {
  const effectiveTaskType = TASK_CONFIG.normalizeTaskType(taskType || '')
  const useTemplateView = effectiveTaskType === 'template_selection' && hasTemplateStructure(evalResult)

  if (useTemplateView) {
    return <TemplateSelectionAiEvalCard evalResult={evalResult} compact={compact} />
  }

  return <GenericAiEvalCard evalResult={evalResult} compact={compact} />
}

export default LandingPageAiEvalSection
