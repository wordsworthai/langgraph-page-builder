import { useState, useCallback } from 'react'

/**
 * Manages eval mode state and handlers.
 * Requires setActiveThreadId from parent for coordination with checkpoint mode.
 */
export function useEvalMode(config, setActiveThreadId) {
  const [evalSets, setEvalSets] = useState([])
  const [activeEvalSetId, setActiveEvalSetId] = useState(null)
  const [evalSetRuns, setEvalSetRuns] = useState([])
  const [currentRunIndex, setCurrentRunIndex] = useState(-1)
  const [evalSubView, setEvalSubView] = useState('list')
  const [activeTaskType, setActiveTaskType] = useState('landing_page')
  const [loading, setLoading] = useState({ evalSets: false })
  const [error, setError] = useState(null)

  const loadEvalSets = useCallback(async () => {
    setLoading(prev => ({ ...prev, evalSets: true }))
    setError(null)
    try {
      const response = await fetch('/api/eval-sets', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          mongo_uri: config.mongoUri,
          db_name: config.dbName,
          limit: 50
        })
      })
      const data = await response.json()
      if (data.detail) throw new Error(data.detail)
      setEvalSets(data.eval_sets || [])
    } catch (err) {
      setError(err.message)
      setEvalSets([])
    } finally {
      setLoading(prev => ({ ...prev, evalSets: false }))
    }
  }, [config])

  const handleSelectEvalSet = useCallback((evalSetId, taskType) => {
    setActiveEvalSetId(evalSetId)
    setCurrentRunIndex(-1)
    setActiveThreadId(null)
    setEvalSubView('runs')
    setActiveTaskType(taskType || 'full')
  }, [setActiveThreadId])

  const handleSelectRun = useCallback((run, index) => {
    setCurrentRunIndex(index)
    const threadId = run.thread_id || run.request_id || run.generation_version_id
    if (threadId) {
      setActiveThreadId(threadId)
      setEvalSubView('detail')
      if (run.task_type) setActiveTaskType(run.task_type)
    }
  }, [setActiveThreadId])

  const handleRunsLoaded = useCallback((runs) => setEvalSetRuns(runs), [])

  const handleTaskTypeDetected = useCallback((detectedTaskType) => {
    if (detectedTaskType) setActiveTaskType(prev => prev === detectedTaskType ? prev : detectedTaskType)
  }, [])

  const handleNavigatePrev = useCallback(() => {
    if (currentRunIndex > 0 && evalSetRuns.length > 0) {
      const newIndex = currentRunIndex - 1
      handleSelectRun(evalSetRuns[newIndex], newIndex)
    }
  }, [currentRunIndex, evalSetRuns, handleSelectRun])

  const handleNavigateNext = useCallback(() => {
    if (currentRunIndex < evalSetRuns.length - 1) {
      const newIndex = currentRunIndex + 1
      handleSelectRun(evalSetRuns[newIndex], newIndex)
    }
  }, [currentRunIndex, evalSetRuns, handleSelectRun])

  const handleBackToRuns = useCallback(() => {
    setActiveThreadId(null)
    setCurrentRunIndex(-1)
    setEvalSubView('runs')
  }, [setActiveThreadId])

  const handleBackToEvalSetsList = useCallback(() => {
    setActiveEvalSetId(null)
    setEvalSetRuns([])
    setCurrentRunIndex(-1)
    setActiveThreadId(null)
    setEvalSubView('list')
  }, [setActiveThreadId])

  const reset = useCallback(() => {
    setActiveEvalSetId(null)
    setEvalSetRuns([])
    setCurrentRunIndex(-1)
    setEvalSubView('list')
  }, [])

  return {
    evalSets,
    activeEvalSetId,
    evalSetRuns,
    currentRunIndex,
    evalSubView,
    activeTaskType,
    loading,
    error,
    loadEvalSets,
    handleSelectEvalSet,
    handleSelectRun,
    handleRunsLoaded,
    handleTaskTypeDetected,
    handleNavigatePrev,
    handleNavigateNext,
    handleBackToRuns,
    handleBackToEvalSetsList,
    reset
  }
}
