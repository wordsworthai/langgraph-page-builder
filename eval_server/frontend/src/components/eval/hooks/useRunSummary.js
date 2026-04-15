import { useState, useEffect } from 'react'
import { convertRunSummary } from '../task_input_output/landing_page/converters'

export function useRunSummary(threadId, config, evalSetId, currentRun, taskType) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!threadId) return
    const fetchSummary = async () => {
      setLoading(true)
      setError(null)
      try {
        const body = { mongo_uri: config.mongoUri, db_name: config.dbName, thread_id: threadId }
        if (evalSetId && currentRun?.run_id) {
          body.eval_set_id = evalSetId
          body.run_id = currentRun.run_id
        }
        const response = await fetch('/api/run-summary', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body)
        })
        const result = await response.json()
        if (result.detail) throw new Error(result.detail)
        const converted = convertRunSummary(taskType, result)
        setData(converted)
      } catch (err) {
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }
    fetchSummary()
  }, [threadId, config.mongoUri, config.dbName, evalSetId, currentRun?.run_id, taskType])

  return { data, loading, error }
}
