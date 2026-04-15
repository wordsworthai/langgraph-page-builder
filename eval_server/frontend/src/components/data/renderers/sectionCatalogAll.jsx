import React from 'react'

function normalizeSections(result) {
  if (!result || !result.success) return []
  if (Array.isArray(result.result)) return result.result
  if (Array.isArray(result.result?.sections)) return result.result.sections
  return []
}

function SectionCatalogAllResult({ result }) {
  const sections = normalizeSections(result)

  if (!sections.length) {
    return <div className="data-debug-empty">No sections returned for this query.</div>
  }

  return (
    <div className="section-repo-grid">
      {sections.map((section, idx) => {
        const sectionId = section.section_id || section._id || `section_${idx}`
        const displayName = section.section_l1
          ? `${section.section_l0 || ''} - ${section.section_l1}`
          : section.section_l0 || sectionId
        const previewUrl = section.desktop_image_url

        return (
          <div key={sectionId} className="section-card">
            {previewUrl && (
              <div className="section-card-preview">
                <img src={previewUrl} alt="" />
              </div>
            )}
            <div className="section-card-body">
              <div className="section-card-name">{displayName}</div>
              <div className="section-card-id">{String(sectionId)}</div>
            </div>
          </div>
        )
      })}
    </div>
  )
}

export default SectionCatalogAllResult

