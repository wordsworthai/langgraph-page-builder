import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { HotTable } from '@handsontable/react';
import { SuccessMessage, ErrorMessage } from '../utils/notification';
import type { CellChange, ChangeSource } from 'handsontable/common';
import { registerAllModules } from 'handsontable/registry';
import 'handsontable/dist/handsontable.full.min.css';
import '../wwai_schema/handsontable-dark.css';

interface ParentRowsTabProps {
  sectionId: string;
}

interface ParentRow {
  element_type?: string;
  element_id?: string;
  block_type?: string;
  parent_element_id?: string;
  parent_block_type?: string;
  [key: string]: unknown;
}

const PARENT_ROW_COLUMNS = [
  'element_type',
  'element_id',
  'block_type',
  'parent_element_id',
  'parent_block_type',
] as const;

const borderColor = 'var(--border-color, #333)';
const textPrimary = 'var(--text-primary, #ccc)';
const textSecondary = 'var(--text-secondary, #999)';
const bgTertiary = 'var(--bg-tertiary, #1e1e1e)';

const ParentRowsTab: React.FC<ParentRowsTabProps> = ({ sectionId }) => {
  const [fullParentRows, setFullParentRows] = useState<ParentRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  useEffect(() => {
    registerAllModules();
  }, []);

  const fetchMetadata = useCallback(async () => {
    if (!sectionId) return;
    setLoading(true);
    setError(null);
    setSaveError(null);
    setHasUnsavedChanges(false);
    try {
      const res = await fetch('/api/sections/metadata/parent-rows', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ section_id: sectionId }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data.detail || `Failed to fetch: ${res.status}`);
      }
      const rows = data?.parent_rows ?? [];
      setFullParentRows(Array.isArray(rows) ? rows.map((r: ParentRow) => ({ ...r })) : []);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load');
    } finally {
      setLoading(false);
    }
  }, [sectionId]);

  useEffect(() => {
    if (sectionId) {
      fetchMetadata();
    }
  }, [sectionId, fetchMetadata]);

  const { dataRows } = useMemo(() => {
    const rows = fullParentRows.map((row) =>
      PARENT_ROW_COLUMNS.map((col) => {
        const val = row[col];
        if (val === undefined || val === null) return '';
        if (typeof val === 'object') return JSON.stringify(val);
        return String(val);
      })
    );
    return { dataRows: rows };
  }, [fullParentRows]);

  const handleAfterChange = useCallback(
    (changes: CellChange[] | null, source: ChangeSource) => {
      if (source === 'loadData' || !changes || changes.length === 0) return;
      setFullParentRows((prev) => {
        const next = prev.map((row) => ({ ...row }));
        for (const [rowIndex, col, , newVal] of changes) {
          if (rowIndex < 0 || rowIndex >= next.length) continue;
          const colIdx = typeof col === 'number' ? col : -1;
          if (colIdx < 0 || colIdx >= PARENT_ROW_COLUMNS.length) continue;
          const header = PARENT_ROW_COLUMNS[colIdx];
          next[rowIndex] = { ...next[rowIndex], [header]: newVal ?? '' };
        }
        return next;
      });
      setHasUnsavedChanges(true);
      setSaveError(null);
    },
    []
  );

  const handleSave = useCallback(async () => {
    if (!sectionId || !hasUnsavedChanges || saving) return;
    setSaving(true);
    setSaveError(null);
    try {
      const res = await fetch('/api/sections/metadata/parent-rows/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ section_id: sectionId, parent_rows: fullParentRows }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data.detail || `Save failed: ${res.status}`);
      }
      setHasUnsavedChanges(false);
      SuccessMessage('Parent rows saved successfully');
      fetchMetadata();
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Failed to save';
      setSaveError(msg);
      ErrorMessage(msg);
    } finally {
      setSaving(false);
    }
  }, [sectionId, hasUnsavedChanges, saving, fullParentRows, fetchMetadata]);

  const containerStyle: React.CSSProperties = {
    padding: 16,
    flex: 1,
    overflow: 'auto',
    color: textSecondary,
    fontSize: 13,
  };

  if (loading) {
    return <div style={containerStyle}>Loading...</div>;
  }

  if (error) {
    return (
      <div style={containerStyle}>
        <span style={{ color: '#f87171' }}>{error}</span>
      </div>
    );
  }

  if (fullParentRows.length === 0) {
    return (
      <div style={{ ...containerStyle, display: 'flex', flexDirection: 'column', gap: 16 }}>
        <div
          style={{
            padding: 16,
            fontSize: 12,
            color: textPrimary,
            border: `1px solid ${borderColor}`,
            borderRadius: 8,
            backgroundColor: bgTertiary,
          }}
        >
          <div style={{ fontSize: 14, fontWeight: 600, color: textPrimary, marginBottom: 4 }}>
            Parent rows
          </div>
          <p style={{ fontSize: 11, color: textSecondary, margin: 0 }}>
            Element hierarchy from{' '}
            <span style={{ fontFamily: 'monospace' }}>section_metadata.parent_rows</span>.
          </p>
        </div>
        <div
          style={{
            padding: 16,
            fontSize: 12,
            color: textSecondary,
            border: `1px solid ${borderColor}`,
            borderRadius: 8,
            backgroundColor: bgTertiary,
          }}
        >
          No parent rows recorded for this section.
        </div>
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
      <div
        className="wwai-schema-hot"
        style={{ flex: 1, minHeight: 450, width: '100%', position: 'relative' }}
      >
        <HotTable
          key={`parent-rows-${sectionId}-${fullParentRows.length}`}
          data={dataRows}
          colHeaders={PARENT_ROW_COLUMNS.map((c) => c.replace(/_/g, ' '))}
          rowHeaders={true}
          height={550}
          autoWrapRow={false}
          autoWrapCol={false}
          manualColumnResize={true}
          stretchH="all"
          readOnly={false}
          licenseKey="non-commercial-and-evaluation"
          afterChange={handleAfterChange}
        />
      </div>
    </div>
  );
};

export default ParentRowsTab;
