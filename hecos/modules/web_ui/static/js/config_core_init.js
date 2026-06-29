/**
 * config_core_init.js
 * Master initialization, registry merging, UI state persistence.
 * Depends on: config_core_utils.js (fetchWithTimeout, setSaveMsg)
 * Uses globals: window.cfg, window.sysOptions, isInitialLoading, uiState
 *               (declared in config_core.js entry point)
 */

/**
 * Master Initialization with retry logic (max 3 attempts).
 *
 * PHASE 0 (< 10ms): Render the hub tab bar immediately from CONFIG_HUB manifest alone.
 *                   No network, no cfg needed. Menu is visible instantly.
 * PHASE 1 (background): Load window.cfg, options, registry, media config.
 *                   Re-render hub to apply plugin enabled/disabled filters.
 */
async function initAll(attempt = 1) {
    isInitialLoading = true;
    console.time('[Init] Total load');
    console.log(`Initializing Configuration (Attempt ${attempt})...`);
    setSaveMsg(I18N.msg_loading || 'Loading...', 'muted');

    // ── PHASE 0: Render hub IMMEDIATELY ──────────────────────────────────────
    // At this point window.cfg may already be populated (Jinja pre-injection)
    // or may be empty {}. Either way, render NOW so the user sees the menu.
    setViewMode(viewMode, true);
    renderConfigHub(viewMode);
    // Only call showTab if there's an active tab to restore (not 'welcome')
    if (activeTab && activeTab !== 'welcome') {
        showTab(activeTab, true);
    }
    console.log('[Init] Phase 0: Hub rendered immediately.');

    try {
        // ── PHASE 1: Load cfg if not pre-injected ────────────────────────────
        if (!window.cfg || Object.keys(window.cfg).length === 0) {
            console.log('[Init] No pre-injected cfg — fetching from API...');
            try {
                const rCfg = await fetchWithTimeout('/hecos/config');
                if (rCfg.ok) {
                    window.cfg = await rCfg.json();
                    // Re-render now that we have real plugin state
                    renderConfigHub(viewMode);
                    console.log('[Init] Phase 1: cfg loaded, hub re-rendered.');
                }
            } catch(e) {
                console.warn('[Init] cfg fetch failed:', e);
            }
        } else {
            console.log('[Init] Fast-path: cfg already pre-injected by Jinja.');
        }

        // Fetch agent config if missing (small payload, fast)
        if (!window.cfg.agent) {
            try {
                const rAgent = await fetchWithTimeout('/hecos/config/agent');
                if (rAgent.ok) window.cfg.agent = await rAgent.json();
            } catch(e) { console.warn('[Init] Agent config fetch failed:', e); }
        }

        // ── PHASE 2: Background metadata — fully independent, non-blocking ──────
        // Each request is processed as soon as it resolves.
        // /hecos/options (ModelManager) is intentionally last and non-blocking.
        console.log('[Init] Phase 2: launching background fetches...');

        // 2a. Plugin registry — merges dynamic plugins into hub (CRITICAL, fast)
        fetchWithTimeout('/api/plugins/registry')
            .then(r => r.ok ? r.json() : null)
            .then(data => {
                if (data) { try { mergeRegistry(data); } catch(e) {} }
            })
            .catch(() => {});

        // 2b. HPM hub panels — adds config tabs for installed HPM packages (fast)
        fetchWithTimeout('/api/hub/panels')
            .then(r => r.ok ? r.json() : null)
            .then(panels => {
                if (panels && Array.isArray(panels)) {
                    try { mergeHubPanels(panels); } catch(e) {}
                }
            })
            .catch(() => {});

        // 2c. UI state (fast)
        fetch('/api/webui/state')
            .then(r => r.ok ? r.json() : null)
            .then(data => {
                if (data) uiState = Object.assign(uiState, data);
            })
            .catch(() => {});

        // 2d. Audio devices + config (fast)
        fetchWithTimeout('/api/audio/devices')
            .then(r => r.ok ? r.json() : null)
            .then(data => { if (data) audioDevices = data; })
            .catch(() => {});

        fetchWithTimeout('/api/audio/config')
            .then(r => r.ok ? r.json() : null)
            .then(data => { if (data && data.config) audioConfig = data.config; })
            .catch(() => {});

        // 2e. Media config (fast)
        fetchWithTimeout('/hecos/api/config/media')
            .then(r => r.ok ? r.json() : null)
            .then(data => {
                if (data) {
                    mediaConfig = data;
                    if (_panelCache['igen'] && typeof populateMediaUI === 'function') populateMediaUI();
                }
            })
            .catch(() => {});

        // 2f. Core re-render: fired after registry + HPM panels are likely ready (50ms grace)
        setTimeout(() => {
            renderConfigHub(viewMode);
            // Guard: populateUI lives in config_mapper.js (Phase 2 script).
            // If it's already loaded (e.g. cached from a previous visit), run it now.
            // Otherwise the phase2 loader will call it after all mappers are ready.
            if (typeof populateUI === 'function') {
                try { populateUI(); } catch(e) { console.warn('[Init] populateUI failed (mapper not ready?):', e); }
            }
            isInitialLoading = false;
            window.HECOS_HUB_READY = true;  // Signal phase2 loader to start
            setSaveMsg((I18N.msg_synced || 'Synced') + ' (' + new Date().toLocaleTimeString() + ')', 'ok');
            console.timeEnd('[Init] Total load');
            console.log('[Init] Phase 2 complete — hub ready.');
        }, 50);

        // 2g. Model list — SLOW (Ollama/cloud network query). Loaded LAST, completely non-blocking.
        // UI is already fully functional before this completes.
        fetchWithTimeout('/hecos/options', 8000)
            .then(r => r.ok ? r.json() : null)
            .then(data => {
                if (data) {
                    window.sysOptions = data;
                    console.log('[Init] Options loaded (models available for backend panel).');
                }
            })
            .catch(() => { console.log('[Init] /hecos/options unavailable (Ollama offline?). Using cache.'); });

        console.log('[Init] Hub ready. Background sync in progress...');


    } catch (e) {
        console.warn(`Init attempt ${attempt} failed:`, e);
        if (attempt < 3) {
            const delay = 2000;
            setSaveMsg(`Retrying in ${delay / 1000}s...`, 'muted');
            setTimeout(() => initAll(attempt + 1), delay);
        } else {
            console.error('Master Init failed after 3 attempts.');
            setSaveMsg((I18N.msg_err || 'Error') + ': ' + e.message, 'err');
            isInitialLoading = false;
        }
    }
}

