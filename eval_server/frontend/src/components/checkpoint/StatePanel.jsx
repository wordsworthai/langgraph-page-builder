import React, { useState, useMemo } from 'react'

function safeStringify(value, indent = null) {
  try {
    return JSON.stringify(value, null, indent)
  } catch (e) {
    return String(value)
  }
}

function truncate(str, maxLen) {
  if (!str) return ''
  str = String(str)
  if (str.length <= maxLen) return str
  return str.substring(0, maxLen) + '...'
}

function StatePanel({ node, onOpenModal }) {
  const [activeTab, setActiveTab] = useState('writes')

  const tabs = [
    { id: 'writes', label: 'Writes' },
    { id: 'channels', label: 'Channels' },
    { id: 'metadata', label: 'Metadata' }
  ]

  const content = useMemo(() => {
    if (!node) return null

    if (activeTab === 'writes') {
      const writes = node.writes || []
      if (writes.length === 0) {
        return (
          <div className="state-empty">
            <p>No writes at this checkpoint</p>
          </div>
        )
      }
      return writes.map((write, idx) => (
        <div
          key={idx}
          className="write-item"
          onClick={() => onOpenModal(write.channel || 'Write Value', write.value)}
        >
          <div className="write-channel">{write.channel || 'unknown'}</div>
          <div className="write-value">{truncate(safeStringify(write.value), 100)}</div>
        </div>
      ))
    }

    if (activeTab === 'channels') {
      const channels = node.channel_values || {}
      const keys = Object.keys(channels)
      if (keys.length === 0) {
        return (
          <div className="state-empty">
            <p>No channel values</p>
          </div>
        )
      }
      return keys.map((key) => (
        <div
          key={key}
          className="channel-item"
          onClick={() => onOpenModal(key, channels[key])}
        >
          <div className="channel-name">{key}</div>
          <div className="channel-preview">{truncate(safeStringify(channels[key]), 80)}</div>
        </div>
      ))
    }

    if (activeTab === 'metadata') {
      return (
        <>
          <div className="state-section">
            <div className="state-section-title">Metadata</div>
            <div className="state-json">{safeStringify(node.metadata, 2)}</div>
          </div>
          <div className="state-section">
            <div className="state-section-title">Updated Channels</div>
            <div className="state-json">{safeStringify(node.updated_channels, 2)}</div>
          </div>
        </>
      )
    }

    return null
  }, [node, activeTab, onOpenModal])

  return (
    <div className="state-panel">
      <div className="state-header">
        <h3>{node ? `[Step ${node.step}] ${node.node_name}` : 'Node State'}</h3>
        <div className="node-info">
          {node 
            ? `Checkpoint: ${node.checkpoint_id.substring(0, 16)}...`
            : 'Click a node in the graph to view its state'}
        </div>
      </div>

      <div className="state-tabs">
        {tabs.map(tab => (
          <div
            key={tab.id}
            className={`state-tab ${activeTab === tab.id ? 'active' : ''}`}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
          </div>
        ))}
      </div>

      <div className="state-content">
        {node ? (
          content
        ) : (
          <div className="state-empty">
            <div className="icon">📊</div>
            <p>Select a node to inspect its state</p>
          </div>
        )}
      </div>
    </div>
  )
}

export default StatePanel
