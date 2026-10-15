/**
 * packages_panel_init.js
 * ─────────────────────────────────────────────────────────────────────────────
 * Initialization for Hecos Package Manager Frontend
 */

window.hpmInit = function () {
  if (typeof window.hpmLoadRepositories === 'function') {
    window.hpmLoadRepositories();
  }
  window.hpmSwitchTab('packages');
  // Compute initial builtin count from CONFIG_HUB if present
  if (window.CONFIG_HUB && Array.isArray(window.CONFIG_HUB.modules)) {
    const builtinCount = window.CONFIG_HUB.modules.filter(m => !m.isHpm && m.id !== 'plugins' && m.id !== 'packages' && m.id !== 'hpm-settings').length;
    if (builtinCount > 0) window.hpmUpdateCount('builtin', builtinCount);
  }

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
  }, 300);
};

document.addEventListener('DOMContentLoaded', window.hpmInit);
if (document.readyState !== 'loading') {
  window.hpmInit();
}
