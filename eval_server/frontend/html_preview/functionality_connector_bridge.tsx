// Bridge: copy function from parent -> iframe before your HTML runs

export const functionalityConnectorBridgeScript = `
<script>
    try {
    // Assign parent's function onto iframe's global
    window._WWAI_DYNAMIC_PRODUCT_DATA_FETCH_FUNCTION =
        (window.parent && window.parent._WWAI_DYNAMIC_PRODUCT_DATA_FETCH_FUNCTION) || null;
    } catch (e) {
    console.error('Bridge error:', e);
    }
</script>
`;

// Script to emit WWAI data to parent
export const wwaiEmitScript = `
<script>
    (function() {
    // Function to check and emit WWAI data
    function emitWWAIData() {
        if (window.__WWAI__) {
        try {
            window.parent.postMessage({
            type: 'WWAI_DATA_READY',
            data: window.__WWAI__
            }, '*');
            console.log('🔧 WWAI data emitted to parent:', window.__WWAI__);
        } catch (error) {
            console.log('Error emitting WWAI data:', error);
        }
        } else {
        // Retry after a short delay if WWAI not ready yet
        setTimeout(emitWWAIData, 100);
        }
    }
    
    // Start checking for WWAI data
    emitWWAIData();
    })();
</script>
`;

// Message handler function for WWAI data from iframe
export const createWWAIMessageHandler = (onWWAIUpdate?: (wwaiData: Record<string, unknown>) => void) => {
  return (event: MessageEvent) => {
    if (event.data && event.data.type === 'WWAI_DATA_READY') {
      console.log('🔧 Received WWAI data from iframe:', event.data.data);
      if (onWWAIUpdate) {
        onWWAIUpdate(event.data.data);
      }
    }
  };
};

// Enhanced message handler that handles all WWAI message types
export const createEnhancedWWAIMessageHandler = (
  onWWAIUpdate?: (wwaiData: Record<string, unknown>) => void,
  onWWAIReady?: () => void,
  onWWAIError?: (error: string) => void
) => {
  return (event: MessageEvent) => {
    const { type, data, error } = event.data || {};
    
    switch (type) {
      case 'WWAI_DATA_READY':
        console.log('🔧 Received WWAI data from iframe:', data);
        if (onWWAIUpdate) {
          onWWAIUpdate(data);
        }
        break;
        
      case 'WWAI_READY':
        console.log('🔧 WWAI message handlers ready in iframe');
        if (onWWAIReady) {
          onWWAIReady();
        }
        break;
        
      case 'WWAI_ERROR':
        console.error('🔧 WWAI error from iframe:', error);
        if (onWWAIError) {
          onWWAIError(error);
        }
        break;
        
      default:
        // Ignore other message types
        break;
    }
  };
};