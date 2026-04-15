import { useState, useCallback } from 'react'

/**
 * Manages checkpoint mode state and handlers.
 * Requires setActiveThreadId from parent for coordination with eval mode.
 */
export function useCheckpointMode(config, setActiveThreadId) {
  const [threads, setThreads] = useState([])
  const [checkpointData, setCheckpointData] = useState(null)
  const [selectedNode, setSelectedNode] = useState(null)
  const [loading, setLoading] = useState({ threads: false, checkpoints: false })
  const [error, setError] = useState(null)

  const loadThreads = useCallback(async () => {
    setLoading(prev => ({ ...prev, threads: true }))
    setError(null)
    try {
      const response = await fetch('/api/threads', {
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
      setThreads(data.threads || [])
    } catch (err) {
      setError(err.message)
      setThreads([])
    } finally {
      setLoading(prev => ({ ...prev, threads: false }))
    }
  }, [config])

  const loadCheckpoints = useCallback(async (threadId) => {
    setActiveThreadId(threadId)
    setSelectedNode(null)
    setLoading(prev => ({ ...prev, checkpoints: true }))
    setError(null)
    try {
      const response = await fetch('/api/checkpoints', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          mongo_uri: config.mongoUri,
          db_name: config.dbName,
          thread_id: threadId
        })
      })
      const data = await response.json()
      if (data.detail) throw new Error(data.detail)
      setCheckpointData(data)
    } catch (err) {
      setError(err.message)
      setCheckpointData(null)
    } finally {
      setLoading(prev => ({ ...prev, checkpoints: false }))
    }
  }, [config, setActiveThreadId])

  const handleSelectThread = useCallback((threadId) => {
    setActiveThreadId(threadId)
    loadCheckpoints(threadId)
  }, [loadCheckpoints, setActiveThreadId])

  const handleNodeSelect = useCallback((nodeData) => setSelectedNode(nodeData), [])
  const handleNodeDeselect = useCallback(() => setSelectedNode(null), [])

  const reset = useCallback(() => {
    setThreads([])
    setCheckpointData(null)
    setSelectedNode(null)
    setError(null)
  }, [])

  return {
    threads,
    checkpointData,
    selectedNode,
    loading,
    error,
    loadThreads,
    loadCheckpoints,
    handleSelectThread,
    handleNodeSelect,
    handleNodeDeselect,
    reset
  }
}
