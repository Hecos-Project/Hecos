/**
 * config_core.js — Entry Point / Orchestrator
 *
 * Declares all shared global state and wires up top-level event listeners.
 * All domain logic is delegated to sub-modules loaded before this file:
 *
 *   config_core_utils.js       → fetchWithTimeout, setSaveMsg, setSpanText, rebootSystem, escapeHtml
 *   config_core_init.js        → initAll, mergeRegistry, loadUIState, saveUIState
 *   config_core_navigation.js  → showTab, _loadPanel, setViewMode, toggleCategory, setCategoryFilter
 *   config_core_hub.js         → renderConfigHub, renderFilterTabs, injectIconsInPanel
 *   config_core_persistence.js → saveConfig
 *   config_core_status.js      → refreshStatus
 *
 * Load order in index.html must match the dependency chain above:
 *   ...sub-modules... → config_core.js (this file, last)
 */

// ── Shared Global State ────────────────────────────────────────────────────────
window.cfg         = {};
window.sysOptions  = {};
let audioDevices   = null;
let audioConfig    = null;
let mediaConfig    = null;
let isInitialLoading = false;

const I18N = window.I18N || {};
let configRegistry = {};
let uiState = {
    collapsedCategories: []
};

// View / navigation state
let viewMode = localStorage.getItem('hecos-config-view') || 'tabs';
const navType   = window.performance?.getEntriesByType("navigation")[0]?.type;
const isRefresh = navType === 'reload';
let activeTab = window.location.hash.substring(1)
    || sessionStorage.getItem('hecos-config-tab')
    || (isRefresh ? 'backend' : 'welcome');
window.activeCategoryFilter = sessionStorage.getItem('hecos-config-filter') || '';

// Lazy panel cache — shared with _loadPanel (config_core_navigation.js)
const _panelCache    = {};  // panelId → true
const _panelFetching = {};  // panelId → Promise (prevents duplicate fetches)

// ── Global Exports ─────────────────────────────────────────────────────────────
// (sub-modules export their own functions; list remaining core ones here)
window.initAll            = initAll;
window.showTab            = showTab;
window.setViewMode        = setViewMode;
window.renderConfigHub    = renderConfigHub;
window.renderFilterTabs   = renderFilterTabs;
window.setCategoryFilter  = setCategoryFilter;
window.toggleAllCategories = toggleAllCategories;
window.saveConfig         = saveConfig;
window.refreshStatus      = refreshStatus;
window.rebootSystem       = rebootSystem;

// ── Event Listeners ────────────────────────────────────────────────────────────

// Universal auto-save on change (selects, checkboxes, inputs, textareas)
document.addEventListener('change', (e) => {
  if (e.target.closest('.no-autosave') || e.target.closest('#tab-logs')) return;
  const tag  = e.target.tagName;
  const type = e.target.type;
  if (tag === 'SELECT' || tag === 'TEXTAREA' || type === 'checkbox' || (tag === 'INPUT' && type !== 'file')) {

    // Sync data-plugin toggle state across any duplicate checkboxes
    if (e.target.dataset.plugin) {
        const pluginTag = e.target.dataset.plugin;
        document.querySelectorAll(`[data-plugin="${pluginTag}"]`).forEach(cb => {
            if (cb !== e.target) cb.checked = e.target.checked;
        });
        if (typeof syncPluginStateToMemory === 'function') {
            syncPluginStateToMemory(pluginTag, e.target.checked);
        }
    }

    // Sync Image Gen enabled state between locations
    if (e.target.id === 'igen-enabled') {
        const other = document.querySelector('[data-plugin="IMAGE_GEN"]');
        if (other) other.checked = e.target.checked;
    } else if (e.target.dataset.plugin === 'IMAGE_GEN') {
        const other = document.getElementById('igen-enabled');
        if (other) other.checked = e.target.checked;
    }

    // Avatar preview on persona change
    if (e.target.id === 'ia-personality-main') {
        if (typeof loadPersonaAvatar === 'function') loadPersonaAvatar(e.target.value);
    }

    // Auto-stop voice if toggle is turned off
    if (e.target.id === 'sys-voice-status' && !e.target.checked) {
       if (typeof stopVoice === 'function') stopVoice();
    }

    saveConfig(true);
  }
});

// Backend type card visibility switcher
document.addEventListener('DOMContentLoaded', () => {
    const backendTypeEl = document.getElementById('backend-type');
    if (backendTypeEl) {
        backendTypeEl.addEventListener('change', function() {
          const v = this.value;
          const cardCloud  = document.getElementById('card-cloud');
          const cardOllama = document.getElementById('card-ollama');
          const cardKobold = document.getElementById('card-kobold');
          if (cardCloud)  cardCloud.style.display  = v === 'cloud'  ? '' : 'none';
          if (cardOllama) cardOllama.style.display = v === 'ollama' ? '' : 'none';
          if (cardKobold) cardKobold.style.display = v === 'kobold' ? '' : 'none';
        });
    }
});

// Deep-linking via URL hash changes (e.g. from dashboard widgets)
window.addEventListener('hashchange', () => {
    const tab = window.location.hash.substring(1);
    if (tab && typeof showTab === 'function') showTab(tab);
});
