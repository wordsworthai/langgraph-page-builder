import React, { useState, useCallback, useMemo, useEffect } from 'react'
import Navbar from './components/layout/Navbar'
import Sidebar from './components/layout/Sidebar'
import SettingsModal from './components/layout/SettingsModal'
import CheckpointModeView from './components/CheckpointModeView'
import EvalModeView from './components/EvalModeView'
import MetricsView from './components/metrics/MetricsView'
import DataExplorerView from './components/data/DataExplorerView'
import SectionBrowserView from './components/SectionBrowserView'
import CuratedPageBuilderView from './components/CuratedPageBuilderView'
import Modal from './components/layout/Modal'
import { ToastContainer } from 'react-toastify'
import { TwoPanelLayout, PreviewProvider } from '@code_editor'
import { useTaskConfigs, useCheckpointMode, useEvalMode } from './hooks'

function App() {
  const [config, setConfig] = useState({
    mongoUri: 'mongodb://localhost:27020',
    dbName: 'eval'
  })

  const [mode, setMode] = useState(() => {
    if (typeof window !== 'undefined') {
      const path = window.location.pathname
      if (path === '/metrics') return 'metrics'
      if (path === '/data') return 'data'
      if (path === '/code') return 'code'
      if (path === '/section-browser') return 'section_browser'
      if (path === '/curated-page-builder') return 'curated_page_builder'
    }
    return 'eval'
  })

  const [activeThreadId, setActiveThreadId] = useState(null)
  const [modal, setModal] = useState({ open: false, title: '', content: null })
  const [activeDataTab, setActiveDataTab] = useState('section_repo')
  const [initialCodeSectionId, setInitialCodeSectionId] = useState(null)
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false)
  const [settingsModalOpen, setSettingsModalOpen] = useState(false)

  const { taskConfigs } = useTaskConfigs()
  const checkpoint = useCheckpointMode(config, setActiveThreadId)
  const evalMode = useEvalMode(config, setActiveThreadId)

  const loading = {
    threads: checkpoint.loading.threads,
    checkpoints: checkpoint.loading.checkpoints,
    evalSets: evalMode.loading.evalSets
  }

  const handleModeChange = useCallback((newMode, codeSectionId) => {
    setMode(newMode)
    if (newMode !== 'code') setInitialCodeSectionId(null)
    if (typeof window !== 'undefined') {
      if (newMode === 'metrics') window.history.pushState({}, '', '/metrics')
      else if (newMode === 'data') window.history.pushState({}, '', '/data')
      else if (newMode === 'code') {
        const url = codeSectionId ? `/code?section_id=${encodeURIComponent(codeSectionId)}` : '/code'
        window.history.pushState({}, '', url)
      }
      else if (newMode === 'section_browser') window.history.pushState({}, '', '/section-browser')
      else if (newMode === 'curated_page_builder') window.history.pushState({}, '', '/curated-page-builder')
      else if (['/metrics', '/data', '/code', '/section-browser', '/curated-page-builder'].includes(window.location.pathname)) {
        window.history.pushState({}, '', '/')
      }
    }
    setActiveThreadId(null)
    checkpoint.reset()
    evalMode.reset()
  }, [checkpoint.reset, evalMode.reset])

  const codeSectionIdFromUrl = useMemo(() => {
    if (typeof window === 'undefined' || mode !== 'code') return null
    const params = new URLSearchParams(window.location.search)
    return params.get('section_id') || null
  }, [mode])

  const effectiveCodeSectionId = initialCodeSectionId || codeSectionIdFromUrl

  const handleNavigateToCode = useCallback((sectionId) => {
    const url = `${window.location.origin}/code?section_id=${encodeURIComponent(sectionId)}`
    window.open(url, '_blank', 'noopener,noreferrer')
  }, [])

  const syncModeFromUrl = useCallback(() => {
    if (typeof window === 'undefined') return
    const path = window.location.pathname
    if (path === '/metrics') setMode('metrics')
    else if (path === '/data') setMode('data')
    else if (path.startsWith('/code')) setMode('code')
    else if (path === '/section-browser') setMode('section_browser')
    else if (path === '/curated-page-builder') setMode('curated_page_builder')
    else setMode('eval')
  }, [])

  useEffect(() => {
    window.addEventListener('popstate', syncModeFromUrl)
    return () => window.removeEventListener('popstate', syncModeFromUrl)
  }, [syncModeFromUrl])

  const openModal = useCallback((title, content) => {
    setModal({ open: true, title, content })
  }, [])

  const closeModal = useCallback(() => {
    setModal({ open: false, title: '', content: null })
  }, [])

  const showSidebar = mode === 'checkpoint' || mode === 'eval'
  const showCodeEditor = mode === 'code'
  const currentTaskConfig = taskConfigs[evalMode.activeTaskType] || null

  return (
    <div className="app-wrapper">
      <Navbar
        mode={mode}
        onModeChange={handleModeChange}
        onOpenSettings={() => setSettingsModalOpen(true)}
      />
      <div className={`app-container ${showSidebar ? (isSidebarCollapsed ? 'sidebar-collapsed' : '') : 'no-sidebar'}`}>
        {showSidebar && (
          <Sidebar
            mode={mode}
            threads={checkpoint.threads}
            activeThreadId={activeThreadId}
            loading={loading.threads}
            onLoadThreads={checkpoint.loadThreads}
            onSelectThread={checkpoint.handleSelectThread}
            evalSets={evalMode.evalSets}
            activeEvalSetId={evalMode.activeEvalSetId}
            onLoadEvalSets={evalMode.loadEvalSets}
            onSelectEvalSet={evalMode.handleSelectEvalSet}
            loadingEvalSets={loading.evalSets}
            taskConfigs={taskConfigs}
            collapsed={isSidebarCollapsed}
            onToggleCollapsed={() => setIsSidebarCollapsed(prev => !prev)}
          />
        )}
        {mode === 'checkpoint' && (
          <CheckpointModeView
            activeThreadId={activeThreadId}
            checkpointData={checkpoint.checkpointData}
            selectedNode={checkpoint.selectedNode}
            loading={loading}
            error={checkpoint.error}
            onNodeSelect={checkpoint.handleNodeSelect}
            onNodeDeselect={checkpoint.handleNodeDeselect}
            onOpenModal={openModal}
            config={config}
          />
        )}
        {mode === 'eval' && (
          <EvalModeView
            evalSubView={evalMode.evalSubView}
            activeEvalSetId={evalMode.activeEvalSetId}
            activeThreadId={activeThreadId}
            config={config}
            taskType={evalMode.activeTaskType}
            taskConfig={currentTaskConfig}
            evalSetRuns={evalMode.evalSetRuns}
            currentRunIndex={evalMode.currentRunIndex}
            onSelectRun={evalMode.handleSelectRun}
            onBack={evalMode.handleBackToEvalSetsList}
            onRunsLoaded={evalMode.handleRunsLoaded}
            onTaskTypeDetected={evalMode.handleTaskTypeDetected}
            onNavigatePrev={evalMode.handleNavigatePrev}
            onNavigateNext={evalMode.handleNavigateNext}
            onBackToEvalSet={evalMode.handleBackToRuns}
          />
        )}
        {mode === 'metrics' && (
          <main className="main full-width">
            <MetricsView config={config} />
          </main>
        )}
        {mode === 'data' && (
          <main className="main full-width">
            <DataExplorerView
              config={config}
              activeTab={activeDataTab}
              onTabChange={setActiveDataTab}
            />
          </main>
        )}
        {mode === 'section_browser' && (
          <SectionBrowserView
            config={config}
            onNavigateToCode={handleNavigateToCode}
          />
        )}
        {mode === 'curated_page_builder' && (
          <CuratedPageBuilderView config={config} />
        )}
        {showCodeEditor && (
          <main className="main full-width" style={{ display: 'flex', flexDirection: 'column', minHeight: 0, overflow: 'hidden' }}>
            <div
              style={{
                flexShrink: 0,
                display: 'flex',
                alignItems: 'center',
                padding: '8px 12px',
                borderBottom: '1px solid var(--border-color)',
                background: 'var(--bg-secondary)',
              }}
            >
              <button
                type="button"
                onClick={() => handleModeChange('section_browser')}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                  padding: '6px 12px',
                  fontSize: 13,
                  cursor: 'pointer',
                  background: 'var(--bg-tertiary)',
                  border: '1px solid var(--border-color)',
                  borderRadius: 6,
                  color: 'var(--text-primary)',
                }}
              >
                ← Back to Section Browser
              </button>
            </div>
            <PreviewProvider>
              <TwoPanelLayout initialSectionId={effectiveCodeSectionId} />
            </PreviewProvider>
          </main>
        )}
      </div>

      <SettingsModal
        open={settingsModalOpen}
        config={config}
        onConfigChange={setConfig}
        onClose={() => setSettingsModalOpen(false)}
      />

      <Modal
        open={modal.open}
        title={modal.title}
        content={modal.content}
        onClose={closeModal}
      />

      <ToastContainer />
    </div>
  )
}

export default App
