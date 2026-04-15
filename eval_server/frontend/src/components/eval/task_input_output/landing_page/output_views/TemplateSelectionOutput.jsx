import React from 'react'
import HTMLCompilationOutput from './components/HTMLCompilationOutput'
import OutputCard from './components/OutputCard'
import FullOutputJSON from './components/FullOutputJSON'

function TemplateSelectionOutput({ output, hasHtmlPreview = true, onViewPreview }) {
  if (!output) return null

  const templates = output.templates ?? output.raw_output?.templates
  const sectionMapped = output.section_mapped_recommendations ?? output.resolved_template_recommendations
  const hasResults = output.html_compilation_results || output.s3_url || output.html_url || templates || sectionMapped

  if (!hasResults) {
    return (
      <div className="eval-section output-section">
        <h3>📤 Output</h3>
        <div className="no-output">
          <p>No template selection results found.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="eval-section output-section">
      <h3>📤 Output</h3>

      {(output.html_compilation_results || output.s3_url || output.html_url) && (
        <HTMLCompilationOutput
          output={output}
          hasHtmlPreview={hasHtmlPreview}
          onViewPreview={onViewPreview}
        />
      )}

      {(templates || sectionMapped) && (
        <div className="output-cards">
          {templates && (
            <OutputCard
              label="Templates"
              value={templates}
              isCollapsible
              fullWidth
              summary={`View Templates (${Array.isArray(templates) ? templates.length : 'N/A'})`}
            />
          )}
          {sectionMapped && (
            <OutputCard
              label="Section Mapped Recommendations"
              value={sectionMapped}
              isCollapsible
              fullWidth
            />
          )}
        </div>
      )}

      {(output.html_compilation_results || output.raw_output?.html_compilation_results) && (
        <FullOutputJSON output={output.html_compilation_results ?? output.raw_output?.html_compilation_results} />
      )}
    </div>
  )
}

export default TemplateSelectionOutput
