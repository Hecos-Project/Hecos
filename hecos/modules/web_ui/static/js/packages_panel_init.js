/**
 * packages_panel_init.js
 * ─────────────────────────────────────────────────────────────────────────────
 * Initialization for Hecos Package Manager Frontend
 */

window.hpmInit = function () {
  window.hpmSwitchTab('packages');
  // Fetch widget count from API so the badge is always accurate
  setTimeout(() => {
    if (document.getElementById('tab-plugins')) {
      const builtinCount = document.querySelectorAll('#tab-plugins .toggle-row, #tab-plugins .plugin-card, #tab-plugins [data-plugin]').length;
      if (builtinCount > 0) window.hpmUpdateCount('builtin', builtinCount);
    }
    // Authoritative widget count from server, not DOM
    fetch('/api/widgets').then(r => r.ok ? r.json() : null).then(data => {
      if (data && Array.isArray(data.widgets)) {
        const count = data.widgets.filter(w => w.sidebar_widget !== false).length;
        window.hpmUpdateCount('widgets', count);
      }
    }).catch(() => {
      // Fallback to DOM count
      if (document.getElementById('tab-widgets')) {
        const widgetCount = document.querySelectorAll('#tab-widgets .widget-card').length;
        if (widgetCount > 0) window.hpmUpdateCount('widgets', widgetCount);
      }
    });
  }, 1000);
};

document.addEventListener('DOMContentLoaded', window.hpmInit);
if (document.readyState !== 'loading') {
  window.hpmInit();
}
