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
let activeTab = sessionStorage.getItem('zentra-config-tab') || 'backend';
window.activeCategoryFilter = 'ALL';


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

  // No special redirects for drive-editor anymore, it has a config panel
  // if (targetId === 'drive-editor') ...

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
  sessionStorage.setItem('zentra-config-tab', name);
  
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
  const { timeout = 30000 } = options;
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
        // 1. Fetch CRITICAL data first (only if not preloaded by Jinja)
        // Draw the UI immediately using injected data first (instant render)
        if (Object.keys(window.cfg || {}).length > 0 && Object.keys(window.sysOptions || {}).length > 0) {
            setViewMode(viewMode, true);
            renderConfigHub(viewMode);
            showTab(activeTab, true);
        }

        if (Object.keys(window.cfg || {}).length === 0 || Object.keys(window.sysOptions || {}).length === 0) {
            console.log("No preloaded config, fetching from API...");
            const [rOpts, rCfg] = await Promise.all([
                fetchWithTimeout('/zentra/options'),
                fetchWithTimeout('/zentra/config')
            ]);
            if (!rOpts.ok || !rCfg.ok) throw new Error(`Critical fetch failed: Options=${rOpts.status}, Config=${rCfg.status}`);
            window.sysOptions = await rOpts.json();
            window.cfg = await rCfg.json();
            
            // Re-render now that we fetched them
            setViewMode(viewMode, true);
            renderConfigHub(viewMode);
            showTab(activeTab, true);
        } else {
            console.log("Using server-injected configuration data.");
        }

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
        // Skip hidden/internal core plugins
        if (hub.internalTags && hub.internalTags.includes(tag)) return;

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

/**
 * Filter by category selection
 */
function setCategoryFilter(cat) {
    window.activeCategoryFilter = cat;
    renderConfigHub(viewMode);
}

