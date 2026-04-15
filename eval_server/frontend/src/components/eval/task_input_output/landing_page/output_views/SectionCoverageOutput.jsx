import React from 'react'
import HTMLCompilationOutput from './components/HTMLCompilationOutput'
import FullOutputJSON from './components/FullOutputJSON'

function SectionCoverageOutput({ output, hasHtmlPreview = true, onViewPreview }) {
  if (!output) return null

  const htmlResults = output.html_compilation_results ?? output.raw_output?.html_compilation_results
  const hasHtml = htmlResults || output.s3_url || output.html_url

  if (!hasHtml) {
    return (
      <div className="eval-section output-section">
        <h3>📤 Output</h3>
        <div className="no-output">
          <p>No HTML compilation results found.</p>
          <p>The pipeline may still be running or encountered an error.</p>
        </div>
      </div>
    )
  }

  const outputWithHtml = { ...output, html_compilation_results: htmlResults, s3_url: output.s3_url ?? output.html_url }

  return (
    <div className="eval-section output-section">
      <h3>📤 Output</h3>
      <HTMLCompilationOutput
        output={outputWithHtml}
        hasHtmlPreview={hasHtmlPreview}
        onViewPreview={onViewPreview}
      />
      {htmlResults && <FullOutputJSON output={htmlResults} />}
    </div>
  )
}

export default SectionCoverageOutput
