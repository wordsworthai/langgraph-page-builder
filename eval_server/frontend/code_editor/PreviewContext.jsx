import React, { createContext, useContext, useState, useCallback } from 'react';

const PreviewContext = createContext(null);

export function PreviewProvider({ children }) {
  const [compiledHtml, setCompiledHtmlState] = useState('');
  const setCompiledHtml = useCallback((html) => {
    setCompiledHtmlState(html);
  }, []);

  const value = { compiledHtml, setCompiledHtml };
  return (
    <PreviewContext.Provider value={value}>
      {children}
    </PreviewContext.Provider>
  );
}

export function usePreviewContext() {
  const ctx = useContext(PreviewContext);
  return ctx;
}
