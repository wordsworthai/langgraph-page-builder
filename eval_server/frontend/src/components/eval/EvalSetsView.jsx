import React, { useState, useEffect } from 'react'
import { TASK_CONFIG } from './constants'
import { getRunDisplayInfo } from './task_input_output/landing_page/converters/runUtils'

// Score badge component (inline for simplicity)
function ScoreBadge({ score, size = 'small' }) {
  if (score == null) return null
  
  let colorClass = 'low'
  if (score >= 7) colorClass = 'high'
  else if (score >= 4) colorClass = 'medium'
  
  return (
    <span className={`score-badge ${size} ${colorClass}`}>
      {score.toFixed(1)}
    </span>
  )
}

function EvalSetsView({ 
  evalSetId, 
  config, 
  taskType,
  taskConfig,
  onSelectRun,
  onBack,
  onRunsLoaded,
  onTaskTypeDetected
}) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  
  // AI eval results map: { run_id: evalResult, ... }
  const [evalResultsMap, setEvalResultsMap] = useState({})
  const [evalMetrics, setEvalMetrics] = useState(null)

  // Fetch runs
  useEffect(() => {
    if (!evalSetId) return

    const fetchRuns = async () => {
      setLoading(true)
      setError(null)

      try {
        const response = await fetch('/api/eval-set-runs', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            mongo_uri: config.mongoUri,
            db_name: config.dbName,
            eval_set_id: evalSetId,
            status_filter: 'completed'
          })
        })

        const result = await response.json()
        if (result.detail) throw new Error(result.detail)
        setData(result)
        
        if (onRunsLoaded && result.runs) {
          onRunsLoaded(result.runs)
        }
        if (onTaskTypeDetected && result.summary?.task_type) {
          onTaskTypeDetected(result.summary.task_type)
        }
      } catch (err) {
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }

    fetchRuns()
  }, [evalSetId, config.mongoUri, config.dbName])

  // Fetch AI eval results (separate call to get score badges)
  useEffect(() => {
    if (!evalSetId) return

    const fetchEvalResults = async () => {
      try {
        const response = await fetch('/api/eval-results-map', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            mongo_uri: config.mongoUri,
            db_name: config.dbName,
            eval_set_id: evalSetId,
            task_name: 'template_eval'
          })
        })

        const result = await response.json()
        if (result.results_map) {
          setEvalResultsMap(result.results_map)
        }
      } catch (err) {
        console.error('Failed to fetch eval results:', err)
      }
    }

    // Also fetch metrics
    const fetchMetrics = async () => {
      try {
        const response = await fetch('/api/eval-results', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            mongo_uri: config.mongoUri,
            db_name: config.dbName,
            eval_set_id: evalSetId,
            task_name: 'template_eval'
          })
        })

        const result = await response.json()
        if (result.metrics) {
          setEvalMetrics(result.metrics)
        }
      } catch (err) {
        console.error('Failed to fetch eval metrics:', err)
      }
    }

    fetchEvalResults()
    fetchMetrics()
  }, [evalSetId, config.mongoUri, config.dbName])

  // Helper to get eval result for a run
  const getEvalResultForRun = (run) => {
    return run?.run_id ? evalResultsMap[run.run_id] || null : null
  }

  if (!evalSetId) {
    return (
      <div className="eval-sets-view">
        <div className="eval-empty">
          <div className="icon">📁</div>
          <p>Select an eval set from the sidebar to view its runs</p>
        </div>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="eval-sets-view">
        <div className="loading">Loading runs</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="eval-sets-view">
        <div className="error-state">Error: {error}</div>
      </div>
    )
  }

  if (!data) return null

  const { summary, runs } = data
  const actualTaskType = summary?.task_type || taskType || 'full'

  return (
    <div className="eval-sets-view">
      <div className="eval-sets-header">
        <div>
          <div className="breadcrumb">
            <span className="breadcrumb-item" onClick={onBack}>Eval Sets</span>
            <span className="breadcrumb-separator">›</span>
            <span className="breadcrumb-item active">{evalSetId}</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <h2>Eval Set Runs</h2>
            <span 
              className="task-type-badge"
              style={{ 
                backgroundColor: TASK_CONFIG.badgeStyle.bg,
                color: TASK_CONFIG.badgeStyle.color,
                padding: '4px 10px',
                borderRadius: '4px',
                fontSize: '12px',
                fontWeight: 500
              }}
            >
              {taskConfig?.display_name || actualTaskType}
            </span>
          </div>
        </div>
        <button className="back-btn" onClick={onBack}>
          ← Back to Eval Sets
        </button>
      </div>

      <div className="eval-sets-content">
        {/* Summary Stats */}
        <div className="summary-stats">
          <div className="stat-item">
            <span className="stat-value">{summary.total}</span>
            <span className="stat-label">Total</span>
          </div>
          <div className="stat-item">
            <span className="stat-value status-completed">{summary.completed}</span>
            <span className="stat-label">Completed</span>
          </div>
          <div className="stat-item">
            <span className="stat-value status-failed">{summary.failed}</span>
            <span className="stat-label">Failed</span>
          </div>
          <div className="stat-item">
            <span className="stat-value status-running">{summary.running}</span>
            <span className="stat-label">Running</span>
          </div>
          <div className="stat-item">
            <span className="stat-value" style={{ color: 'var(--accent-blue)' }}>
              {summary.progress_pct.toFixed(0)}%
            </span>
            <span className="stat-label">Progress</span>
          </div>
          
          {/* AI Eval Metrics */}
          {evalMetrics && evalMetrics.avg_score != null && (
            <>
              <div className="stat-item stat-divider" />
              <div className="stat-item">
                <span className="stat-value">
                  <ScoreBadge score={evalMetrics.avg_score} size="medium" />
                </span>
                <span className="stat-label">Avg Score</span>
              </div>
              {evalMetrics.avg_compliance != null && (
                <div className="stat-item">
                  <span className="stat-value">
                    <ScoreBadge score={evalMetrics.avg_compliance} size="medium" />
                  </span>
                  <span className="stat-label">Compliance</span>
                </div>
              )}
            </>
          )}
        </div>

        {/* Runs List - one row per data point (business + intent) */}
        <div className="runs-list">
          <div className="runs-list-header">
            <div className="run-index-header">#</div>
            <div className="run-info-header">Business / Intent</div>
            <div className="run-score-header">AI Eval</div>
            <div className="run-status-header">Status</div>
          </div>
          
          {runs.map((run, idx) => {
            const { businessId, websiteIntention } = getRunDisplayInfo(run)
            const intentLabel = websiteIntention ? websiteIntention.replace(/_/g, ' ') : ''
            const evalResult = getEvalResultForRun(run)
            const avgScore = evalResult?.output?.average_score
            
            return (
              <div
                key={run._id || `${run.eval_set_id}-${businessId}-${websiteIntention}`}
                className="run-item"
                onClick={() => onSelectRun(run, idx)}
              >
                <div className="run-index">{idx + 1}</div>
                <div className="run-info">
                  <div className="run-business-id">
                    {String(businessId || '').slice(0, 12)}
                    {businessId && businessId.length > 12 ? '…' : ''}
                  </div>
                  {intentLabel && (
                    <div className="run-intent" title={websiteIntention}>
                      {intentLabel}
                    </div>
                  )}
                </div>
                <div className="run-score">
                  {evalResult ? (
                    <div className="ai-eval-compact">
                      <ScoreBadge score={avgScore} size="small" />
                      {evalResult.status === 'failed' && (
                        <span className="eval-status-mini error" title="Eval failed">✗</span>
                      )}
                    </div>
                  ) : (
                    <span className="no-eval">—</span>
                  )}
                </div>
                <div className={`run-status ${run.status}`}>
                  {run.status}
                </div>
              </div>
            )
          })}
        </div>

        {runs.length === 0 && (
          <div className="eval-empty">
            <div className="icon">📭</div>
            <p>No runs found for this eval set</p>
          </div>
        )}
      </div>
    </div>
  )
}

export default EvalSetsView