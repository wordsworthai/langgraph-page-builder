import React, { useCallback, useEffect, useState } from 'react';
import { SuccessMessage, ErrorMessage } from '../utils/notification';

interface SectionAiSignalsTabProps {
  sectionId: string;
}

interface SectionAiSignals {
  content_description?: string;
  styling_description?: string;
  section_layout_description?: string;
  [key: string]: unknown;
}

const KNOWN_FIELDS = [
  'content_description',
  'styling_description',
  'section_layout_description',
] as const;

const borderColor = 'var(--border-color, #333)';
const textPrimary = 'var(--text-primary, #ccc)';
const textSecondary = 'var(--text-secondary, #999)';
const bgTertiary = 'var(--bg-tertiary, #1e1e1e)';

const SectionAiSignalsTab: React.FC<SectionAiSignalsTabProps> = ({ sectionId }) => {
  const [signals, setSignals] = useState<SectionAiSignals>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  const fetchMetadata = useCallback(async () => {
    if (!sectionId) return;
    setLoading(true);
    setError(null);
    setSaveError(null);
    setHasUnsavedChanges(false);
    try {
      const res = await fetch('/api/sections/metadata/section-ai-signals', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ section_id: sectionId }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data.detail || `Failed to fetch: ${res.status}`);
      }
      const sig = data?.section_ai_signals ?? {};
      setSignals(typeof sig === 'object' ? { ...sig } : {});
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

  const handleFieldChange = useCallback((field: string, value: string) => {
    setSignals((prev) => ({ ...prev, [field]: value }));
    setHasUnsavedChanges(true);
    setSaveError(null);
  }, []);

  const handleSave = useCallback(async () => {
    if (!sectionId || !hasUnsavedChanges || saving) return;
    setSaving(true);
    setSaveError(null);
    try {
      const res = await fetch('/api/sections/metadata/section-ai-signals/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ section_id: sectionId, section_ai_signals: signals }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data.detail || `Save failed: ${res.status}`);
      }
      setHasUnsavedChanges(false);
      SuccessMessage('Section AI signals saved successfully');
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Failed to save';
      setSaveError(msg);
      ErrorMessage(msg);
    } finally {
      setSaving(false);
    }
  }, [sectionId, hasUnsavedChanges, saving, signals]);

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
          Section AI signals
        </div>
        <p style={{ fontSize: 11, color: textSecondary, margin: 0 }}>
          AI-generated descriptions from{' '}
          <span style={{ fontFamily: 'monospace' }}>section_metadata.section_ai_signals</span>.
        </p>
      </div>

      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 12,
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
        style={{
          display: 'flex',
          flexDirection: 'column',
          gap: 12,
          border: `1px solid ${borderColor}`,
          borderRadius: 8,
          overflow: 'hidden',
          backgroundColor: bgTertiary,
        }}
      >
        {KNOWN_FIELDS.map((key) => {
          const value = signals[key];
          const displayValue =
            value === undefined || value === null ? '' : typeof value === 'object' ? JSON.stringify(value) : String(value);
          return (
            <div
              key={key}
              style={{
                padding: 12,
                borderBottom: `1px solid ${borderColor}`,
              }}
            >
              <div
                style={{
                  fontSize: 11,
                  fontWeight: 600,
                  color: textSecondary,
                  textTransform: 'uppercase',
                  marginBottom: 6,
                }}
              >
                {key.replace(/_/g, ' ')}
              </div>
              <textarea
                value={displayValue}
                onChange={(e) => handleFieldChange(key, e.target.value)}
                rows={4}
                style={{
                  width: '100%',
                  margin: 0,
                  padding: 8,
                  fontSize: 12,
                  color: textPrimary,
                  backgroundColor: 'var(--bg-secondary, #252526)',
                  border: `1px solid ${borderColor}`,
                  borderRadius: 4,
                  resize: 'vertical',
                  fontFamily: 'inherit',
                  boxSizing: 'border-box',
                }}
              />
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default SectionAiSignalsTab;
