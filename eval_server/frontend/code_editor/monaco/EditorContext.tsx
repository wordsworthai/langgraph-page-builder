import React, { createContext, useCallback, useContext, useEffect, useMemo, useReducer, useRef } from 'react';
import { FileItem, SectionData } from '../types/editor';
import { ErrorMessage, SuccessMessage } from '../utils/notification.tsx';
import { sectionDataToSectionMapping } from '../utils/sectionDataMapper';

interface EditorState {
  files: FileItem[];
  originalFiles: FileItem[];
  activeFileId: string;
  openTabs: string[];
  isFullscreen: boolean;
  isExplorerCollapsed: boolean;
  hasUnsavedChanges: boolean;
  isSaving: boolean;
  isCompiling: boolean;
}

type EditorAction =
  | { type: 'INIT_FROM_SECTION'; payload: { files: FileItem[]; originalFiles: FileItem[]; activeFileId: string; openTabs: string[] } }
  | { type: 'SET_FILES'; payload: FileItem[] }
  | { type: 'SET_ORIGINAL_FILES'; payload: FileItem[] }
  | { type: 'SET_ACTIVE_FILE_ID'; payload: string }
  | { type: 'SET_OPEN_TABS'; payload: string[] }
  | { type: 'SELECT_FILE'; payload: { fileId: string } }
  | { type: 'ADD_FILE'; payload: { parentFolderName: 'snippets' | 'assets'; fileName: string; fileType: 'snippet' | 'css' | 'js' } }
  | { type: 'REMOVE_FILE'; payload: { fileId: string } }
  | { type: 'SET_FULLSCREEN'; payload: boolean }
  | { type: 'SET_EXPLORER_COLLAPSED'; payload: boolean }
  | { type: 'SET_HAS_UNSAVED_CHANGES'; payload: boolean }
  | { type: 'SAVE_START' }
  | { type: 'SAVE_END' }
  | { type: 'COMPILE_START' }
  | { type: 'COMPILE_END' };

const initialState: EditorState = {
  files: [],
  originalFiles: [],
  activeFileId: '',
  openTabs: [],
  isFullscreen: false,
  isExplorerCollapsed: false,
  hasUnsavedChanges: false,
  isSaving: false,
  isCompiling: false,
};

function editorReducer(state: EditorState, action: EditorAction): EditorState {
  switch (action.type) {
    case 'INIT_FROM_SECTION': {
      return {
        ...state,
        files: action.payload.files,
        originalFiles: action.payload.originalFiles,
        activeFileId: action.payload.activeFileId,
        openTabs: action.payload.openTabs,
        hasUnsavedChanges: false,
      };
    }
    case 'SET_FILES': {
      return { ...state, files: action.payload };
    }
    case 'SET_ORIGINAL_FILES': {
      return { ...state, originalFiles: action.payload };
    }
    case 'SET_ACTIVE_FILE_ID': {
      return { ...state, activeFileId: action.payload };
    }
    case 'SET_OPEN_TABS': {
      return { ...state, openTabs: action.payload };
    }
    case 'SELECT_FILE': {
      const { fileId } = action.payload;
      const alreadyOpen = state.openTabs.includes(fileId);
      return {
        ...state,
        activeFileId: fileId,
        openTabs: alreadyOpen ? state.openTabs : [...state.openTabs, fileId],
      };
    }
    case 'ADD_FILE': {
      const { parentFolderName, fileName, fileType } = action.payload;
      const { newFiles, newFileId } = addFileToFolder(state.files, parentFolderName, fileName, fileType);
      return {
        ...state,
        files: newFiles,
        activeFileId: newFileId,
        openTabs: [...state.openTabs, newFileId],
      };
    }
    case 'REMOVE_FILE': {
      const { fileId } = action.payload;
      const newFiles = removeFileFromTree(state.files, fileId);
      const newOpenTabs = state.openTabs.filter(id => id !== fileId);
      let newActiveFileId = state.activeFileId;
      if (state.activeFileId === fileId) {
        newActiveFileId = newOpenTabs[newOpenTabs.length - 1] || newOpenTabs[0] || '';
      }
      return {
        ...state,
        files: newFiles,
        openTabs: newOpenTabs,
        activeFileId: newActiveFileId,
      };
    }
    case 'SET_FULLSCREEN': {
      return { ...state, isFullscreen: action.payload };
    }
    case 'SET_EXPLORER_COLLAPSED': {
      return { ...state, isExplorerCollapsed: action.payload };
    }
    case 'SET_HAS_UNSAVED_CHANGES': {
      return { ...state, hasUnsavedChanges: action.payload };
    }
    case 'SAVE_START': {
      return { ...state, isSaving: true };
    }
    case 'SAVE_END': {
      return { ...state, isSaving: false };
    }
    case 'COMPILE_START': {
      return { ...state, isCompiling: true };
    }
    case 'COMPILE_END': {
      return { ...state, isCompiling: false };
    }
    default:
      return state;
  }
}

