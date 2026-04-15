import { useState, useEffect, useRef, useCallback } from 'react'
import { toast } from 'react-toastify'
import { getRunDisplayInfo } from '../task_input_output/landing_page/converters/runUtils'

export function useFeedback(threadId, taskType, config, taxonomy, currentRun, evalSetId) {
  const [feedback, setFeedback] = useState({})
  const [feedbackOpen, setFeedbackOpen] = useState(false)
  const [feedbackSaving, setFeedbackSaving] = useState(false)
  const [feedbackSaved, setFeedbackSaved] = useState(false)
  const [feedbackLoading, setFeedbackLoading] = useState(false)

  const lastLoadedThreadRef = useRef(null)

  const categories = taxonomy?.categories?.filter(c => c.active) ?? []

  useEffect(() => {
    if (!threadId) return
    // Wait for taxonomy to load before fetching feedback - otherwise we can't normalize
    // the saved feedback into the form fields (categories defines the keys)
    if (!taxonomy || categories.length === 0) return

    const cacheKey = `${threadId}-${taskType}`
    if (lastLoadedThreadRef.current === cacheKey) return

    const emptyFeedback = {}
    categories.forEach(cat => {
      if (cat.value_type === 'boolean') emptyFeedback[cat.key] = null
      else if (cat.value_type === 'number') emptyFeedback[cat.key] = null
      else emptyFeedback[cat.key] = ''
    })

    let isCancelled = false
    const loadFeedback = async () => {
      setFeedbackLoading(true)
      try {
        const response = await fetch('/api/feedback', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            mongo_uri: config.mongoUri,
            db_name: config.dbName,
            thread_id: threadId
          })
        })
        if (isCancelled) return
        const result = await response.json()
        if (isCancelled) return
        lastLoadedThreadRef.current = `${threadId}-${taskType}`
        if (result.feedback && result.feedback.feedback) {
          const savedFeedback = result.feedback.feedback
          if (typeof savedFeedback === 'object') {
            const normalized = { ...emptyFeedback }
            categories.forEach(cat => {
              const v = savedFeedback[cat.key]
              if (v === undefined) return
              if (cat.value_type === 'boolean') {
                if (v === true || v === 'true') normalized[cat.key] = true
                else if (v === false || v === 'false') normalized[cat.key] = false
                else normalized[cat.key] = null
              } else {
                normalized[cat.key] = v
              }
            })
            setFeedback(normalized)
          } else {
            setFeedback(emptyFeedback)
          }
          setFeedbackSaved(true)
        } else {
          setFeedback(emptyFeedback)
          setFeedbackSaved(false)
        }
      } catch (err) {
        if (!isCancelled) {
          console.error('Failed to load feedback:', err)
          setFeedback(emptyFeedback)
          setFeedbackSaved(false)
        }
      } finally {
        if (!isCancelled) setFeedbackLoading(false)
      }
    }
    loadFeedback()
    return () => { isCancelled = true }
  }, [threadId, config.mongoUri, config.dbName, taskType, taxonomy])

  const hasFeedbackContent = useCallback(() => {
    return Object.values(feedback).some(v => {
      if (typeof v === 'boolean') return true
      if (typeof v === 'string') return v.trim().length > 0
      if (typeof v === 'number' && !isNaN(v)) return true
      return false
    })
  }, [feedback])

  const updateFeedbackField = useCallback((key, value) => {
    setFeedback(prev => ({ ...prev, [key]: value }))
    setFeedbackSaved(false)
  }, [])

  const saveFeedback = useCallback(async () => {
    if (!threadId || !hasFeedbackContent()) return
    setFeedbackSaving(true)
    try {
      const cleanedFeedback = {}
      Object.entries(feedback).forEach(([key, value]) => {
        if (typeof value === 'boolean') cleanedFeedback[key] = value
        else if (typeof value === 'number' && !isNaN(value)) cleanedFeedback[key] = value
        else if (typeof value === 'string' && value.trim()) cleanedFeedback[key] = value.trim()
      })
      const { businessId } = getRunDisplayInfo(currentRun)
      const eval_set_id = currentRun?.eval_set_id ?? evalSetId ?? null
      const run_id = currentRun?.run_id ?? null

      if (!eval_set_id || !run_id) {
        console.error('Cannot save feedback: eval_set_id and run_id are required', {
          eval_set_id,
          run_id,
          currentRun,
          evalSetId
        })
        throw new Error('Missing eval_set_id or run_id. Ensure you selected a run from an eval set.')
      }

      const response = await fetch('/api/feedback/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          mongo_uri: config.mongoUri,
          db_name: config.dbName,
          thread_id: threadId,
          eval_set_id,
          run_id,
          business_id: businessId || null,
          feedback: cleanedFeedback
        })
      })
      const result = await response.json()

      if (!response.ok) {
        throw new Error(result.detail || `Save failed: ${response.status}`)
      }
      if (result.success) {
        setFeedbackSaved(true)
        setFeedbackOpen(false)
      }
    } catch (err) {
      console.error('Failed to save feedback:', err)
      toast.error(err.message || 'Failed to save feedback')
    } finally {
      setFeedbackSaving(false)
    }
  }, [threadId, config.mongoUri, config.dbName, currentRun, evalSetId, feedback, hasFeedbackContent])

  return {
    feedback,
    feedbackOpen,
    setFeedbackOpen,
    feedbackSaving,
    feedbackSaved,
    feedbackLoading,
    updateFeedbackField,
    saveFeedback,
    hasFeedbackContent
  }
}
