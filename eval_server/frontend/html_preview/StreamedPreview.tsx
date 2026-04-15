import React, { useMemo } from 'react';
import HtmlPreview from './HtmlPreview';
import { useCompiledHtml } from './useCompiledHtml';
import { DUMMY_HTML } from './dummyHtml';

interface StreamedPreviewProps {
  viewMode?: 'desktop' | 'mobile';
  isSidebarCollapsed?: boolean;
  customHtml?: string;
}

const StreamedPreview: React.FC<StreamedPreviewProps> = ({
  viewMode = 'desktop',
  isSidebarCollapsed = false,
  customHtml = '',
}) => {
  const { compiledHtml } = useCompiledHtml();
  const currentHtml = compiledHtml || customHtml || DUMMY_HTML;

  const memoizedHtmlPreview = useMemo(
    () => (
      <HtmlPreview
        renderedHTML={currentHtml}
        frameKey="stable-key"
        viewMode={viewMode}
        isSidebarCollapsed={isSidebarCollapsed}
      />
    ),
    [currentHtml, viewMode, isSidebarCollapsed]
  );

  return memoizedHtmlPreview;
};

export default StreamedPreview;
