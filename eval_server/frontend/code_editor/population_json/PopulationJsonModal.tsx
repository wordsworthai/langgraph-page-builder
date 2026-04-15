import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import Editor from '@monaco-editor/react';

type TabId = 'population' | 'reference' | 'structure-diff';

/** Recursively collect leaf key paths from a settings object (no recursion into nested 'settings'). */
function collectSettingsKeys(obj: unknown, prefix: string): string[] {
  const keys: string[] = [];
  if (!obj || typeof obj !== 'object' || Array.isArray(obj)) return keys;
  for (const [k, v] of Object.entries(obj)) {
    const path = `${prefix}.${k}`;
    if (k === 'settings' && v && typeof v === 'object' && !Array.isArray(v)) {
      // Nested settings: go one level deeper, report keys at parent level for comparison
      keys.push(...collectSettingsKeys(v, prefix));
    } else {
      keys.push(path);
    }
  }
  return keys;
}

/** Detect if JSON is reference template format (section_id, settings.blocks object) vs population (blocks array). */
function isReferenceFormat(obj: Record<string, unknown>): boolean {
  if ('section_id' in obj) return true;
  const s = obj.settings;
  if (s && typeof s === 'object' && !Array.isArray(s)) {
    const inner = s as Record<string, unknown>;
    if (inner.blocks && typeof inner.blocks === 'object' && !Array.isArray(inner.blocks)) return true;
  }
  return false;
}

/** Extract structural keys for Population JSON: settings.* and blocks.<type>.settings.* */
function extractPopulationKeys(obj: unknown): { settings: string[]; blocks: string[] } {
  const settings: string[] = [];
  const blockKeysByType = new Map<string, Set<string>>();

  if (!obj || typeof obj !== 'object' || Array.isArray(obj)) return { settings, blocks: [] };
  const o = obj as Record<string, unknown>;

  if (o.settings && typeof o.settings === 'object') {
    settings.push(...collectSettingsKeys(o.settings, 'settings'));
  }

  if (Array.isArray(o.blocks)) {
    o.blocks.forEach((block: unknown) => {
      if (block && typeof block === 'object' && !Array.isArray(block)) {
        const b = block as Record<string, unknown>;
        const blockType = (b.type as string) ?? 'unknown';
        if (!blockKeysByType.has(blockType)) blockKeysByType.set(blockType, new Set());
        const keySet = blockKeysByType.get(blockType)!;
        if (b.settings && typeof b.settings === 'object') {
          const keys = collectSettingsKeys(b.settings, `blocks.${blockType}.settings`);
          keys.forEach((k) => keySet.add(k));
        }
      }
    });
  }

  const blocks = Array.from(blockKeysByType.values()).flatMap((s) => Array.from(s));
  return { settings, blocks };
}

/** Extract structural keys for Reference Template JSON: settings.* from settings.settings, blocks.<type>.settings.* from settings.blocks */
function extractReferenceKeys(obj: unknown): { settings: string[]; blocks: string[] } {
  const settings: string[] = [];
  const blocks: string[] = [];

  if (!obj || typeof obj !== 'object' || Array.isArray(obj)) return { settings, blocks };
  const o = obj as Record<string, unknown>;

  const s = o.settings;
  if (s && typeof s === 'object' && !Array.isArray(s)) {
    const inner = s as Record<string, unknown>;
    const config = inner.settings;
    if (config && typeof config === 'object') {
      settings.push(...collectSettingsKeys(config, 'settings'));
    }
    const blocksMap = inner.blocks;
    if (blocksMap && typeof blocksMap === 'object' && !Array.isArray(blocksMap)) {
      for (const [blockType, blockConfig] of Object.entries(blocksMap)) {
        if (blockConfig && typeof blockConfig === 'object' && !Array.isArray(blockConfig)) {
          const bc = blockConfig as Record<string, unknown>;
          if (bc.settings && typeof bc.settings === 'object') {
            blocks.push(...collectSettingsKeys(bc.settings, `blocks.${blockType}.settings`));
          }
        }
      }
    }
  }

  return { settings, blocks };
}

