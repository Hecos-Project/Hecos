/**
 * config_core_navigation.js
 * Tab switching, lazy panel loading, view mode, category filters.
 * Depends on: config_core_utils.js (fetchWithTimeout)
 * Uses globals: _panelCache, _panelFetching, viewMode, activeTab, uiState
 *               (all declared in config_core.js entry point)
 */

/**
 * Tab switching — supports lazy-loaded panels.
 * First click: fetches HTML from server, injects into #panel-container.
 * Subsequent clicks served from DOM (no fetch).
 */
async function showTab(name, skipScroll = false) {
  let targetId = name;
  const hub = window.CONFIG_HUB;
  const mod = (hub && hub.modules) ? hub.modules.find(m => m.id === name) : null;

  // Welcome screen toggling
  const mainWrapper      = document.getElementById('config-main-ui-wrapper');
  const welcomeContainer = document.getElementById('config-welcome-container');
  const tBar             = document.getElementById('tabs-bar-container');
  const wall             = document.getElementById('config-wall');

  if (name === 'welcome') {
      if (welcomeContainer) welcomeContainer.style.display = 'block';
      if (mainWrapper)      mainWrapper.style.setProperty('display', 'none', 'important');
  } else {
      if (welcomeContainer) welcomeContainer.style.display = 'none';
      if (mainWrapper)      mainWrapper.style.display = 'block';
      if (tBar && viewMode === 'tabs') tBar.style.display = 'block';
      if (wall && viewMode === 'wall') wall.style.display = 'flex';
  }

  // Resolve target ID via tagMap or MCP category
  if (hub.tagMap && hub.tagMap[mod?.pluginTag]) {
      targetId = hub.tagMap[mod.pluginTag];
  } else if (mod && mod.cat === 'MCP') {
      targetId = 'mcp';
  }

  // Fallback redirect for plugins without a dedicated panel
  if (!_panelCache[targetId] && mod && mod.cat === 'PLUGINS') {
      console.log(`Panel ${targetId} not found. Redirecting to plugins toggle list.`);
      targetId = 'plugins';
  }

  activeTab = name;
  sessionStorage.setItem('hecos-config-tab', name);

  if (name !== 'welcome' && activeTab === 'welcome') {
    sessionStorage.setItem('hecos-config-welcome-seen', 'true');
    uiState.collapsedCategories = [];
  }

  // If the panel was silently pre-fetched (no scripts), remove it so _loadPanel
  // can re-inject it properly with all interactive scripts
  if (window._searchCache && window._searchCache[targetId]) {
      const stalePanel = document.getElementById('tab-' + targetId);
      if (stalePanel && stalePanel.dataset.prefetchOnly === 'true') {
          stalePanel.remove();
      }
      delete window._searchCache[targetId];
  }

  // Lazy load: fetch panel HTML if not yet in DOM
  if (name !== 'welcome' && !_panelCache[targetId]) {
    if (_panelFetching[targetId]) {
      await _panelFetching[targetId];
    } else {
      _panelFetching[targetId] = _loadPanel(targetId);
      await _panelFetching[targetId];
      delete _panelFetching[targetId];
    }
  }

  let panel = document.getElementById('tab-' + targetId);

  // After lazy load, handle plugins fallback scroll
  if (!panel && mod && mod.cat === 'PLUGINS') {
      targetId = 'plugins';
      panel    = document.getElementById('tab-plugins');
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

  document.querySelectorAll('.panel').forEach(p       => p.classList.remove('active'));
  document.querySelectorAll('.tab').forEach(t         => t.classList.remove('active'));
  document.querySelectorAll('.module-card').forEach(c => c.classList.remove('active'));

  if (panel) panel.classList.add('active');

  // Highlight active tab button
  const tabBtn = document.querySelector(`.tab[onclick*="'${name}'"]`);
  if (tabBtn) tabBtn.classList.add('active');
  else {
      const containerTab = document.querySelector(`.tab[onclick*="'${targetId}'"]`);
      if (containerTab) containerTab.classList.add('active');
  }

  const card = document.querySelector(`.module-card[onclick*="'${name}'"]`);
  if (card) card.classList.add('active');

  if (viewMode === 'wall' && panel && !skipScroll) {
      panel.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  // Call panel-specific load functions
  if (name === 'users'   || targetId === 'users') {
      if (typeof loadMyProfile  === 'function') loadMyProfile();
      if (typeof loadUsersData  === 'function') loadUsersData();
  }
  if (name === 'payload' && typeof loadPayloadData === 'function') loadPayloadData();
  if (name === 'drive'   && typeof loadDriveConfig === 'function') loadDriveConfig();
  if (name === 'reminder' && typeof window.refreshReminderConfig === 'function') {
      window.refreshReminderConfig();
      if (typeof window.refreshPresetRingtones === 'function') window.refreshPresetRingtones();
  }
  if (name === 'calendar' && typeof window.hcal !== 'undefined') {
      if (typeof window.hcal.refresh === 'function') window.hcal.refresh();
  }
  if (name === 'logs' && typeof startLogStream === 'function') {
      startLogStream();
      if (typeof refreshLogFiles === 'function') refreshLogFiles();
      setTimeout(() => {
          if (typeof activeLogWindows !== 'undefined') {
              activeLogWindows.forEach(w => { if (w && w.body) w.body.scrollTop = w.body.scrollHeight; });
          }
      }, 50);
  }
  if ((name === 'keymanager' || targetId === 'keymanager') && typeof kmRefresh    === 'function') kmRefresh();
  if ((name === 'ia'         || name === 'persona')        && typeof personaRefresh === 'function') personaRefresh();
}

/**
 * Fetches a config panel fragment and injects it into #panel-container.
 */
async function _loadPanel(panelId) {
  const container = document.getElementById('panel-container');
  const skeleton  = document.getElementById('panel-skeleton');
  if (!container) return;

  if (skeleton) skeleton.style.display = 'block';
  try {
    const res = await fetchWithTimeout(`/hecos/config/fragment/${panelId}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const html = await res.text();

    const tmp = document.createElement('div');
    tmp.innerHTML = html;

    // Extract scripts before injecting (they won't auto-run)
    const scripts = Array.from(tmp.querySelectorAll('script'));
    scripts.forEach(s => s.parentNode.removeChild(s));

    while (tmp.firstChild) {
      container.appendChild(tmp.firstChild);
    }
    _panelCache[panelId] = true;

    // Execute scripts sequentially to preserve dependency order
    for (const oldScript of scripts) {
      await new Promise((resolve) => {
        const newScript = document.createElement('script');
        Array.from(oldScript.attributes).forEach(attr => newScript.setAttribute(attr.name, attr.value));
        newScript.textContent = oldScript.textContent;
        if (newScript.src) {
          newScript.onload  = () => resolve();
          newScript.onerror = () => { console.error(`[LazyHub] Failed to load script: ${newScript.src}`); resolve(); };
        } else {
          document.head.appendChild(newScript);
          resolve();
          return;
        }
        document.head.appendChild(newScript);
      });
    }

    window.injectIconsInPanel(panelId);
    if (typeof populateUI            === 'function') populateUI();
    if (typeof initRestartIndicators === 'function') initRestartIndicators();
    if (window.HecosSearch && typeof window.HecosSearch.run === 'function') {
        const inp = document.getElementById('zs-input');
        if (inp && inp.value.trim()) {
            window.HecosSearch.run(inp.value.trim());
        }
    }
    console.log(`[LazyHub] Panel '${panelId}' loaded and injected.`);
  } catch (e) {
    console.error(`[LazyHub] Failed to load panel '${panelId}':`, e);
    container.insertAdjacentHTML('beforeend',
      `<div class="panel active" id="tab-${panelId}" style="padding:30px; color:var(--red);">
        ⚠️ Failed to load panel. Please try again.
      </div>`
    );
  } finally {
    if (skeleton) skeleton.style.display = 'none';
  }
}

/** Switches between tabs/wall view and persists the choice. */
function setViewMode(mode, silent = false) {
    viewMode = mode;
    localStorage.setItem('hecos-config-view', mode);

    const tabsContainer = document.getElementById('tabs-bar-container');
    const wallContainer = document.getElementById('config-wall');
    const switcherTabs  = document.getElementById('view-tabs');
    const switcherWall  = document.getElementById('view-wall');

    if (mode === 'wall') {
        if (tabsContainer) tabsContainer.style.display = 'none';
        if (wallContainer) wallContainer.style.display = 'flex';
        if (switcherWall)  switcherWall.classList.add('active');
        if (switcherTabs)  switcherTabs.classList.remove('active');
        renderConfigHub('wall');
    } else {
        if (tabsContainer) tabsContainer.style.display = 'block';
        if (wallContainer) wallContainer.style.display = 'none';
        if (switcherTabs)  switcherTabs.classList.add('active');
        if (switcherWall)  switcherWall.classList.remove('active');
        renderConfigHub('tabs');
    }
}

/** Collapses/expands a category group and persists the state. */
function toggleCategory(catId) {
    const idx = uiState.collapsedCategories.indexOf(catId);
    if (idx === -1) {
        uiState.collapsedCategories.push(catId);
    } else {
        uiState.collapsedCategories.splice(idx, 1);
    }
    saveUIState();
    renderConfigHub();
}

/** Expands or collapses all category groups. */
function toggleAllCategories(expanded) {
    const hub = window.CONFIG_HUB;
    if (!hub || !hub.categories) return;
    uiState.collapsedCategories = expanded ? [] : Object.keys(hub.categories);
    saveUIState();
    renderConfigHub();
}

/** Applies a category filter and re-renders the hub. */
function setCategoryFilter(cat) {
    window.activeCategoryFilter = cat;
    sessionStorage.setItem('hecos-config-filter', cat);

    if (activeTab === 'welcome') {
        const welcomeContainer = document.getElementById('config-welcome-container');
        if (welcomeContainer) welcomeContainer.style.display = 'none';
        sessionStorage.setItem('hecos-config-welcome-seen', 'true');
        activeTab = '';
        uiState.collapsedCategories = [];
        const mainWrapper = document.getElementById('config-main-ui-wrapper');
        if (mainWrapper) mainWrapper.style.display = 'block';
        const wall = document.getElementById('config-wall');
        if (wall && viewMode === 'wall') wall.style.display = 'flex';
    }
    renderConfigHub(viewMode);
}

window.showTab              = showTab;
window.setViewMode          = setViewMode;
window.toggleCategory       = toggleCategory;
window.toggleAllCategories  = toggleAllCategories;
window.setCategoryFilter    = setCategoryFilter;

/**
 * Silent background fetch for a panel.
 * Unlike _loadPanel, this does NOT touch the skeleton spinner,
 * does NOT run populateUI() globally, and does NOT execute panel scripts.
 * Its sole purpose is to inject the HTML so the search engine can index it.
 */
async function _prefetchPanel(panelId) {
    if (_panelCache[panelId]) return;  // Already fully loaded by a user click
    if (window._searchCache && window._searchCache[panelId]) return; // Already prefetched
    const container = document.getElementById('panel-container');
    if (!container) return;
    try {
        const res = await fetch(`/hecos/config/fragment/${panelId}`);
        if (!res.ok) return;
        const html = await res.text();
        // Only inject if user hasn't loaded it in the meantime via a click
        if (_panelCache[panelId]) return;
        const tmp = document.createElement('div');
        tmp.innerHTML = html;
        // Strip scripts so they don't auto-execute and mess up state
        tmp.querySelectorAll('script').forEach(s => s.remove());
        // Mark the root element with a data attribute so showTab knows to re-load with scripts
        const firstEl = tmp.firstElementChild;
        if (firstEl) firstEl.dataset.prefetchOnly = 'true';
        // Inject silently — panel will be hidden (no 'active' class)
        while (tmp.firstChild) container.appendChild(tmp.firstChild);
        // Mark as search-only prefetched (NOT _panelCache — so showTab still triggers real load)
        if (!window._searchCache) window._searchCache = {};
        window._searchCache[panelId] = true;
        // Re-run search if user is searching
        if (window.HecosSearch && typeof window.HecosSearch.run === 'function') {
            const inp = document.getElementById('zs-input');
            if (inp && inp.value.trim()) {
                window.HecosSearch.run(inp.value.trim());
            }
        }
    } catch (e) {
        // Silent fail — hydration is best-effort
    }
}

const _prefetchQueue = {};  // panelId → Promise

/**
 * Background Progressive Hydration
 * Silently fetches all panels in the background so the search engine can
 * index ALL configuration content without the user having to open each tab.
 */
window._startProgressiveHydration = function(delayMs = 1500) {
    if (window._hydrationStarted) return;
    window._hydrationStarted = true;
    
    setTimeout(async () => {
        const hub = window.CONFIG_HUB;
        if (!hub || !hub.modules) return;
        
        console.log("[LazyHub] Starting silent background hydration for search indexing...");
        const seen = new Set();
        for (const mod of hub.modules) {
            let pid = mod.id;
            if (hub.tagMap && hub.tagMap[mod.pluginTag]) {
                pid = hub.tagMap[mod.pluginTag];
            } else if (mod.cat === 'MCP') {
                pid = 'mcp';
            } else if (mod.cat === 'PLUGINS') {
                pid = 'plugins';
            }
            if (!pid || seen.has(pid)) continue;
            seen.add(pid);
            // Skip already loaded panels and external links
            if (_panelCache[pid]) continue;
            if (mod.external) continue;
            // Prefetch silently
            if (!_prefetchQueue[pid]) {
                _prefetchQueue[pid] = _prefetchPanel(pid);
            }
            await _prefetchQueue[pid];
            // Small yield between panels so the browser stays responsive
            await new Promise(r => setTimeout(r, 150));
        }
        console.log("[LazyHub] Silent hydration done — all panels indexed.");
    }, delayMs);
};

