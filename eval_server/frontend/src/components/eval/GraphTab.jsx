import React from 'react'
import GraphView from '../checkpoint/GraphView'
import StatePanel from '../checkpoint/StatePanel'

function GraphTab({ checkpointData, loadingCheckpoints, selectedNode, onNodeSelect, onNodeDeselect, onOpenModal }) {
  return (
    <div className="eval-graph-container">
      <div className="eval-graph-main">
        <GraphView
          data={checkpointData}
          loading={loadingCheckpoints}
          error={null}
          onNodeSelect={onNodeSelect}
          onNodeDeselect={onNodeDeselect}
        />
      </div>
      <div className="eval-graph-panel">
        <StatePanel node={selectedNode} onOpenModal={onOpenModal} />
      </div>
    </div>
  )
}

export default GraphTab
