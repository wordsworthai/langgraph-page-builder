//@ts-nocheck
// WWAI Message Communication System
// Handles communication between parent component and iframe for live preview operations

// Message types for parent ↔ iframe communication
export type WWAIMessage =
  | { type: 'WWAI_READY' }                                         // child → parent
  | { type: 'WWAI_ERROR'; error: string }                          // child → parent
  | { type: 'WWAI_SET_CSS'; css: string }                          // parent → child
  | { type: 'WWAI_SET_CONFIG'; config: Record<string, unknown> }   // parent → child
  | { type: 'WWAI_SCROLL_TO'; id: string; behavior?: ScrollBehavior; block?: ScrollLogicalPosition }
  | { type: 'WWAI_HIGHLIGHT_ADD'; selector: string }               // parent → child
  | { type: 'WWAI_HIGHLIGHT_CLEAR_ALL' };                          // parent → child

// Iframe-side script that gets injected into the preview
export const wwaiMessageHandlersScript = `
<script>
(function () {
  const DEV = (window.__WWAI_DEV__ = window.__WWAI_DEV__ || {});
  DEV.highlights = DEV.highlights || []; // store overlay elements

  // 1) CSS: single style element, replaced each time
  function ensureStyleEl() {
    if (DEV.styleEl && DEV.styleEl.isConnected) return DEV.styleEl;
    const el = document.createElement('style');
    el.id = 'wwai-custom-css';
    // Keep last in <head> to win cascade
    (document.head || document.documentElement).appendChild(el);
    DEV.styleEl = el;
    return el;
  }
  
  function setCustomCss(css) {
    const el = ensureStyleEl();
    // Use textContent (not innerHTML) to avoid accidental tag parsing
    el.textContent = css || '';
  }

  // 2) WWAI config: merge + announce (don't overwrite everything)
  function setConfig(cfg) {
    try {
      // Merge new config with existing config instead of overwriting
      if (window.__WWAI__ && typeof window.__WWAI__ === 'object') {
              // Deep merge the new config with existing config
      window.__WWAI__ = { ...window.__WWAI__, ...cfg };
      console.log('🔧 WWAI config merged:', { existing: window.__WWAI__, new: cfg });
    } else {
      // If no existing config, create new one
      window.__WWAI__ = cfg;
      console.log('🔧 WWAI config created:', cfg);
    }
    
    // Reinitialize functionality with updated config
    if (window.reinitializeFunctionality && typeof window.reinitializeFunctionality === 'function') {
      try {
        console.log('🔄 Reinitializing functionality with new config...');
        window.reinitializeFunctionality();
        console.log('✅ Functionality reinitialized successfully');
      } catch (reinitError) {
        console.warn('⚠️ Error reinitializing functionality:', reinitError);
      }
    } else {
      console.log('ℹ️ reinitializeFunctionality function not found, skipping reinitialization');
    }
    
    window.dispatchEvent(new CustomEvent('wwai-config-updated'));
    } catch (e) {
      console.error('❌ Error updating WWAI config:', e);
      window.parent?.postMessage({ type: 'WWAI_ERROR', error: String(e) }, '*');
    }
  }

  // 3) Scroll to section by id (smooth default)
  function scrollToId(id, behavior = 'smooth', block = 'center') {
    const el = document.getElementById(id);
    if (!el) return;
    el.scrollIntoView({ behavior, block, inline: 'nearest' });
  }

  // 4) Highlight elements (persistent until cleared)
  function addHighlight(selector) {
    const nodes = Array.from(document.querySelectorAll(selector));
    if (!nodes.length) return;

    nodes.forEach((node) => {
      // Create main overlay container
      const overlay = document.createElement('div');
      overlay.className = 'wwai-highlight-overlay';
      overlay.style.position = 'fixed';
      overlay.style.pointerEvents = 'none';
      overlay.style.zIndex = '2147483647';
      overlay.style.background = 'transparent';
      overlay.style.display = 'flex';
      overlay.style.flexDirection = 'column';

      // Create striped border effect with multiple rectangles
      const createStripedBorder = () => {
        const r = node.getBoundingClientRect();
        const stripWidth = 3; // Width of each strip
        const gap = 2; // Gap between strips
        
        // Clear existing strips
        overlay.innerHTML = '';
        
        // Top border strips (grey-red-grey)
        for (let i = 0; i < 3; i++) {
          const strip = document.createElement('div');
          strip.style.position = 'absolute';
          strip.style.height = stripWidth + 'px';
          strip.style.width = r.width + 'px';
          strip.style.left = '0px';
          strip.style.top = (i * (stripWidth + gap)) + 'px';
          strip.style.backgroundColor = i === 1 ? 'rgba(255,0,0,0.8)' : 'rgba(128,128,128,0.9)';
          strip.style.boxShadow = '0 0 4px rgba(0,0,0,0.3)';
          overlay.appendChild(strip);
        }
        
        // Bottom border strips (grey-red-grey)
        for (let i = 0; i < 3; i++) {
          const strip = document.createElement('div');
          strip.style.position = 'absolute';
          strip.style.height = stripWidth + 'px';
          strip.style.width = r.width + 'px';
          strip.style.left = '0px';
          strip.style.bottom = (i * (stripWidth + gap)) + 'px';
          strip.style.backgroundColor = i === 1 ? 'rgba(255,0,0,0.8)' : 'rgba(128,128,128,0.8)';
          strip.style.boxShadow = '0 0 4px rgba(0,0,0,0.3)';
          overlay.appendChild(strip);
        }
        
        // Left border strips (grey-red-grey)
        for (let i = 0; i < 3; i++) {
          const strip = document.createElement('div');
          strip.style.position = 'absolute';
          strip.style.width = stripWidth + 'px';
          strip.style.height = r.height + 'px';
          strip.style.top = '0px';
          strip.style.left = (i * (stripWidth + gap)) + 'px';
          strip.style.backgroundColor = i === 1 ? 'rgba(255,0,0,0.8)' : 'rgba(128,128,128,0.8)';
          strip.style.boxShadow = '0 0 4px rgba(0,0,0,0.3)';
          overlay.appendChild(strip);
        }
        
        // Right border strips (grey-red-grey)
        for (let i = 0; i < 3; i++) {
          const strip = document.createElement('div');
          strip.style.position = 'absolute';
          strip.style.width = stripWidth + 'px';
          strip.style.height = r.height + 'px';
          strip.style.top = '0px';
          strip.style.right = (i * (stripWidth + gap)) + 'px';
          strip.style.backgroundColor = i === 1 ? 'rgba(255,0,0,0.8)' : 'rgba(128,128,128,0.8)';
          strip.style.boxShadow = '0 0 4px rgba(0,0,0,0.3)';
          overlay.appendChild(strip);
        }
      };

      function place() {
        const r = node.getBoundingClientRect();
        overlay.style.left = r.left + 'px';
        overlay.style.top = r.top + 'px';
        overlay.style.width = r.width + 'px';
        overlay.style.height = r.height + 'px';
        overlay.style.display = r.width && r.height ? 'block' : 'none';
        
        // Update striped border when repositioning
        createStripedBorder();
      }

      place();
      DEV.highlights.push({ node, overlay, place });
      document.body.appendChild(overlay);
    });

    // Global listeners once
    if (!DEV._repositionBound) {
      DEV._repositionBound = true;
      const tick = () => {
        DEV.highlights.forEach((h) => h.place());
        DEV._raf = requestAnimationFrame(tick);
      };
      DEV._raf = requestAnimationFrame(tick);
      window.addEventListener('resize', () => DEV.highlights.forEach((h) => h.place()));
      window.addEventListener('scroll', () => DEV.highlights.forEach((h) => h.place()), true);
    }
  }

  function clearAllHighlights() {
    if (DEV._raf) cancelAnimationFrame(DEV._raf);
    DEV._repositionBound = false;
    (DEV.highlights || []).forEach(({ overlay }) => overlay.remove());
    DEV.highlights = [];
  }

  // Message router
  window.addEventListener('message', (e) => {
    const msg = e.data || {};
    switch (msg.type) {
      case 'WWAI_SET_CSS':
        setCustomCss(String(msg.css || ''));
        break;
      case 'WWAI_SET_CONFIG':
        setConfig(msg.config);
        break;
      case 'WWAI_SCROLL_TO':
        scrollToId(String(msg.id), msg.behavior || 'smooth', msg.block || 'center');
        break;
      case 'WWAI_HIGHLIGHT_ADD':
        addHighlight(String(msg.selector));
        break;
      case 'WWAI_HIGHLIGHT_CLEAR_ALL':
        clearAllHighlights();
        break;
    }
  });

  // Tell parent we're ready
  window.parent && window.parent !== window && window.parent.postMessage({ type: 'WWAI_READY' }, '*');
})();
</script>
`;

