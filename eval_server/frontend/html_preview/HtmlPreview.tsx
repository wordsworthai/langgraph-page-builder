import { useRef, useEffect, forwardRef, useImperativeHandle, useState, useCallback, useMemo } from 'react';
import React from 'react';
import { Settings, AlertCircle } from 'lucide-react';
import { createWWAISenders, wwaiMessageHandlersScript, WWAISenders } from './iframe_message_connectors/message_connectors';
import { createEnhancedWWAIMessageHandler, functionalityConnectorBridgeScript, wwaiEmitScript } from './functionality_connector_bridge';
import { COMPLETE_HEAD_IMPORTS } from './common_css_js_imports';

// Layout constants for Liquid Preview
export const LAYOUT_DIMENSIONS = {
  // Sidebar dimensions
  SIDEBAR: {
    EXPANDED_WIDTH: 400,  // px
    COLLAPSED_WIDTH: 50,  // px
  },
  
  // Header dimensions
  HEADER: {
    HEIGHT: 60,  // px
  },
  
  // Padding and margins
  SPACING: {
    PADDING: 0,  // px - no padding for accurate offset calculation
  }
};

// Device dimensions for preview modes (intrinsic iframe size before scaling)
export const DEVICE_DIMENSIONS = {
  desktop: { width: 1200, height: 900, label: 'Desktop' },
  mobile: { width: 375, height: 667, label: 'Mobile' }
};


interface HtmlPreviewProps {
  renderedHTML: string;
  frameKey?: number | string;
  viewMode?: 'desktop' | 'mobile';
  isSidebarCollapsed?: boolean;
  onWWAIUpdate?: (wwaiData: Record<string, unknown>) => void; // Callback for WWAI data
}

export interface HtmlPreviewRef {
  iframe: HTMLIFrameElement | null;
  getDocument: () => Document | null;
  wwaiSenders: WWAISenders | null;

  loadAnalytics: (url: string, options?: Record<string, any>) => Promise<any>;
}

/**
 * HTML Preview component that uses srcDoc consistently for safe re-initialization
 */
