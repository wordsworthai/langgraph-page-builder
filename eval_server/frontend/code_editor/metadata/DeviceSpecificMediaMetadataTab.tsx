import React, { useCallback, useEffect, useState } from 'react';

interface DeviceSpecificMediaMetadataTabProps {
  sectionId: string;
}

type Side = 'desktop' | 'mobile';

interface MediaRow {
  side: Side;
  elementKey: string;
  blockType: string;
  index: string;
  width: number | null;
  height: number | null;
  source: string | null;
  isDefault: boolean;
}

const extractRowsForSide = (meta: Record<string, unknown> | null | undefined, side: Side): MediaRow[] => {
  const sideData = meta?.[side];
  if (!sideData || typeof sideData !== 'object') return [];

  const rows: MediaRow[] = [];
  const sideObj = sideData as Record<string, unknown>;

  Object.entries(sideObj).forEach(([elementKey, blocks]: [string, unknown]) => {
    if (!blocks || typeof blocks !== 'object') return;
    const blocksObj = blocks as Record<string, unknown>;

    Object.entries(blocksObj).forEach(([blockType, blockVal]: [string, unknown]) => {
      if (!blockVal || typeof blockVal !== 'object') return;
      const blockValObj = blockVal as Record<string, unknown>;
      const byIndex = blockValObj.by_index;
      const defaultIndex = blockValObj.default_index;
      if (!byIndex || typeof byIndex !== 'object') return;
      const byIndexObj = byIndex as Record<string, unknown>;

      Object.entries(byIndexObj).forEach(([indexKey, info]: [string, unknown]) => {
        const infoObj = (info as Record<string, unknown>) ?? {};
        const width =
          typeof infoObj?.width === 'number'
            ? infoObj.width
            : Number.isFinite(Number(infoObj?.width))
              ? Number(infoObj.width)
              : null;
        const height =
          typeof infoObj?.height === 'number'
            ? infoObj.height
            : Number.isFinite(Number(infoObj?.height))
              ? Number(infoObj.height)
              : null;
        const source = (infoObj?.source as string) ?? null;

        rows.push({
          side,
          elementKey,
          blockType,
          index: indexKey,
          width,
          height,
          source,
          isDefault:
            defaultIndex !== undefined &&
            defaultIndex !== null &&
            String(defaultIndex) === String(indexKey),
        });
      });
    });
  });

  return rows;
};

const borderColor = 'var(--border-color, #333)';
const textPrimary = 'var(--text-primary, #ccc)';
const textSecondary = 'var(--text-secondary, #999)';
const bgSecondary = 'var(--bg-secondary, #252526)';
const bgTertiary = 'var(--bg-tertiary, #1e1e1e)';

