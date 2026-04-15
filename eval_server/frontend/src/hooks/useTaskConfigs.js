import { useState, useEffect, useRef } from 'react'

/**
 * Loads task configs from the server on mount.
 * Prevents duplicate loads (e.g. React Strict Mode).
 */
export function useTaskConfigs() {
  const [taskConfigs, setTaskConfigs] = useState({})
  const [loading, setLoading] = useState(false)
  const loadedRef = useRef(false)

  useEffect(() => {
    const hasConfigs = Object.keys(taskConfigs).length > 0
    if (loadedRef.current || hasConfigs) return

    let isCancelled = false

    const load = async () => {
      setLoading(true)
      try {
        const response = await fetch('/api/task-configs')
        if (isCancelled) return
        if (!response.ok) throw new Error(`HTTP ${response.status}: ${response.statusText}`)

        const data = await response.json()
        if (isCancelled) return

        if (data.task_configs && typeof data.task_configs === 'object') {
          setTaskConfigs(data.task_configs)
          loadedRef.current = true
        } else {
          console.error('[TaskConfigs] Invalid task_configs in response')
        }
      } catch (err) {
        if (!isCancelled) console.error('[TaskConfigs] Failed to load task configs:', err)
      } finally {
        if (!isCancelled) setLoading(false)
      }
    }

    load()
    return () => { isCancelled = true }
  }, [])

  return { taskConfigs, loading }
}
