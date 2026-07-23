/**
 * packages_panel_render_meta.js
 * ─────────────────────────────────────────────────────────────────────────────
 * Global variables and helpers for Hecos Package Manager
 */

window.hpm_ti = function(en, it, es) {
  const l = (document.documentElement.lang || 'en').toLowerCase();
  if (l.startsWith('it')) return it || en;
  if (l.startsWith('es')) return es || en;
  return en;
};

window.HPM_HUB_CATEGORIES = {
  'INTELLIGENZA': { label: window.hpm_ti('Intelligence', 'Intelligenza', 'Inteligencia'), icon: 'fa-brain',         color: '#66fcf1', order: 1 },
  'MULTIMEDIA':   { label: 'Multimedia',   icon: 'fa-compact-disc',  color: '#ec4899', order: 2 },
  'CONNETTIVITÀ': { label: window.hpm_ti('Connectivity', 'Connettività', 'Conectividad'), icon: 'fa-network-wired', color: '#3b82f6', order: 3 },
  'RISORSE':      { label: window.hpm_ti('Resources', 'Risorse', 'Recursos'),      icon: 'fa-folder-open',   color: '#f59e0b', order: 4 },
  'SISTEMA':      { label: window.hpm_ti('System', 'Sistema', 'Sistema'),      icon: 'fa-cogs',          color: '#45a29e', order: 5 },
  'APPS_EXTRAS':  { label: 'App & Extras', icon: 'fa-th-large',      color: '#8b5cf6', order: 6 }
};

window.hpmGetHubCategoryLabel = function(catKey) {
  const k = (catKey || 'CONNETTIVITÀ').toUpperCase();
  if (window.HPM_HUB_CATEGORIES[k]) return window.HPM_HUB_CATEGORIES[k].label;
  return catKey;
};

window.HPM_TYPE_META = {
  plugin:      { label: window.hpm_ti('Plugins', 'Plugin', 'Plugins'),      icon: 'fa-plug',              color: '#3b82f6', order: 1 },
  app:         { label: window.hpm_ti('Apps', 'App', 'Apps'),               icon: 'fa-th-large',          color: '#8b5cf6', order: 2 },
  widget:      { label: window.hpm_ti('Widgets', 'Widget', 'Widgets'),      icon: 'fa-expand-arrows-alt', color: '#f59e0b', order: 3 },
  persona:     { label: window.hpm_ti('Personas', 'Persona', 'Personas'),   icon: 'fa-user-astronaut',    color: '#ec4899', order: 4 },
  theme:       { label: window.hpm_ti('Themes', 'Temi', 'Temas'),           icon: 'fa-palette',           color: '#10b981', order: 5 },
  extension:   { label: window.hpm_ti('Extensions', 'Estensioni', 'Extensiones'), icon: 'fa-puzzle-piece',      color: '#45a29e', order: 6 },
  skill_pack:  { label: window.hpm_ti('Skill Packs', 'Pacchetti Skill', 'Paquetes de Skill'), icon: 'fa-graduation-cap',    color: '#f97316', order: 7 },
  core_module: { label: window.hpm_ti('Core Modules', 'Moduli Core', 'Módulos Core'), icon: 'fa-microchip',         color: '#ff4444', order: 8 },
  other:       { label: window.hpm_ti('Other', 'Altro', 'Otros'),           icon: 'fa-cube',              color: '#6b7280', order: 9 }
};

window.hpmGetCategory = function (pkg) {
  let type = (pkg.type || '').toLowerCase().trim();
  if (!type && pkg.level === 1) type = 'core_module';
  if (!window.HPM_TYPE_META[type]) type = 'other';
  return type;
};

window.HPM_UI_STATE = window.HPM_UI_STATE || { collapsedCategories: [] };

window._hesc = function (s) {
  return String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
};
