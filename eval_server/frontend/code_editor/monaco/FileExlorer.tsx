import React, { useRef, useEffect, useState } from 'react';
import { Files, ChevronRight, ChevronDown, ChevronLeft, X, Plus, Trash2 } from 'lucide-react';
import { getFileIcon } from './iconUtils';
import { useEditor } from './EditorContext';
import { FileItem, getFileLanguage } from '../types/editor';

const findFileById = (items: FileItem[], id: string): FileItem | null => {
  for (const item of items) {
    if (item.id === id) return item;
    if (item.children) {
      const found = findFileById(item.children, id);
      if (found) return found;
    }
  }
  return null;
};

type AddFilePopup = {
  folderName: 'snippets' | 'assets';
  fileType: 'snippet' | 'css' | 'js';
};

const FileExplorer: React.FC<{}> = () => {
  const { files, activeFileId, openTabs, selectFile, toggleFolder, closeTab, selectTab, toggleExplorer, addFile, removeFile, readOnly } = useEditor();
  const activeFileRef = useRef<HTMLDivElement | null>(null);
  const [contextMenu, setContextMenu] = useState<{ x: number; y: number; folderName?: string; fileId?: string } | null>(null);
  const [addFilePopup, setAddFilePopup] = useState<AddFilePopup | null>(null);
  const [addFileNameInput, setAddFileNameInput] = useState('');
  const addFileInputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    if (activeFileId && activeFileRef.current) {
      activeFileRef.current.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    }
  }, [activeFileId]);

  const handleFileClick = (file: FileItem) => {
    if (file.type === 'folder') {
      toggleFolder(file.id);
    } else {
      const fileWithLanguage = {
        ...file,
        language: file.language || getFileLanguage(file.name)
      };
      selectFile(fileWithLanguage);
    }
  };

  const handleRightClick = (e: React.MouseEvent, item: FileItem, parentFolderName?: string) => {
    e.preventDefault();
    e.stopPropagation();
    if (readOnly) return;
    if (item.type === 'folder' && (item.name === 'snippets' || item.name === 'assets')) {
      setContextMenu({ x: e.clientX, y: e.clientY, folderName: item.name });
    } else if (item.type === 'file' && parentFolderName && (parentFolderName === 'snippets' || parentFolderName === 'assets')) {
      setContextMenu({ x: e.clientX, y: e.clientY, fileId: item.id });
    }
  };

  useEffect(() => {
    const handleClickOutside = () => setContextMenu(null);
    if (contextMenu) {
      document.addEventListener('click', handleClickOutside);
      return () => document.removeEventListener('click', handleClickOutside);
    }
  }, [contextMenu]);

  const openAddFilePopup = (folderName: 'snippets' | 'assets', fileType: 'snippet' | 'css' | 'js') => {
    setContextMenu(null);
    setAddFilePopup({ folderName, fileType });
    setAddFileNameInput('');
  };

  useEffect(() => {
    if (addFilePopup) {
      const timer = setTimeout(() => addFileInputRef.current?.focus(), 50);
      return () => clearTimeout(timer);
    }
  }, [addFilePopup]);

  const closeAddFilePopup = () => {
    setAddFilePopup(null);
    setAddFileNameInput('');
  };

  const handleCreateFile = () => {
    if (!addFilePopup) return;
    const name = addFileNameInput.trim();
    addFile(addFilePopup.folderName, addFilePopup.fileType, name || undefined);
    closeAddFilePopup();
  };

  useEffect(() => {
    if (!addFilePopup) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') closeAddFilePopup();
      if (e.key === 'Enter') {
        const name = addFileNameInput.trim();
        addFile(addFilePopup.folderName, addFilePopup.fileType, name || undefined);
        closeAddFilePopup();
      }
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [addFilePopup, addFileNameInput, addFile]);

  const renderFileTree = (items: FileItem[], depth = 0, parentFolderName?: string): React.ReactNode => {
    return items.map(item => {
      const isActive = activeFileId === item.id && item.type === 'file';
      const isFolder = item.type === 'folder';
      const isOpen = isFolder && item.isOpen;

      const canAddFile = !readOnly && isFolder && (item.name === 'snippets' || item.name === 'assets');
      const canDeleteFile = !readOnly && !isFolder && parentFolderName && (parentFolderName === 'snippets' || parentFolderName === 'assets');

      return (
        <div key={item.id}>
          <div
            ref={isActive ? (el) => { activeFileRef.current = el; } : undefined}
            className={`flex items-center py-2 px-3 cursor-pointer hover:bg-gray-700 transition-colors duration-150 group ${
              isActive ? 'bg-blue-600' : ''
            }`}
            style={{ paddingLeft: `${8 + depth * 16}px` }}
            onClick={() => handleFileClick(item)}
            onContextMenu={(e) => handleRightClick(e, item, parentFolderName)}
            title={item.name}
          >
            <span className="mr-2 flex-shrink-0 w-4 flex items-center justify-center">
              {isFolder ? (
                isOpen ? (
                  <ChevronDown size={14} className="text-gray-400" />
                ) : (
                  <ChevronRight size={14} className="text-gray-400" />
                )
              ) : null}
            </span>
            <span className="mr-2 flex-shrink-0">{getFileIcon(item)}</span>
            <span className="text-sm text-gray-200 flex-1 truncate">
              {item.name}
            </span>
            {isFolder && item.children && (
              <span className="text-xs text-gray-500 ml-1">
                {item.children.length}
              </span>
            )}
            {canAddFile && (
              <button
                type="button"
                className="ml-1 p-0.5 rounded opacity-0 group-hover:opacity-100 hover:bg-gray-600 text-gray-400 hover:text-white transition-all flex-shrink-0"
                onClick={(e) => {
                  e.stopPropagation();
                  if (item.name === 'snippets') {
                    openAddFilePopup('snippets', 'snippet');
                  } else {
                    openAddFilePopup('assets', 'css');
                  }
                }}
                title="Add new file"
              >
                <Plus size={14} />
              </button>
            )}
            {canDeleteFile && (
              <button
                type="button"
                className="ml-1 p-0.5 rounded opacity-0 group-hover:opacity-100 hover:bg-red-600/80 text-gray-400 hover:text-white transition-all flex-shrink-0"
                onClick={(e) => {
                  e.stopPropagation();
                  removeFile(item.id);
                }}
                title="Delete file"
              >
                <Trash2 size={14} />
              </button>
            )}
          </div>
          {isFolder && isOpen && item.children && (
            <div>
              {renderFileTree(item.children, depth + 1, item.name)}
            </div>
          )}
        </div>
      );
    });
  };

  const getTotalFileCount = (items: FileItem[]): number => {
    let count = 0;
    items.forEach(item => {
      if (item.type === 'file') {
        count++;
      } else if (item.children) {
        count += getTotalFileCount(item.children);
      }
    });
    return count;
  };

  const totalFiles = getTotalFileCount(files);

  return (
    <div 
      className="bg-gray-800 border-r border-gray-700 flex flex-col h-full"
    >
      <div className="flex items-center justify-between p-2 border-b border-gray-700">
        <h3 className="text-sm font-semibold text-gray-200">EXPLORER</h3>
        <div className="flex items-center gap-1">
          <span className="text-xs text-gray-500">{totalFiles} files</span>
          <button
            onClick={toggleExplorer}
            className="p-1 rounded hover:bg-gray-700 text-gray-400 hover:text-white transition-colors"
            title="Collapse explorer"
          >
            <ChevronLeft size={16} />
          </button>
        </div>
      </div>
      
      <div className="flex-1 overflow-y-auto scrollbar-thin scrollbar-thumb-gray-600 scrollbar-track-gray-800 min-h-0">
        {files.length > 0 ? (
          <div className="py-2">
            {renderFileTree(files)}
          </div>
        ) : (
          <div className="p-4 text-center text-gray-500 text-sm">
            <div className="mb-2 flex justify-center">
              <Files size={32} className="text-gray-600" />
            </div>
            <p>No files to display</p>
          </div>
        )}
      </div>

      {contextMenu && (
        <div
          className="fixed z-50 bg-gray-800 border border-gray-600 rounded shadow-lg py-1 min-w-[160px]"
          style={{ left: contextMenu.x, top: contextMenu.y }}
          onClick={(e) => e.stopPropagation()}
        >
          {contextMenu.fileId && (
            <button
              type="button"
              className="w-full px-3 py-2 text-left text-sm text-red-400 hover:bg-gray-700 flex items-center gap-2"
              onClick={() => {
                if (contextMenu.fileId) removeFile(contextMenu.fileId);
                setContextMenu(null);
              }}
            >
              <Trash2 size={14} />
              Delete
            </button>
          )}
          {contextMenu.folderName === 'snippets' && (
            <button
              type="button"
              className="w-full px-3 py-2 text-left text-sm text-gray-200 hover:bg-gray-700"
              onClick={() => openAddFilePopup('snippets', 'snippet')}
            >
              New snippet
            </button>
          )}
          {contextMenu.folderName === 'assets' && (
            <>
              <button
                type="button"
                className="w-full px-3 py-2 text-left text-sm text-gray-200 hover:bg-gray-700"
                onClick={() => openAddFilePopup('assets', 'css')}
              >
                New CSS file
              </button>
              <button
                type="button"
                className="w-full px-3 py-2 text-left text-sm text-gray-200 hover:bg-gray-700"
                onClick={() => openAddFilePopup('assets', 'js')}
              >
                New JS file
              </button>
            </>
          )}
        </div>
      )}

      {addFilePopup && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={closeAddFilePopup}>
          <div
            className="bg-gray-800 border border-gray-600 rounded-lg shadow-xl p-4 min-w-[280px]"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="text-sm font-medium text-gray-200 mb-1">
              New {addFilePopup.fileType === 'snippet' ? 'snippet' : addFilePopup.fileType === 'css' ? 'CSS' : 'JS'} file
            </div>
            <div className="text-xs text-gray-500 mb-2">
              {addFilePopup.fileType === 'snippet' ? '.liquid' : addFilePopup.fileType === 'css' ? '.css' : '.js'} will be added if omitted
            </div>
            <input
              ref={(el) => { addFileInputRef.current = el; }}
              type="text"
              value={addFileNameInput}
              onChange={(e) => setAddFileNameInput(e.target.value)}
              placeholder={
                addFilePopup.fileType === 'snippet'
                  ? 'main_component'
                  : addFilePopup.fileType === 'css'
                    ? 'new_style'
                    : 'new_script'
              }
              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded text-gray-200 text-sm placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 mb-4"
            />
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={closeAddFilePopup}
                className="px-3 py-1.5 text-sm text-gray-300 hover:text-white hover:bg-gray-700 rounded"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleCreateFile}
                className="px-3 py-1.5 text-sm bg-blue-600 hover:bg-blue-700 text-white rounded"
              >
                Create
              </button>
            </div>
          </div>
        </div>
      )}

      {openTabs.length > 0 && (
        <div className="flex-shrink-0 border-t border-gray-700">
          <div className="px-2 py-1.5 text-xs font-medium text-gray-400">Open files</div>
          <div className="max-h-32 overflow-y-auto scrollbar-thin scrollbar-thumb-gray-600 scrollbar-track-gray-800">
            {openTabs.map(tabId => {
              const file = findFileById(files, tabId);
              if (!file) return null;
              const isActive = activeFileId === tabId;
              return (
                <div
                  key={tabId}
                  className={`flex items-center px-2 py-1.5 cursor-pointer group hover:bg-gray-700 ${
                    isActive ? 'bg-gray-700' : ''
                  }`}
                  onClick={() => selectTab(tabId)}
                >
                  <span className="mr-2 flex-shrink-0">{getFileIcon(file)}</span>
                  <span className="text-xs text-gray-200 flex-1 truncate" title={file.name}>
                    {file.name}
                  </span>
                  <button
                    className="ml-1 opacity-0 group-hover:opacity-100 hover:bg-gray-600 rounded p-0.5 flex-shrink-0"
                    onClick={(e) => { e.stopPropagation(); closeTab(tabId); }}
                    title="Close"
                  >
                    <X size={12} />
                  </button>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};

export default FileExplorer;