const DeviceSpecificMediaMetadataTab: React.FC<DeviceSpecificMediaMetadataTabProps> = ({
  sectionId,
}) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [deviceMeta, setDeviceMeta] = useState<Record<string, unknown> | null>(null);
  const [activeSide, setActiveSide] = useState<Side>('desktop');

  const fetchMetadata = useCallback(async () => {
    if (!sectionId) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch('/api/sections/metadata/device-specific-media', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ section_id: sectionId }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data.detail || `Failed to fetch: ${res.status}`);
      }
      const meta = data?.device_specific_media_metadata ?? {};
      setDeviceMeta(typeof meta === 'object' ? meta : {});
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

  const desktopRows = extractRowsForSide(deviceMeta, 'desktop');
  const mobileRows = extractRowsForSide(deviceMeta, 'mobile');
  const rows = activeSide === 'desktop' ? desktopRows : mobileRows;

  const renderTable = (tableRows: MediaRow[], side: Side) => {
    if (tableRows.length === 0) {
      return (
        <div style={{ fontSize: 12, color: textSecondary }}>
          No {side} media entries recorded for this section.
        </div>
      );
    }

    return (
      <div style={{ marginTop: 12, overflowX: 'auto' }}>
        <table
          style={{
            minWidth: '100%',
            textAlign: 'left',
            fontSize: 11,
            color: textPrimary,
            border: `1px solid ${borderColor}`,
            borderRadius: 8,
            borderCollapse: 'collapse',
          }}
        >
          <thead>
            <tr>
              <th style={{ padding: '8px 12px', borderBottom: `1px solid ${borderColor}`, backgroundColor: bgTertiary, textTransform: 'uppercase' }}>
                Element ID
              </th>
              <th style={{ padding: '8px 12px', borderBottom: `1px solid ${borderColor}`, backgroundColor: bgTertiary, textTransform: 'uppercase' }}>
                Block type
              </th>
              <th style={{ padding: '8px 12px', borderBottom: `1px solid ${borderColor}`, backgroundColor: bgTertiary, textTransform: 'uppercase' }}>
                Index
              </th>
              <th style={{ padding: '8px 12px', borderBottom: `1px solid ${borderColor}`, backgroundColor: bgTertiary, textTransform: 'uppercase' }}>
                Width
              </th>
              <th style={{ padding: '8px 12px', borderBottom: `1px solid ${borderColor}`, backgroundColor: bgTertiary, textTransform: 'uppercase' }}>
                Height
              </th>
              <th style={{ padding: '8px 12px', borderBottom: `1px solid ${borderColor}`, backgroundColor: bgTertiary, textTransform: 'uppercase' }}>
                Source
              </th>
              <th style={{ padding: '8px 12px', borderBottom: `1px solid ${borderColor}`, backgroundColor: bgTertiary, textTransform: 'uppercase' }}>
                Default
              </th>
            </tr>
          </thead>
          <tbody style={{ backgroundColor: bgSecondary }}>
            {tableRows.map((row, idx) => (
              <tr
                key={`${side}-${row.elementKey}-${row.blockType}-${row.index}-${idx}`}
                style={{ borderBottom: `1px solid ${borderColor}` }}
              >
                <td style={{ padding: '8px 12px', verticalAlign: 'top', maxWidth: 220, wordBreak: 'break-all' }}>
                  {row.elementKey}
                </td>
                <td style={{ padding: '8px 12px', verticalAlign: 'top' }}>{row.blockType}</td>
                <td style={{ padding: '8px 12px', verticalAlign: 'top', fontFamily: 'monospace' }}>
                  {row.index}
                </td>
                <td style={{ padding: '8px 12px', verticalAlign: 'top' }}>
                  {row.width != null ? (
                    <span style={{ fontFamily: 'monospace' }}>{row.width}</span>
                  ) : (
                    <span style={{ color: textSecondary }}>–</span>
                  )}
                </td>
                <td style={{ padding: '8px 12px', verticalAlign: 'top' }}>
                  {row.height != null ? (
                    <span style={{ fontFamily: 'monospace' }}>{row.height}</span>
                  ) : (
                    <span style={{ color: textSecondary }}>–</span>
                  )}
                </td>
                <td style={{ padding: '8px 12px', verticalAlign: 'top', maxWidth: 260, wordBreak: 'break-all' }}>
                  {row.source ? (
                    <span>{row.source}</span>
                  ) : (
                    <span style={{ color: textSecondary }}>–</span>
                  )}
                </td>
                <td style={{ padding: '8px 12px', verticalAlign: 'top' }}>
                  {row.isDefault ? (
                    <span
                      style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        padding: '2px 8px',
                        borderRadius: 9999,
                        border: '1px solid rgba(16, 185, 129, 0.7)',
                        backgroundColor: 'rgba(6, 95, 70, 0.4)',
                        fontSize: 10,
                        color: '#6ee7b7',
                      }}
                    >
                      Default
                    </span>
                  ) : (
                    <span style={{ color: textSecondary }}>–</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  };

  const containerStyle: React.CSSProperties = {
    padding: 16,
    flex: 1,
    overflow: 'auto',
    color: textSecondary,
    fontSize: 13,
  };

  if (loading) {
    return (
      <div style={containerStyle}>
        Loading...
      </div>
    );
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
          Device-specific media metadata
        </div>
        <p style={{ fontSize: 11, color: textSecondary, margin: 0 }}>
          Media items and their rendered dimensions on desktop and mobile. From{' '}
          <span style={{ fontFamily: 'monospace' }}>section_metadata.device_specific_media_metadata</span>.
        </p>
      </div>

      <div style={{ display: 'flex', gap: 12, borderBottom: `1px solid ${borderColor}` }}>
        <button
          type="button"
          onClick={() => setActiveSide('desktop')}
          style={{
            padding: '8px 12px',
            fontSize: 12,
            cursor: 'pointer',
            background: 'none',
            border: 'none',
            borderBottom: activeSide === 'desktop' ? '2px solid var(--accent-blue, #007acc)' : '2px solid transparent',
            color: activeSide === 'desktop' ? textPrimary : textSecondary,
            marginBottom: -1,
          }}
        >
          Desktop
        </button>
        <button
          type="button"
          onClick={() => setActiveSide('mobile')}
          style={{
            padding: '8px 12px',
            fontSize: 12,
            cursor: 'pointer',
            background: 'none',
            border: 'none',
            borderBottom: activeSide === 'mobile' ? '2px solid var(--accent-blue, #007acc)' : '2px solid transparent',
            color: activeSide === 'mobile' ? textPrimary : textSecondary,
            marginBottom: -1,
          }}
        >
          Mobile
        </button>
      </div>

      {rows.length === 0 ? (
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
          No {activeSide} media entries recorded for this section yet.
        </div>
      ) : (
        renderTable(rows, activeSide)
      )}
    </div>
  );
};

export default DeviceSpecificMediaMetadataTab;
