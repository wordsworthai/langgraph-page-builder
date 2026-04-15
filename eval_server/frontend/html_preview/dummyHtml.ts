/**
 * Placeholder HTML shown when no compiled content is available.
 * Used in the code editor preview panel before a section is loaded.
 * Uses full viewport width so it renders correctly in both desktop (1200px) and mobile (375px) modes.
 */
export const DUMMY_HTML = `
<div style="font-family: system-ui, -apple-system, sans-serif; padding: 2rem 2.5rem; min-height: 100%; box-sizing: border-box;">
  <div style="max-width: 800px; margin: 0 auto;">
    <h1 style="font-size: 2rem; color: #1a1a2e; margin: 0 0 0.5rem 0; line-height: 1.3;">Welcome to the Preview</h1>
    <p style="color: #4a5568; line-height: 1.5; margin-bottom: 1.5rem; font-size: 1rem;">
      Load a section from the code editor to see your template rendered here.
      Until then, this placeholder shows how the preview will look.
    </p>
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 1rem;">
      <div style="background: #f7fafc; padding: 1rem; border-radius: 8px; border: 1px solid #e2e8f0;">
        <h3 style="font-size: 0.95rem; color: #2d3748; margin: 0 0 0.25rem 0;">Hero</h3>
        <p style="font-size: 0.85rem; color: #718096; margin: 0;">Your hero section will appear here.</p>
      </div>
      <div style="background: #f7fafc; padding: 1rem; border-radius: 8px; border: 1px solid #e2e8f0;">
        <h3 style="font-size: 0.95rem; color: #2d3748; margin: 0 0 0.25rem 0;">Features</h3>
        <p style="font-size: 0.85rem; color: #718096; margin: 0;">Feature blocks go here.</p>
      </div>
      <div style="background: #f7fafc; padding: 1rem; border-radius: 8px; border: 1px solid #e2e8f0;">
        <h3 style="font-size: 0.95rem; color: #2d3748; margin: 0 0 0.25rem 0;">Footer</h3>
        <p style="font-size: 0.85rem; color: #718096; margin: 0;">Footer content here.</p>
      </div>
    </div>
    <p style="font-size: 0.8rem; color: #a0aec0; margin-top: 1.5rem;">
      Use the desktop/mobile toggle above to switch view modes.
    </p>
  </div>
</div>
`;
