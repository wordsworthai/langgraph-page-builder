import React from 'react'
import EvalSetsView from './eval/EvalSetsView'
import EvalView from './eval/EvalView'

export default function EvalModeView({
  evalSubView,
  activeEvalSetId,
  activeThreadId,
  config,
  taskType,
  taskConfig,
  evalSetRuns,
  currentRunIndex,
  onSelectRun,
  onBack,
  onRunsLoaded,
  onTaskTypeDetected,
  onNavigatePrev,
  onNavigateNext,
  onBackToEvalSet
}) {
  if (evalSubView === 'runs' && activeEvalSetId) {
    return (
      <main className="main full-width">
        <EvalSetsView
          evalSetId={activeEvalSetId}
          config={config}
          taskType={taskType}
          taskConfig={taskConfig}
          onSelectRun={onSelectRun}
          onBack={onBack}
          onRunsLoaded={onRunsLoaded}
          onTaskTypeDetected={onTaskTypeDetected}
        />
      </main>
    )
  }

  if (evalSubView === 'detail' && activeThreadId) {
    return (
      <main className="main full-width">
        <EvalView
          threadId={activeThreadId}
          config={config}
          taskType={taskType}
          taskConfig={taskConfig}
          evalSetId={activeEvalSetId}
          evalSetRuns={evalSetRuns}
          currentRunIndex={currentRunIndex}
          onNavigatePrev={onNavigatePrev}
          onNavigateNext={onNavigateNext}
          onBackToEvalSet={onBackToEvalSet}
        />
      </main>
    )
  }

  return (
    <main className="main full-width">
      <div className="eval-sets-view">
        <div className="eval-empty">
          <div className="icon">📁</div>
          <p>Select an eval set from the sidebar to view its runs</p>
        </div>
      </div>
    </main>
  )
}
