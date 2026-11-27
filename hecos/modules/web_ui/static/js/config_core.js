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
window.cfg         = window.cfg || {};
window.sysOptions  = window.sysOptions || {};
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
let rawHash = window.location.hash.substring(1);
if (rawHash && rawHash.startsWith('tab-')) rawHash = rawHash.slice(4);
let activeTab = rawHash
    || sessionStorage.getItem('hecos-config-tab')
    || (isRefresh ? 'backend' : 'welcome');
window.activeCategoryFilter = sessionStorage.getItem('hecos-config-filter') || '';

// Lazy panel cache — shared with _loadPanel (config_core_navigation.js)
const _panelCache    = {};  // panelId → true
const _panelFetching = {};  // panelId → Promise (prevents duplicate fetches)
// Expose on window so progressive hydration can check cache state from navigation.js
window._panelCache    = _panelCache;
window._panelFetching = _panelFetching;
// NOTE: Do NOT add window._loadPanel here — _loadPanel is a top-level function
// declaration in config_core_navigation.js and is already on window. Creating
// a wrapper here would cause infinite recursion (wrapper calls itself).

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

// ── Chat Interface Live Sync (Instant Broadcast to Open Chat Tabs) ────────────
function _updateWelcomeModeDesc(mode) {
    const descEl = document.getElementById('chatui-welcome-mode-desc');
    if (!descEl) return;
    const val = mode || (document.getElementById('chatui-welcome-mode') || {}).value || 'hybrid';
    if (val === 'classic') {
        descEl.innerHTML = '<strong>Classic Mode:</strong> Always shows the System Logo and the "Capability Chips" carousel without switching to the 3D Avatar card.';
    } else if (val === 'avatar') {
        descEl.innerHTML = '<strong>Avatar Mode:</strong> Skips the capability chips and displays only the 3D flipping Avatar card for the active persona.';
    } else {
        descEl.innerHTML = '<strong>Hybrid Mode:</strong> Shows the "Capability Chips" on startup. When you click the chat area or text input, they fade out to reveal the 3D Avatar card.';
    }
}
window._updateWelcomeModeDesc = _updateWelcomeModeDesc;

