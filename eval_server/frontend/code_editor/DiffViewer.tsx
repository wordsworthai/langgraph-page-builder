import React, { useState } from 'react';
import ReactDiffViewer from 'react-diff-viewer-continued';
import type { SectionData } from './types/editor';
import { getFilesForDiff } from './utils/diffUtils';
import { sectionDataToSectionMapping } from './utils/sectionDataMapper';

interface DiffViewerProps {
  originalSectionData: SectionData;
  stagingSectionData: SectionData;
  sectionId: string;
  onClose: () => void;
  onSaveSuccess?: () => void;
}

const DiffViewer: React.FC<DiffViewerProps> = ({
  originalSectionData,
  stagingSectionData,
  sectionId,
  onClose,
  onSaveSuccess,
}) => {
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  const handleSaveToMain = async () => {
    if (!sectionId || saving) return;
    setSaving(true);
    setSaveError(null);
    try {
      const sectionMapping = sectionDataToSectionMapping(stagingSectionData);
      const res = await fetch('/api/sections/code/promote', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ section_id: sectionId, section_mapping: sectionMapping }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data.detail || `Save failed: ${res.status}`);
      }
      onSaveSuccess?.();
      onClose();
    } catch (e) {
      setSaveError(e instanceof Error ? e.message : 'Failed to save to main');
    } finally {
      setSaving(false);
    }
  };
  const originalFiles = getFilesForDiff(originalSectionData);
  const stagingFiles = getFilesForDiff(stagingSectionData);

  const fileMap = new Map<string, { original: string; staging: string }>();
  for (const f of originalFiles) {
    fileMap.set(f.path, { original: f.content, staging: f.content });
  }
  for (const f of stagingFiles) {
    const existing = fileMap.get(f.path);
    if (existing) {
      existing.staging = f.content;
    } else {
      fileMap.set(f.path, { original: '', staging: f.content });
    }
  }

  const changedFiles = Array.from(fileMap.entries()).filter(
    ([_, { original, staging }]) => original !== staging
  );

  const [selectedPath, setSelectedPath] = useState<string | null>(
    changedFiles.length > 0 ? changedFiles[0][0] : null
  );

  const selected = selectedPath ? fileMap.get(selectedPath) : null;

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 100,
        background: 'var(--bg-primary, #1e1e1e)',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      <div
        style={{
          flexShrink: 0,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '12px 16px',
          borderBottom: '1px solid var(--border-color, #333)',
          background: 'var(--bg-secondary, #252526)',
        }}
      >
        <h2 style={{ margin: 0, fontSize: 16, fontWeight: 600, color: 'var(--text-primary)' }}>
          Diff: Original vs Staging
        </h2>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {saveError && (
            <span style={{ fontSize: 12, color: 'var(--error-color, #f87171)' }}>{saveError}</span>
          )}
          <button
            type="button"
            onClick={handleSaveToMain}
            disabled={saving}
            style={{
              padding: '6px 12px',
              fontSize: 13,
              cursor: saving ? 'not-allowed' : 'pointer',
              background: saving ? 'var(--bg-tertiary)' : 'var(--accent-blue, #2563eb)',
              border: '1px solid var(--border-color)',
              borderRadius: 4,
              color: 'white',
            }}
          >
            {saving ? 'Saving…' : 'Save to main'}
          </button>
          <button
            type="button"
            onClick={onClose}
            style={{
              padding: '6px 12px',
              fontSize: 13,
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
      <div style={{ flex: 1, display: 'flex', minHeight: 0 }}>
        <div
          style={{
            width: 220,
            flexShrink: 0,
            borderRight: '1px solid var(--border-color)',
            overflowY: 'auto',
            padding: 8,
          }}
        >
          <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 8 }}>
            Changed files ({changedFiles.length})
          </div>
          {changedFiles.length === 0 ? (
            <p style={{ fontSize: 13, color: 'var(--text-secondary)' }}>No differences</p>
          ) : (
            changedFiles.map(([path]) => (
              <button
                key={path}
                type="button"
                onClick={() => setSelectedPath(path)}
                style={{
                  display: 'block',
                  width: '100%',
                  textAlign: 'left',
                  padding: '6px 8px',
                  marginBottom: 4,
                  fontSize: 12,
                  cursor: 'pointer',
                  background: selectedPath === path ? 'var(--accent-blue)' : 'transparent',
                  color: selectedPath === path ? 'white' : 'var(--text-primary)',
                  border: 'none',
                  borderRadius: 4,
                }}
              >
                {path}
              </button>
            ))
          )}
        </div>
        <div style={{ flex: 1, overflow: 'auto', padding: 16 }}>
          {selected && selectedPath ? (
            <ReactDiffViewer
              oldValue={selected.original}
              newValue={selected.staging}
              splitView={true}
              useDarkTheme={true}
              leftTitle="Original"
              rightTitle="Staging"
              styles={{
                variables: {
                  dark: {
                    diffViewerBackground: '#1e1e1e',
                    diffViewerColor: '#d4d4d4',
                    addedBackground: '#1e3a1e',
                    addedColor: '#d4d4d4',
                    removedBackground: '#3a1e1e',
                    removedColor: '#d4d4d4',
                  },
                },
              }}
            />
          ) : (
            <p style={{ color: 'var(--text-secondary)' }}>
              {changedFiles.length === 0 ? 'No files have been changed.' : 'Select a file.'}
            </p>
          )}
        </div>
      </div>
    </div>
  );
};

export default DiffViewer;
