import { useState, useEffect } from 'react'

export function useCheckpoints(threadId, activeTab, config) {
  const [checkpointData, setCheckpointData] = useState(null)
  const [loadingCheckpoints, setLoadingCheckpoints] = useState(false)
  const [selectedNode, setSelectedNode] = useState(null)

  useEffect(() => {
    if (!threadId || activeTab !== 'graph') return
    if (checkpointData && checkpointData.thread_id === threadId) return
    const fetchCheckpoints = async () => {
      setLoadingCheckpoints(true)
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
        const result = await response.json()
        if (result.detail) throw new Error(result.detail)
        setCheckpointData(result)
      } catch (err) {
        console.error('Failed to load checkpoints:', err)
      } finally {
        setLoadingCheckpoints(false)
      }
    }
    fetchCheckpoints()
  }, [threadId, activeTab, config.mongoUri, config.dbName, checkpointData])

  useEffect(() => {
    setCheckpointData(null)
    setSelectedNode(null)
  }, [threadId])

  return { checkpointData, loadingCheckpoints, selectedNode, setSelectedNode }
}
