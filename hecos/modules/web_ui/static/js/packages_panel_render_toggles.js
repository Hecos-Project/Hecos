/**
 * packages_panel_render_toggles.js
 * ─────────────────────────────────────────────────────────────────────────────
 * Toggles for Hecos Package Manager list and wall views
 */

window.hpmToggleEnabled = function (id, isBuiltin, isChecked) {
  const tag = id;
  if (window.cfg) {
    if (!window.cfg.plugins) window.cfg.plugins = {};
    if (!window.cfg.plugins[tag]) window.cfg.plugins[tag] = {};
    window.cfg.plugins[tag].enabled = isChecked;
  }

  if (!isBuiltin) {
    const status = isChecked ? 'installed' : 'disabled';
    if (typeof window.hpmSetStatus === 'function') {
      window.hpmSetStatus(id, status, false);
    }
  } else {
    if (typeof window.saveConfig === 'function') window.saveConfig(true);
    if (window._packages) {
      const pkg = window._packages.find(p => p.id === id);
      if (pkg) {
        pkg.status = isChecked ? 'installed' : 'disabled';
        window.hpmRenderHierarchy();
      }
    }
  }
};

window.hpmToggleLazy = function (id, isBuiltin, isChecked) {
  const tag = id;
  if (window.cfg) {
    if (!window.cfg.plugins) window.cfg.plugins = {};
    if (!window.cfg.plugins[tag]) window.cfg.plugins[tag] = {};
    window.cfg.plugins[tag].lazy_load = isChecked;
  }

  if (typeof window.saveConfig === 'function') window.saveConfig(true);

  if (window._packages) {
    const pkg = window._packages.find(p => p.id === id);
    if (pkg) {
      pkg.lazy_load = isChecked;
    }
  }
};
