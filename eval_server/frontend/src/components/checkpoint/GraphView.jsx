import React, { useEffect, useRef, useCallback, useMemo } from 'react'
import { Network } from 'vis-network'
import { DataSet } from 'vis-data'

// Color palette for nodes - visually distinct colors
const NODE_COLOR_PALETTE = [
  '#58a6ff', // blue
  '#3fb950', // green
  '#a371f7', // purple
  '#f85149', // red
  '#d29922', // orange
  '#db61a2', // pink
  '#79c0ff', // light blue
  '#7ee787', // light green
  '#d2a8ff', // light purple
  '#ffa657', // light orange
  '#56d4dd', // cyan
  '#f778ba', // magenta
]

// Simple string hash function for consistent color assignment
function hashString(str) {
  let hash = 0
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i)
    hash = ((hash << 5) - hash) + char
    hash = hash & hash // Convert to 32bit integer
  }
  return Math.abs(hash)
}

// Get consistent color for a node based on its name
function getNodeColor(nodeName) {
  if (!nodeName) return '#8b949e'
  
  // Use the base node name (strip prefixes like index numbers)
  const baseName = nodeName.replace(/^\[\d+\]\s*/, '').toLowerCase()
  
  // Special cases for common structural nodes
  if (baseName === '__start__' || baseName === 'start') return '#3fb950'
  if (baseName === '__end__' || baseName === 'end') return '#f85149'
  if (baseName === '__input__' || baseName === 'input') return '#3fb950'
  if (baseName === 'loop') return '#d29922' // Fan-out entry (orange)
  if (baseName.startsWith('fanout')) return '#d29922' // Fan-out node (orange)
  
  // Hash the name to get consistent color from palette
  const colorIndex = hashString(baseName) % NODE_COLOR_PALETTE.length
  return NODE_COLOR_PALETTE[colorIndex]
}

// Get display label for a node - prioritize actual node_name over generic labels
function getNodeDisplayLabel(node, index) {
  // Priority: node_name > label > fallback
  const actualName = node.node_name || node.label || `Node ${index}`
  
  // If label is generic (like "loop"), prefer node_name
  const genericLabels = ['loop', 'node', 'step', '__start__', '__end__']
  const label = node.label?.toLowerCase()
  
  if (label && genericLabels.includes(label) && node.node_name && node.node_name !== label) {
    return `[${index}] ${node.node_name}`
  }
  
  return `[${index}] ${actualName}`
}

function GraphView({ data, loading, error, onNodeSelect, onNodeDeselect }) {
  const containerRef = useRef(null)
  const networkRef = useRef(null)
  const nodeDataMapRef = useRef({})

  const renderGraph = useCallback(() => {
    if (!data || !containerRef.current) return

    // Clean up existing network
    if (networkRef.current) {
      networkRef.current.destroy()
      networkRef.current = null
    }

    // Build node data map
    nodeDataMapRef.current = {}
    data.nodes.forEach(node => {
      nodeDataMapRef.current[node.id] = node.data
    })

    // Create vis.js nodes with proper labels
    const visNodes = data.nodes.map((node, index) => {
      const displayLabel = getNodeDisplayLabel(node, index)
      const colorSource = node.node_name || node.label || ''
      
      return {
        id: node.id,
        label: displayLabel,
        level: index,
        color: {
          background: getNodeColor(colorSource),
          border: '#30363d',
          highlight: {
            background: '#58a6ff',
            border: '#58a6ff'
          }
        },
        font: {
          color: '#e6edf3',
          size: 12,
          face: 'JetBrains Mono, monospace'
        },
        shape: 'box',
        margin: 10,
        // Store original data for tooltip/inspection
        title: `Node: ${node.node_name || 'unknown'}\nCheckpoint: ${node.id?.substring(0, 16) || 'N/A'}...`
      }
    })

    const visEdges = data.edges.map(edge => ({
      from: edge.from,
      to: edge.to,
      arrows: 'to',
      color: {
        color: '#30363d',
        highlight: '#58a6ff'
      },
      smooth: {
        type: 'cubicBezier',
        forceDirection: 'vertical'
      }
    }))

    const nodes = new DataSet(visNodes)
    const edges = new DataSet(visEdges)

    const options = {
      layout: {
        hierarchical: {
          enabled: true,
          direction: 'UD',
          sortMethod: 'directed',
          levelSeparation: 100,
          nodeSpacing: 200,
          treeSpacing: 200,
          blockShifting: true,
          edgeMinimization: true
        }
      },
      physics: {
        enabled: false
      },
      interaction: {
        hover: true,
        selectConnectedEdges: true
      },
      nodes: {
        borderWidth: 2,
        borderWidthSelected: 3
      },
      edges: {
        width: 2
      }
    }

    try {
      networkRef.current = new Network(containerRef.current, { nodes, edges }, options)

      networkRef.current.on('selectNode', (params) => {
        if (params.nodes.length > 0) {
          const nodeId = params.nodes[0]
          const nodeData = nodeDataMapRef.current[nodeId]
          if (nodeData) {
            onNodeSelect(nodeData)
          }
        }
      })

      networkRef.current.on('deselectNode', () => {
        onNodeDeselect()
      })

      networkRef.current.once('stabilized', () => {
        networkRef.current.fit()
      })
    } catch (err) {
      console.error('Error creating network:', err)
    }
  }, [data, onNodeSelect, onNodeDeselect])

  useEffect(() => {
    renderGraph()
    
    return () => {
      if (networkRef.current) {
        networkRef.current.destroy()
        networkRef.current = null
      }
    }
  }, [renderGraph])

  if (loading) {
    return (
      <div className="graph-container">
        <div className="loading">Loading checkpoints</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="graph-container">
        <div className="error-state">Error: {error}</div>
      </div>
    )
  }

  if (!data) {
    return (
      <div className="graph-container">
        <div className="empty-state">
          <div className="icon">🔗</div>
          <p>Select a thread from the left panel to visualize its execution graph</p>
        </div>
      </div>
    )
  }

  return (
    <div className="graph-container" ref={containerRef} />
  )
}

export default GraphView
