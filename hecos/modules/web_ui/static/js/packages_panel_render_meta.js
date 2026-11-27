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
  'INTELLIGENCE': { label: window.hpm_ti('Intelligence', 'Intelligenza', 'Inteligencia'), icon: 'fa-brain',       color: '#66fcf1', order: 1 },
  'MULTIMEDIA':   { label: window.hpm_ti('Multimedia', 'Multimedia', 'Multimedia'),       icon: 'fa-photo-film',  color: '#ec4899', order: 2 },
  'CONNECTIVITY': { label: window.hpm_ti('Connectivity', 'Connettività', 'Conectividad'), icon: 'fa-globe',       color: '#3b82f6', order: 3 },
  'RESOURCES':    { label: window.hpm_ti('Resources', 'Risorse', 'Recursos'),             icon: 'fa-folder-open', color: '#f59e0b', order: 4 },
  'AUTOMATION':   { label: window.hpm_ti('Automation', 'Automazione', 'Automatización'),  icon: 'fa-gears',       color: '#a78bfa', order: 5 },
  'SYSTEM':       { label: window.hpm_ti('System', 'Sistema', 'Sistema'),                 icon: 'fa-sliders',     color: '#45a29e', order: 6 },
  'APPS_EXTRAS':  { label: window.hpm_ti('Apps & Extras', 'App & Extra', 'Apps y Extras'),icon: 'fa-th-large',    color: '#8b5cf6', order: 7 }
};

window.HPM_HUB_CAT_ALIASES = {
  'INTELLIGENZA': 'INTELLIGENCE',
  'CONNETTIVITÀ': 'CONNECTIVITY',
  'CONNETTIVITA': 'CONNECTIVITY',
  'RISORSE':      'RESOURCES',
  'DOCUMENTS':    'RESOURCES',
  'AUTOMAZIONE':  'AUTOMATION',
  'SISTEMA':      'SYSTEM'
};

window.hpmGetHubCategoryLabel = function(catKey) {
  const raw = (catKey || 'SYSTEM').toUpperCase().trim();
  const k = window.HPM_HUB_CAT_ALIASES[raw] || raw;
  if (window.HPM_HUB_CATEGORIES[k]) return window.HPM_HUB_CATEGORIES[k].label;
  return catKey;
};

window.HPM_TYPE_META = {
  plugin:      { label: window.hpm_ti('Plugins', 'Plugin', 'Plugins'),                       icon: 'fa-plug',              color: '#3b82f6', order: 1 },
  app:         { label: window.hpm_ti('Apps', 'App', 'Apps'),                                icon: 'fa-th-large',          color: '#8b5cf6', order: 2 },
  system_app:  { label: window.hpm_ti('System App', 'App di Sistema', 'App de Sistema'),     icon: 'fa-layer-group',       color: '#66fcf1', order: 3 },
  widget:      { label: window.hpm_ti('Widgets', 'Widget', 'Widgets'),                       icon: 'fa-expand-arrows-alt', color: '#f59e0b', order: 4 },
  library:     { label: window.hpm_ti('Libraries', 'Librerie', 'Librerías'),                 icon: 'fa-book',              color: '#8b5cf6', order: 5 },
  persona:     { label: window.hpm_ti('Personas', 'Persona', 'Personas'),                    icon: 'fa-masks-theater',     color: '#ec4899', order: 6 },
  theme:       { label: window.hpm_ti('Themes', 'Temi', 'Temas'),                            icon: 'fa-palette',           color: '#10b981', order: 7 },
  extension:   { label: window.hpm_ti('Extensions', 'Estensioni', 'Extensiones'),            icon: 'fa-puzzle-piece',      color: '#45a29e', order: 8 },
  playbook:    { label: window.hpm_ti('Playbooks', 'Playbook', 'Playbooks'),                  icon: 'fa-book-open',         color: '#06b6d4', order: 8.5 },
  skill_pack:  { label: window.hpm_ti('Skill Packs', 'Pacchetti Skill', 'Paquetes de Skill'), icon: 'fa-graduation-cap',   color: '#f97316', order: 9 },
  core_module: { label: window.hpm_ti('Core Modules', 'Moduli Core', 'Módulos Core'), shortLabel: window.hpm_ti('Core', 'Core', 'Core'), icon: 'fa-microchip', color: '#ff4444', order: 10 },
  other:       { label: window.hpm_ti('Other', 'Altro', 'Otros'),                            icon: 'fa-cube',              color: '#6b7280', order: 11 }
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
