import React, { useState } from 'react'
import Modal from '../layout/Modal'
import { TASK_CONFIG } from './constants'
import EvalHeader from './EvalHeader'
import OverviewTab from './OverviewTab'
import PreviewTab from './PreviewTab'
import GraphTab from './GraphTab'
import AiEvalTab from './AiEvalTab'
import FeedbackModal from './FeedbackModal'
import {
  useRunSummary,
  useCheckpoints,
  useFeedbackTaxonomy,
  useFeedback,
  useAiEvalResult
} from './hooks'

function EvalView({
  threadId,
  config,
  taskType,
  taskConfig,
  evalSetId,
  evalSetRuns,
  currentRunIndex,
  onNavigatePrev,
  onNavigateNext,
  onBackToEvalSet
}) {
  const [activeTab, setActiveTab] = useState('overview')
  const [previewDevice, setPreviewDevice] = useState('desktop')
  const [modal, setModal] = useState({ open: false, title: '', content: null })

  const hasHtmlPreview = TASK_CONFIG.hasHtmlPreview(taskType)
  const hasNavigation = evalSetRuns && evalSetRuns.length > 0
  const currentRun = evalSetRuns?.[currentRunIndex]

  const { data, loading, error } = useRunSummary(threadId, config, evalSetId, currentRun, taskType)
  const { checkpointData, loadingCheckpoints, selectedNode, setSelectedNode } = useCheckpoints(
    threadId,
    activeTab,
    config
  )
  const { taxonomy, feedbackType } = useFeedbackTaxonomy(taskType)
  const {
    feedback,
    feedbackOpen,
    setFeedbackOpen,
    feedbackSaving,
    feedbackSaved,
    feedbackLoading,
    updateFeedbackField,
    saveFeedback,
    hasFeedbackContent
  } = useFeedback(threadId, taskType, config, taxonomy, currentRun, evalSetId)
  const { aiEvalResult, aiEvalLoading, aiEvalCollapsed, setAiEvalCollapsed } = useAiEvalResult(
    evalSetRuns,
    currentRunIndex,
    config
  )

  const openModal = (title, content) => setModal({ open: true, title, content })
  const closeModal = () => setModal({ open: false, title: '', content: null })

  if (!threadId) {
    return (
      <div className="eval-view">
        <div className="eval-empty">
          <div className="icon">📊</div>
          <p>Select a run to view its details</p>
        </div>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="eval-view">
        <div className="loading">Loading run summary</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="eval-view">
        <EvalHeader
          threadId={threadId}
          taskType={taskType}
          taskConfig={taskConfig}
          data={null}
          activeTab={activeTab}
          onTabChange={setActiveTab}
          hasHtmlPreview={hasHtmlPreview}
          aiEvalResult={aiEvalResult}
          hasNavigation={hasNavigation}
          currentRunIndex={currentRunIndex}
          evalSetRuns={evalSetRuns}
          onNavigatePrev={onNavigatePrev}
          onNavigateNext={onNavigateNext}
          onBackToEvalSet={onBackToEvalSet}
        />
        <div className="error-state">Error: {error}</div>
      </div>
    )
  }

  if (!data) return null

  const { input, output, steps } = data

  return (
    <div className="eval-view">
      <EvalHeader
        threadId={threadId}
        taskType={taskType}
        taskConfig={taskConfig}
        data={data}
        activeTab={activeTab}
        onTabChange={setActiveTab}
        hasHtmlPreview={hasHtmlPreview}
        aiEvalResult={aiEvalResult}
        hasNavigation={hasNavigation}
        currentRunIndex={currentRunIndex}
        evalSetRuns={evalSetRuns}
        currentRun={currentRun}
        onNavigatePrev={onNavigatePrev}
        onNavigateNext={onNavigateNext}
        onBackToEvalSet={onBackToEvalSet}
      />

      {activeTab === 'overview' && (
        <OverviewTab
          input={input}
          output={output}
          steps={steps}
          taskType={taskType}
          taskConfig={taskConfig}
          config={config}
          run={currentRun}
          onViewPreview={() => setActiveTab('preview')}
        />
      )}
      {activeTab === 'preview' && hasHtmlPreview && (
        <PreviewTab
          output={output}
          previewDevice={previewDevice}
          onDeviceChange={setPreviewDevice}
        />
      )}
      {activeTab === 'graph' && (
        <GraphTab
          checkpointData={checkpointData}
          loadingCheckpoints={loadingCheckpoints}
          selectedNode={selectedNode}
          onNodeSelect={setSelectedNode}
          onNodeDeselect={() => setSelectedNode(null)}
          onOpenModal={openModal}
        />
      )}
      {activeTab === 'ai-eval' && (
        <AiEvalTab aiEvalResult={aiEvalResult} aiEvalLoading={aiEvalLoading} taskType={taskType} />
      )}

      <button
        className={`feedback-fab ${feedbackSaved && hasFeedbackContent() ? 'has-feedback' : ''}`}
        onClick={() => setFeedbackOpen(true)}
        title="Add feedback for this example"
      >
        {feedbackSaved && hasFeedbackContent() ? '✓' : '💬'}
      </button>

      <FeedbackModal
        open={feedbackOpen}
        onClose={() => setFeedbackOpen(false)}
        threadId={threadId}
        feedback={feedback}
        feedbackType={feedbackType}
        feedbackSaved={feedbackSaved}
        feedbackSaving={feedbackSaving}
        taxonomy={taxonomy}
        taskType={taskType}
        onUpdateField={updateFeedbackField}
        onSave={saveFeedback}
        hasFeedbackContent={hasFeedbackContent()}
        aiEvalResult={aiEvalResult}
        aiEvalLoading={aiEvalLoading}
        aiEvalCollapsed={aiEvalCollapsed}
        onAiEvalToggle={() => setAiEvalCollapsed(prev => !prev)}
      />

      <Modal
        open={modal.open}
        title={modal.title}
        content={modal.content}
        onClose={closeModal}
      />
    </div>
  )
}

export default EvalView
