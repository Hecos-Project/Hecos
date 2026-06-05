import React from 'react';
import ReactDOM from 'react-dom/client';
import FlowsApp from './FlowsApp.jsx';

function mountApp() {
  const mountEl = document.getElementById('rf-canvas-root');
  if (mountEl) {
    const root = ReactDOM.createRoot(mountEl);
    root.render(<FlowsApp />);
  } else {
    console.error('[HecosFlows] Mount point #rf-canvas-root not found in DOM.');
  }
}

// The bundle may be loaded in <head> before the DOM is ready.
// DOMContentLoaded ensures #rf-canvas-root exists before we try to mount.
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', mountApp);
} else {
  // DOM already parsed (e.g., bundle loaded at end of body)
  mountApp();
}