/**
 * Merges dynamically discovered plugins from the registry into CONFIG_HUB.
 */
function mergeRegistry(registry) {
    const hub = window.CONFIG_HUB;
    Object.keys(registry).forEach(tag => {
        if (hub.internalTags && hub.internalTags.includes(tag)) return;

        const plug       = registry[tag];
        const resolvedId = (hub.tagMap && hub.tagMap[tag]) || tag.toLowerCase().replace('_', '-');
        const existing   = hub.modules.find(m => m.id === resolvedId || m.pluginTag === tag);

        if (existing) {
            if (!existing.icon)      existing.icon      = plug.icon;
            if (!existing.pluginTag) existing.pluginTag = tag;
        } else {
            // ── HPM-installed or dynamically discovered plugin ───────────────
            // Flag as isHpm so the Module Manager can filter these out
            // (HPM packages have their own section in the Package Manager)
            hub.modules.push({
                id:        resolvedId,
                label:     plug.name || tag,
                icon:      plug.icon || '<i class="fas fa-puzzle-piece"></i>',
                cat:       plug.category || 'CONNETTIVITÀ',
                pluginTag: tag,
                isHpm:     true
            });
        }
    });
}

/** Loads UI state (collapsed categories, etc.) from the server. */
async function loadUIState() {
    try {
        const r = await fetch('/api/webui/state');
        if (r.ok) {
            const data = await r.json();
            uiState = Object.assign(uiState, data);
        }
    } catch(e) { console.warn("Could not load UI state:", e); }
}

/** Persists the current UI state to the server. */
async function saveUIState() {
    try {
        await fetch('/api/webui/state', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(uiState)
        });
    } catch(e) { console.error("Could not save UI state:", e); }
}

/**
 * Merges HPM-installed config panel tabs into CONFIG_HUB.
 * Called with the response from GET /api/hub/panels.
 * Each panel gets a tab in the hub without needing manual edits to config_manifest.js.
 */
