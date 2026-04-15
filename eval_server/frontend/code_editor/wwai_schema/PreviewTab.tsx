import React, { useEffect, useState } from 'react';

type PreviewSubTab = 'desktop' | 'mobile';

interface SectionDetails {
  section_l0?: string;
  section_l1?: string;
  section_label?: string;
  desktop_image_url?: string;
  mobile_image_url?: string;
}

interface PreviewTabProps {
  sectionId: string;
}

const PreviewTab: React.FC<PreviewTabProps> = ({ sectionId }) => {
  const [details, setDetails] = useState<SectionDetails | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeSubTab, setActiveSubTab] = useState<PreviewSubTab>('desktop');

  useEffect(() => {
    if (!sectionId) return;
    setLoading(true);
    setError(null);
    fetch('/api/sections/details', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ section_id: sectionId }),
    })
      .then((res) => {
        if (!res.ok) throw new Error(res.status === 404 ? 'Section not found' : `Failed to fetch: ${res.status}`);
        return res.json();
      })
      .then(setDetails)
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed to load'))
      .finally(() => setLoading(false));
  }, [sectionId]);

  if (loading) {
    return (
      <div style={{ padding: 24, color: 'var(--text-secondary)', fontSize: 13 }}>
        Loading preview…
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
  if (!details) {
    return null;
  }

  const desktopUrl = details.desktop_image_url;
  const mobileUrl = details.mobile_image_url;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0, overflow: 'hidden' }}>
      <div
        style={{
          display: 'flex',
          gap: 0,
          borderBottom: '1px solid var(--border-color, #333)',
          padding: '0 16px',
          flexShrink: 0,
        }}
      >
        {(['desktop', 'mobile'] as const).map((tabId) => (
          <button
            key={tabId}
            type="button"
            onClick={() => setActiveSubTab(tabId)}
            style={{
              padding: '8px 16px',
              fontSize: 13,
              fontWeight: 500,
              cursor: 'pointer',
              background: 'none',
              border: 'none',
              borderBottom: activeSubTab === tabId
                ? '2px solid var(--accent-blue, #007acc)'
                : '2px solid transparent',
              color: activeSubTab === tabId ? 'var(--text-primary)' : 'var(--text-secondary)',
              marginBottom: -1,
            }}
          >
            {tabId === 'desktop' ? 'Desktop' : 'Mobile'}
          </button>
        ))}
      </div>
      <div
        style={{
          flex: 1,
          minHeight: 0,
          overflow: 'hidden',
          padding: 16,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        {activeSubTab === 'desktop' && (
          desktopUrl ? (
            <img
              src={desktopUrl}
              alt="Desktop preview"
              style={{
                display: 'block',
                maxWidth: '100%',
                maxHeight: '100%',
                width: 'auto',
                height: 'auto',
                objectFit: 'contain',
              }}
            />
          ) : (
            <span style={{ color: 'var(--text-secondary)', fontSize: 13 }}>No desktop image available</span>
          )
        )}
        {activeSubTab === 'mobile' && (
          mobileUrl ? (
            <img
              src={mobileUrl}
              alt="Mobile preview"
              style={{
                display: 'block',
                maxWidth: '100%',
                maxHeight: '100%',
                width: 'auto',
                height: 'auto',
                objectFit: 'contain',
              }}
            />
          ) : (
            <span style={{ color: 'var(--text-secondary)', fontSize: 13 }}>No mobile image available</span>
          )
        )}
      </div>
    </div>
  );
};

export default PreviewTab;
