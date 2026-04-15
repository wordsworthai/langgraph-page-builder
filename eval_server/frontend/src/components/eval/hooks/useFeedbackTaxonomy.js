import { useState, useEffect } from 'react'

export function useFeedbackTaxonomy(taskType) {
  const [taxonomy, setTaxonomy] = useState(null)

  useEffect(() => {
    if (!taskType) {
      setTaxonomy(null)
      return
    }
    let cancelled = false
    const fetchTaxonomy = async () => {
      try {
        const res = await fetch(`/api/feedback/taxonomy?task_type=${encodeURIComponent(taskType)}`)
        if (cancelled) return
        if (res.ok) {
          const data = await res.json()
          setTaxonomy(data)
        } else {
          setTaxonomy(null)
        }
      } catch {
        if (!cancelled) setTaxonomy(null)
      }
    }
    fetchTaxonomy()
    return () => { cancelled = true }
  }, [taskType])

  const categories = (taxonomy?.categories?.filter(c => c.active) ?? []).sort(
    (a, b) => (a.order ?? 0) - (b.order ?? 0)
  )
  const feedbackType = taxonomy?.mode ?? 'categories'

  return { taxonomy, categories, feedbackType }
}
