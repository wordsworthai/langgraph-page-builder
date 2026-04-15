import React from 'react';
import { 
  Folder, 
  FolderOpen, 
  FileText, 
  Globe, 
  Palette, 
  Braces, 
  Droplets,
  FileCode
} from 'lucide-react';
import { FileItem } from '../types/editor';


/**
 * Returns the appropriate Lucide React icon for a file or folder
 */
export const getFileIcon = (file: FileItem): React.ReactElement => {
  const iconProps = { size: 16, className: "text-gray-400" };
  
  if (file.type === 'folder') {
    return file.isOpen 
      ? <FolderOpen {...iconProps} className="text-blue-400" />
      : <Folder {...iconProps} className="text-blue-400" />;
  }

  const ext = file.name.split('.').pop()?.toLowerCase();
  
  switch (ext) {
    case 'js':
    case 'jsx':
      return <FileCode {...iconProps} className="text-yellow-400" />;
    case 'ts':
    case 'tsx':
      return <FileCode {...iconProps} className="text-blue-400" />;
    case 'css':
    case 'scss':
      return <Palette {...iconProps} className="text-pink-400" />;
    case 'html':
      return <Globe {...iconProps} className="text-orange-400" />;
    case 'json':
      return <Braces {...iconProps} className="text-green-400" />;
    case 'liquid':
      return <Droplets {...iconProps} className="text-cyan-400" />;
    default:
      return <FileText {...iconProps} className="text-gray-400" />;
  }
};