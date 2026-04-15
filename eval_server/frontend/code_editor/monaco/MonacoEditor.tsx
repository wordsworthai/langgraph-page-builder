import React, { useState, useRef, useEffect } from 'react';
import Editor from '@monaco-editor/react';
import { FileItem, SUPPORTED_LANGUAGES, DEFAULT_EDITOR_OPTIONS, SupportedLanguage } from '../types/editor';
import { Expand, Minimize, Settings, X, Save } from 'lucide-react';
import { getFileIcon } from './iconUtils';
import { useEditor } from './EditorContext';

const CodeEditor: React.FC<{}> = () => {
  const { activeFile, openTabs, files, changeContent, closeTab, selectTab, toggleFullscreen, 
    isFullscreen, hasUnsavedChanges, save, isSaving, canSave, readOnly } = useEditor();

  const [language, setLanguage] = useState<SupportedLanguage>(
    (activeFile?.language as SupportedLanguage) || 'liquid'
  );
  const editorRef = useRef<any>(null);

  useEffect(() => {
    if (activeFile?.language && SUPPORTED_LANGUAGES.includes(activeFile.language as SupportedLanguage)) {
      setLanguage(activeFile.language as SupportedLanguage);
    }
  }, [activeFile]);

  const findFileById = (fileId: string): FileItem | null => {
    const findInFiles = (items: FileItem[]): FileItem | null => {
      for (const file of items) {
        if (file.id === fileId) return file;
        if (file.children) {
          const found = findInFiles(file.children);
          if (found) return found;
        }
      }
      return null;
    };
    return findInFiles(files);
  };

  const editorOptions = {
    ...DEFAULT_EDITOR_OPTIONS,
    minimap: { enabled: false },
    wordWrap: 'on' as const,
    readOnly,
  };

  const handleEditorDidMount = (editor: any, monacoInstance: any) => {
    editorRef.current = editor;
    editor.addCommand(
      monacoInstance.KeyMod.CtrlCmd | monacoInstance.KeyCode.KeyS,
      () => {
        if (activeFile && hasUnsavedChanges && canSave) {
          save();
        }
      }
    );

    editor.addCommand(
      monacoInstance.KeyCode.F11,
      () => {
        toggleFullscreen();
      }
    );

    editor.addAction({
      id: 'format-document',
      label: 'Format Document',
      keybindings: [monacoInstance.KeyMod.Shift | monacoInstance.KeyMod.Alt | monacoInstance.KeyCode.KeyF],
      run: () => {
        editor.trigger('format', 'editor.action.formatDocument', {});
      },
    });

    editor.addCommand(
      monacoInstance.KeyMod.CtrlCmd | monacoInstance.KeyCode.Slash,
      () => {
        editor.trigger('comment', 'editor.action.commentLine', {});
      }
    );

  };

  const handleEditorChange = (value: string | undefined) => {
    if (activeFile && value !== undefined && !readOnly) {
      changeContent(activeFile.id, value);
    }
  };

  const handleTabClose = (fileId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    closeTab(fileId);
  };

  const handleSave = () => {
    if (hasUnsavedChanges && !isSaving && canSave) {
      save();
    }
  };

  useEffect(() => {
    if (editorRef.current) {
      const timeoutId = setTimeout(() => {
        editorRef.current.layout();
      }, 150);
      return () => clearTimeout(timeoutId);
    }
  }, [isFullscreen]);

  const editorHeight = isFullscreen ? 'calc(100vh - 68px)' : '100%';

  if (!activeFile && openTabs.length === 0) {
    return (
      <div className="flex-1 flex flex-col bg-gray-900 min-w-0">
        <div className="flex items-center justify-center h-full text-gray-500">
          <div className="text-center max-w-md">
            <div className="mb-4 flex justify-center">
              <Settings size={48} className="text-gray-600" />
            </div>
            <h2 className="text-2xl mb-2 text-gray-400">Code Editor</h2>
            <p className="text-gray-500 mb-4">
              {isFullscreen ? 'Fullscreen mode active - ' : ''}
              Select a file from the explorer to start editing
            </p>
            <div className="bg-gray-800 rounded-lg p-4 text-left text-sm">
              <h3 className="text-gray-300 font-semibold mb-2">Editing Rules:</h3>
              <div className="text-gray-400 space-y-1">
                <div className="flex items-center">
                  <span className="w-2 h-2 bg-green-500 rounded-full mr-2"></span>
                  Section files are editable
                </div>
                <div className="flex items-center">
                  <span className="w-2 h-2 bg-red-500 rounded-full mr-2"></span>
                  Assets and snippets are read-only
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col bg-gray-900 min-w-0">
      {openTabs.length > 0 && (
        <div className={`flex justify-between bg-gray-800 border-b border-gray-700 transition-all ${
          isFullscreen ? 'bg-gray-900 border-gray-600' : ''
        }`}>
          <div className="flex-1 flex overflow-x-auto scrollbar-thin scrollbar-thumb-gray-600 scrollbar-track-gray-800">
            {openTabs.map(tabId => {
              const file = findFileById(tabId);
              if (!file) return null;
              return (
                <div
                  key={tabId}
                  className={`flex-shrink-0 flex items-center px-3 py-2 border-r border-gray-700 cursor-pointer min-w-0 max-w-xs group transition-colors ${
                    activeFile?.id === tabId 
                      ? (isFullscreen ? 'bg-gray-800 text-white' : 'bg-gray-900 text-white')
                      : 'bg-gray-800 text-gray-400 hover:text-white hover:bg-gray-750'
                  }`}
                  onClick={() => selectTab(tabId)}
                >
                  <span className="mr-2 flex-shrink-0">{getFileIcon(file)}</span>
                  <span className="text-sm truncate flex-1 flex items-center" title={file.name}>
                    {file.name}
                  </span>
                  <button
                    className="ml-2 opacity-0 group-hover:opacity-100 hover:bg-gray-600 rounded p-0.5 text-xs transition-all"
                    onClick={(e) => handleTabClose(tabId, e)}
                    title="Close tab"
                  >
                    <X size={14} />
                  </button>
                </div>
              );
            })}
          </div>
          <div className="flex items-center border-l border-gray-700">
            {hasUnsavedChanges && canSave && (
              <button
                onClick={handleSave}
                disabled={isSaving}
                className={`px-3 py-2 text-white transition-colors flex items-center gap-1 ${
                  isSaving 
                    ? 'bg-gray-600 cursor-not-allowed' 
                    : 'bg-green-600 hover:bg-green-700'
                }`}
                title="Save changes (Ctrl+S)"
              >
                {isSaving ? (
                  <div className="animate-spin">
                    <Settings size={14} />
                  </div>
                ) : (
                  <Save size={14} />
                )}
                <span className="text-xs hidden sm:inline">
                  {isSaving ? 'Saving...' : 'Save'}
                </span>
              </button>
            )}
            <button
              onClick={toggleFullscreen}
              className={`px-3 py-2 text-gray-400 hover:text-white transition-colors ${
                isFullscreen 
                  ? 'bg-blue-600 text-white hover:bg-blue-700' 
                  : 'hover:bg-gray-700'
              }`}
              title={isFullscreen ? "Exit fullscreen (F11 or Esc)" : "Enter fullscreen (F11)"}
            >
              {isFullscreen ? (
                <Minimize size={16} />
              ) : (
                <Expand size={16} />
              )}
            </button>
          </div>
        </div>
      )}
      <div className="flex-1 min-h-0 flex flex-col overflow-hidden">
        {activeFile ? (
          <Editor
            key={activeFile.id}
            height={editorHeight}
            language={language}
            value={activeFile.content || ''}
            path={activeFile ? `${activeFile.name}-${activeFile.id}` : undefined}
            theme="vs-dark"
            onChange={handleEditorChange}
            onMount={handleEditorDidMount}
            keepCurrentModel={false}
            options={editorOptions}
            loading={
              <div className="flex items-center justify-center h-full bg-gray-900 text-gray-400">
                <div className="text-center">
                  <div className="animate-spin mb-2">
                    <Settings size={24} />
                  </div>
                  <p>Loading Code Editor...</p>
                </div>
              </div>
            }
          />
        ) : (
          <div className="flex items-center justify-center h-full text-gray-500">
            <p>Select a file to start editing</p>
          </div>
        )}
      </div>

      <div className="bg-gray-800 text-gray-300 px-4 py-1 text-xs flex justify-between items-center border-t border-gray-700">
        <div className="flex gap-4">
          {activeFile && (
            <>
              <span>Lines: {(activeFile.content || '').split('\n').length}</span>
              <span>Chars: {(activeFile.content || '').length}</span>
              {hasUnsavedChanges && (
                <span className="text-orange-400">• Unsaved changes</span>
              )}
            </>
          )}
        </div>
        <div className="flex gap-2 items-center">
          <select
            value={language}
            onChange={(e) => setLanguage(e.target.value as SupportedLanguage)}
            className="bg-gray-700 text-white px-2 py-0.5 rounded text-xs border border-gray-600"
            disabled={!activeFile}
          >
            {SUPPORTED_LANGUAGES.map((lang) => (
              <option key={lang} value={lang}>
                {lang.charAt(0).toUpperCase() + lang.slice(1)}
              </option>
            ))}
          </select>
        </div>
      </div>
    </div>
  );
};

export default CodeEditor;