// Parent-side sender functions
export function createWWAISenders(iframe: HTMLIFrameElement | null, targetOrigin: string = '*') {
  const win = iframe?.contentWindow;
  if (!win) return null;
  
  return {
    setCss: (css: string) => win.postMessage({ type: 'WWAI_SET_CSS', css }, targetOrigin),
    setConfig: (config: Record<string, unknown>) => win.postMessage({ type: 'WWAI_SET_CONFIG', config }, targetOrigin),
    scrollTo: (id: string, behavior: ScrollBehavior = 'smooth', block: ScrollLogicalPosition = 'center') =>
      win.postMessage({ type: 'WWAI_SCROLL_TO', id, behavior, block }, targetOrigin),
    highlight: (selector: string) => win.postMessage({ type: 'WWAI_HIGHLIGHT_ADD', selector }, targetOrigin),
    clearHighlights: () => win.postMessage({ type: 'WWAI_HIGHLIGHT_CLEAR_ALL' }, targetOrigin),
  };
}

// Utility function to create debounced CSS sender
export function createDebouncedCssSender(
  iframe: HTMLIFrameElement | null, 
  delay: number = 200
) {
  let timeoutId: NodeJS.Timeout | null = null;
  
  return (css: string) => {
    if (timeoutId) {
      clearTimeout(timeoutId);
    }
    
    timeoutId = setTimeout(() => {
      const senders = createWWAISenders(iframe);
      senders?.setCss(css);
    }, delay);
  };
}

// Type for the sender functions
export type WWAISenders = ReturnType<typeof createWWAISenders>;
