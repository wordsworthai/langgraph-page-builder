import React, { useCallback, useEffect, useState } from 'react';
import DeviceSpecificMediaMetadataTab from './DeviceSpecificMediaMetadataTab';
import ParentRowsTab from './ParentRowsTab';
import SectionAiSignalsTab from './SectionAiSignalsTab';
import { SuccessMessage, ErrorMessage } from '../utils/notification';

type TabId = 'device_specific_media_metadata' | 'parent_rows' | 'section_ai_signals';

const TAB_CONFIG: { id: TabId; label: string }[] = [
  { id: 'device_specific_media_metadata', label: 'Device-specific media' },
  { id: 'parent_rows', label: 'Parent rows' },
  { id: 'section_ai_signals', label: 'Section AI signals' },
];

interface MetadataModalProps {
  open: boolean;
  onClose: () => void;
  sectionId: string;
}

const MetadataModal: React.FC<MetadataModalProps> = ({ open, onClose, sectionId }) => {
  const [activeTab, setActiveTab] = useState<TabId>('device_specific_media_metadata');
  const [regenerating, setRegenerating] = useState(false);

  const handleRegenerate = useCallback(async () => {
    if (!sectionId || regenerating) return;
    setRegenerating(true);
    try {
      const res = await fetch('/api/sections/metadata/regenerate-section-code-generation-config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ section_id: sectionId }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data.detail || 'Regeneration failed');
      }
      SuccessMessage('Section code generation config regenerated');
    } catch (e) {
      ErrorMessage(e instanceof Error ? e.message : 'Regeneration failed');
    } finally {
      setRegenerating(false);
    }
  }, [sectionId, regenerating]);

  useEffect(() => {
    if (!open) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [open, onClose]);

  if (!open) return null;
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
            Section Metadata
          </h2>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <button
              type="button"
              onClick={handleRegenerate}
              disabled={!sectionId || regenerating}
              style={{
                padding: '4px 10px',
                fontSize: 12,
                cursor: !sectionId || regenerating ? 'not-allowed' : 'pointer',
                background: 'var(--bg-tertiary)',
                border: '1px solid var(--border-color)',
                borderRadius: 4,
                color: !sectionId || regenerating ? 'var(--text-secondary)' : 'var(--text-primary)',
              }}
            >
              {regenerating ? 'Regenerating…' : 'Regenerate section code generation config'}
            </button>
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
          {TAB_CONFIG.map(({ id, label }) => (
            <button
              key={id}
              type="button"
              onClick={() => setActiveTab(id)}
              style={{
                padding: '10px 16px',
                fontSize: 13,
                fontWeight: 500,
                cursor: 'pointer',
                background: 'none',
                border: 'none',
                borderBottom:
                  activeTab === id
                    ? '2px solid var(--accent-blue, #007acc)'
                    : '2px solid transparent',
                color: activeTab === id ? 'var(--text-primary)' : 'var(--text-secondary)',
                marginBottom: -1,
              }}
            >
              {label}
            </button>
          ))}
        </div>
        <div
          style={{
            overflow: 'hidden',
            flex: 1,
            minHeight: 0,
            display: 'flex',
            flexDirection: 'column',
          }}
        >
          {activeTab === 'device_specific_media_metadata' && (
            <DeviceSpecificMediaMetadataTab sectionId={sectionId} />
          )}
          {activeTab === 'parent_rows' && <ParentRowsTab sectionId={sectionId} />}
          {activeTab === 'section_ai_signals' && <SectionAiSignalsTab sectionId={sectionId} />}
        </div>
      </div>
    </div>
  );
};

export default MetadataModal;
