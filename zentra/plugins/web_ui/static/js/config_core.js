/**
 * Zentra Core WebUI - Core Configuration Logic
 * Handles initialization, global state, and shared utilities.
 */

// Use window objects to share state with config_mapper.js
window.cfg = {};
window.sysOptions = {};
let audioDevices = null;
let audioConfig = null;
let mediaConfig = null;
let isInitialLoading = false;


const I18N = window.I18N || {};
let configRegistry = {};
let uiState = {
    collapsedCategories: []
};
let viewMode = localStorage.getItem('zentra-config-view') || 'tabs';
let activeTab = 'backend';

/**
 * Tab switching logic
 */
function showTab(name, skipScroll = false) {
  let targetId = name;
  const hub = window.CONFIG_HUB;
  const mod = hub.modules.find(m => m.id === name);

  // 1. Resolve Target ID via tagMap or category
  if (hub.tagMap && hub.tagMap[mod?.pluginTag]) {
      targetId = hub.tagMap[mod.pluginTag];
  } else if (mod && mod.cat === 'MCP') {
      targetId = 'mcp';
  }

  // 1.5 Special Redirects
  if (targetId === 'drive-editor') {
      window.location.href = '/drive';
      return;
  }

  let panel = document.getElementById('tab-' + targetId);
  
  // 2. Fallback Redirection (if panel still not found)
  if (!panel && mod && mod.cat === 'PLUGINS') {
      console.log(`Panel tab-${targetId} not found. Redirecting to plugins toggle list.`);
      targetId = 'plugins';
      panel = document.getElementById('tab-plugins');
      
      // SCROLL TO PLUGIN ROW in Global List
      setTimeout(() => {
          const row = document.querySelector(`[data-plugin="${mod.pluginTag || name.toUpperCase().replace('-','_')}"]`);
          if (row) {
              const parentRow = row.closest('.plugin-row');
              if (parentRow) {
                  parentRow.scrollIntoView({ behavior: 'smooth', block: 'center' });
                  parentRow.style.background = 'rgba(108,140,255,0.1)';
                  setTimeout(() => { parentRow.style.background = ''; }, 2000);
              }
          }
      }, 300);
  }

  activeTab = name; // Consolidate the logical active tab
  document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.module-card').forEach(c => c.classList.remove('active'));

  if (panel) panel.classList.add('active');

  // Highlight the correct tab btn
  const tabBtn = document.querySelector(`.tab[onclick*="'${name}'"]`);
  if (tabBtn) tabBtn.classList.add('active');
  else {
      // If we redirected, highlight the container tab
      const containerTab = document.querySelector(`.tab[onclick*="'${targetId}'"]`);
      if (containerTab) containerTab.classList.add('active');
  }

  const card = document.querySelector(`.module-card[onclick*="'${name}'"]`);
  if (card) card.classList.add('active');

  // Removed automatic setViewMode('tabs') to allow persistent Wall/Grid navigation
  if (viewMode === 'wall' && panel && !skipScroll) {
      panel.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  // Call specific load functions
  if (name === 'users') {
      if (typeof loadMyProfile === 'function') loadMyProfile();
      if (typeof loadUsersData === 'function') loadUsersData();
  }
  if (name === 'payload' && typeof loadPayloadData === 'function') loadPayloadData();
  if (name === 'drive' && typeof loadDriveConfig === 'function') loadDriveConfig();
  if (name === 'logs' && typeof startLogStream === 'function') {
      startLogStream();
      if (typeof refreshLogFiles === 'function') refreshLogFiles();
      setTimeout(() => {
          if (typeof activeLogWindows !== 'undefined') {
              activeLogWindows.forEach(w => {
                  if (w && w.body) w.body.scrollTop = w.body.scrollHeight;
              });
          }
      }, 50);
  }
  if (name === 'keymanager' && typeof kmRefresh === 'function') kmRefresh();
}

function setViewMode(mode, silent = false) {
    viewMode = mode;
    localStorage.setItem('zentra-config-view', mode);
    
    const tabsContainer = document.getElementById('tabs-bar-container');
    const wallContainer = document.getElementById('config-wall');
    const switcherTabs = document.getElementById('view-tabs');
    const switcherWall = document.getElementById('view-wall');

    if (mode === 'wall') {
        if (tabsContainer) tabsContainer.style.display = 'none';
        if (wallContainer) wallContainer.style.display = 'flex';
        if (switcherWall) switcherWall.classList.add('active');
        if (switcherTabs) switcherTabs.classList.remove('active');
        renderConfigHub('wall');
    } else {
        if (tabsContainer) tabsContainer.style.display = 'block';
        if (wallContainer) wallContainer.style.display = 'none';
        if (switcherTabs) switcherTabs.classList.add('active');
        if (switcherWall) switcherWall.classList.remove('active');
        renderConfigHub('tabs');
    }
}

async function fetchWithTimeout(resource, options = {}) {
  const { timeout = 10000 } = options;
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), timeout);
  try {
    const response = await fetch(resource, { ...options, signal: controller.signal });
    clearTimeout(id);
    return response;
  } catch (error) {
    clearTimeout(id);
    if (error.name === 'AbortError') {
        console.warn("Fetch aborted:", resource);
        // Return a mock response so the caller doesn't break if it expects one
        return { ok: false, json: async () => ({ ok: false, error: 'Aborted' }) };
    }
    throw error;
  }
}

