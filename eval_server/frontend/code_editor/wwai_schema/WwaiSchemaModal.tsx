import React, { useEffect, useState } from 'react';
import PreviewTab from './PreviewTab';
import SchemaTab from './SchemaTab';

type TabId = 'preview' | 'schema';

interface WwaiSchemaModalProps {
  open: boolean;
  onClose: () => void;
  sectionId: string;
}

const WwaiSchemaModal: React.FC<WwaiSchemaModalProps> = ({ open, onClose, sectionId }) => {
  const [activeTab, setActiveTab] = useState<TabId>('preview');

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
            WWAI Schema
          </h2>
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
        <div
          style={{
            display: 'flex',
            gap: 0,
            borderBottom: '1px solid var(--border-color, #333)',
            padding: '0 16px',
          }}
        >
          {(['preview', 'schema'] as const).map((tabId) => (
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
              {tabId === 'preview' ? 'Preview' : 'Schema'}
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
          {activeTab === 'preview' && <PreviewTab sectionId={sectionId} />}
          {activeTab === 'schema' && <SchemaTab sectionId={sectionId} />}
        </div>
      </div>
    </div>
  );
};

export default WwaiSchemaModal;