function broadcastChatUiConfig(opts = {}) {
    const wui = (window.cfg && window.cfg.plugins && window.cfg.plugins.WEB_UI) ? window.cfg.plugins.WEB_UI : {};
    const modeEl = document.getElementById('chatui-welcome-mode');
    const newFirstEl = document.getElementById('wui-dcc-new-first');
    const hoursEl = document.getElementById('wui-dcc-highlight-hours');

    const welcomeMode = opts.chatui_welcome_mode ?? (modeEl ? modeEl.value : (wui.chatui_welcome_mode || 'hybrid'));
    const dccNewFirst = opts.dcc_new_first ?? (newFirstEl ? newFirstEl.checked : (wui.dcc_new_first ?? true));
    const dccHours = opts.dcc_new_highlight_hours ?? (hoursEl ? (parseInt(hoursEl.value, 10) || 72) : (parseInt(wui.dcc_new_highlight_hours, 10) || 72));

    // Keep in-memory window.cfg immediately synchronized so Phase 2 populateUI won't revert it
    window.cfg = window.cfg || {};
    window.cfg.plugins = window.cfg.plugins || {};
    window.cfg.plugins.WEB_UI = Object.assign(window.cfg.plugins.WEB_UI || {}, {
        chatui_welcome_mode: welcomeMode,
        dcc_new_first: dccNewFirst,
        dcc_new_highlight_hours: dccHours
    });

    const payload = {
        type: 'chat_ui_config_updated',
        chatui_welcome_mode: welcomeMode,
        dcc_new_first: dccNewFirst,
        dcc_new_highlight_hours: dccHours,
        persisted: opts.persisted !== false,
        ts: Date.now()
    };

    try {
        if (typeof BroadcastChannel !== 'undefined') {
            const ch = new BroadcastChannel('hecos_chat_ui');
            ch.postMessage(payload);
            ch.close();
        }
    } catch (_) {}
    try {
        localStorage.setItem('hecos_chat_ui_sync', JSON.stringify(payload));
    } catch (_) {}

    return payload;
}
window.broadcastChatUiConfig = broadcastChatUiConfig;

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



    // Avatar preview on persona change
    if (e.target.id === 'ia-personality-main') {
        if (typeof loadPersonaAvatar === 'function') loadPersonaAvatar(e.target.value);
    }

    // Auto-stop voice if toggle is turned off
    if (e.target.id === 'sys-voice-status' && !e.target.checked) {
       if (typeof stopVoice === 'function') stopVoice();
    }

    // Instant live sync for Chat Interface settings (Welcome Mode & DCC highlights)
    if (e.target.id === 'chatui-welcome-mode' || e.target.id === 'wui-dcc-new-first' || e.target.id === 'wui-dcc-highlight-hours') {
        if (e.target.id === 'chatui-welcome-mode') {
            _updateWelcomeModeDesc(e.target.value);
        }
        const snap = broadcastChatUiConfig({ persisted: false });
        // If Phase 2 mappers aren't loaded yet, persist directly so the edit is never silently dropped
        if (typeof buildPayload !== 'function') {
            fetch('/hecos/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    plugins: {
                        WEB_UI: {
                            chatui_welcome_mode: snap.chatui_welcome_mode,
                            dcc_new_first: snap.dcc_new_first,
                            dcc_new_highlight_hours: snap.dcc_new_highlight_hours
                        }
                    }
                })
            }).then(r => r.json()).then(d => {
                if (d && d.ok) {
                    broadcastChatUiConfig({ persisted: true });
                    if (typeof setSaveMsg === 'function') {
                        const syncedMsg = (I18N.webui_conf_msg_synced || '✓ Changes auto-saved').replace('✅ ', '✓ ');
                        setSaveMsg(syncedMsg, 'ok');
                    }
                }
            }).catch(() => {});
            return;
        }
    }

    saveConfig(true);
  }
});

// Backend type card visibility switcher (event delegation — works with lazy-loaded panels)
function _applyBackendCardVisibility(type) {
  const v = type || (document.getElementById('backend-type') || {}).value || 'ollama';
  const cardCloud    = document.getElementById('card-cloud-settings');
  const cardOllama   = document.getElementById('card-ollama');
  const cardKobold   = document.getElementById('card-kobold');
  const cardLlamaCpp = document.getElementById('card-llama-cpp');
  if (cardCloud)    cardCloud.style.display    = (v === 'cloud' || v === 'hybrid') ? '' : 'none';
  if (cardOllama)   cardOllama.style.display   = (v === 'ollama' || v === 'hybrid') ? '' : 'none';
  if (cardKobold)   cardKobold.style.display   = (v === 'kobold') ? '' : 'none';
  if (cardLlamaCpp) cardLlamaCpp.style.display = (v === 'llama_cpp') ? '' : 'none';
}
window._applyBackendCardVisibility = _applyBackendCardVisibility;

document.addEventListener('change', (e) => {
  if (e.target.id === 'backend-type') {
    _applyBackendCardVisibility(e.target.value);
  }
});

// Deep-linking via URL hash changes (e.g. from dashboard widgets)
window.addEventListener('hashchange', () => {
    let tab = window.location.hash.substring(1);
    if (tab && tab.startsWith('tab-')) tab = tab.slice(4);
    if (tab && typeof showTab === 'function') showTab(tab);
});

// Start background panel hydration so the search engine can index all panels.
// Delayed to 8 seconds so the UI fully renders before any prefetching begins.
// Hydration is also gated by the 'hecos-search-preload' localStorage toggle (default: OFF).
if (document.readyState === 'complete') {
    window._startProgressiveHydration(8000);
} else {
    window.addEventListener('load', () => window._startProgressiveHydration(8000));
}