/** Extract structural keys, dispatching by format. */
function extractStructuralKeys(obj: unknown): { settings: string[]; blocks: string[] } {
  if (!obj || typeof obj !== 'object' || Array.isArray(obj)) return { settings: [], blocks: [] };
  return isReferenceFormat(obj as Record<string, unknown>)
    ? extractReferenceKeys(obj)
    : extractPopulationKeys(obj);
}

/** Diff two key arrays: onlyInA = in A but not B, onlyInB = in B but not A. */
function diffKeys(a: string[], b: string[]): { onlyInA: string[]; onlyInB: string[] } {
  const setB = new Set(b);
  const setA = new Set(a);
  return {
    onlyInA: a.filter((k) => !setB.has(k)),
    onlyInB: b.filter((k) => !setA.has(k)),
  };
}

interface StructureDiffTabProps {
  jsonContent: string;
  refJsonContent: string;
  refLoading: boolean;
  refError: string | null;
}

const StructureDiffTab: React.FC<StructureDiffTabProps> = ({
  jsonContent,
  refJsonContent,
  refLoading,
  refError,
}) => {
  const diffResult = useMemo(() => {
    if (refLoading || refError) return null;
    let pop: unknown;
    let ref: unknown;
    try {
      pop = JSON.parse(jsonContent);
    } catch {
      return { parseError: 'population' as const };
    }
    try {
      ref = JSON.parse(refJsonContent);
    } catch {
      return { parseError: 'reference' as const };
    }
    const popKeys = extractStructuralKeys(pop);
    const refKeys = extractStructuralKeys(ref);
    const settingsDiff = diffKeys(refKeys.settings, popKeys.settings);
    const blocksDiff = diffKeys(refKeys.blocks, popKeys.blocks);
    return {
      settings: settingsDiff,
      blocks: blocksDiff,
    };
  }, [jsonContent, refJsonContent, refLoading, refError]);

  if (refLoading) {
    return (
      <div style={{ padding: 24, color: 'var(--text-secondary)', fontSize: 13 }}>Loading…</div>
    );
  }
  if (refError) {
    return (
      <div style={{ padding: 24, color: 'var(--text-error, #f85149)', fontSize: 13 }}>
        {refError}
      </div>
    );
  }
  if (diffResult?.parseError === 'population') {
    return (
      <div style={{ padding: 24, color: 'var(--text-error, #f85149)', fontSize: 13 }}>
        Invalid JSON in Population JSON. Fix the JSON to view structure diff.
      </div>
    );
  }
  if (diffResult?.parseError === 'reference') {
    return (
      <div style={{ padding: 24, color: 'var(--text-error, #f85149)', fontSize: 13 }}>
        Invalid JSON in Reference Template JSON. Fix the JSON to view structure diff.
      </div>
    );
  }
  if (!diffResult) return null;

  const { settings, blocks } = diffResult;
  const hasRefOnly = settings.onlyInA.length > 0 || blocks.onlyInA.length > 0;
  const hasPopOnly = settings.onlyInB.length > 0 || blocks.onlyInB.length > 0;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16, flex: 1, minHeight: 0 }}>
      <div style={{ display: 'flex', gap: 16, flex: 1, minHeight: 0, overflow: 'auto' }}>
        <div
          style={{
            flex: 1,
            border: '1px solid var(--border-color, #333)',
            borderRadius: 4,
            padding: 12,
            background: 'var(--bg-secondary, #252526)',
            overflow: 'auto',
          }}
        >
          <h3 style={{ margin: '0 0 12px', fontSize: 14, color: 'var(--text-primary)' }}>
            In Reference only
          </h3>
          {!hasRefOnly ? (
            <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>No keys</div>
          ) : (
            <>
              {settings.onlyInA.length > 0 && (
                <div style={{ marginBottom: 8 }}>
                  <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginBottom: 4 }}>
                    settings
                  </div>
                  <ul style={{ margin: 0, paddingLeft: 18, fontSize: 12 }}>
                    {settings.onlyInA.map((k) => (
                      <li key={k}>{k}</li>
                    ))}
                  </ul>
                </div>
              )}
              {blocks.onlyInA.length > 0 && (
                <div>
                  <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginBottom: 4 }}>
                    blocks
                  </div>
                  <ul style={{ margin: 0, paddingLeft: 18, fontSize: 12 }}>
                    {blocks.onlyInA.map((k) => (
                      <li key={k}>{k}</li>
                    ))}
                  </ul>
                </div>
              )}
            </>
          )}
        </div>
        <div
          style={{
            flex: 1,
            border: '1px solid var(--border-color, #333)',
            borderRadius: 4,
            padding: 12,
            background: 'var(--bg-secondary, #252526)',
            overflow: 'auto',
          }}
        >
          <h3 style={{ margin: '0 0 12px', fontSize: 14, color: 'var(--text-primary)' }}>
            In Population only
          </h3>
          {!hasPopOnly ? (
            <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>No keys</div>
          ) : (
            <>
              {settings.onlyInB.length > 0 && (
                <div style={{ marginBottom: 8 }}>
                  <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginBottom: 4 }}>
                    settings
                  </div>
                  <ul style={{ margin: 0, paddingLeft: 18, fontSize: 12 }}>
                    {settings.onlyInB.map((k) => (
                      <li key={k}>{k}</li>
                    ))}
                  </ul>
                </div>
              )}
              {blocks.onlyInB.length > 0 && (
                <div>
                  <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginBottom: 4 }}>
                    blocks
                  </div>
                  <ul style={{ margin: 0, paddingLeft: 18, fontSize: 12 }}>
                    {blocks.onlyInB.map((k) => (
                      <li key={k}>{k}</li>
                    ))}
                  </ul>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
};