function renderFilterTabs() {
    const container = document.getElementById('config-filter-tabs');
    const hub = window.CONFIG_HUB;
    if (!container || !hub) return;

    // Calculate counts for ALL visible modules — must match renderConfigHub() logic exactly
    const userRole = (window.currentUser && window.currentUser.role) || 'user';
    const allVisible = hub.modules.filter(m => {
        if (m.adminOnly && userRole !== 'admin') return false;

        // Extension: check parent enabled + own state + panel existence
        if (m.isExtension && m.parentPluginTag) {
            const parent = window.cfg.plugins && window.cfg.plugins[m.parentPluginTag];
            if (!parent || parent.enabled === false) return false;
            const extId = m.pluginTag.replace(m.parentPluginTag + '_', '').toLowerCase();
            const extState = (parent.extensions || {})[extId];
            if (extState && extState.enabled === false) return false;
            return !!document.getElementById('tab-' + m.id);
        }

        // Standard plugin
        if (m.pluginTag) {
            const p = window.cfg.plugins && window.cfg.plugins[m.pluginTag];
            if (p && p.enabled === false) return false;
        }
        return (document.getElementById('tab-' + m.id) || (hub.tagMap && hub.tagMap[m.pluginTag]) || m.cat === 'MCP');
    });

    const counts = { 'ALL': allVisible.length };
    allVisible.forEach(m => {
        counts[m.cat] = (counts[m.cat] || 0) + 1;
    });

    let html = `
        <button class="filter-btn ${window.activeCategoryFilter === 'ALL' ? 'active' : ''}" onclick="setCategoryFilter('ALL')">
            <span>✨</span> ${window.t ? window.t('hub_filter_all') : 'Tutto'}
            <span class="btn-badge">${counts['ALL']}</span>
        </button>
    `;

    Object.keys(hub.categories).forEach(catId => {
        const cat = hub.categories[catId];
        const activeClass = (window.activeCategoryFilter === catId) ? 'active' : '';
        const count = counts[catId] || 0;
        if (count === 0) return; // Hide empty categories

        html += `
            <button class="filter-btn ${activeClass}" onclick="setCategoryFilter('${catId}')">
                <span>${cat.icon}</span> ${window.t ? window.t(cat.label) : catId}
                <span class="btn-badge">${count}</span>
            </button>
        `;
    });

    container.innerHTML = html;
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
    
    const resCfg = await fetch('/zentra/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await resCfg.json();

    const resAud = await fetch('/api/audio/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(audioPayload)
    });
    const audData = await resAud.json();

    const resMed = await fetch('/zentra/api/config/media', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(mediaPayload)
    });
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
          
          
          // setTimeout(() => location.reload(), 1500);
      } else {
          // Provide clear visual feedback for silent background saves
          setSaveMsg('✓ Changes auto-saved', 'ok');
          // Reset any designated elements that should only be active for one save cycle
          document.querySelectorAll('.save-reset').forEach(el => {
              if (el.type === 'checkbox') el.checked = false;
          });
          setTimeout(() => {
              const msgEl = document.getElementById('save-msg');
              if (msgEl && msgEl.textContent.includes('auto-saved')) {
                  setSaveMsg('', 'muted'); // Clear message without reloading
              }
          }, 3500);
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
    
    // System Metrics with threshold coloring
    const updateMetric = (id, val) => {
        const el = document.getElementById(id);
        if (!el) return;
        el.textContent = (val !== undefined && val !== null) ? val + '%' : '—';
        el.className = 'stat-val ' + (val >= 90 ? 'val-err' : '');
    };
    updateMetric('s-cpu', d.cpu);
    updateMetric('s-ram', d.ram);
    updateMetric('s-vram', d.vram);
    
    // Status indicators with ON/OFF coloring
    const updateStatus = (id, val) => {
        const el = document.getElementById(id);
        if (!el) return;
        el.textContent = val || '—';
        el.className = 'stat-val ' + (val === 'ON' ? 'val-ok' : 'val-err');
    };
    updateStatus('s-mic', d.mic);
    updateStatus('s-tts', d.tts);
    updateStatus('s-ptt', d.ptt);
    
    setSpanText('s-bridge', d.bridge || '—');
    setSpanText('s-config', d.config || '—');
    setSpanText('s-model', d.model || '—');
    
    const isOnline = !!d.model;
    setSpanText('hdr-model', isOnline ? 'Online' : (window.I18N?.webui_chat_offline || 'Offline'));
    const hdrDot = document.getElementById('hdr-dot');
    if (hdrDot) {
        hdrDot.style.background = isOnline ? 'var(--green)' : 'var(--red)';
        hdrDot.style.boxShadow = isOnline ? '0 0 8px var(--green)' : '0 0 8px var(--red)';
        hdrDot.style.animation = isOnline ? 'pulse 2s infinite' : 'none';
    }
    
    // Conditional visibility for system metrics
    const dashEnabled = window.cfg?.plugins?.DASHBOARD?.enabled !== false;
    document.querySelectorAll('.dashboard-only').forEach(el => {
        el.style.display = dashEnabled ? '' : 'none';
    });
  } catch(e) {
    setSpanText('hdr-model', window.I18N?.webui_chat_offline || 'Offline');
    const hdrDot = document.getElementById('hdr-dot');
    if (hdrDot) {
        hdrDot.style.background = 'var(--red)';
        hdrDot.style.boxShadow = '0 0 8px var(--red)';
        hdrDot.style.animation = 'none';
    }
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
 * ZENTRA HUB ENGINE v0.18.1
 */
function renderConfigHub(mode = 'tabs') {
    const hub = window.CONFIG_HUB;
    const tabsBar = document.getElementById('config-tabs-bar');
    const wallArea = document.getElementById('config-wall');
    const userRole = (window.currentUser && window.currentUser.role) || 'user';

    if (!tabsBar || !wallArea) return;

    if (window.activeCategoryFilter === 'ALL') {
        wallArea.classList.add('is-all-mode');
        tabsBar.classList.add('is-all-mode');
    } else {
        wallArea.classList.remove('is-all-mode');
        tabsBar.classList.remove('is-all-mode');
    }


    const visibleModules = hub.modules.filter(m => {
        // Admin check
        if (m.adminOnly && userRole !== 'admin') return false;

        // Extension check: depends on parent plugin being enabled AND its own enabled state
        if (m.isExtension && m.parentPluginTag) {
            const parent = window.cfg.plugins && window.cfg.plugins[m.parentPluginTag];
            if (!parent || parent.enabled === false) return false; // parent off → hide extension
            const extId = m.pluginTag.replace(m.parentPluginTag + '_', '').toLowerCase();
            const extState = (parent.extensions || {})[extId];
            if (extState && extState.enabled === false) return false; // extension explicitly off
            // Extension tab only shown if it has a dedicated panel
            return !!document.getElementById('tab-' + m.id);
        }

        // Standard plugin check
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

    // --- APPLY CATEGORY FILTER ---
    const filteredModules = visibleModules.filter(m => {
        if (window.activeCategoryFilter === 'ALL') return true;
        return m.cat === window.activeCategoryFilter;
    });

    // Sort by category order then label
    filteredModules.sort((a, b) => {
        const catA = hub.categories[a.cat] || { order: 99 };
        const catB = hub.categories[b.cat] || { order: 99 };
        if (catA.order !== catB.order) return catA.order - catB.order;
        return a.label.localeCompare(b.label);
    });

    // --- ICON INJECTION LOGIC ---
    // Automatically add icons to the titles of the configuration panels
    setTimeout(() => {
        filteredModules.forEach(m => {
            const panel = document.getElementById('tab-' + m.id);
            if (!panel) return;
            const title = panel.querySelector('.card-title');
            if (title && !title.getAttribute('data-icon-injected')) {
                const icon = window.getIconForModule(m.id, m.label, m.icon);
                // Prevent duplicates: strip logic if it already starts with an emoji or similar
                let cleanText = title.innerHTML.trim();
                // Simple regex to remove leading emoji if present (basic range)
                cleanText = cleanText.replace(/^[\u{1F300}-\u{1F9FF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}]\s*/u, '');
                
                title.innerHTML = `${icon} ${cleanText}`;
                title.setAttribute('data-icon-injected', 'true');
            }
        });
    }, 100);

    // 0. Pre-calculate counts
    const catCounts = {};
    filteredModules.forEach(m => {
        catCounts[m.cat] = (catCounts[m.cat] || 0) + 1;
    });

    // 1. Render TABS
    let tabsHtml = '';
    let currentTabCat = null;
    filteredModules.forEach(m => {
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
    if (filteredModules.length > 0) tabsHtml += `</div></div>`; // Close last section
    tabsBar.innerHTML = tabsHtml;

    // 2. Render WALL
    let wallHtml = '';
    // Special Landing Page for ALL view in Wall mode
    if (window.activeCategoryFilter === 'ALL') {
        const usedCats = [...new Set(visibleModules.map(m => m.cat))];
        // Sort cats by order
        usedCats.sort((a, b) => {
            const catA = hub.categories[a] || { order: 99 };
            const catB = hub.categories[b] || { order: 99 };
            return catA.order - catB.order;
        });

        usedCats.forEach(catId => {
            const catData = hub.categories[catId] || { label: catId, icon: '📂' };
            const count = visibleModules.filter(m => m.cat === catId).length;
            const translatedLabel = window.t ? window.t(catData.label) : catData.label;
            
            wallHtml += `
                <div class="cat-card" onclick="setCategoryFilter('${catId}')">
                    <div class="cat-card-icon">${catData.icon}</div>
                    <div class="cat-card-label">${translatedLabel}</div>
                    <div class="cat-card-badge">${count}</div>
                </div>
            `;
        });
        wallArea.innerHTML = `<div class="cat-landing-grid">${wallHtml}</div>`;
    } else {
        // Standard Detail view for single category or filtered results
        let currentCat = null;
        let currentCatData = null; 
        filteredModules.forEach(m => {
            if (m.cat !== currentCat) {
                if (currentCat !== null) wallHtml += `</div></div>`; // Close previous section
                currentCat = m.cat;
                currentCatData = hub.categories[currentCat] || { label: currentCat, icon: '📂' };
                const isCollapsed = uiState.collapsedCategories.includes(currentCat);
                const toggleIcon = isCollapsed ? '⊕' : '⊖';
                wallHtml += `
                    <div class="category-group ${isCollapsed ? 'collapsed' : ''}">
                        <div class="category-header" onclick="toggleCategory('${currentCat}')">
                            <span class="cat-toggle">${toggleIcon}</span>
                            <span class="cat-label">${currentCatData.icon} ${window.t ? window.t(currentCatData.label) : currentCatData.label}</span>
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
                    <div class="m-cat">${window.t ? window.t(currentCatData.label) : currentCat}</div>
                </div>
            `;
        });
        if (filteredModules.length > 0) wallHtml += `</div></div>`;
        wallArea.innerHTML = wallHtml;
    }


    // 3. Render FILTER TABS (Categories bar)
    renderFilterTabs();
}


window.setViewMode = setViewMode;
window.renderConfigHub = renderConfigHub;
window.setCategoryFilter = setCategoryFilter;
window.renderFilterTabs = renderFilterTabs;


window.showTab = showTab;
window.initAll = initAll;
window.toggleAllCategories = toggleAllCategories;
window.saveConfig = saveConfig;
window.refreshStatus = refreshStatus;
window.rebootSystem = rebootSystem;
// window.populateSelect, window.populateUI moved to config_mapper
// --- Event Listeners (Global/Core) ---

// Listen for global changes (checkboxes, selects, inputs, textareas) for auto-saving
document.addEventListener('change', (e) => {
  if (e.target.closest('.no-autosave') || e.target.closest('#tab-logs')) return;
  const tag = e.target.tagName;
  const type = e.target.type;
  if (tag === 'SELECT' || tag === 'TEXTAREA' || type === 'checkbox' || (tag === 'INPUT' && type !== 'file')) {
    // Sync Image Gen enabled status between different UI locations
    if (e.target.id === 'igen-enabled') {
        const other = document.querySelector('[data-plugin="IMAGE_GEN"]');
        if (other) other.checked = e.target.checked;
    } else if (e.target.dataset.plugin === 'IMAGE_GEN') {
        const other = document.getElementById('igen-enabled');
        if (other) other.checked = e.target.checked;
    }
    
    // Sync Persona Selectors + mark the changed one as dirty
    if (e.target.id === 'ia-personality-main') {
        // Avatar preview update on persona change
        if (typeof loadPersonaAvatar === 'function') loadPersonaAvatar(e.target.value);
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

