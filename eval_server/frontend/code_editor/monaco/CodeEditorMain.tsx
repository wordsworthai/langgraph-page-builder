import React, { useEffect, useRef, useState } from 'react';
import { Braces, ChevronRight, GitCompare, Trash2, FileJson, Info } from 'lucide-react';
import { CodeVariant, SectionData } from '../types/editor';
import FileExplorer from './FileExlorer';
import CodeEditor from './MonacoEditor';
import { EditorProvider, useEditor } from './EditorContext';
import { sectionMappingToSectionData } from '../utils/sectionDataMapper';
import DiffViewer from '../DiffViewer';
import { PopulationJsonModal } from '../population_json';
import { WwaiSchemaModal } from '../wwai_schema';
import { MetadataModal } from '../metadata';

interface CodeEditorMainProps {
  sectionData: SectionData;
  sectionId: string;
  activeVariant: CodeVariant;
  stagingExists: boolean;
  onSwitchVariant: (variant: CodeVariant) => void;
  switchingLoading?: boolean;
  onClear: () => void;
  setCompiledHtml?: (html: string) => void;
  onSave?: (updatedSectionData: SectionData) => void | Promise<void>;
  onDiscardDraft?: () => void | Promise<void>;
  onPromoteToMainSuccess?: () => void;
}

const EXPLORER_WIDTH = 280;
const COLLAPSED_WIDTH = 48;

const EditorToolbar: React.FC<{
  sectionName: string;
  sectionId: string;
  activeVariant: CodeVariant;
  stagingExists: boolean;
  onSwitchVariant: (variant: CodeVariant) => void;
  switchingLoading?: boolean;
  onClear: () => void;
  onViewDiff: () => void;
  onDiscardDraft?: () => void | Promise<void>;
  onOpenWwaiSchema: () => void;
  onOpenPopulationJson: () => void;
  onOpenMetadata: () => void;
}> = ({
  sectionName,
  activeVariant,
  stagingExists,
  onSwitchVariant,
  switchingLoading,
  onClear,
  onViewDiff,
  onDiscardDraft,
  onOpenWwaiSchema,
  onOpenPopulationJson,
  onOpenMetadata,
}) => {
  const { compile, isCompiling } = useEditor();

  const btnBase = {
    padding: '4px 10px',
    fontSize: 12,
    display: 'flex',
    alignItems: 'center',
    gap: 4,
    whiteSpace: 'nowrap' as const,
    cursor: 'pointer',
    background: 'var(--bg-tertiary)',
    border: '1px solid var(--border-color)',
    borderRadius: 4,
    color: 'var(--text-primary)',
  };

  return (
    <div
      style={{
        flexShrink: 0,
        display: 'flex',
        alignItems: 'center',
        gap: 12,
        padding: '8px 12px',
        background: 'var(--bg-secondary)',
        borderBottom: '1px solid var(--border-color)',
        flexWrap: 'wrap',
      }}
    >
      <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>Section: {sectionName}</span>
      {switchingLoading && (
        <span style={{ fontSize: 11, color: 'var(--text-secondary)' }}>Loading…</span>
      )}
      <div
        style={{
          width: 1,
          height: 18,
          background: 'var(--border-color)',
          alignSelf: 'stretch',
        }}
      />
      <div style={{ display: 'flex', gap: 2 }}>
        {(['original', 'staging', 'boilerplate'] as CodeVariant[]).map((v) => {
          if (v === 'staging' && !stagingExists) return null;
          return (
            <button
              key={v}
              type="button"
              onClick={() => onSwitchVariant(v)}
              disabled={switchingLoading || v === activeVariant}
              style={{
                padding: '4px 8px',
                fontSize: 11,
                fontWeight: 600,
                whiteSpace: 'nowrap',
                cursor: switchingLoading || v === activeVariant ? 'default' : 'pointer',
                background: v === activeVariant ? 'var(--accent-blue)' : 'var(--bg-tertiary)',
                border: `1px solid ${v === activeVariant ? 'var(--accent-blue)' : 'var(--border-color)'}`,
                borderRadius: 4,
                color: v === activeVariant ? 'white' : 'var(--text-primary)',
                textTransform: 'capitalize',
              }}
            >
              {v}
            </button>
          );
        })}
      </div>
      <div
        style={{
          width: 1,
          height: 18,
          background: 'var(--border-color)',
          alignSelf: 'stretch',
        }}
      />
      <button
        type="button"
        onClick={() => compile()}
        disabled={isCompiling}
        style={{
          ...btnBase,
          cursor: isCompiling ? 'not-allowed' : 'pointer',
          background: 'var(--accent-blue)',
          border: 'none',
          color: 'white',
        }}
      >
        {isCompiling ? 'Compiling…' : 'Compile'}
      </button>
      <button type="button" onClick={onViewDiff} style={btnBase} title="Compare original vs staging">
        <GitCompare size={14} />
        Diff
      </button>
      <button
        type="button"
        onClick={onOpenWwaiSchema}
        style={btnBase}
        title="View WWAI schema for this section"
      >
        <FileJson size={14} />
        Schema
      </button>
      <button
        type="button"
        onClick={onOpenPopulationJson}
        style={btnBase}
        title="View and edit population JSON for this section"
      >
        <Braces size={14} />
        Population JSON
      </button>
      <button
        type="button"
        onClick={onOpenMetadata}
        style={btnBase}
        title="View section metadata"
      >
        <Info size={14} />
        Metadata
      </button>
      {onDiscardDraft && (
        <button
          type="button"
          onClick={onDiscardDraft}
          style={{ ...btnBase, color: 'var(--text-error, #f85149)' }}
          title="Discard draft and reload from original"
        >
          <Trash2 size={14} />
          Discard
        </button>
      )}
      <div style={{ flex: 1, minWidth: 8 }} />
      <button type="button" onClick={onClear} style={btnBase} title="Load a different section">
        Load section
      </button>
    </div>
  );
};

