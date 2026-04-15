import { useContext } from 'react';
import { usePreviewContext } from '../code_editor/PreviewContext';

/**
 * Returns compiled HTML for the preview panel.
 * Reads from PreviewContext when available (e.g. in code editor layout).
 * Falls back to empty string when outside provider - ready for future
 * code-to-HTML pipeline wiring.
 */
export function useCompiledHtml(): { compiledHtml: string } {
  const ctx = usePreviewContext();
  const compiledHtml = ctx?.compiledHtml ?? '';
  return { compiledHtml };
}
