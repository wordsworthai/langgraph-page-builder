import React, { useState } from 'react'
import GraphView from './checkpoint/GraphView'
import StatePanel from './checkpoint/StatePanel'
import PromptTracesView from './checkpoint/PromptTracesView'

export default function CheckpointModeView({
  activeThreadId,
  checkpointData,
  selectedNode,
  loading,
  error,
  onNodeSelect,
  onNodeDeselect,
  onOpenModal,
  config = {},
}) {
  const [activeTab, setActiveTab] = useState('graph')

  return (
    <>
      <main className="main">
        <div className="main-header">
          <h2>
            {activeThreadId
              ? `Thread: ${activeThreadId.substring(0, 8)}...`
              : 'Select a thread to view its checkpoint graph'}
          </h2>
          {checkpointData && activeTab === 'graph' && (
            <span className="stats">{checkpointData.checkpoint_count} checkpoints</span>
          )}
        </div>

        {activeThreadId && (
          <div className="checkpoint-tabs" style={{
            display: 'flex',
            gap: 8,
            marginBottom: 12,
            borderBottom: '1px solid var(--border-color)',
          }}>
            <button
              type="button"
              onClick={() => setActiveTab('graph')}
              style={{
                padding: '8px 16px',
                background: activeTab === 'graph' ? 'var(--bg-tertiary)' : 'none',
                border: 'none',
                borderBottom: activeTab === 'graph' ? '2px solid var(--accent-color)' : '2px solid transparent',
                cursor: 'pointer',
                fontSize: 14,
                color: 'var(--text-primary)',
              }}
            >
              Graph
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('prompt-traces')}
              style={{
                padding: '8px 16px',
                background: activeTab === 'prompt-traces' ? 'var(--bg-tertiary)' : 'none',
                border: 'none',
                borderBottom: activeTab === 'prompt-traces' ? '2px solid var(--accent-color)' : '2px solid transparent',
                cursor: 'pointer',
                fontSize: 14,
                color: 'var(--text-primary)',
              }}
            >
              Prompt Traces
            </button>
          </div>
        )}

        {activeTab === 'graph' && (
          <GraphView
            data={checkpointData}
            loading={loading.checkpoints}
            error={error}
            onNodeSelect={onNodeSelect}
            onNodeDeselect={onNodeDeselect}
          />
        )}
        {activeTab === 'prompt-traces' && (
          <PromptTracesView generationVersionId={activeThreadId} config={config} />
        )}
      </main>

      <StatePanel node={selectedNode} onOpenModal={onOpenModal} />
    </>
  )
}
