import React, { useState } from 'react'
import { TASK_CONFIG } from '../eval/constants'

// Task-agnostic badge style (single color for all task types)
const TASK_BADGE_STYLE = TASK_CONFIG.badgeStyle

function Sidebar({ 
  // Checkpoint mode props
  threads, 
  activeThreadId, 
  loading, 
  onLoadThreads, 
  onSelectThread,
  // Eval mode props
  evalSets,
  activeEvalSetId,
  onLoadEvalSets,
  onSelectEvalSet,
  loadingEvalSets,
  // Mode (for conditional content)
  mode,
  // Task configs
  taskConfigs,
  collapsed,
  onToggleCollapsed,
}) {
  const [directThreadId, setDirectThreadId] = useState('')

  const handleGoToThread = () => {
    if (directThreadId.trim()) {
      onSelectThread(directThreadId.trim())
      setDirectThreadId('')
    }
  }

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      handleGoToThread()
    }
  }

  if (collapsed) {
    return (
      <div className="sidebar is-collapsed">
        <div className="sidebar-collapse-row">
          <button className="panel-collapse-btn" onClick={onToggleCollapsed} title="Expand sidebar">
            »
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="sidebar">
      <div className="sidebar-collapse-row">
        <button className="panel-collapse-btn" onClick={onToggleCollapsed} title="Collapse sidebar">
          «
        </button>
      </div>
      {(mode === 'checkpoint' || mode === 'eval') && (
      <div className="sidebar-header">
        {mode === 'checkpoint' && (
          <>
            {/* Direct Thread ID Input - only in checkpoint mode */}
            <div className="config-group">
              <label>Go to Thread ID</label>
              <div className="thread-input-row">
                <input
                  type="text"
                  value={directThreadId}
                  onChange={(e) => setDirectThreadId(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder="Enter thread ID..."
                />
                <button 
                  className="btn btn-go" 
                  onClick={handleGoToThread}
                  disabled={!directThreadId.trim()}
                >
                  Go
                </button>
              </div>
            </div>
            
            <button 
              className="btn" 
              onClick={onLoadThreads}
              disabled={loading}
            >
              {loading ? 'Loading...' : 'Load Threads'}
            </button>
          </>
        )}

        {mode === 'eval' && (
          <button 
            className="btn" 
            onClick={onLoadEvalSets}
            disabled={loadingEvalSets}
          >
            {loadingEvalSets ? 'Loading...' : 'Load Eval Sets'}
          </button>
        )}
      </div>
      )}
      
      {mode === 'checkpoint' ? (
        <div className="thread-list">
          {threads.length === 0 ? (
            <div className="state-empty">
              <div className="icon">📋</div>
              <p>Click "Load Threads" to see available checkpoints</p>
            </div>
          ) : (
            threads.map(thread => (
              <div
                key={thread.thread_id}
                className={`thread-item ${activeThreadId === thread.thread_id ? 'active' : ''}`}
                onClick={() => onSelectThread(thread.thread_id)}
              >
                <div className="thread-id">{thread.thread_id}</div>
                <div className="thread-count">{thread.checkpoint_count} checkpoints</div>
              </div>
            ))
          )}
        </div>
      ) : (
        <div className="thread-list">
          {(!evalSets || evalSets.length === 0) ? (
            <div className="state-empty">
              <div className="icon">📁</div>
              <p>Click "Load Eval Sets" to see available eval runs</p>
            </div>
          ) : (
            evalSets.map(evalSet => {
              const taskType = evalSet.task_type || 'landing_page'
              const displayTaskType = TASK_CONFIG.normalizeTaskType(taskType)
              return (
                <div
                  key={evalSet.eval_set_id}
                  className={`thread-item ${activeEvalSetId === evalSet.eval_set_id ? 'active' : ''}`}
                  onClick={() => onSelectEvalSet(evalSet.eval_set_id, taskType)}
                >
                  <div className="thread-id" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span 
                      className="task-type-badge-mini"
                      title={taskConfigs?.[displayTaskType]?.display_name || taskType}
                      style={{
                        backgroundColor: TASK_BADGE_STYLE.bg,
                        color: TASK_BADGE_STYLE.color,
                        padding: '2px 6px',
                        borderRadius: '3px',
                        fontSize: '10px',
                        fontWeight: 600,
                        letterSpacing: '0.5px'
                      }}
                    >
                      {TASK_BADGE_STYLE.short}
                    </span>
                    <span>{evalSet.eval_set_id}</span>
                  </div>
                  <div className="thread-count">
                    <span className="status-completed">{evalSet.completed}</span>
                    <span className="status-separator">/</span>
                    <span>{evalSet.total}</span>
                    {evalSet.failed > 0 && (
                      <span className="status-failed"> ({evalSet.failed} failed)</span>
                    )}
                    {evalSet.running > 0 && (
                      <span className="status-running"> ({evalSet.running} running)</span>
                    )}
                  </div>
                </div>
              )
            })
          )}
        </div>
      )}
    </div>
  )
}

export default Sidebar