interface PopulationJsonModalProps {
  open: boolean;
  onClose: () => void;
  sectionId: string;
}

const PopulationJsonModal: React.FC<PopulationJsonModalProps> = ({ open, onClose, sectionId }) => {
  const [activeTab, setActiveTab] = useState<TabId>('population');
  const [jsonContent, setJsonContent] = useState<string>('{}');
  const [initialContent, setInitialContent] = useState<string>('{}');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const editorRef = useRef<any>(null);

  const [refJsonContent, setRefJsonContent] = useState<string>('{}');
  const [refLoading, setRefLoading] = useState(false);
  const [refError, setRefError] = useState<string | null>(null);
  const [refFetched, setRefFetched] = useState(false);
  const refEditorRef = useRef<any>(null);

  const fetchPopulationJson = useCallback(async () => {
    if (!sectionId) return;
    setLoading(true);
    setError(null);
    setSaveError(null);
    try {
      const res = await fetch('/api/sections/population-json', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ section_id: sectionId }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data.detail || `Failed to fetch: ${res.status}`);
      }
      const payload = data?.populated_template_json ?? {};
      const str = JSON.stringify(payload, null, 2);
      setJsonContent(str);
      setInitialContent(str);
      setHasUnsavedChanges(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load');
    } finally {
      setLoading(false);
    }
  }, [sectionId]);

  const fetchReferenceTemplateJson = useCallback(async () => {
    if (!sectionId) return;
    setRefLoading(true);
    setRefError(null);
    try {
      const res = await fetch('/api/sections/reference-template-json', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ section_id: sectionId }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data.detail || `Failed to fetch: ${res.status}`);
      }
      const payload = data?.reference_template_json ?? {};
      const str = JSON.stringify(payload, null, 2);
      setRefJsonContent(str);
      setRefFetched(true);
    } catch (e) {
      setRefError(e instanceof Error ? e.message : 'Failed to load');
    } finally {
      setRefLoading(false);
    }
  }, [sectionId]);

  useEffect(() => {
    if (open && sectionId) {
      setActiveTab('population');
      setRefFetched(false);
      fetchPopulationJson();
    }
  }, [open, sectionId, fetchPopulationJson]);

  useEffect(() => {
    if (
      open &&
      sectionId &&
      (activeTab === 'reference' || activeTab === 'structure-diff') &&
      !refFetched &&
      !refLoading
    ) {
      fetchReferenceTemplateJson();
    }
  }, [open, sectionId, activeTab, refFetched, refLoading, fetchReferenceTemplateJson]);

  useEffect(() => {
    if (!open) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [open, onClose]);

  const handleEditorChange = useCallback(
    (value: string | undefined) => {
      if (value === undefined) return;
      setJsonContent(value);
      setHasUnsavedChanges(value !== initialContent);
      setSaveError(null);
    },
    [initialContent]
  );

  const handleFormat = useCallback(() => {
    if (activeTab === 'population' && editorRef.current) {
      editorRef.current.trigger('format', 'editor.action.formatDocument', {});
    } else if (activeTab === 'reference' && refEditorRef.current) {
      refEditorRef.current.trigger('format', 'editor.action.formatDocument', {});
    }
  }, [activeTab]);

  const handleSave = useCallback(async () => {
    if (!sectionId || saving) return;
    setSaveError(null);
    let parsed: object;
    try {
      parsed = JSON.parse(jsonContent);
    } catch (e) {
      setSaveError(e instanceof Error ? e.message : 'Invalid JSON');
      return;
    }
    setSaving(true);
    try {
      const res = await fetch('/api/sections/population-json/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          section_id: sectionId,
          populated_template_json: parsed,
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data.detail || `Save failed: ${res.status}`);
      }
      setInitialContent(jsonContent);
      setHasUnsavedChanges(false);
    } catch (e) {
      setSaveError(e instanceof Error ? e.message : 'Failed to save');
    } finally {
      setSaving(false);
    }
  }, [sectionId, jsonContent, saving]);

  if (!open) return null;

  const showSaveButton = activeTab === 'population';

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 100,
        background: 'rgba(0,0,0,0.6)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 16,
        boxSizing: 'border-box',
      }}
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div
        style={{
          background: 'var(--bg-secondary, #252526)',
          borderRadius: 8,
          border: '1px solid var(--border-color, #333)',
          width: '92%',
          height: '92%',
          maxWidth: 'calc(100vw - 32px)',
          maxHeight: 'calc(100vh - 32px)',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '12px 16px',
            borderBottom: '1px solid var(--border-color, #333)',
          }}
        >
          <h2 style={{ margin: 0, fontSize: 16, fontWeight: 600, color: 'var(--text-primary)' }}>
            Population JSON
          </h2>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            {showSaveButton && saveError && (
              <span style={{ fontSize: 12, color: 'var(--text-error, #f87171)' }}>{saveError}</span>
            )}
            {(activeTab === 'population' || activeTab === 'reference') && (
              <button
                type="button"
                onClick={handleFormat}
                style={{
                  padding: '4px 10px',
                  fontSize: 12,
                  cursor: 'pointer',
                  background: 'var(--bg-tertiary)',
                  border: '1px solid var(--border-color)',
                  borderRadius: 4,
                  color: 'var(--text-primary)',
                }}
              >
                Format
              </button>
            )}
            {showSaveButton && (
              <button
                type="button"
                onClick={handleSave}
                disabled={!hasUnsavedChanges || saving}
                style={{
                  padding: '4px 10px',
                  fontSize: 12,
                  cursor: !hasUnsavedChanges || saving ? 'not-allowed' : 'pointer',
                  background: hasUnsavedChanges && !saving ? 'var(--accent-blue, #2563eb)' : 'var(--bg-tertiary)',
                  border: '1px solid var(--border-color)',
                  borderRadius: 4,
                  color: hasUnsavedChanges && !saving ? 'white' : 'var(--text-secondary)',
                }}
              >
                {saving ? 'Saving…' : hasUnsavedChanges ? 'Save' : 'No changes'}
              </button>
            )}
            <button
              type="button"
              onClick={onClose}
              style={{
                padding: '4px 10px',
                fontSize: 12,
                cursor: 'pointer',
                background: 'var(--bg-tertiary)',
                border: '1px solid var(--border-color)',
                borderRadius: 4,
                color: 'var(--text-primary)',
              }}
            >
              Close
            </button>
          </div>
        </div>
        <div
          style={{
            display: 'flex',
            gap: 0,
            borderBottom: '1px solid var(--border-color, #333)',
            padding: '0 16px',
          }}
        >
          {(['population', 'reference', 'structure-diff'] as const).map((tabId) => (
            <button
              key={tabId}
              type="button"
              onClick={() => setActiveTab(tabId)}
              style={{
                padding: '10px 16px',
                fontSize: 13,
                fontWeight: 500,
                cursor: 'pointer',
                background: 'none',
                border: 'none',
                borderBottom: activeTab === tabId
                  ? '2px solid var(--accent-blue, #007acc)'
                  : '2px solid transparent',
                color: activeTab === tabId
                  ? 'var(--text-primary)'
                  : 'var(--text-secondary)',
                marginBottom: -1,
              }}
            >
              {tabId === 'population'
                ? 'Population JSON'
                : tabId === 'reference'
                  ? 'Reference Template JSON'
                  : 'Structure Diff'}
            </button>
          ))}
        </div>
        <div
          style={{
            flex: 1,
            minHeight: 0,
            overflow: 'hidden',
            display: 'flex',
            flexDirection: 'column',
            padding: 16,
          }}
        >
          {activeTab === 'population' && (
            <>
              {loading && (
                <div style={{ padding: 24, color: 'var(--text-secondary)', fontSize: 13 }}>
                  Loading…
                </div>
              )}
              {error && !loading && (
                <div style={{ padding: 24, color: 'var(--text-error, #f85149)', fontSize: 13 }}>
                  {error}
                </div>
              )}
              {!loading && !error && (
                <div style={{ flex: 1, minHeight: 0, border: '1px solid var(--border-color, #333)', borderRadius: 4, background: '#1e1e1e' }}>
                  <Editor
                    height="100%"
                    language="json"
                    theme="vs-dark"
                    value={jsonContent}
                    onChange={handleEditorChange}
                    onMount={(editor) => {
                      editorRef.current = editor;
                    }}
                    options={{
                      readOnly: false,
                      minimap: { enabled: false },
                      wordWrap: 'on',
                      formatOnPaste: true,
                      fontFamily: 'Menlo, Monaco, "Courier New", monospace',
                      fontSize: 13,
                    }}
                  />
                </div>
              )}
            </>
          )}
          {activeTab === 'reference' && (
            <>
              {refLoading && (
                <div style={{ padding: 24, color: 'var(--text-secondary)', fontSize: 13 }}>
                  Loading…
                </div>
              )}
              {refError && !refLoading && (
                <div style={{ padding: 24, color: 'var(--text-error, #f85149)', fontSize: 13 }}>
                  {refError}
                </div>
              )}
              {!refLoading && !refError && (
                <div style={{ flex: 1, minHeight: 0, border: '1px solid var(--border-color, #333)', borderRadius: 4, background: '#1e1e1e' }}>
                  <Editor
                    height="100%"
                    language="json"
                    theme="vs-dark"
                    value={refJsonContent}
                    onChange={(v) => v !== undefined && setRefJsonContent(v)}
                    onMount={(editor) => {
                      refEditorRef.current = editor;
                    }}
                    options={{
                      readOnly: true,
                      minimap: { enabled: false },
                      wordWrap: 'on',
                      fontFamily: 'Menlo, Monaco, "Courier New", monospace',
                      fontSize: 13,
                    }}
                  />
                </div>
              )}
            </>
          )}
          {activeTab === 'structure-diff' && (
            <StructureDiffTab
              jsonContent={jsonContent}
              refJsonContent={refJsonContent}
              refLoading={refLoading}
              refError={refError}
            />
          )}
        </div>
      </div>
    </div>
  );
};

export default PopulationJsonModal;