function mergeHubPanels(panels) {
    const hub = window.CONFIG_HUB;
    let added = 0;
    panels.forEach(p => {
        const panelId = p.id;
        if (!panelId) return;
        // Skip if already registered (either static or from previous mergeRegistry call)
        const existing = hub.modules.find(m => m.id === panelId || m.pluginTag === p.plugin_tag);
        
        const rawIcon = p.icon || '';
        const iconHtml = rawIcon.includes('<') ? rawIcon : `<i class="fas ${rawIcon || 'fa-puzzle-piece'}"></i>`;

        if (existing) {
            // Overwrite generic registry data with specific HPM package data
            existing.id = panelId;
            existing.label = p.name || panelId;
            existing.icon = iconHtml;
            existing.cat = p.category || existing.cat || 'CONNETTIVITÀ';
            existing.pluginTag = p.plugin_tag || panelId.toUpperCase();
            existing.isHpm = true;
            added++;
        } else {
            hub.modules.push({
                id:        panelId,
                label:     p.name || panelId,
                icon:      iconHtml,
                cat:       p.category || 'CONNETTIVITÀ',
                pluginTag: p.plugin_tag || panelId.toUpperCase(),
                isHpm:     true
            });
            added++;
        }
        // Ensure the panel_id is in the lazy set so the tab renders
        if (window.LAZY_PANEL_IDS) {
            window.LAZY_PANEL_IDS.add(panelId);
        }
        // Ensure tagMap is updated for visibility filtering
        if (p.plugin_tag && hub.tagMap && !hub.tagMap[p.plugin_tag]) {
            hub.tagMap[p.plugin_tag] = panelId;
        }

        // Dynamic Asset Loader (CSS/JS)
        // HPM plugin assets are served via /hpm/static/<plugin_id>/<path>
        // core assets remain under /static/<path>
        const cssPrefix = p.css_file && p.css_file.startsWith('hpm_plugin/') ? '/' : '/static/';
        const jsPrefix  = p.js_file  && p.js_file.startsWith('hpm_plugin/')  ? '/' : '/static/';
        
        if (p.css_file && !document.querySelector(`link[href^="${cssPrefix}${p.css_file}"]`)) {
            const link = document.createElement('link');
            link.rel = 'stylesheet';
            link.href = `${cssPrefix}${p.css_file}`;
            document.head.appendChild(link);
            console.log(`[HPM AssetLoader] Injected CSS: ${p.css_file}`);
        }
        if (p.js_file && !document.querySelector(`script[src^="${jsPrefix}${p.js_file}"]`)) {
            const script = document.createElement('script');
            script.src = `${jsPrefix}${p.js_file}?v=${window.VERSION || Date.now()}`;
            script.defer = true;
            document.head.appendChild(script);
            console.log(`[HPM AssetLoader] Injected JS: ${p.js_file}`);
        }
    });
    if (added > 0) {
        console.log(`[HubPanels] Merged ${added} HPM panel(s) into hub.`);
        // Re-render to show newly added tabs
        if (typeof renderConfigHub === 'function') renderConfigHub(window.viewMode || 'list');
    }
}

window.mergeHubPanels = mergeHubPanels;
window.initAll       = initAll;
window.mergeRegistry = mergeRegistry;
window.loadUIState   = loadUIState;
window.saveUIState   = saveUIState;

window.hpmRefreshConfigHub = async function(evictPanelId = null) {
    // If a panel is being disabled, remove it from cache and DOM so it vanishes instantly
    if (evictPanelId) {
        if (window._panelCache) delete window._panelCache[evictPanelId];
        if (window.LAZY_PANEL_IDS) window.LAZY_PANEL_IDS.delete(evictPanelId);
        const domPanel = document.getElementById('tab-' + evictPanelId);
        if (domPanel) domPanel.remove();
        // If this was the active tab, go back to welcome
        if (typeof activeTab !== 'undefined' && activeTab === evictPanelId) {
            if (typeof showTab === 'function') showTab('welcome');
        }
    }

    try {
        const res = await fetch('/api/hub/panels');
        if (res && res.ok) {
            const panels = await res.json();
            // Remove existing HPM panels
            if (window.CONFIG_HUB && window.CONFIG_HUB.modules) {
                window.CONFIG_HUB.modules = window.CONFIG_HUB.modules.filter(m => !m.isHpm);
            }
            window.mergeHubPanels(panels);
            if (typeof window.renderConfigHub === 'function') {
                window.renderConfigHub(window.viewMode);
            }
        }
    } catch (e) {
        console.warn("[HubRefresh] Failed to refresh HPM panels:", e);
    }
};