const CodeViewerInner: React.FC<{
  onClear: () => void;
  sectionName: string;
  sectionId: string;
  activeVariant: CodeVariant;
  stagingExists: boolean;
  onSwitchVariant: (variant: CodeVariant) => void;
  switchingLoading?: boolean;
  onViewDiff: () => void;
  onDiscardDraft?: () => void | Promise<void>;
  onOpenWwaiSchema: () => void;
  onOpenPopulationJson: () => void;
  onOpenMetadata: () => void;
}> = ({
  onClear,
  sectionName,
  sectionId,
  activeVariant,
  stagingExists,
  onSwitchVariant,
  switchingLoading,
  onViewDiff,
  onDiscardDraft,
  onOpenWwaiSchema,
  onOpenPopulationJson,
  onOpenMetadata,
}) => {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const { setFullscreenTarget, isFullscreen, isExplorerCollapsed, toggleExplorer } = useEditor();

  useEffect(() => {
    setFullscreenTarget(containerRef.current);
    return () => setFullscreenTarget(null);
  }, [setFullscreenTarget]);

  return (
    <div style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
        <EditorToolbar
        sectionName={sectionName}
        sectionId={sectionId}
        activeVariant={activeVariant}
        stagingExists={stagingExists}
        onSwitchVariant={onSwitchVariant}
        switchingLoading={switchingLoading}
        onClear={onClear}
        onViewDiff={onViewDiff}
        onDiscardDraft={onDiscardDraft}
        onOpenWwaiSchema={onOpenWwaiSchema}
        onOpenPopulationJson={onOpenPopulationJson}
        onOpenMetadata={onOpenMetadata}
      />
      <div
        ref={containerRef}
        className={`flex bg-gray-900 text-white overflow-hidden transition-all duration-300 flex-1 min-h-0 ${
          isFullscreen ? 'fixed inset-0 z-50 h-screen w-screen' : 'relative'
        }`}
      >
        <div
          className="flex-shrink-0 flex flex-col border-r border-gray-700 transition-all duration-300 overflow-hidden"
          style={{ width: isExplorerCollapsed ? COLLAPSED_WIDTH : EXPLORER_WIDTH }}
        >
          {isExplorerCollapsed ? (
            <div className="flex flex-col items-center justify-start h-full py-2 bg-gray-800">
              <button
                onClick={toggleExplorer}
                className="p-2 rounded hover:bg-gray-700 text-gray-400 hover:text-white transition-colors"
                title="Expand explorer"
              >
                <ChevronRight size={20} />
              </button>
            </div>
          ) : (
            <FileExplorer />
          )}
        </div>
        <div className="flex-1 min-w-0 flex flex-col">
          <CodeEditor />
        </div>
      </div>
    </div>
  );
};

