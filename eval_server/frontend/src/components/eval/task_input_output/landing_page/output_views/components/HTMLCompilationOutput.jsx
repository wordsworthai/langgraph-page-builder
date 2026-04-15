import React from 'react'

function HTMLCompilationOutput({ output, hasHtmlPreview = true, onViewPreview }) {
  const s3Url = output?.s3_url ?? output?.html_url
  if (!output?.html_compilation_results && !s3Url) return null

  return (
    <>
      <div className="output-links">
        {s3Url && (
          <a
            href={s3Url}
            target="_blank"
            rel="noopener noreferrer"
            className="btn-primary"
          >
            🌐 Open Generated HTML
          </a>
        )}
        {hasHtmlPreview && (
          <button
            className="btn-secondary"
            onClick={onViewPreview}
          >
            View Preview →
          </button>
        )}
      </div>
      {output.local_path && (
        <div className="local-path">
          <label>Local Path:</label>
          <code>{output.local_path}</code>
        </div>
      )}
    </>
  )
}

export default HTMLCompilationOutput