// Utilities moved from CodeViewer
const findFileById = (files: FileItem[], id: string): FileItem | null => {
  for (const file of files) {
    if (file.id === id) return file;
    if (file.children) {
      const found = findFileById(file.children, id);
      if (found) return found;
    }
  }
  return null;
};

const updateFileContent = (files: FileItem[], id: string, content: string): FileItem[] => {
  return files.map(file => {
    if (file.id === id) {
      return { ...file, content };
    }
    if (file.children) {
      return { ...file, children: updateFileContent(file.children, id, content) };
    }
    return file;
  });
};

const toggleFolderOpen = (files: FileItem[], id: string): FileItem[] => {
  return files.map(file => {
    if (file.id === id && file.type === 'folder') {
      return { ...file, isOpen: !file.isOpen };
    }
    if (file.children) {
      return { ...file, children: toggleFolderOpen(file.children, id) };
    }
    return file;
  });
};

const removeFileFromTree = (files: FileItem[], fileId: string): FileItem[] => {
  return files.map(folder => {
    if (folder.type === 'folder' && folder.children) {
      const newChildren = folder.children.filter(c => c.id !== fileId);
      return { ...folder, children: newChildren };
    }
    return folder;
  });
};

const addFileToFolder = (
  files: FileItem[],
  parentFolderName: 'snippets' | 'assets',
  fileName: string,
  fileType: 'snippet' | 'css' | 'js'
): { newFiles: FileItem[]; newFileId: string } => {
  const newFileId = `new-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
  const language = fileType === 'snippet' ? 'liquid' : fileType === 'css' ? 'css' : 'javascript';
  const newFile: FileItem = {
    id: newFileId,
    name: fileName,
    type: 'file',
    language,
    content: ''
  };

  const newFiles = files.map(folder => {
    if (folder.name === parentFolderName && folder.type === 'folder') {
      const children = [...(folder.children || []), newFile];
      return { ...folder, children, isOpen: true };
    }
    return folder;
  });

  return { newFiles, newFileId };
};

const convertSectionDataToFiles = (sectionData: SectionData): FileItem[] => {
  const { definition, content } = sectionData;
  const files: FileItem[] = [];
  let fileIdCounter = 1;

  const sectionsChildren: FileItem[] = [];
  const sectionLiquidContent = `${content.liquid_file_content}

{% schema %}
${JSON.stringify(content.liquid_schema, null, 2)}
{% endschema %}`;

  const sectionFile: FileItem = {
    id: (fileIdCounter++).toString(),
    name: definition.section_filename,
    type: 'file',
    language: 'liquid',
    content: sectionLiquidContent
  };
  sectionsChildren.push(sectionFile);
  const sectionsFolder: FileItem = {
    id: (fileIdCounter++).toString(),
    name: 'sections',
    type: 'folder',
    isOpen: true,
    children: sectionsChildren
  };
  files.push(sectionsFolder);

  // Always create snippets folder (even when empty) so users can add new files
  const snippetsChildren: FileItem[] = [];
  Object.entries(content.snippets).forEach(([filename, snippetData]) => {
    const snippetContent = snippetData.value || '';
    const snippetFilename = filename.endsWith('.liquid') ? filename : `${filename}.liquid`;
    snippetsChildren.push({
      id: (fileIdCounter++).toString(),
      name: snippetFilename,
      type: 'file',
      language: 'liquid',
      content: snippetContent
    });
  });
  const snippetsFolder: FileItem = {
    id: (fileIdCounter++).toString(),
    name: 'snippets',
    type: 'folder',
    isOpen: true,
    children: snippetsChildren
  };
  files.push(snippetsFolder);

  // Always create assets folder (even when empty) so users can add new files
  const assetsChildren: FileItem[] = [];
  Object.entries(content.css_files).forEach(([filename, fileData]) => {
    const cssContent = fileData.value || '';
    const cssFileName = filename.endsWith('.css') ? filename : `${filename}.css`;
    assetsChildren.push({
      id: (fileIdCounter++).toString(),
      name: cssFileName,
      type: 'file',
      language: 'css',
      content: cssContent
    });
  });
  Object.entries(content.js_files).forEach(([filename, fileData]) => {
    const jsContent = fileData.value || '';
    const jsFileName = filename.endsWith('.js') ? filename : `${filename}.js`;
    assetsChildren.push({
      id: (fileIdCounter++).toString(),
      name: jsFileName,
      type: 'file',
      language: 'javascript',
      content: jsContent
    });
  });
  if (content.section_custom_css && content.section_custom_css.length > 0) {
    const customCssContent = content.section_custom_css.join('\n\n');
    const customCssFile: FileItem = {
      id: (fileIdCounter++).toString(),
      name: `${definition.section_name.replace(/\s+/g, '_').toLowerCase()}_custom.css`,
      type: 'file',
      language: 'css',
      content: customCssContent
    };
    assetsChildren.push(customCssFile);
  }

  const assetsFolder: FileItem = {
    id: (fileIdCounter++).toString(),
    name: 'assets',
    type: 'folder',
    isOpen: true,
    children: assetsChildren
  };
  files.push(assetsFolder);

  return files;
};

const convertFilesToSectionData = (files: FileItem[], originalSectionData: SectionData): SectionData => {
  const updatedSectionData = { ...originalSectionData };
  // Process sections folder
  const sectionsFolder = files.find(f => f.name === 'sections' && f.type === 'folder');
  if (sectionsFolder && sectionsFolder.children) {
    const sectionFile = sectionsFolder.children[0];
    if (sectionFile && sectionFile.content) {
      const content = sectionFile.content;
      const schemaRegex = /{% schema %}([\s\S]*?){% endschema %}/;
      const match = content.match(schemaRegex);
      if (match) {
        const liquidContent = content.substring(0, match.index).trim();
        try {
          const schemaJson = JSON.parse(match[1].trim());
          updatedSectionData.content = {
            ...updatedSectionData.content,
            liquid_file_content: liquidContent,
            liquid_schema: schemaJson
          };
        } catch (error) {
          updatedSectionData.content = {
            ...updatedSectionData.content,
            liquid_file_content: liquidContent
          };
        }
      } else {
        updatedSectionData.content = {
          ...updatedSectionData.content,
          liquid_file_content: content
        };
      }
    }
  }
  // Process snippets folder - build from tree (deleted files are excluded)
  // Compiler expects snippet keys WITH .liquid suffix (e.g. main_link.liquid)
  const snippetsFolder = files.find(f => f.name === 'snippets' && f.type === 'folder');
  if (snippetsFolder && snippetsFolder.children) {
    const updatedSnippets: Record<string, { key: string; content_type: string; value: string }> = {};
    snippetsFolder.children.forEach(snippetFile => {
      if (snippetFile.type === 'file' && snippetFile.content !== undefined) {
        const snippetKey = snippetFile.name.endsWith('.liquid') ? snippetFile.name : `${snippetFile.name}.liquid`;
        const existing = updatedSectionData.content.snippets[snippetKey] || updatedSectionData.content.snippets[snippetFile.name.replace(/\.liquid$/, '')];
        updatedSnippets[snippetKey] = {
          ...(existing || {}),
          key: snippetKey,
          content_type: 'text/html',
          value: snippetFile.content
        };
      }
    });
    updatedSectionData.content = {
      ...updatedSectionData.content,
      snippets: updatedSnippets
    };
  }
  // Process assets folder - build from tree (deleted files are excluded)
  const assetsFolder = files.find(f => f.name === 'assets' && f.type === 'folder');
  if (assetsFolder && assetsFolder.children) {
    const updatedCssFiles: Record<string, { key: string; content_type: string; value: string }> = {};
    const updatedJsFiles: Record<string, { key: string; content_type: string; value: string }> = {};
    let updatedCustomCss: string[] = [];
    assetsFolder.children.forEach(assetFile => {
      if (assetFile.type === 'file' && assetFile.content !== undefined) {
        if (assetFile.name.endsWith('.css')) {
          if (assetFile.name.includes('_custom.css')) {
            updatedCustomCss = [assetFile.content];
          } else {
            const cssKey = assetFile.name.replace(/\.css$/, '');
            const existing = updatedSectionData.content.css_files[cssKey] || updatedSectionData.content.css_files[`${cssKey}.css`];
            updatedCssFiles[cssKey] = {
              ...(existing || {}),
              key: cssKey,
              content_type: 'text/css',
              value: assetFile.content
            };
          }
        }
        if (assetFile.name.endsWith('.js')) {
          const jsKey = assetFile.name.replace(/\.js$/, '');
          const existing = updatedSectionData.content.js_files[jsKey] || updatedSectionData.content.js_files[`${jsKey}.js`];
          updatedJsFiles[jsKey] = {
            ...(existing || {}),
            key: jsKey,
            content_type: 'application/javascript',
            value: assetFile.content
          };
        }
      }
    });
    // updatedCustomCss stays [] if no _custom.css file in tree (deleted files excluded)
    updatedSectionData.content = {
      ...updatedSectionData.content,
      css_files: updatedCssFiles,
      js_files: updatedJsFiles,
      section_custom_css: updatedCustomCss
    };
  }
  return updatedSectionData;
};

interface EditorContextValue extends EditorState {
  activeFile: FileItem | null;
  selectFile: (file: FileItem) => void;
  toggleFolder: (folderId: string) => void;
  changeContent: (fileId: string, content: string) => void;
  closeTab: (fileId: string) => void;
  selectTab: (fileId: string) => void;
  addFile: (parentFolderName: 'snippets' | 'assets', fileType?: 'snippet' | 'css' | 'js', customFileName?: string) => void;
  removeFile: (fileId: string) => void;
  toggleFullscreen: () => void;
  toggleExplorer: () => void;
  save: () => Promise<void>;
  compile: () => Promise<void>;
  setFullscreenTarget: (el: HTMLElement | null) => void;
  canSave: boolean;
  readOnly: boolean;
}

const EditorContext = createContext<EditorContextValue | undefined>(undefined);

interface EditorProviderProps {
  sectionData?: SectionData;
  sectionId?: string;
  onSave?: (updatedSectionData: SectionData) => Promise<void> | void;
  setCompiledHtml?: (html: string) => void;
  readOnly?: boolean;
  children: React.ReactNode;
}

export const EditorProvider: React.FC<EditorProviderProps> = ({
  sectionData,
  sectionId,
  onSave,
  setCompiledHtml,
  readOnly = false,
  children,
}) => {
  const [state, dispatch] = useReducer(editorReducer, initialState);
  const fullscreenTargetRef = useRef<HTMLElement | null>(null);

  // Initialize from section data
  useEffect(() => {
    // Avoid re-initializing while the user has unsaved edits or while saving
    if (state.hasUnsavedChanges || state.isSaving) {
      return;
    }
    if (!sectionData) {
      dispatch({ type: 'INIT_FROM_SECTION', payload: { files: [], originalFiles: [], activeFileId: '', openTabs: [] } });
      return;
    }
    const newFiles = convertSectionDataToFiles(sectionData);
    const mainSectionFile = (() => {
      const sectionsFolder = newFiles.find(f => f.name === 'sections' && f.type === 'folder');
      if (sectionsFolder && sectionsFolder.children) {
        return sectionsFolder.children.find(f => f.type === 'file') || null;
      }
      return null;
    })();
    dispatch({
      type: 'INIT_FROM_SECTION',
      payload: {
        files: newFiles,
        originalFiles: JSON.parse(JSON.stringify(newFiles)),
        activeFileId: mainSectionFile ? mainSectionFile.id : '',
        openTabs: mainSectionFile ? [mainSectionFile.id] : [],
      },
    });
  }, [sectionData]);

  // Unsaved change detection
  useEffect(() => {
    if (state.originalFiles.length === 0 || state.files.length === 0) {
      dispatch({ type: 'SET_HAS_UNSAVED_CHANGES', payload: false });
      return;
    }
    const hasChanges = JSON.stringify(state.files) !== JSON.stringify(state.originalFiles);
    dispatch({ type: 'SET_HAS_UNSAVED_CHANGES', payload: hasChanges });
  }, [state.files, state.originalFiles]);

  // Fullscreen listeners
  useEffect(() => {
    const handleFullscreenChange = () => {
      const isActive = document.fullscreenElement === fullscreenTargetRef.current;
      dispatch({ type: 'SET_FULLSCREEN', payload: isActive });
    };
    document.addEventListener('fullscreenchange', handleFullscreenChange);
    document.addEventListener('webkitfullscreenchange', handleFullscreenChange as any);
    document.addEventListener('mozfullscreenchange', handleFullscreenChange as any);
    document.addEventListener('MSFullscreenChange', handleFullscreenChange as any);
    return () => {
      document.removeEventListener('fullscreenchange', handleFullscreenChange);
      document.removeEventListener('webkitfullscreenchange', handleFullscreenChange as any);
      document.removeEventListener('mozfullscreenchange', handleFullscreenChange as any);
      document.removeEventListener('MSFullscreenChange', handleFullscreenChange as any);
    };
  }, []);

  const activeFile = useMemo(() => findFileById(state.files, state.activeFileId), [state.files, state.activeFileId]);

  const selectFile = useCallback((file: FileItem) => {
    dispatch({ type: 'SELECT_FILE', payload: { fileId: file.id } });
  }, []);

  const toggleFolder = useCallback((folderId: string) => {
    dispatch({ type: 'SET_FILES', payload: toggleFolderOpen(state.files, folderId) });
  }, [state.files]);

  const addFile = useCallback((parentFolderName: 'snippets' | 'assets', fileType?: 'snippet' | 'css' | 'js', customFileName?: string) => {
    const folder = state.files.find(f => f.name === parentFolderName && f.type === 'folder');
    const existingNames = new Set((folder?.children || []).map(c => c.name));

    let fileName: string;
    let resolvedFileType: 'snippet' | 'css' | 'js';

    if (customFileName && customFileName.trim()) {
      let name = customFileName.trim();
      if (parentFolderName === 'snippets') {
        resolvedFileType = 'snippet';
        if (!name.endsWith('.liquid')) {
          name = name + '.liquid';
        }
      } else {
        resolvedFileType = fileType || 'css';
        if (resolvedFileType === 'css' && !name.endsWith('.css')) {
          name = name + '.css';
        } else if (resolvedFileType === 'js' && !name.endsWith('.js')) {
          name = name + '.js';
        }
      }
      if (existingNames.has(name)) {
        let i = 1;
        const base = name.replace(/\.(liquid|css|js)$/, '');
        const ext = name.match(/\.(liquid|css|js)$/)?.[0] || '';
        while (existingNames.has(base + '_' + i + ext)) {
          i++;
        }
        name = base + '_' + i + ext;
      }
      fileName = name;
    } else {
      if (parentFolderName === 'snippets') {
        resolvedFileType = 'snippet';
        let base = 'new_snippet.liquid';
        let i = 1;
        while (existingNames.has(base)) {
          base = `new_snippet_${i}.liquid`;
          i++;
        }
        fileName = base;
      } else {
        resolvedFileType = fileType || 'css';
        const baseName = resolvedFileType === 'css' ? 'new_style' : 'new_script';
        const ext = resolvedFileType === 'css' ? '.css' : '.js';
        let base = baseName + ext;
        let i = 1;
        while (existingNames.has(base)) {
          base = `${baseName}_${i}${ext}`;
          i++;
        }
        fileName = base;
      }
    }

    dispatch({ type: 'ADD_FILE', payload: { parentFolderName, fileName, fileType: resolvedFileType } });
  }, [state.files]);

  const removeFile = useCallback((fileId: string) => {
    dispatch({ type: 'REMOVE_FILE', payload: { fileId } });
  }, []);

  const changeContent = useCallback((fileId: string, content: string) => {
    const file = findFileById(state.files, fileId);
    if (!file) {
      console.warn('Editing not allowed for this type');
      return;
    }
    dispatch({ type: 'SET_FILES', payload: updateFileContent(state.files, fileId, content) });
  }, [state.files]);

  const closeTab = useCallback((fileId: string) => {
    const newOpenTabs = state.openTabs.filter(id => id !== fileId);
    dispatch({ type: 'SET_OPEN_TABS', payload: newOpenTabs });
    if (state.activeFileId === fileId) {
      const nextFileId = newOpenTabs[newOpenTabs.length - 1] || newOpenTabs[0] || '';
      dispatch({ type: 'SET_ACTIVE_FILE_ID', payload: nextFileId });
    }
  }, [state.openTabs, state.activeFileId]);

  const selectTab = useCallback((fileId: string) => {
    dispatch({ type: 'SET_ACTIVE_FILE_ID', payload: fileId });
  }, []);

  const setFullscreenTarget = useCallback((el: HTMLElement | null) => {
    fullscreenTargetRef.current = el;
  }, []);

  const toggleFullscreen = useCallback(() => {
    const target = fullscreenTargetRef.current || document.documentElement;
    if (!document.fullscreenElement) {
      target.requestFullscreen().catch((err) => {
        console.error(`Error attempting to enable full-screen mode: ${err.message} (${err.name})`);
      });
    } else {
      if ((document as any).exitFullscreen) {
        (document as any).exitFullscreen();
      }
    }
  }, []);

  const toggleExplorer = useCallback(() => {
    dispatch({ type: 'SET_EXPLORER_COLLAPSED', payload: !state.isExplorerCollapsed });
  }, [state.isExplorerCollapsed]);

  const save = useCallback(async () => {
    if (!sectionData || !onSave || !state.hasUnsavedChanges) return;
    dispatch({ type: 'SAVE_START' });
    try {
      const updatedSectionData = convertFilesToSectionData(state.files, sectionData);
      await onSave(updatedSectionData);
      dispatch({ type: 'SET_ORIGINAL_FILES', payload: JSON.parse(JSON.stringify(state.files)) });
      dispatch({ type: 'SET_HAS_UNSAVED_CHANGES', payload: false });
      SuccessMessage('Section saved successfully!');
    } catch (error) {
      console.error('Error saving:', error);
      const errorMessage = error instanceof Error ? error.message : 'Failed to save section. Please try again.';
      ErrorMessage(errorMessage);
    } finally {
      dispatch({ type: 'SAVE_END' });
    }
  }, [onSave, sectionData, state.files, state.hasUnsavedChanges]);

  const compile = useCallback(async () => {
    if (!sectionData || !sectionId || !setCompiledHtml) return;
    dispatch({ type: 'COMPILE_START' });
    try {
      const updatedSectionData = convertFilesToSectionData(state.files, sectionData);
      const sectionMapping = sectionDataToSectionMapping(updatedSectionData);
      const res = await fetch('/api/sections/compile', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ section_id: sectionId, section_mapping: sectionMapping }),
      });
      if (!res.ok) {
        const errBody = await res.json().catch(() => ({}));
        throw new Error(errBody.detail || `Compilation failed: ${res.status}`);
      }
      const { compiled_html } = await res.json();
      setCompiledHtml(compiled_html);
      SuccessMessage('Compiled successfully!');
    } catch (error) {
      console.error('Error compiling:', error);
      const errorMessage = error instanceof Error ? error.message : 'Compilation failed. Please try again.';
      ErrorMessage(errorMessage);
    } finally {
      dispatch({ type: 'COMPILE_END' });
    }
  }, [sectionData, sectionId, setCompiledHtml, state.files]);

  // Auto-compile when code editor opens with a section for the first time
  const hasAutoCompiledRef = useRef(false);
  useEffect(() => {
    if (
      hasAutoCompiledRef.current ||
      !sectionData ||
      !sectionId ||
      !setCompiledHtml ||
      state.files.length === 0
    ) {
      return;
    }
    hasAutoCompiledRef.current = true;
    compile();
  }, [sectionData, sectionId, setCompiledHtml, state.files.length, compile]);

  const value: EditorContextValue = {
    ...state,
    activeFile,
    selectFile,
    toggleFolder,
    changeContent,
    closeTab,
    selectTab,
    addFile,
    removeFile,
    toggleFullscreen,
    toggleExplorer,
    save,
    compile,
    setFullscreenTarget,
    canSave: !!onSave,
    readOnly,
  };

  return (
    <EditorContext.Provider value={value}>
      {children}
    </EditorContext.Provider>
  );
};

export const useEditor = (): EditorContextValue => {
  const ctx = useContext(EditorContext);
  if (!ctx) {
    throw new Error('useEditor must be used within an EditorProvider');
  }
  return ctx;
}; 