const CodeEditorMain: React.FC<CodeEditorMainProps> = ({
  sectionData,
  sectionId,
  activeVariant,
  stagingExists,
  onSwitchVariant,
  switchingLoading,
  onClear,
  setCompiledHtml,
  onSave,
  onDiscardDraft,
  onPromoteToMainSuccess,
}) => {
  const isBoilerplate = activeVariant === 'boilerplate';
  const [showWwaiSchemaModal, setShowWwaiSchemaModal] = useState(false);
  const [showPopulationJsonModal, setShowPopulationJsonModal] = useState(false);
  const [showMetadataModal, setShowMetadataModal] = useState(false);
  const [showDiffView, setShowDiffView] = useState(false);
  const [diffData, setDiffData] = useState<{
    original: SectionData;
    staging: SectionData;
  } | null>(null);
  const [diffLoading, setDiffLoading] = useState(false);
  const [diffError, setDiffError] = useState<string | null>(null);

  const handleViewDiff = async () => {
    setDiffLoading(true);
    setDiffError(null);
    try {
      const [templateRes, stagingRes] = await Promise.all([
        fetch('/api/sections/template', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ section_id: sectionId }),
        }),
        fetch('/api/sections/staging/get', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ section_id: sectionId }),
        }),
      ]);

      if (!templateRes.ok) {
        const errBody = await templateRes.json().catch(() => ({}));
        throw new Error(errBody.detail || `Failed to fetch original: ${templateRes.status}`);
      }

      const templateMapping = await templateRes.json();
      const originalSectionData = sectionMappingToSectionData(templateMapping);

      if (!stagingRes.ok) {
        if (stagingRes.status === 404) {
          setDiffError('No draft for this section. Save your edits first.');
          setDiffLoading(false);
          return;
        }
        const errBody = await stagingRes.json().catch(() => ({}));
        throw new Error(errBody.detail || `Failed to fetch staging: ${stagingRes.status}`);
      }

      const stagingMapping = await stagingRes.json();
      const stagingSectionData = sectionMappingToSectionData(stagingMapping);

      setDiffData({ original: originalSectionData, staging: stagingSectionData });
      setShowDiffView(true);
    } catch (e) {
      setDiffError(e instanceof Error ? e.message : 'Failed to load diff');
    } finally {
      setDiffLoading(false);
    }
  };

  return (
    <>
      <EditorProvider
        key={`${sectionId}-${activeVariant}`}
        sectionData={sectionData}
        sectionId={sectionId}
        setCompiledHtml={setCompiledHtml}
        onSave={isBoilerplate ? undefined : onSave}
        readOnly={isBoilerplate}
      >
        <CodeViewerInner
          onClear={onClear}
          sectionName={sectionData.definition?.section_name || sectionId}
          sectionId={sectionId}
          activeVariant={activeVariant}
          stagingExists={stagingExists}
          onSwitchVariant={onSwitchVariant}
          switchingLoading={switchingLoading}
          onViewDiff={handleViewDiff}
          onDiscardDraft={onDiscardDraft}
          onOpenWwaiSchema={() => setShowWwaiSchemaModal(true)}
          onOpenPopulationJson={() => setShowPopulationJsonModal(true)}
          onOpenMetadata={() => setShowMetadataModal(true)}
        />
      </EditorProvider>
      {diffLoading && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            zIndex: 99,
            background: 'rgba(0,0,0,0.5)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: 14,
            color: 'white',
          }}
        >
          Loading diff…
        </div>
      )}
      {diffError && !diffLoading && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            zIndex: 99,
            background: 'rgba(0,0,0,0.5)',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 6,
          }}
        >
          <span style={{ color: 'white', fontSize: 14 }}>{diffError}</span>
          <button
            type="button"
            onClick={() => setDiffError(null)}
            style={{
              padding: '6px 12px',
              fontSize: 13,
              cursor: 'pointer',
              background: 'var(--accent-blue)',
              border: 'none',
              borderRadius: 4,
              color: 'white',
            }}
          >
            Dismiss
          </button>
        </div>
      )}
      {showDiffView && diffData && (
        <DiffViewer
          originalSectionData={diffData.original}
          stagingSectionData={diffData.staging}
          sectionId={sectionId}
          onClose={() => {
            setShowDiffView(false);
            setDiffData(null);
          }}
          onSaveSuccess={onPromoteToMainSuccess}
        />
      )}
      <WwaiSchemaModal
        open={showWwaiSchemaModal}
        onClose={() => setShowWwaiSchemaModal(false)}
        sectionId={sectionId}
      />
      <PopulationJsonModal
        open={showPopulationJsonModal}
        onClose={() => setShowPopulationJsonModal(false)}
        sectionId={sectionId}
      />
      <MetadataModal
        open={showMetadataModal}
        onClose={() => setShowMetadataModal(false)}
        sectionId={sectionId}
      />
    </>
  );
};

export default CodeEditorMain;

