import type { SectionData } from '../types/editor';

/**
 * Converts SectionData back to section_mapping (Section model format) for the compile API.
 */
export function sectionDataToSectionMapping(sectionData: SectionData): Record<string, unknown> {
  return {
    definition: sectionData.definition,
    content: sectionData.content,
    metadata: sectionData.metadata,
    usage: sectionData.usage,
    reference_template_json: sectionData.reference_template_json,
  };
}

/**
 * Converts backend section_mapping (Section.model_dump()) to frontend SectionData.
 * Ensures required fields exist and have correct shape for Monaco editor.
 */
export function sectionMappingToSectionData(sectionMapping: Record<string, unknown>): SectionData {
  const definition = (sectionMapping.definition ?? {}) as SectionData['definition'];
  const content = (sectionMapping.content ?? {}) as Record<string, unknown>;

  return {
    definition: {
      shop_url: definition.shop_url ?? '',
      theme_id: definition.theme_id ?? '',
      section_name: definition.section_name ?? '',
      section_filename: definition.section_filename ?? '',
    },
    content: {
      liquid_file_content: (content.liquid_file_content as string) ?? '',
      liquid_schema: content.liquid_schema ?? {},
      css_files: (content.css_files as Record<string, { key?: string; content_type?: string; value?: string; public_url?: string | null }>) ?? {},
      js_files: (content.js_files as Record<string, { key?: string; content_type?: string; value?: string; public_url?: string | null }>) ?? {},
      snippets: (content.snippets as Record<string, { key?: string; content_type?: string; value?: string; public_url?: string | null }>) ?? {},
      section_custom_css: Array.isArray(content.section_custom_css) ? (content.section_custom_css as string[]) : [],
    },
    metadata: sectionMapping.metadata,
    usage: sectionMapping.usage,
    reference_template_json: sectionMapping.reference_template_json,
  };
}
