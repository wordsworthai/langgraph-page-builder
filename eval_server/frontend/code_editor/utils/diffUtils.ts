import type { SectionData } from '../types/editor';

export interface FileForDiff {
  path: string;
  content: string;
  language: string;
}

/**
 * Extract flat list of files from SectionData for diff comparison.
 * Matches the structure from EditorContext.convertSectionDataToFiles.
 */
export function getFilesForDiff(sectionData: SectionData): FileForDiff[] {
  const { definition, content } = sectionData;
  const files: FileForDiff[] = [];

  const sectionLiquidContent = `${content.liquid_file_content}

{% schema %}
${JSON.stringify(content.liquid_schema, null, 2)}
{% endschema %}`;

  files.push({
    path: `sections/${definition.section_filename}`,
    content: sectionLiquidContent,
    language: 'liquid',
  });

  Object.entries(content.snippets).forEach(([filename, snippetData]) => {
    const snippetContent = snippetData?.value ?? '';
    const snippetFilename = filename.endsWith('.liquid') ? filename : `${filename}.liquid`;
    files.push({
      path: `snippets/${snippetFilename}`,
      content: snippetContent,
      language: 'liquid',
    });
  });

  Object.entries(content.css_files).forEach(([filename, fileData]) => {
    const cssContent = fileData?.value ?? '';
    const cssFileName = filename.endsWith('.css') ? filename : `${filename}.css`;
    files.push({
      path: `assets/${cssFileName}`,
      content: cssContent,
      language: 'css',
    });
  });

  Object.entries(content.js_files).forEach(([filename, fileData]) => {
    const jsContent = fileData?.value ?? '';
    const jsFileName = filename.endsWith('.js') ? filename : `${filename}.js`;
    files.push({
      path: `assets/${jsFileName}`,
      content: jsContent,
      language: 'javascript',
    });
  });

  if (content.section_custom_css && content.section_custom_css.length > 0) {
    const customCssContent = content.section_custom_css.join('\n\n');
    const customCssName = `${definition.section_name.replace(/\s+/g, '_').toLowerCase()}_custom.css`;
    files.push({
      path: `assets/${customCssName}`,
      content: customCssContent,
      language: 'css',
    });
  }

  return files;
}
