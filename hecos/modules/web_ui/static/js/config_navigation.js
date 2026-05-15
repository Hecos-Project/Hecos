/**
 * Hecos WebUI - Navigation Logic
 * Handles tab switching, lazy-loading of panels, and Hub rendering.
 */

window.activeTab = window.location.hash.substring(1) || sessionStorage.getItem('hecos-config-tab') || 'welcome';
window._panelCache = {};
window._panelFetching = {};

async function showTab(name, skipScroll = false) {
  let targetId = name;
  const hub = window.CONFIG_HUB;
  const mod = (hub && hub.modules) ? hub.modules.find(m => m.id === name) : null;

  const mainWrapper      = document.getElementById('config-main-ui-wrapper');
  const welcomeContainer = document.getElementById('config-welcome-container');
  const tBar             = document.getElementById('tabs-bar-container');
  const wall             = document.getElementById('config-wall');
  
  if (name === 'welcome') {
      if (welcomeContainer) welcomeContainer.style.display = 'block';
      if (mainWrapper) mainWrapper.style.setProperty('display', 'none', 'important');
  } else {
      if (welcomeContainer) welcomeContainer.style.display = 'none';
      if (mainWrapper) mainWrapper.style.display = 'block';
      if (tBar && window.viewMode === 'tabs') tBar.style.display = 'block';
      if (wall && window.viewMode === 'wall') wall.style.display = 'flex';
  }

  if (hub.tagMap && hub.tagMap[mod?.pluginTag]) {
      targetId = hub.tagMap[mod.pluginTag];
  } else if (mod && mod.cat === 'MCP') {
      targetId = 'mcp';
  }

  if (!window._panelCache[targetId] && mod && mod.cat === 'PLUGINS') {
      targetId = 'plugins';
  }

  window.activeTab = name;
  sessionStorage.setItem('hecos-config-tab', name);

  if (name !== 'welcome' && !window._panelCache[targetId]) {
    if (window._panelFetching[targetId]) {
      await window._panelFetching[targetId];
    } else {
      window._panelFetching[targetId] = _loadPanel(targetId);
      await window._panelFetching[targetId];
      delete window._panelFetching[targetId];
    }
  }

  let panel = document.getElementById('tab-' + targetId);
  if (!panel && mod && mod.cat === 'PLUGINS') {
      targetId = 'plugins';
      panel = document.getElementById('tab-plugins');
  }

  document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.module-card').forEach(c => c.classList.remove('active'));

  if (panel) panel.classList.add('active');

  const tabBtn = document.querySelector(`.tab[onclick*="'${name}'"]`);
  if (tabBtn) tabBtn.classList.add('active');
  else {
      const containerTab = document.querySelector(`.tab[onclick*="'${targetId}'"]`);
      if (containerTab) containerTab.classList.add('active');
  }

  const card = document.querySelector(`.module-card[onclick*="'${name}'"]`);
  if (card) card.classList.add('active');

  if (window.viewMode === 'wall' && panel && !skipScroll) {
      panel.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  // Load hooks
  if (name === 'users' && typeof loadUsersData === 'function') loadUsersData();
  if (name === 'drive' && typeof loadDriveConfig === 'function') loadDriveConfig();
  if (name === 'reminder' && typeof window.refreshReminderConfig === 'function') window.refreshReminderConfig();
  if (name === 'calendar' && typeof window.hcal !== 'undefined') window.hcal.refresh?.();
  if (name === 'logs' && typeof startLogStream === 'function') startLogStream();
}

async function _loadPanel(panelId) {
  const container = document.getElementById('panel-container');
  const skeleton  = document.getElementById('panel-skeleton');
  if (!container) return;

  if (skeleton) skeleton.style.display = 'block';
  try {
    const res = await fetch(`/hecos/config/fragment/${panelId}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const html = await res.text();
    const tmp = document.createElement('div');
    tmp.innerHTML = html;
    const scripts = Array.from(tmp.querySelectorAll('script'));
    scripts.forEach(s => s.parentNode.removeChild(s));
    while (tmp.firstChild) container.appendChild(tmp.firstChild);
    window._panelCache[panelId] = true;
    for (const oldScript of scripts) {
      await new Promise((resolve) => {
        const newScript = document.createElement('script');
        Array.from(oldScript.attributes).forEach(attr => newScript.setAttribute(attr.name, attr.value));
        newScript.textContent = oldScript.textContent;
        if (newScript.src) {
          newScript.onload = () => resolve();
          newScript.onerror = () => resolve();
        } else {
          document.head.appendChild(newScript);
          resolve();
          return;
        }
        document.head.appendChild(newScript);
      });
    }
    if (typeof window.injectIconsInPanel === 'function') window.injectIconsInPanel(panelId);
    if (typeof populateUI === 'function') populateUI();
  } catch (e) {
    console.error(`[LazyHub] Failed to load panel '${panelId}':`, e);
  } finally {
    if (skeleton) skeleton.style.display = 'none';
  }
}

function renderConfigHub(mode = 'tabs') {
    const hub = window.CONFIG_HUB;
    if (!hub) return;
    const tabsBar = document.getElementById('config-tabs-bar');
    const wallArea = document.getElementById('config-wall');
    if (!tabsBar || !wallArea) return;

    const visibleModules = hub.modules.filter(m => {
        if (m.adminOnly && window.currentUser?.role !== 'admin') return false;
        const inCache = !!window._panelCache[m.id];
        const inLazySet = !!(window.LAZY_PANEL_IDS && window.LAZY_PANEL_IDS.has(m.id));
        const hasPanel = !!document.getElementById('tab-' + m.id);
        const isMapped = !!(hub.tagMap && hub.tagMap[m.pluginTag]);
        return (inCache || inLazySet || hasPanel || isMapped || m.cat === 'MCP');
    });

    const filteredModules = visibleModules.filter(m => {
        if (!window.activeCategoryFilter || window.activeCategoryFilter === 'ALL') return true;
        return m.cat === window.activeCategoryFilter;
    });

    const catCounts = {};
    filteredModules.forEach(m => catCounts[m.cat] = (catCounts[m.cat] || 0) + 1);

    // Render TABS
    let tabsHtml = '';
    let currentTabCat = null;
    filteredModules.forEach(m => {
        if (m.cat !== currentTabCat) {
            if (currentTabCat !== null) tabsHtml += `</div></div>`;
            currentTabCat = m.cat;
            const catData = hub.categories[currentTabCat] || { label: currentTabCat, icon: '📂' };
            const isCollapsed = window.uiState.collapsedCategories.includes(currentTabCat);
            tabsHtml += `<div class="category-group ${isCollapsed ? 'collapsed' : ''}">
                <div class="category-header" onclick="toggleCategory('${currentTabCat}')">
                    <span class="cat-toggle">${isCollapsed ? '⊕' : '⊖'}</span>
                    <span class="cat-label">${catData.icon} ${window.t(catData.label)}</span>
                    <span class="cat-badge">${catCounts[currentTabCat]}</span>
                    <div class="cat-line"></div>
                </div><div class="category-content tabs">`;
        }
        const activeClass = (window.activeTab === m.id) ? 'active' : '';
        const icon = window.getIconForModule(m.id, m.label, m.icon);
        tabsHtml += `<button class="tab ${activeClass}" onclick="showTab('${m.id}')">${icon} ${window.t(m.label)}</button>`;
    });
    if (filteredModules.length > 0) tabsHtml += `</div></div>`;
    tabsBar.innerHTML = tabsHtml;

    // Render WALL
    let wallHtml = '';
    let currentCat = null;
    filteredModules.forEach(m => {
        if (m.cat !== currentCat) {
            if (currentCat !== null) wallHtml += `</div></div>`;
            currentCat = m.cat;
            const catData = hub.categories[currentCat] || { label: currentCat, icon: '📂' };
            const isCollapsed = window.uiState.collapsedCategories.includes(currentCat);
            wallHtml += `<div class="category-group ${isCollapsed ? 'collapsed' : ''}">
                <div class="category-header" onclick="toggleCategory('${currentCat}')">
                    <span class="cat-toggle">${isCollapsed ? '⊕' : '⊖'}</span>
                    <span class="cat-label">${catData.icon} ${window.t(catData.label)}</span>
                    <span class="cat-badge">${catCounts[currentCat]}</span>
                    <div class="cat-line"></div>
                </div><div class="category-content">`;
        }
        const activeClass = (window.activeTab === m.id) ? 'active' : '';
        const icon = window.getIconForModule(m.id, m.label, m.icon);
        wallHtml += `<div class="module-card ${activeClass}" onclick="showTab('${m.id}')">
            <div class="m-icon">${icon}</div>
            <div class="m-label">${window.t(m.label)}</div>
            <div class="m-cat">${window.t(hub.categories[currentCat].label)}</div>
        </div>`;
    });
    if (filteredModules.length > 0) wallHtml += `</div></div>`;
    wallArea.innerHTML = wallHtml;

    if (typeof renderFilterTabs === 'function') renderFilterTabs();
    if (typeof window.injectIconsInPanel === 'function') window.injectIconsInPanel();
}

function setCategoryFilter(cat) {
    window.activeCategoryFilter = cat;
    sessionStorage.setItem('hecos-config-filter', cat);
    renderConfigHub(window.viewMode);
}

function renderFilterTabs() {
    const container = document.getElementById('config-filter-tabs');
    const hub = window.CONFIG_HUB;
    if (!container || !hub) return;
    
    // Simplified filter tabs for brevity, can be expanded if needed
    let html = `<button class="filter-btn ${window.activeCategoryFilter === 'ALL' ? 'active' : ''}" onclick="setCategoryFilter('ALL')">
        <span><i class="fas fa-star"></i></span> ${window.t('hub_filter_all')}
    </button>`;
    
    Object.keys(hub.categories).forEach(catId => {
        const cat = hub.categories[catId];
        html += `<button class="filter-btn ${window.activeCategoryFilter === catId ? 'active' : ''}" onclick="setCategoryFilter('${catId}')">
            <span>${cat.icon}</span> ${window.t(cat.label)}
        </button>`;
    });
    container.innerHTML = html;
}

window.showTab = showTab;
window.renderConfigHub = renderConfigHub;
window.setCategoryFilter = setCategoryFilter;
window.renderFilterTabs = renderFilterTabs;
