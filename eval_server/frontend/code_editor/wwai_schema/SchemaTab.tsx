import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { HotTable } from '@handsontable/react';
import { SuccessMessage, ErrorMessage } from '../utils/notification';
import type { CellChange, ChangeSource } from 'handsontable/common';
import { registerAllModules } from 'handsontable/registry';
import 'handsontable/dist/handsontable.full.min.css';
import './handsontable-dark.css';

interface SchemaTabProps {
  sectionId: string;
}

interface SchemaData {
  schema?: Record<string, unknown>[];
}

/** Columns to hide from display. Data kept internally for edit/save. */
const HIDDEN_COLUMNS = new Set([
  'section_liquid_name',
  'content_from_product_object',
  'html_code_label',
  'content_fill_phase',
  'content_fill_phase_labels',
  'background_color_source',
  'styling_semantic_name',
]);

const SchemaTab: React.FC<SchemaTabProps> = ({ sectionId }) => {
  const [fullSchema, setFullSchema] = useState<Record<string, unknown>[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  useEffect(() => {
    registerAllModules();
  }, []);

  useEffect(() => {
    if (!sectionId) return;
    setLoading(true);
    setError(null);
    setSaveError(null);
    setHasUnsavedChanges(false);
    fetch('/api/sections/schema', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ section_id: sectionId }),
    })
      .then((res) => {
        if (!res.ok) throw new Error(res.status === 404 ? 'Schema not found' : `Failed to fetch: ${res.status}`);
        return res.json();
      })
      .then((data: SchemaData) => {
        if (data?.schema && Array.isArray(data.schema)) {
          setFullSchema(data.schema.map((row) => ({ ...row })));
        } else {
          setFullSchema([]);
        }
      })
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed to load'))
      .finally(() => setLoading(false));
  }, [sectionId]);

  const { headers, dataRows } = useMemo(() => {
    if (!fullSchema.length) return { headers: [] as string[], dataRows: [] as string[][] };
    const firstKeys = Object.keys(fullSchema[0]);
    const allKeys = new Set<string>(firstKeys);
    fullSchema.forEach((el) => Object.keys(el).forEach((k) => allKeys.add(k)));
    const allHeaders = firstKeys.concat(Array.from(allKeys).filter((k) => !firstKeys.includes(k)));
    const visibleHeaders = allHeaders.filter((h) => !HIDDEN_COLUMNS.has(h));
    const rows = fullSchema.map((element) =>
      visibleHeaders.map((header) => {
        const val = element[header];
        if (val === undefined || val === null) return '';
        if (typeof val === 'object') return JSON.stringify(val);
        return String(val);
      })
    );
    return { headers: visibleHeaders, dataRows: rows };
  }, [fullSchema]);

  const handleAfterChange = useCallback(
    (changes: CellChange[] | null, source: ChangeSource) => {
      if (source === 'loadData' || !changes || changes.length === 0) return;
      setFullSchema((prev) => {
        const next = prev.map((row) => ({ ...row }));
        for (const [rowIndex, col, , newVal] of changes) {
          if (rowIndex < 0 || rowIndex >= next.length) continue;
          const header = typeof col === 'number' ? headers[col] : typeof col === 'string' ? col : null;
          if (!header) continue;
          next[rowIndex] = { ...next[rowIndex], [header]: newVal ?? '' };
        }
        return next;
      });
      setHasUnsavedChanges(true);
      setSaveError(null);
    },
    [headers]
  );

  const [selectedRowIndex, setSelectedRowIndex] = useState<number | null>(null);

  const handleDeleteRow = useCallback((rowIndex: number) => {
    if (rowIndex < 0 || rowIndex >= fullSchema.length) return;
    setFullSchema((prev) => {
      const next = [...prev];
      next.splice(rowIndex, 1);
      return next;
    });
    setSelectedRowIndex(null);
    setHasUnsavedChanges(true);
    setSaveError(null);
  }, [fullSchema.length]);

  const handleDeleteSelectedRow = useCallback(() => {
    if (selectedRowIndex !== null) {
      handleDeleteRow(selectedRowIndex);
    }
  }, [selectedRowIndex, handleDeleteRow]);

  const handleSave = useCallback(async () => {
    if (!sectionId || !hasUnsavedChanges || saving) return;
    setSaving(true);
    setSaveError(null);
    try {
      const res = await fetch('/api/sections/schema/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ section_id: sectionId, schema: fullSchema }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data.detail || `Save failed: ${res.status}`);
      }
      setHasUnsavedChanges(false);
      SuccessMessage('Schema saved successfully');
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Failed to save';
      setSaveError(msg);
      ErrorMessage(msg);
    } finally {
      setSaving(false);
    }
  }, [sectionId, hasUnsavedChanges, saving, fullSchema]);

  if (loading) {
    return (
      <div style={{ padding: 24, color: 'var(--text-secondary)', fontSize: 13 }}>
        Loading schema…
      </div>
    );
  }
  if (error) {
    return (
      <div style={{ padding: 24, color: 'var(--text-error, #f85149)', fontSize: 13 }}>
        {error}
      </div>
    );
  }
  if (!fullSchema.length) {
    return (
      <div style={{ padding: 24, color: 'var(--text-secondary)', fontSize: 13 }}>
        No schema available for this section.
      </div>
    );
  }

  return (
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
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 12,
          marginBottom: 12,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <button
            type="button"
            onClick={handleDeleteSelectedRow}
            disabled={selectedRowIndex === null}
            title={selectedRowIndex === null ? 'Select a row first' : `Delete row ${selectedRowIndex + 1}`}
            style={{
              padding: '6px 14px',
              fontSize: 12,
              fontWeight: 600,
              cursor: selectedRowIndex === null ? 'not-allowed' : 'pointer',
              background: 'var(--bg-tertiary)',
              border: '1px solid var(--border-color)',
              borderRadius: 4,
              color: selectedRowIndex === null ? 'var(--text-secondary)' : 'var(--text-primary)',
            }}
          >
            Delete row
          </button>
          <button
            type="button"
            onClick={handleSave}
            disabled={!hasUnsavedChanges || saving}
            style={{
              padding: '6px 14px',
              fontSize: 12,
              fontWeight: 600,
              cursor: !hasUnsavedChanges || saving ? 'not-allowed' : 'pointer',
              background: hasUnsavedChanges && !saving ? 'var(--accent-blue)' : 'var(--bg-tertiary)',
              border: '1px solid var(--border-color)',
              borderRadius: 4,
              color: hasUnsavedChanges && !saving ? 'white' : 'var(--text-secondary)',
            }}
          >
            {saving ? 'Saving…' : hasUnsavedChanges ? 'Save' : 'No changes'}
          </button>
          {hasUnsavedChanges && (
            <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>Unsaved changes</span>
          )}
        </div>
        {saveError && (
          <span style={{ fontSize: 12, color: 'var(--text-error, #f85149)' }}>{saveError}</span>
        )}
      </div>
      <div className="wwai-schema-hot" style={{ flex: 1, minHeight: 450, width: '100%', position: 'relative' }}>
        <HotTable
          key={`schema-${sectionId}-${fullSchema.length}`}
          data={dataRows}
          colHeaders={headers}
          rowHeaders={true}
          height={550}
          autoWrapRow={false}
          autoWrapCol={false}
          manualColumnResize={true}
          stretchH="all"
          readOnly={false}
          licenseKey="non-commercial-and-evaluation"
          afterChange={handleAfterChange}
          afterSelection={(row: number, _col: number) => setSelectedRowIndex(row >= 0 ? row : null)}
        />
      </div>
    </div>
  );
};

export default SchemaTab;
