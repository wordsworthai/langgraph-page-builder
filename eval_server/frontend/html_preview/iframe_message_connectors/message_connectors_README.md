# WWAI Message Communication System

This system enables real-time communication between the parent React component and the iframe preview for live editing and testing of WWAI configurations.

## Overview

The system provides 4 main operations:
1. **CSS Updates** - Inject/replace custom CSS in the iframe
2. **WWAI Config Updates** - Update the WWAI configuration object
3. **Scroll to Section** - Navigate to specific sections by ID
4. **Element Highlighting** - Highlight elements with bounding boxes

## Architecture

### Files
- `message_connectors.ts` - Core message system and iframe handlers
- `functionality_connector_bridge.tsx` - Enhanced message handlers
- `WWAIMessageTestPanel.tsx` - Test UI for all operations
- `HtmlPreview.tsx` - Updated to support message system

### Message Flow
```
Parent Component → postMessage → Iframe → Execute Operation → postMessage → Parent (confirmation)
```

## Usage

### 1. CSS Updates
```typescript
const senders = htmlPreviewRef.current?.wwaiSenders;
senders?.setCss(`
  .hero-section { 
    background-color: red !important; 
  }
`);
```

### 2. WWAI Config Updates
```typescript
const senders = htmlPreviewRef.current?.wwaiSenders;
senders?.setConfig({
  WWAI_PRODUCT_GROUP_CONFIG: { /* ... */ },
  JS_PRODUCT_MAPPING_OBJECT: { /* ... */ }
});
```

### 3. Scroll to Section
```typescript
const senders = htmlPreviewRef.current?.wwaiSenders;
senders?.scrollTo('hero-section', 'smooth', 'center');
```

### 4. Element Highlighting
```typescript
const senders = htmlPreviewRef.current?.wwaiSenders;
senders?.highlight('[data-section="hero"]');
senders?.clearHighlights(); // Clear all highlights
```

## Features

### CSS Management
- **Single Style Element**: Uses one `<style id="wwai-custom-css">` element
- **Replaceable**: Each update replaces the entire CSS content
- **Cascade Priority**: Positioned last in `<head>` to win CSS cascade
- **No Bloat**: No accumulation of multiple style tags

### Highlighting System
- **Persistent**: Highlights remain until explicitly cleared
- **Responsive**: Automatically reposition on scroll/resize
- **Visual**: Grey bounding boxes with shadows
- **Performance**: Uses requestAnimationFrame for smooth updates

### Error Handling
- **Validation**: Checks for valid selectors and IDs
- **Fallbacks**: Graceful degradation when operations fail
- **Logging**: Comprehensive console logging for debugging

## Testing

The `WWAIMessageTestPanel` component provides a UI for testing all operations:

1. **CSS Testing**: Textarea for custom CSS with apply/clear buttons
2. **Config Testing**: JSON input for WWAI configuration updates
3. **Scroll Testing**: Input for section ID with scroll button
4. **Highlight Testing**: Selector input with highlight/clear buttons

## Security Considerations

- **Origin Validation**: Messages are validated for source
- **Sandbox**: Iframe uses appropriate sandbox attributes
- **Content Security**: CSS injection uses `textContent` to prevent XSS

## Performance Features

- **Debounced CSS**: CSS updates are debounced (200ms default)
- **Efficient Highlighting**: Single RAF loop for all highlights
- **Memory Management**: Proper cleanup of event listeners and overlays

## Integration

The system integrates seamlessly with existing WWAI components:
- `WWAIConfigPanel` can now send config updates via messages
- `HtmlPreview` exposes `wwaiSenders` through its ref
- All operations work with both desktop and mobile view modes

## Future Enhancements

- **Undo/Redo**: Track CSS and config changes for rollback
- **Batch Operations**: Send multiple updates in single message
- **Conditional Updates**: Update only changed parts of config
- **Real-time Sync**: Bi-directional sync between parent and iframe
