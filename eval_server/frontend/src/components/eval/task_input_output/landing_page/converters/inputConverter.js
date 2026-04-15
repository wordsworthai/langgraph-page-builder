/**
 * Extract raw input and display summary from first checkpoint.
 * Pipeline-specific: __start__, input, preset_sections_input (landing_page builder).
 */
function toDict(obj) {
  if (obj == null) return {}
  if (typeof obj === 'object' && !Array.isArray(obj)) return obj
  if (typeof obj === 'object' && obj.model_dump) return obj.model_dump()
  return {}
}

export function extractInputFromFirstCheckpoint(firstCheckpoint) {
  if (!firstCheckpoint || typeof firstCheckpoint !== 'object') {
    return { raw: {}, summary: {} }
  }

  const inputState = firstCheckpoint.channel_values || {}
  const inputData = inputState.__start__ ?? inputState
  const inputDataObj = toDict(inputData)

  let inp = inputDataObj.input ?? inputDataObj
  if (inp == null || typeof inp !== 'object') inp = inputDataObj

  const psi = inputDataObj.preset_sections_input
  if (psi && typeof psi === 'object') {
    inp = { ...inp, preset_sections_input: psi }
  }

  const summary = rawToSummary(inp)
  return { raw: inp, summary }
}

/**
 * Convert raw input dict to display summary.
 * Task-specific for landing_page pipeline (website_context, brand_context, preset_sections_input).
 */
function rawToSummary(raw) {
  if (!raw || typeof raw !== 'object') return {}

  const psi = raw.preset_sections_input || {}
  const wc = raw.website_context || psi.website_context || {}
  const bc = raw.brand_context || psi.brand_context || {}
  const gc = raw.generic_context || psi.generic_context || {}
  const ec = raw.external_data_context || psi.external_data_context || {}
  const ecSafe = typeof ec === 'object' ? ec : {}

  return {
    business_name: raw.business_name ?? psi.business_name ?? null,
    query: gc.query ?? raw.query ?? null,
    website_intention: wc.website_intention ?? raw.website_intention ?? null,
    website_tone: wc.website_tone ?? raw.website_tone ?? null,
    sector: gc.sector ?? raw.sector ?? null,
    yelp_url: ecSafe.yelp_url ?? raw.yelp_url ?? null,
    palette: bc.palette ?? raw.palette ?? null,
    font_family: bc.font_family ?? raw.font_family ?? null,
    execution_config: raw.execution_config ?? null
  }
}
