import { useState, useEffect } from 'react'

export function useAiEvalResult(evalSetRuns, currentRunIndex, config) {
  const [aiEvalResult, setAiEvalResult] = useState(null)
  const [aiEvalLoading, setAiEvalLoading] = useState(false)
  const [aiEvalCollapsed, setAiEvalCollapsed] = useState(true)

  useEffect(() => {
    const run = evalSetRuns?.[currentRunIndex]
    if (!run || !run.run_id) {
      setAiEvalResult(null)
      return
    }
    let cancelled = false
    setAiEvalLoading(true)
    const fetchAiEval = async () => {
      try {
        const response = await fetch('/api/eval-result', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            mongo_uri: config.mongoUri,
            db_name: config.dbName,
            eval_set_id: run.eval_set_id,
            run_id: run.run_id,
            task_name: 'template_eval'
          })
        })
        if (cancelled) return
        const data = await response.json()
        setAiEvalResult(data.result || null)
      } catch (err) {
        console.error('Failed to fetch AI eval result:', err)
        if (!cancelled) setAiEvalResult(null)
      } finally {
        if (!cancelled) setAiEvalLoading(false)
      }
    }
    fetchAiEval()
    return () => { cancelled = true }
  }, [currentRunIndex, evalSetRuns, config.mongoUri, config.dbName])

  return { aiEvalResult, aiEvalLoading, aiEvalCollapsed, setAiEvalCollapsed }
}