/**
 * Master Initialization
 */
async function initAll(attempt = 1) {
    isInitialLoading = true;
    console.log(`Initializing Configuration (Attempt ${attempt})...`);
    const start = Date.now();
    setSaveMsg(I18N.msg_loading || 'Loading...', 'muted');

    try {
        // 1. Fetch CRITICAL data first
        const [rOpts, rCfg] = await Promise.all([
            fetchWithTimeout('/zentra/options'),
            fetchWithTimeout('/zentra/config')
        ]);

        if (!rOpts.ok || !rCfg.ok) {
            throw new Error(`Critical fetch failed: Options=${rOpts.status}, Config=${rCfg.status}`);
        }

        sysOptions = await rOpts.json();
        cfg = await rCfg.json();
        window.cfg = cfg;
        window.sysOptions = sysOptions;

        // 2. Initial Render (with static modules)
        setViewMode(viewMode, true);
        renderConfigHub();
        showTab(activeTab, true);

        // 3. Lazy-load metadata (Registry, Audio, UI State)
        console.log("Loading metadata in background...");
        const metaPromise = Promise.allSettled([
            fetchWithTimeout('/api/plugins/registry'),
            fetchWithTimeout('/api/audio/devices'),
            fetchWithTimeout('/api/audio/config'),
            fetchWithTimeout('/zentra/api/config/media'),
            fetch('/api/webui/state')
        ]);

        metaPromise.then(async (results) => {
            const [resReg, resAudio, resAudCfg, resMed, resState] = results;

            // Process Registry
            if (resReg.status === 'fulfilled' && resReg.value.ok) {
                try {
                    const registry = await resReg.value.json();
                    mergeRegistry(registry);
                } catch (e) { }
            }

            // Process UI State
            if (resState.status === 'fulfilled' && resState.value.ok) {
                try { uiState = Object.assign(uiState, await resState.value.json()); } catch (e) { }
            }

            // Process Audio/Media if successful
            if (resAudio.status === 'fulfilled' && resAudio.value.ok) try { audioDevices = await resAudio.value.json(); } catch (e) { }
            if (resAudCfg.status === 'fulfilled' && resAudCfg.value.ok) try { audioConfig = (await resAudCfg.value.json()).config; } catch (e) { }
            if (resMed.status === 'fulfilled' && resMed.value.ok) try { mediaConfig = await resMed.value.json(); } catch (e) { }

            console.log("Background metadata loaded.");
            renderConfigHub(); // Re-render with all discovered data and collapsed state
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

function mergeRegistry(registry) {
    const hub = window.CONFIG_HUB;
    Object.keys(registry).forEach(tag => {
        const plug = registry[tag];
        const resolvedId = (hub.tagMap && hub.tagMap[tag]) || tag.toLowerCase().replace('_', '-');
        const existing = hub.modules.find(m => m.id === resolvedId || m.pluginTag === tag);

        if (existing) {
            if (!existing.icon) existing.icon = plug.icon;
            if (!existing.pluginTag) existing.pluginTag = tag;
        } else {
            hub.modules.push({
                id: resolvedId,
                label: tag,
                icon: plug.icon || '🧩',
                cat: plug.category || 'CONNETTIVITÀ',
                pluginTag: tag
            });
        }
    });
}

/**
 * Persistence: Load UI state from server
 */
async function loadUIState() {
    try {
        const r = await fetch('/api/webui/state');
        if (r.ok) {
            const data = await r.json();
            uiState = Object.assign(uiState, data);
        }
    } catch(e) { console.warn("Could not load UI state:", e); }
}

/**
 * Persistence: Save UI state to server
 */
async function saveUIState() {
    try {
        await fetch('/api/webui/state', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(uiState)
        });
    } catch(e) { console.error("Could not save UI state:", e); }
}

function toggleCategory(catId) {
    const idx = uiState.collapsedCategories.indexOf(catId);
    if (idx === -1) {
        uiState.collapsedCategories.push(catId);
    } else {
        uiState.collapsedCategories.splice(idx, 1);
    }
    
    saveUIState();
    renderConfigHub(); // Re-render to update icons and visibility
}

function toggleAllCategories(expanded) {
    const hub = window.CONFIG_HUB;
    if (!hub || !hub.categories) return;
    
    if (expanded) {
        uiState.collapsedCategories = [];
    } else {
        uiState.collapsedCategories = Object.keys(hub.categories);
    }
    
    saveUIState();
    renderConfigHub();
}

// (Mapping logic extracted to config_mapper.js)

async function saveConfig(silent = false) {
  if (isInitialLoading) return;
  if (!silent) setSaveMsg(I18N.msg_saving || 'Saving...', 'muted');
  try {
    const payload = buildPayload();
    payload._force_restart = !silent;

    const audioPayload = (typeof buildAudioPayload === 'function') ? buildAudioPayload() : {};
    const mediaPayload = (typeof buildMediaPayload === 'function') ? buildMediaPayload() : {};
    
    const [resCfg, resAud, resMed] = await Promise.all([
        fetch('/zentra/config', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        }),
        fetch('/api/audio/config', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(audioPayload)
        }),
        fetch('/zentra/api/config/media', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(mediaPayload)
        })
    ]);
    
    const data = await resCfg.json();
    const audData = await resAud.json();
    const medData = await resMed.json();
    
    if (data.ok && audData.ok && medData.ok) {
      if (!silent) {
          setSaveMsg(I18N.msg_saved || 'Saved', 'ok');
          
          // Check if any critical restart-required field was changed
          if (typeof isRestartNeeded === 'function' && isRestartNeeded()) {
            const reboot = confirm("Hai modificato parametri critici (Porte/HTTPS). Vuoi riavviare Zentra ora per applicare i cambiamenti?\n\n(Altrimenti dovrai riavviare manualmente dopo il salvataggio)");
            if (reboot) {
              rebootSystem();
              return;
            }
          }
          
          setTimeout(() => location.reload(), 1500);
      }
    } else {
      setSaveMsg('Error saving config.', 'err');
    }
  } catch (e) {
    setSaveMsg('Fetch error: ' + e, 'err');
  }
}

