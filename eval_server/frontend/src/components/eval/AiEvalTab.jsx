import React from 'react'
import AIEvalResultCard from './AIEvalResultCard'

function AiEvalTab({ aiEvalResult, aiEvalLoading, taskType }) {
  return (
    <div className="eval-content ai-eval-tab-content">
      <div className="ai-eval-tab-wrapper">
        {aiEvalLoading ? (
          <div className="loading">Loading AI evaluation...</div>
        ) : (
          <AIEvalResultCard evalResult={aiEvalResult} taskType={taskType} />
        )}
      </div>
    </div>
  )
}

export default AiEvalTab