const HtmlPreview = React.memo(forwardRef<HtmlPreviewRef, HtmlPreviewProps>(({ 
  renderedHTML, 
  frameKey, 
  viewMode = 'desktop', 
  isSidebarCollapsed = false,
  onWWAIUpdate
 }, ref) => {
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [isLoaded, setIsLoaded] = useState(false);
  const [iframeKey, setIframeKey] = useState(0);
  const prevHtmlRef = useRef<string>('');
  const [containerSize, setContainerSize] = useState({ width: 0, height: 0 });

  // Measure actual container dimensions (preview lives in the right split panel, not full window)
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width, height } = entry.contentRect;
        setContainerSize({ width, height });
      }
    });
    resizeObserver.observe(el);
    return () => resizeObserver.disconnect();
  }, []);

  // Calculate scaling: fit device viewport into the actual container
  // Returns scale factor and wrapper dimensions for proper fit (no scrollbars)
  const getScalingInfo = useCallback(() => {
    const dims = viewMode === 'desktop' ? DEVICE_DIMENSIONS.desktop : DEVICE_DIMENSIONS.mobile;
    const { width: deviceW, height: deviceH } = dims;
    const { width: containerW, height: containerH } = containerSize;
    if (containerW <= 0 || containerH <= 0) {
      return {
        scale: 1,
        wrapperWidth: deviceW,
        wrapperHeight: deviceH,
        iframeWidth: deviceW,
        iframeHeight: deviceH,
      };
    }
    const scale = Math.min(containerW / deviceW, containerH / deviceH, 1);
    return {
      scale,
      wrapperWidth: Math.floor(deviceW * scale),
      wrapperHeight: Math.floor(deviceH * scale),
      iframeWidth: deviceW,
      iframeHeight: deviceH,
    };
  }, [viewMode, containerSize]);

  // Create complete HTML document with functionality connector bridge
  const createCompleteHTML = useMemo(() => {
    if (!renderedHTML) return '';
    
    return `
      <!DOCTYPE html>
      <html>
        <head>
          <meta charset="utf-8">
          <meta name="viewport" content="width=device-width, initial-scale=1.0">
          <title>HTML Preview</title>
          <style>
            body { margin: 0; padding: 0; overflow-y: auto; min-height: 100%; }
            * { box-sizing: border-box; }
          </style>
          ${COMPLETE_HEAD_IMPORTS}
        </head>
        <body>
          ${functionalityConnectorBridgeScript}
          ${renderedHTML}
          ${wwaiEmitScript}
          ${wwaiMessageHandlersScript}
          <script defer src="https://d2zd0wa1vpt7j9.cloudfront.net/wwai_engagement_metrics_visualisation_iframe.js"></script>
        </body>
      </html>
    `;
  }, [renderedHTML]);
  
  // Expose methods to parent components
  // useImperativeHandle(ref, () => ({
  //   iframe: iframeRef.current,
  //   getDocument: () => {
  //     if (iframeRef.current) {
  //       return iframeRef.current.contentDocument || (iframeRef.current.contentWindow && iframeRef.current.contentWindow.document);
  //     }
  //     return null;
  //   },
  //   wwaiSenders: createWWAISenders(iframeRef.current)
  // }));

  useImperativeHandle(ref, () => ({
    iframe: iframeRef.current,
    getDocument: () => {
      if (iframeRef.current) {
        return iframeRef.current.contentDocument || (iframeRef.current.contentWindow && iframeRef.current.contentWindow.document);
      }
      return null;
    },
    wwaiSenders: createWWAISenders(iframeRef.current),
    loadAnalytics: async (url: string, options?: Record<string, any>) => {
      return new Promise((resolve) => {
        const iframe = iframeRef.current;
        if (!iframe || !iframe.contentWindow) {
          resolve({ success: false, error: 'Iframe not available' });
          return;
        }
  
        const contentWindow = iframe.contentWindow;
        
        const checkAndLoad = () => {
          // Type assertion to handle the dynamic property
          const windowWithAnalytics = contentWindow as Window & { 
            loadAnalyticsData?: (url: string, options?: Record<string, any>) => any 
          };
          
          if (windowWithAnalytics.loadAnalyticsData) {
            try {
              const result = windowWithAnalytics.loadAnalyticsData(url, options);
              console.log('Analytics loaded from React:', result);
              resolve(result);
            } catch (error) {
              console.error('Error loading analytics from React:', error);
              resolve({ 
                success: false, 
                error: error instanceof Error ? error.message : 'Unknown error'
              });
            }
          } else {
            // Script not loaded yet, wait and try again
            setTimeout(checkAndLoad, 100);
          }
        };
        
        // Give the iframe some time to load the script
        setTimeout(checkAndLoad, 500);
      });
    }
  }));

  // Handle iframe load event
  const handleIframeLoad = useCallback(() => {
    setIsLoaded(true);
  }, []);

  // Only recreate iframe if HTML content actually changed or frameKey is provided
  useEffect(() => {
    if (renderedHTML !== prevHtmlRef.current) {
      prevHtmlRef.current = renderedHTML;
      
      // Recreate iframe with new content
      setIframeKey(prev => prev + 1);
      setIsLoaded(false);
    }
  }, [renderedHTML, isLoaded]);

  // Handle external frameKey changes (manual refresh)
  useEffect(() => {
    if (frameKey && typeof frameKey === 'string' && frameKey !== 'stable-preview') {
      setIframeKey(prev => prev + 1);
      setIsLoaded(false);
    }
  }, [frameKey]);

  // Listen for WWAI data messages from iframe
  useEffect(() => {
    const handleMessage = createEnhancedWWAIMessageHandler(
      onWWAIUpdate,
      () => console.log('[WWAI] Message handlers ready'),
      (error) => console.error('[WWAI] Error:', error)
    );

    window.addEventListener('message', handleMessage);
    return () => window.removeEventListener('message', handleMessage);
  }, [onWWAIUpdate]);

  // Apply scaling styles when container size or view mode changes
  useEffect(() => {
    const iframe = iframeRef.current;
    if (!iframe || !renderedHTML) return;

    const info = getScalingInfo();
    iframe.style.transform = `scale(${info.scale})`;
    iframe.style.transformOrigin = 'top left';
    iframe.style.width = `${info.iframeWidth}px`;
    iframe.style.height = `${info.iframeHeight}px`;
  }, [viewMode, containerSize, getScalingInfo, renderedHTML]);

  const scalingInfo = getScalingInfo();

  return (
    <div
      ref={containerRef}
      className="w-full h-full relative bg-[#051023] border border-[#2c3441] rounded-lg overflow-hidden flex justify-center items-center"
    >
      {renderedHTML ? (
        <div
          style={{
            width: scalingInfo.wrapperWidth,
            height: scalingInfo.wrapperHeight,
            overflow: 'hidden',
            flexShrink: 0,
          }}
        >
          <iframe
            key={iframeKey}
            ref={iframeRef}
            srcDoc={createCompleteHTML}
            onLoad={handleIframeLoad}
            className={`
              border-none bg-white block
              ${isLoaded ? '' : 'hidden'}
            `}
            style={{
              width: scalingInfo.iframeWidth,
              height: scalingInfo.iframeHeight,
              transform: `scale(${scalingInfo.scale})`,
              transformOrigin: 'top left',
            }}
            title="HTML Preview"
            sandbox="allow-scripts allow-same-origin allow-modals allow-forms"
          />
        </div>
      ) : null}
      {!renderedHTML && (
        <div className="p-5 text-center text-gray-400 min-h-[600px] flex items-center justify-center">
          <div className="flex items-center gap-2">
            <AlertCircle size={20} />
            No HTML content to display
          </div>
        </div>
      )}
      
      {!isLoaded && renderedHTML && (
        <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 text-gray-400 text-base flex items-center gap-2">
          <Settings size={16} className="animate-spin" />
          Loading preview...
        </div>
      )}
    </div>
  );
}));

export default HtmlPreview;