// (Payload builder extracted to config_mapper.js)

function setSaveMsg(msg, type) {
  const el = document.getElementById('save-msg');
  if (!el) return;
  el.textContent = msg;
  el.style.color = type === 'ok' ? 'var(--green)' : type === 'err' ? 'var(--red)' : 'var(--muted)';
}

async function refreshStatus() {
  try {
    const r = await fetch('/zentra/status');
    const d = await r.json();
    setSpanText('s-backend', d.backend || '—');
    setSpanText('s-model', d.model || '—');
    setSpanText('s-bridge', d.bridge || '—');
    setSpanText('s-mic', d.mic || '—');
    setSpanText('s-tts', d.tts || '—');
    setSpanText('s-config', d.config || '—');
    setSpanText('hdr-model', d.model || (I18N.offline || 'Offline'));
    
    const m = document.getElementById('s-model');
    if (m) m.className = 'stat-val ' + (d.model && d.model !== '—' ? 'val-ok' : 'val-warn');
  } catch(e) {
    setSpanText('hdr-model', I18N.offline || 'Offline');
  }
}

function setSpanText(id, text) { const el = document.getElementById(id); if (el) el.textContent = text; }

async function rebootSystem() {
  setSaveMsg('Rebooting...', 'err');
  try {
    const res = await fetch("/api/system/reboot", { method: "POST" });
    if (res.ok) {
       console.log("Reboot command sent.");
       setTimeout(() => { location.reload(); }, 5000);
    } else {
       const err = await res.json();
       setSaveMsg("Reboot error: " + (err.error || "Unknown"), 'err');
    }
  } catch (e) {
    setSaveMsg("Network error during reboot", 'err');
  }
}

