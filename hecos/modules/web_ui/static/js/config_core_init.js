/**
 * config_core_init.js
 * Master initialization, registry merging, UI state persistence.
 * Depends on: config_core_utils.js (fetchWithTimeout, setSaveMsg)
 * Uses globals: window.cfg, window.sysOptions, isInitialLoading, uiState
 *               (declared in config_core.js entry point)
 */

/**
 * Master Initialization with retry logic (max 3 attempts).
 */
async function initAll(attempt = 1) {
    isInitialLoading = true;
    console.log(`Initializing Configuration (Attempt ${attempt})...`);
    setSaveMsg(I18N.msg_loading || 'Loading...', 'muted');

    try {
        // 1. If Jinja pre-injected the data, render immediately (zero-latency boot)
        if (Object.keys(window.cfg || {}).length > 0 && Object.keys(window.sysOptions || {}).length > 0) {
            setViewMode(viewMode, true);
            renderConfigHub(viewMode);
            showTab(activeTab, true);
        }

        // 2. If data is not preloaded, fetch from API
        if (Object.keys(window.cfg || {}).length === 0 || Object.keys(window.sysOptions || {}).length === 0) {
            console.log("No preloaded config, fetching from API...");
            const [rOpts, rCfg, rAgent] = await Promise.all([
                fetchWithTimeout('/hecos/options'),
                fetchWithTimeout('/hecos/config'),
                fetchWithTimeout('/hecos/config/agent')
            ]);
            if (!rOpts.ok || !rCfg.ok || !rAgent.ok) {
                throw new Error(`Critical fetch failed: Options=${rOpts.status}, Config=${rCfg.status}, Agent=${rAgent.status}`);
            }
            window.sysOptions   = await rOpts.json();
            window.cfg          = await rCfg.json();
            window.cfg.agent    = await rAgent.json();

            setViewMode(viewMode, true);
            renderConfigHub(viewMode);
            showTab(activeTab, true);
        } else {
            console.log("Using server-injected configuration data.");
        }

        // 3. Lazy-load background metadata (registry, audio devices, media, UI state)
        console.log("Loading metadata in background...");
        const metaPromise = Promise.allSettled([
            fetchWithTimeout('/api/plugins/registry'),
            fetchWithTimeout('/api/audio/devices'),
            fetchWithTimeout('/api/audio/config'),
            fetchWithTimeout('/hecos/api/config/media'),
            fetch('/api/webui/state')
        ]);

        metaPromise.then(async (results) => {
            const [resReg, resAudio, resAudCfg, resMed, resState] = results;

            if (resReg.status === 'fulfilled' && resReg.value.ok) {
                try { mergeRegistry(await resReg.value.json()); } catch (e) { }
            }
            if (resState.status === 'fulfilled' && resState.value.ok) {
                try { uiState = Object.assign(uiState, await resState.value.json()); } catch (e) { }
            }
            if (resAudio.status === 'fulfilled'  && resAudio.value.ok)  try { audioDevices = await resAudio.value.json();               } catch (e) { }
            if (resAudCfg.status === 'fulfilled' && resAudCfg.value.ok) try { audioConfig  = (await resAudCfg.value.json()).config;       } catch (e) { }
            if (resMed.status === 'fulfilled'    && resMed.value.ok)    try { mediaConfig   = await resMed.value.json();                  } catch (e) { }

            console.log("Background metadata loaded.");
            renderConfigHub();
            populateUI();
            isInitialLoading = false;
            setSaveMsg((I18N.msg_synced || 'Synced') + ' (' + new Date().toLocaleTimeString() + ')', 'ok');
        });

        console.log("UI basic layout ready.");

    } catch (e) {
        console.warn(`Init attempt ${attempt} failed:`, e);
        if (attempt < 3) {
            const delay = 2000;
            setSaveMsg(`Retrying in ${delay / 1000}s...`, 'muted');
            setTimeout(() => initAll(attempt + 1), delay);
        } else {
            console.error("Master Init failed after 3 attempts.");
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
            hub.modules.push({
                id:        resolvedId,
                label:     tag,
                icon:      plug.icon || '<i class="fas fa-puzzle-piece"></i>',
                cat:       plug.category || 'CONNETTIVITÀ',
                pluginTag: tag
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
