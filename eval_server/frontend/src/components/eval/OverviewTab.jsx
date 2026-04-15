import React from 'react'
import { InputSection, OutputSection } from './task_input_output'

function OverviewTab({ input, output, steps, taskType, taskConfig, config, run, onViewPreview }) {
  return (
    <div className="eval-content">
      <InputSection input={input} taskType={taskType} config={config} run={run} />
      <OutputSection
        output={output}
        taskType={taskType}
        onViewPreview={onViewPreview}
      />
    </div>
  )
}

export default OverviewTab
