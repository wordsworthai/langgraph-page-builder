import React from 'react'
import { TASK_CONFIG } from './constants'

function EvalHeader({
  threadId,
  taskType,
  taskConfig,
  data,
  activeTab,
  onTabChange,
  hasHtmlPreview,
  aiEvalResult,
  hasNavigation,
  currentRunIndex,
  evalSetRuns,
  currentRun,
  onNavigatePrev,
  onNavigateNext,
  onBackToEvalSet
}) {
  const canGoPrev = hasNavigation && currentRunIndex > 0
  const canGoNext = hasNavigation && currentRunIndex < evalSetRuns.length - 1

  const taskBadgeStyle = taskConfig ? {
    backgroundColor: TASK_CONFIG.badgeStyle.bg,
    color: TASK_CONFIG.badgeStyle.color,
    padding: '3px 8px',
    borderRadius: '4px',
    fontSize: '11px',
    fontWeight: 500,
    marginRight: '8px'
  } : {}

  return (
    <div className="eval-header">
      <div className="eval-header-left">
        {hasNavigation && onBackToEvalSet && (
          <button className="back-btn" onClick={onBackToEvalSet}>
            ← Back
          </button>
        )}
        <h2>Run Details</h2>
        <div className="eval-meta">
          {taskConfig && (
            <span className="task-type-badge" style={taskBadgeStyle}>
              {taskConfig.display_name || taskType}
            </span>
          )}
          {taskType === 'curated_pages' && currentRun?.task_details?.page_path && (
            <span
              className="page-type-badge"
              title={currentRun.task_details.page_title ? `Page: ${currentRun.task_details.page_path} (${currentRun.task_details.page_title})` : `Page type: ${currentRun.task_details.page_path}`}
            >
              {currentRun.task_details.page_path}
            </span>
          )}
          <span className="thread-badge">{threadId?.substring(0, 8)}...</span>
          <span className="step-count">{data?.checkpoint_count} steps</span>
        </div>
      </div>

      {hasNavigation && (
        <div className="nav-buttons">
          <button
            className="nav-btn"
            onClick={onNavigatePrev}
            disabled={!canGoPrev}
          >
            ← Prev
          </button>
          <span className="nav-position">
            {currentRunIndex + 1} / {evalSetRuns.length}
          </span>
          <button
            className="nav-btn"
            onClick={onNavigateNext}
            disabled={!canGoNext}
          >
            Next →
          </button>
        </div>
      )}

      <div className="eval-tabs">
        <button
          className={`eval-tab ${activeTab === 'overview' ? 'active' : ''}`}
          onClick={() => onTabChange('overview')}
        >
          📋 Overview
        </button>
        {hasHtmlPreview && (
          <button
            className={`eval-tab ${activeTab === 'preview' ? 'active' : ''}`}
            onClick={() => onTabChange('preview')}
          >
            🌐 Preview
          </button>
        )}
        <button
          className={`eval-tab ${activeTab === 'graph' ? 'active' : ''}`}
          onClick={() => onTabChange('graph')}
        >
          🔗 Graph
        </button>
        <button
          className={`eval-tab ${activeTab === 'ai-eval' ? 'active' : ''}`}
          onClick={() => onTabChange('ai-eval')}
        >
          🤖 AI Eval
          {aiEvalResult?.output?.average_score != null && (
            <span className="tab-score-badge">
              {aiEvalResult.output.average_score.toFixed(1)}
            </span>
          )}
        </button>
      </div>
    </div>
  )
}

export default EvalHeader
