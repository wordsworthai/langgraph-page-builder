/**
 * Extract display info from a run (task-specific for landing_page pipeline).
 * Replaces backend run_with_frontend_shape - extraction from task_details/inputs.
 */
export function getRunDisplayInfo(run) {
  if (!run || typeof run !== 'object') {
    return { businessId: null, websiteIntention: null }
  }

  const td = run.task_details || {}
  let websiteIntention = td.website_intention ?? run.website_intention ?? null

  if (!websiteIntention && run.inputs) {
    for (const key of ['template_selection_input', 'landing_page_input']) {
      const wc = run.inputs[key]?.website_context || {}
      if (wc.website_intention) {
        websiteIntention = wc.website_intention
        break
      }
    }
  }

  const businessId = td.business_id ?? run.business_id ?? null

  return { businessId, websiteIntention }
}
