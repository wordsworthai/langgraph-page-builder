import React from 'react'
import LandingPageAiEvalSection from './task_input_output/landing_page/ai_eval_views/LandingPageAiEvalSection'

/**
 * AIEvalResultCard - Displays AI eval results (task-specific or JSON fallback).
 * Delegates to LandingPageAiEvalSection which routes by taskType.
 */
function AIEvalResultCard({ evalResult, taskType, compact = false }) {
  return (
    <LandingPageAiEvalSection
      evalResult={evalResult}
      taskType={taskType}
      compact={compact}
    />
  )
}

export default AIEvalResultCard
