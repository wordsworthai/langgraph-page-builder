import React, { useState, useEffect, useCallback } from 'react'

// Score badge component
function ScoreBadge({ score, size = 'small' }) {
  if (score == null) return <span className="score-na">—</span>
  
  let colorClass = 'low'
  if (score >= 7) colorClass = 'high'
  else if (score >= 4) colorClass = 'medium'
  
  return (
    <span className={`score-badge ${size} ${colorClass}`}>
      {score.toFixed(1)}
    </span>
  )
}

// Percentage badge (0-100)
function PctBadge({ pct, size = 'small' }) {
  if (pct == null) return <span className="score-na">—</span>
  const value = typeof pct === 'number' ? pct : parseFloat(pct)
  if (Number.isNaN(value)) return <span className="score-na">—</span>
  const display = (value * 100).toFixed(0)
  let colorClass = 'low'
  if (value >= 0.8) colorClass = 'high'
  else if (value >= 0.5) colorClass = 'medium'
  return (
    <span className={`score-badge ${size} ${colorClass}`} title={`${display}%`}>
      {display}%
    </span>
  )
}

function MetricsView({ config }) {
  const [data, setData] = useState(null)
  const [aiEvalData, setAiEvalData] = useState({}) // Map of eval_set_id -> metrics
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [expandedEvalSetId, setExpandedEvalSetId] = useState(null)

  const fetchSummary = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetch('/api/metrics/summary', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          mongo_uri: config.mongoUri,
          db_name: config.dbName,
          limit: 50
        })
      })
      const result = await response.json()
      if (result.detail) throw new Error(result.detail)
      setData(result)
      
      // Fetch AI eval metrics for each eval set
      const evalSets = result.eval_sets || []
      const aiMetricsPromises = evalSets.map(async (evalSet) => {
        try {
          const res = await fetch('/api/eval-results', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              mongo_uri: config.mongoUri,
              db_name: config.dbName,
              eval_set_id: evalSet.eval_set_id,
              task_name: 'template_eval'
            })
          })
          const data = await res.json()
          return { eval_set_id: evalSet.eval_set_id, metrics: data.metrics }
        } catch (e) {
          return { eval_set_id: evalSet.eval_set_id, metrics: null }
        }
      })
      
      const aiMetricsResults = await Promise.all(aiMetricsPromises)
      const metricsMap = {}
      aiMetricsResults.forEach(r => {
        if (r.metrics) metricsMap[r.eval_set_id] = r.metrics
      })
      setAiEvalData(metricsMap)
      
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [config.mongoUri, config.dbName])

  useEffect(() => {
    fetchSummary()
  }, [fetchSummary])

  if (loading) {
    return (
      <div className="metrics-view">
        <div className="loading">Loading metrics…</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="metrics-view">
        <div className="error-state">Error: {error}</div>
      </div>
    )
  }

  const evalSets = data?.eval_sets || []

  return (
    <div className="metrics-view">
      <div className="metrics-header">
        <h2>Eval Set Metrics</h2>
        <button className="btn-secondary" onClick={fetchSummary}>Refresh</button>
      </div>
      <div className="metrics-table-wrap">
        <table className="metrics-table">
          <thead>
            <tr>
              <th>Eval Set ID</th>
              <th>Task Type</th>
              <th>Total</th>
              <th>Completed</th>
              <th>Failed</th>
              <th>Progress</th>
              <th className="score-cell">Avg Score</th>
              <th className="score-cell">Compliance</th>
              <th className="score-cell">Human Pass</th>
              <th className="score-cell">AI Pass</th>
              <th className="score-cell">Agreement</th>
              <th>Human / AI</th>
            </tr>
          </thead>
          <tbody>
            {evalSets.map(row => {
              const aiMetrics = aiEvalData[row.eval_set_id] || {}
              const m = row.metrics || {}
              const taskKpis = m.task_kpis || {}
              const hasTaskKpis = Object.keys(taskKpis).length > 0
              const isExpanded = expandedEvalSetId === row.eval_set_id
              return (
                <React.Fragment key={row.eval_set_id}>
                  <tr>
                    <td>
                      {hasTaskKpis ? (
                        <button
                          type="button"
                          className="expand-btn"
                          onClick={() => setExpandedEvalSetId(isExpanded ? null : row.eval_set_id)}
                          aria-expanded={isExpanded}
                        >
                          {isExpanded ? '▼' : '▶'} {row.eval_set_id}
                        </button>
                      ) : (
                        row.eval_set_id
                      )}
                    </td>
                    <td>{row.task_type}</td>
                    <td>{row.total}</td>
                    <td>{row.completed}</td>
                    <td>{row.failed}</td>
                    <td>{row.progress_pct != null ? `${row.progress_pct.toFixed(0)}%` : '—'}</td>
                    <td className="score-cell">
                      <ScoreBadge score={aiMetrics.avg_score} />
                    </td>
                    <td className="score-cell">
                      <ScoreBadge score={aiMetrics.avg_compliance} />
                    </td>
                    <td className="score-cell">
                      <PctBadge pct={m.human_pass_pct} />
                    </td>
                    <td className="score-cell">
                      <PctBadge pct={m.ai_pass_pct} />
                    </td>
                    <td className="score-cell">
                      <PctBadge pct={m.agreement_pct} />
                    </td>
                    <td>
                      {row.metrics && (
                        <span className="metrics-inline">
                          H: {row.metrics.human_feedback_count ?? '—'} / A: {row.metrics.ai_feedback_count ?? '—'}
                        </span>
                      )}
                    </td>
                  </tr>
                  {isExpanded && hasTaskKpis && (
                    <tr className="task-kpis-row">
                      <td colSpan={12}>
                        <div className="task-kpis-section">
                          <strong>Task KPIs:</strong>
                          <div className="task-kpis-grid">
                            {Object.entries(taskKpis).map(([k, v]) => (
                              <span key={k} className="task-kpi-item">
                                {k.replace(/_/g, ' ')}: {typeof v === 'number' ? (v * 100).toFixed(0) + '%' : String(v)}
                              </span>
                            ))}
                          </div>
                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              )
            })}
          </tbody>
        </table>
      </div>
      
      {/* Per-Intent Breakdown (if an eval set is expanded) */}
      {Object.keys(aiEvalData).length > 0 && (
        <div className="metrics-breakdown">
          <h3>Score by Intent (Latest Eval Set)</h3>
          <div className="intent-metrics-grid">
            {Object.entries(aiEvalData).slice(0, 1).map(([evalSetId, metrics]) => (
              <div key={evalSetId} className="intent-metrics-card">
                <div className="intent-card-header">{evalSetId}</div>
                {metrics.by_intent && Object.entries(metrics.by_intent).map(([intent, data]) => (
                  <div key={intent} className="intent-row">
                    <span className="intent-name">{intent.replace(/_/g, ' ')}</span>
                    <span className="intent-count">{data.count} runs</span>
                    <ScoreBadge score={data.avg_score} />
                  </div>
                ))}
              </div>
            ))}
          </div>
        </div>
      )}
      
      {evalSets.length === 0 && (
        <div className="eval-empty">
          <p>No eval sets found.</p>
        </div>
      )}
    </div>
  )
}

export default MetricsView