function escapeHtml(text) {
  const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
  return (text || '').replace(/[&<>"']/g, m => map[m]);
}

/**
 * ZENTRA HUB ENGINE v0.18.0
 */
function renderConfigHub(mode = 'tabs') {
    const hub = window.CONFIG_HUB;
    const tabsBar = document.getElementById('config-tabs-bar');
    const wallArea = document.getElementById('config-wall');
    const userRole = (window.currentUser && window.currentUser.role) || 'user';

    if (!tabsBar || !wallArea) return;

    // Filter modules based on dynamic plugin status
    const visibleModules = hub.modules.filter(m => {
        // Admin check
        if (m.adminOnly && userRole !== 'admin') return false;
        
        // Plugin check
        if (m.pluginTag) {
            const p = window.cfg.plugins && window.cfg.plugins[m.pluginTag];
            if (p && p.enabled === false) return false;
        }
        
        // Modules with panels always visible. 
        // Modules from MCP category are always visible 
        // Modules in tagMap are always visible
        const hasPanel = document.getElementById('tab-' + m.id);
        const isMapped = hub.tagMap && hub.tagMap[m.pluginTag];
        const isMcp = (m.cat === 'MCP');
        
        return (hasPanel || isMapped || isMcp);
    });

    // Sort by category order then label
    visibleModules.sort((a, b) => {
        const catA = hub.categories[a.cat] || { order: 99 };
        const catB = hub.categories[b.cat] || { order: 99 };
        if (catA.order !== catB.order) return catA.order - catB.order;
        return a.label.localeCompare(b.label);
    });

    // 0. Pre-calculate counts
    const catCounts = {};
    visibleModules.forEach(m => {
        catCounts[m.cat] = (catCounts[m.cat] || 0) + 1;
    });

    // 1. Render TABS
    let tabsHtml = '';
    let currentTabCat = null;
    visibleModules.forEach(m => {
        if (m.cat !== currentTabCat) {
            if (currentTabCat !== null) tabsHtml += `</div></div>`; // Close previous section
            currentTabCat = m.cat;
            const catData = hub.categories[currentTabCat] || { label: currentTabCat, icon: '📂' };
            const isCollapsed = uiState.collapsedCategories.includes(currentTabCat);
            const toggleIcon = isCollapsed ? '⊕' : '⊖';

            tabsHtml += `
                <div class="category-group ${isCollapsed ? 'collapsed' : ''}">
                    <div class="category-header" onclick="toggleCategory('${currentTabCat}')">
                        <span class="cat-toggle">${toggleIcon}</span>
                        <span class="cat-label">${catData.icon} ${window.t ? window.t(catData.label) : catData.label}</span>
                        <span class="cat-badge">${catCounts[currentTabCat]}</span>
                        <div class="cat-line"></div>
                    </div>
                    <div class="category-content tabs">
            `;
        }
        
        const activeClass = (activeTab === m.id) ? 'active' : '';
        const icon = window.getIconForModule(m.id, m.label, m.icon);
        tabsHtml += `<button class="tab ${activeClass}" onclick="showTab('${m.id}')">${icon} ${window.t ? window.t(m.label) : m.label}</button>`;
    });
    if (visibleModules.length > 0) tabsHtml += `</div></div>`; // Close last section
    tabsBar.innerHTML = tabsHtml;

    // 2. Render WALL
    let wallHtml = '';
    let currentCat = null;
    visibleModules.forEach(m => {
        if (m.cat !== currentCat) {
            if (currentCat !== null) wallHtml += `</div></div>`; // Close previous section
            currentCat = m.cat;
            const catData = hub.categories[currentCat] || { label: currentCat, icon: '📂' };
            const isCollapsed = uiState.collapsedCategories.includes(currentCat);
            const toggleIcon = isCollapsed ? '⊕' : '⊖';
            wallHtml += `
                <div class="category-group ${isCollapsed ? 'collapsed' : ''}">
                    <div class="category-header" onclick="toggleCategory('${currentCat}')">
                        <span class="cat-toggle">${toggleIcon}</span>
                        <span class="cat-label">${catData.icon} ${window.t ? window.t(catData.label) : catData.label}</span>
                        <span class="cat-badge">${catCounts[currentCat]}</span>
                        <div class="cat-line"></div>
                    </div>
                    <div class="category-content">
            `;
        }
        
        const activeClass = (activeTab === m.id) ? 'active' : '';
        const icon = window.getIconForModule(m.id, m.label, m.icon);
        wallHtml += `
            <div class="module-card ${activeClass}" onclick="showTab('${m.id}')">
                <div class="m-icon">${icon}</div>
                <div class="m-label">${window.t ? window.t(m.label) : m.label}</div>
                <div class="m-cat">${currentCat}</div>
            </div>
        `;
    });
    if (visibleModules.length > 0) wallHtml += `</div></div>`; // Close last section
    wallArea.innerHTML = wallHtml;
}

window.setViewMode = setViewMode;
window.renderConfigHub = renderConfigHub;

window.showTab = showTab;
window.initAll = initAll;
window.toggleAllCategories = toggleAllCategories;
window.saveConfig = saveConfig;
window.refreshStatus = refreshStatus;
window.rebootSystem = rebootSystem;
// window.populateSelect, window.populateUI moved to config_mapper
// --- Event Listeners (Global/Core) ---

// Listen for global checkbox/select changes for auto-saving
document.addEventListener('change', (e) => {
  if (e.target.type === 'checkbox' || e.target.tagName === 'SELECT') {
    // Sync Image Gen enabled status between different UI locations
    if (e.target.id === 'igen-enabled') {
        const other = document.querySelector('[data-plugin="IMAGE_GEN"]');
        if (other) other.checked = e.target.checked;
    } else if (e.target.dataset.plugin === 'IMAGE_GEN') {
        const other = document.getElementById('igen-enabled');
        if (other) other.checked = e.target.checked;
    }
    
    // Auto-stop voice if toggle is turned off
    if (e.target.id === 'sys-voice-status' && !e.target.checked) {
       if (typeof stopVoice === 'function') stopVoice();
    }
    
    saveConfig(true);
  }
});

// Handle Backend Type card switching
document.addEventListener('DOMContentLoaded', () => {
    const backendTypeEl = document.getElementById('backend-type');
    if (backendTypeEl) {
        backendTypeEl.addEventListener('change', function() {
          const v = this.value;
          const cardCloud = document.getElementById('card-cloud');
          const cardOllama = document.getElementById('card-ollama');
          const cardKobold = document.getElementById('card-kobold');
          if (cardCloud) cardCloud.style.display  = v === 'cloud'  ? '' : 'none';
          if (cardOllama) cardOllama.style.display = v === 'ollama' ? '' : 'none';
          if (cardKobold) cardKobold.style.display = v === 'kobold' ? '' : 'none';
        });
    }
});

