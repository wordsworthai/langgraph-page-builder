/**
 * Build display output from raw checkpoint history, last checkpoint, and eval_output.
 * Pipeline-specific: post_process, template, resolved_template_recommendations (landing_page builder).
 */
function toDict(obj) {
  if (obj == null) return {}
  if (typeof obj === 'object' && !Array.isArray(obj)) return obj
  if (typeof obj === 'object' && obj.model_dump) return obj.model_dump()
  return {}
}

function extractHtmlResultsFromHistory(history) {
  if (!Array.isArray(history)) return null
  for (let i = history.length - 1; i >= 0; i--) {
    const ckpt = history[i]
    const channelValues = ckpt?.channel_values || {}
    let postProcess = toDict(channelValues.post_process)
    let htmlResults = postProcess.html_compilation_results
    if (htmlResults && typeof htmlResults === 'object') return htmlResults
    const writes = ckpt?.writes || []
    for (const w of writes) {
      if (w.channel === 'post_process' && w.value) {
        postProcess = toDict(w.value)
        htmlResults = postProcess.html_compilation_results
        if (htmlResults && typeof htmlResults === 'object') return htmlResults
      }
    }
  }
  return null
}

function loadTemplatesFromChannelValues(channelValues) {
  if (!channelValues || typeof channelValues !== 'object') return []
  let templates = channelValues.refined_templates || channelValues.templates || []
  if (templates.length > 0) return templates
  const templateChannel = toDict(channelValues.template)
  templates = templateChannel.refined_templates || templateChannel.templates || []
  if (templates.length > 0) return templates
  const resolved = channelValues.resolved_template_recommendations || []
  if (resolved.length > 0) {
    const first = toDict(resolved[0])
    const sectionMappings = first.section_mappings || []
    return [{
      template_id: first.template_id,
      template_name: first.template_name,
      section_info: sectionMappings.map(m => ({
        section_id: m?.section_id,
        section_l0: m?.section_l0,
        section_l1: m?.section_l1
      })),
      section_mappings: sectionMappings
    }]
  }
  return []
}

/**
 * Build display output from history, last_checkpoint, and eval_output.
 */
export function buildOutputFromRaw(history, lastCheckpoint, evalOutput) {
  const output = {}
  const lastCv = lastCheckpoint?.channel_values || {}
  const lastCvCopy = { ...lastCv }

  for (const w of lastCheckpoint?.writes || []) {
    if (w.channel && w.value != null) lastCvCopy[w.channel] = w.value
  }

  const htmlResults = extractHtmlResultsFromHistory(history)
  if (htmlResults) {
    output.html_compilation_results = htmlResults
    output.s3_url = htmlResults.compiled_html_s3_url
    output.local_path = htmlResults.compiled_html_path
  }

  const keys = [
    'resolved_template_recommendations',
    'autopopulation_results',
    'autopopulation_langgraph_state',
    'input',
    'data',
    'template',
    'post_process'
  ]
  for (const key of keys) {
    if (key in lastCvCopy) output[key] = lastCvCopy[key]
  }

  const templates = loadTemplatesFromChannelValues(lastCvCopy)
  if (templates.length > 0) output.templates = templates
  output.section_mapped_recommendations = output.resolved_template_recommendations

  const inpLast = lastCvCopy.input
  if (inpLast && typeof inpLast === 'object') {
    output.business_name = inpLast.business_name
    output.sector = inpLast.sector
  }
  const data = lastCvCopy.data
  if (data && typeof data === 'object') {
    output.sector = output.sector ?? data.derived_sector
  }

  if (evalOutput && typeof evalOutput === 'object') {
    if (!output.s3_url && evalOutput.html_url) {
      output.s3_url = evalOutput.html_url
      output.html_url = evalOutput.html_url
    }
    const raw = evalOutput.raw_output || {}
    if (!output.html_compilation_results && raw.html_compilation_results) {
      output.html_compilation_results = raw.html_compilation_results
      if (!output.s3_url) {
        output.s3_url = raw.html_compilation_results?.compiled_html_s3_url
      }
    }
    if (!output.templates && raw.templates) output.templates = raw.templates
    if (!output.section_mapped_recommendations && raw.section_mapped_recommendations) {
      output.section_mapped_recommendations = raw.section_mapped_recommendations
    }
  }

  return output
}
