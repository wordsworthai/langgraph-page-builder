import { TASK_CONFIG } from '../../../constants'
import { extractInputFromFirstCheckpoint } from './inputConverter'
import { buildOutputFromRaw } from './outputConverter'

/**
 * Convert raw API response to display-ready shape for the eval UI.
 * API returns: first_checkpoint, last_checkpoint, history, eval_output, steps
 * @param {string} taskType - e.g. 'landing_page', 'template_selection', 'section_coverage'
 * @param {object} apiResponse - Raw API response
 * @returns {object} { input: { summary, full }, output, steps, ... }
 */
export function convertRunSummary(taskType, apiResponse) {
  if (!apiResponse) return null

  const effectiveTaskType = TASK_CONFIG.normalizeTaskType(taskType || '')
  const firstCheckpoint = apiResponse.first_checkpoint
  const lastCheckpoint = apiResponse.last_checkpoint
  const history = apiResponse.history ?? []
  const evalOutput = apiResponse.eval_output ?? null

  let input = { summary: {}, full: {} }
  let output = {}

  if (['landing_page', 'template_selection', 'section_coverage', 'color_palette', 'curated_pages'].includes(effectiveTaskType)) {
    const inputResult = extractInputFromFirstCheckpoint(firstCheckpoint)
    input = { summary: inputResult.summary, full: inputResult.raw }
    output = buildOutputFromRaw(history, lastCheckpoint, evalOutput)
  } else {
    if (firstCheckpoint?.channel_values) {
      const inputState = firstCheckpoint.channel_values
      const inputData = inputState.__start__ ?? inputState
      input.full = inputData?.input ?? inputData ?? {}
      input.summary = input.full && typeof input.full === 'object' ? { ...input.full } : {}
    }
    output = buildOutputFromRaw(history, lastCheckpoint, evalOutput)
  }

  return {
    ...apiResponse,
    input,
    output,
    steps: apiResponse.steps ?? []
  }
}
