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

        // ── PHASE 2: Background metadata (options, registry, audio, media) ──
        // /hecos/options calls ModelManager (slow) — must NOT block anything.
        console.log('[Init] Loading background metadata...');
        const metaPromise = Promise.allSettled([
            fetchWithTimeout('/hecos/options'),
            fetchWithTimeout('/api/plugins/registry'),
            fetchWithTimeout('/api/audio/devices'),
            fetchWithTimeout('/api/audio/config'),
            fetchWithTimeout('/hecos/api/config/media'),
            fetch('/api/webui/state')
        ]);

        metaPromise.then(async (results) => {
            const [resOpts, resReg, resAudio, resAudCfg, resMed, resState] = results;

            if (resOpts.status === 'fulfilled' && resOpts.value.ok) {
                try { window.sysOptions = await resOpts.value.json(); } catch (e) { }
            }
            if (resReg.status === 'fulfilled' && resReg.value.ok) {
                try { mergeRegistry(await resReg.value.json()); } catch (e) { }
            }
            if (resState.status === 'fulfilled' && resState.value.ok) {
                try { uiState = Object.assign(uiState, await resState.value.json()); } catch (e) { }
            }
            if (resAudio.status === 'fulfilled'  && resAudio.value.ok)  try { audioDevices = await resAudio.value.json();               } catch (e) { }
            if (resAudCfg.status === 'fulfilled' && resAudCfg.value.ok) try { audioConfig  = (await resAudCfg.value.json()).config;       } catch (e) { }
            if (resMed.status === 'fulfilled'    && resMed.value.ok)    try {
                mediaConfig = await resMed.value.json();
                if (_panelCache['igen'] && typeof populateMediaUI === 'function') populateMediaUI();
            } catch (e) { }

            console.log('[Init] Background metadata loaded.');
            // Final re-render: apply registry merges + plugin state filters
            renderConfigHub(viewMode);
            populateUI();
            isInitialLoading = false;
            setSaveMsg((I18N.msg_synced || 'Synced') + ' (' + new Date().toLocaleTimeString() + ')', 'ok');
            console.timeEnd('[Init] Total load');
        });

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

window.initAll       = initAll;
window.mergeRegistry = mergeRegistry;
window.loadUIState   = loadUIState;
window.saveUIState   = saveUIState;
