export interface FileItem {
    id: string;
    name: string;
    type: 'file' | 'folder';
    content?: string;
    language?: string;
    children?: FileItem[];
    isOpen?: boolean;
  }
  
  // Supported languages
  export const SUPPORTED_LANGUAGES = [
    'javascript',
    'typescript', 
    'html',
    'css',
    'json',
    'liquid'
  ] as const;
  
  export type SupportedLanguage = typeof SUPPORTED_LANGUAGES[number];
  
  // Language mapping from file extensions
  export const EXTENSION_TO_LANGUAGE: Record<string, SupportedLanguage> = {
    'js': 'javascript',
    'jsx': 'javascript',
    'ts': 'typescript',
    'tsx': 'typescript',
    'css': 'css',
    'scss': 'css',
    'html': 'html',
    'json': 'json',
    'liquid': 'liquid'
  };
  
  // Utility function for getting file language
  export const getFileLanguage = (fileName: string): SupportedLanguage => {
    const ext = fileName.split('.').pop()?.toLowerCase();
    return EXTENSION_TO_LANGUAGE[ext || ''] || 'javascript';
  };
  
  // Monaco Editor default options
  export const DEFAULT_EDITOR_OPTIONS = {
    minimap: { enabled: true },
    fontSize: 12,
    fontFamily: 'Menlo, Monaco, "Courier New", monospace',
    lineNumbers: 'on' as const,
    wordWrap: 'on' as const,
    automaticLayout: true,
    scrollBeyondLastLine: false,
    readOnly: false,
    cursorStyle: 'line' as const,
    mouseWheelZoom: true,
    tabSize: 2,
    insertSpaces: true,
    detectIndentation: true,
    folding: true,
    foldingHighlight: true,
    foldingStrategy: 'indentation' as const,
    showFoldingControls: 'always' as const,
    unfoldOnClickAfterEndOfLine: false,
    bracketPairColorization: {
      enabled: true,
    },
    guides: {
      bracketPairs: true,
      indentation: true,
    },
    suggest: {
      showKeywords: true,
      showSnippets: true,
      showClasses: true,
      showFunctions: true,
      showVariables: true,
    },
    quickSuggestions: {
      other: true,
      comments: true,
      strings: true,
    },
  };
  
  interface SectionDefinition {
    shop_url: string;
    theme_id: string;
    section_name: string;
    section_filename: string;
  }
  
  interface Asset {
    key: string;
    content_type: string;
    value: string;
    public_url?: string | null;
  }
  
  interface SectionContent {
    liquid_file_content: string;
    liquid_schema: any;
    css_files: Record<string, Asset>;
    js_files: Record<string, Asset>;
    snippets: Record<string, Asset>;
    section_custom_css: string[];
  }
  
  export type CodeVariant = 'original' | 'staging' | 'boilerplate';

  export interface SectionData {
    definition: SectionDefinition;
    content: SectionContent;
    metadata?: any;
    usage?: any;
    reference_template_json?: any;
  }