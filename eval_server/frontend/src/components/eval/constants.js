export const DEVICE_PRESETS = {
  desktop: { width: 1440, height: 900, label: '💻 Desktop' },
  mobile: { width: 375, height: 812, label: '📱 Mobile' }
}

/**
 * Task type config - centralized so changes are localized.
 * Task-agnostic styling (single badge color) and preview visibility logic.
 */
export const TASK_CONFIG = {
  /** Single badge style for all task types */
  badgeStyle: { bg: '#2a1a3a', color: '#a78bfa', short: 'EV' },

  /** Task types that show the HTML Preview tab */
  taskTypesWithHtmlPreview: ['template_selection', 'landing_page', 'section_coverage', 'color_palette', 'curated_pages'],

  /** Legacy alias: full -> landing_page */
  normalizeTaskType: (taskType) => (taskType === 'full' ? 'landing_page' : taskType),

  /** Whether this task type shows HTML preview */
  hasHtmlPreview: (taskType) => {
    const effective = TASK_CONFIG.normalizeTaskType(taskType)
    return TASK_CONFIG.taskTypesWithHtmlPreview.includes(effective)
  }
}
