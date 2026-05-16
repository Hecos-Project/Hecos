/**
 * config_core_hub.js
 * CONFIG HUB ENGINE — renders the tab bar, wall view, and filter category bar.
 * Also provides injectIconsInPanel for automatic icon decoration.
 * Depends on: config_core_navigation.js (showTab, toggleCategory, setCategoryFilter)
 * Uses globals: _panelCache, viewMode, activeTab, uiState, window.activeCategoryFilter
 *               (declared in config_core.js entry point)
 */

/**
 * Renders the category filter pill buttons above the hub.
 */
function renderFilterTabs() {
    const container = document.getElementById('config-filter-tabs');
    const hub       = window.CONFIG_HUB;
    if (!container || !hub) return;

    const userRole = (window.currentUser && window.currentUser.role) || 'user';
    const allVisible = hub.modules.filter(m => {
        if (m.adminOnly && userRole !== 'admin') return false;
        if (m.isExtension && m.parentPluginTag) {
            const parent = window.cfg.plugins && window.cfg.plugins[m.parentPluginTag];
            if (!parent || parent.enabled === false) return false;
            const extId = m.pluginTag.replace(m.parentPluginTag + '_', '').toLowerCase();
            const extState = (parent.extensions || {})[extId];
            if (extState && extState.enabled === false) return false;
            return !!document.getElementById('tab-' + m.id);
        }
        if (m.pluginTag) {
            const p = window.cfg.plugins && window.cfg.plugins[m.pluginTag];
            if (p && p.enabled === false) return false;
        }
        return (document.getElementById('tab-' + m.id) || (hub.tagMap && hub.tagMap[m.pluginTag]) || m.cat === 'MCP');
    });

    const counts = { 'ALL': allVisible.length };
    allVisible.forEach(m => { counts[m.cat] = (counts[m.cat] || 0) + 1; });

    let html = `
        <button class="filter-btn ${window.activeCategoryFilter === 'ALL' ? 'active' : ''}" onclick="setCategoryFilter('ALL')">
            <span><i class="fas fa-star"></i></span> ${window.t ? window.t('hub_filter_all') : 'Tutto'}
            <span class="btn-badge">${counts['ALL']}</span>
        </button>
    `;

    Object.keys(hub.categories).forEach(catId => {
        const cat         = hub.categories[catId];
        const activeClass = (window.activeCategoryFilter === catId) ? 'active' : '';
        const count       = counts[catId] || 0;
        if (count === 0) return;
        html += `
            <button class="filter-btn ${activeClass}" onclick="setCategoryFilter('${catId}')">
                <span>${cat.icon}</span> ${window.t ? window.t(cat.label) : catId}
                <span class="btn-badge">${count}</span>
            </button>
        `;
    });
    container.innerHTML = html;
}

/**
 * Main Hub render — builds tab bar, wall cards, and filter bar.
 */
function renderConfigHub(mode = 'tabs') {
    const hub      = window.CONFIG_HUB;
    const tabsBar  = document.getElementById('config-tabs-bar');
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

    // Visibility filter
    const visibleModules = hub.modules.filter(m => {
        if (m.adminOnly && userRole !== 'admin') return false;

        if (m.isExtension && m.parentPluginTag) {
            const parent = window.cfg.plugins && window.cfg.plugins[m.parentPluginTag];
            if (!parent || parent.enabled === false) return false;
            const extId    = m.pluginTag.replace(m.parentPluginTag + '_', '').toLowerCase();
            const extState = (parent.extensions || {})[extId];
            if (extState && extState.enabled === false) return false;
            return (_panelCache[m.id] || !!window.LAZY_PANEL_IDS?.has(m.id) || !!document.getElementById('tab-' + m.id));
        }

        if (m.pluginTag) {
            const p = window.cfg.plugins && window.cfg.plugins[m.pluginTag];
            if (p && p.enabled === false) return false;
        }

        const inCache   = !!_panelCache[m.id];
        const inLazySet = !!(window.LAZY_PANEL_IDS && window.LAZY_PANEL_IDS.has(m.id));
        const hasPanel  = !!document.getElementById('tab-' + m.id);
        const isMapped  = !!(hub.tagMap && hub.tagMap[m.pluginTag]);
        const isMcp     = (m.cat === 'MCP');
        return (inCache || inLazySet || hasPanel || isMapped || isMcp);
    });

    // Category filter
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

    // Icon injection helper
    window.injectIconsInPanel = function(specificId = null) {
        if (!hub) return;
        const modulesToProcess = specificId
            ? hub.modules.filter(m => m.id === specificId)
            : hub.modules;

        setTimeout(() => {
            modulesToProcess.forEach(m => {
                const panel = document.getElementById('tab-' + (specificId || m.id));
                if (!panel) return;
                const titles = panel.querySelectorAll('.card-title, .panel-title, .section-title');
                titles.forEach(title => {
                    if (title.getAttribute('data-icon-injected')) return;
                    const icon = window.getIconForModule(m.id, m.label, m.icon);
                    let cleanText = title.innerHTML.trim();
                    cleanText = cleanText.replace(/^[ \u00a9\u00ae\u2000-\u3300\ud83c\ud83d\ud83e\ud83f][\ufe00-\ufe0f]?\s*/u, '');
                    cleanText = cleanText.replace(/^(✅|❌|⚠️|🧠|☁️|🛣️|🤖|🌉|🔊|⚙️|🧩|🛡️|🔒|⏳|💾|↺|📊|🎨|🔍|🛠️|📁|📝|🖼️|🌐|📷|🏠|❓|ℹ️|⚡)\s*/u, '');
                    if (!cleanText || cleanText.length < 2) {
                        cleanText = window.t ? window.t(m.label) : m.label;
                    }
                    title.innerHTML = `${icon} ${cleanText}`;
                    title.setAttribute('data-icon-injected', 'true');
                });
            });
        }, 200);
    };
    window.injectIconsInPanel();

    // Pre-calculate counts per category
    const catCounts = {};
    filteredModules.forEach(m => { catCounts[m.cat] = (catCounts[m.cat] || 0) + 1; });

    // 1. Render TABS bar
    let tabsHtml = '';
    let currentTabCat = null;
    filteredModules.forEach(m => {
        if (m.cat !== currentTabCat) {
            if (currentTabCat !== null) tabsHtml += `</div></div>`;
            currentTabCat = m.cat;
            const catData   = hub.categories[currentTabCat] || { label: currentTabCat, icon: '📂' };
            const isCollapsed = uiState.collapsedCategories.includes(currentTabCat);
            tabsHtml += `
                <div class="category-group ${isCollapsed ? 'collapsed' : ''}">
                    <div class="category-header" onclick="toggleCategory('${currentTabCat}')">
                        <span class="cat-toggle">${isCollapsed ? '⊕' : '⊖'}</span>
                        <span class="cat-label">${catData.icon} ${window.t ? window.t(catData.label) : catData.label}</span>
                        <span class="cat-badge">${catCounts[currentTabCat]}</span>
                        <div class="cat-line"></div>
                    </div>
                    <div class="category-content tabs">
            `;
        }
        const activeClass = (activeTab === m.id) ? 'active' : '';
        const icon        = window.getIconForModule(m.id, m.label, m.icon);
        tabsHtml += `<button class="tab ${activeClass}" onclick="showTab('${m.id}')">${icon} ${window.t ? window.t(m.label) : m.label}</button>`;
    });
    if (filteredModules.length > 0) tabsHtml += `</div></div>`;
    tabsBar.innerHTML = tabsHtml;

    // 2. Render WALL cards
    let wallHtml = '';
    let currentCat = null, currentCatData = null;
    filteredModules.forEach(m => {
        if (m.cat !== currentCat) {
            if (currentCat !== null) wallHtml += `</div></div>`;
            currentCat     = m.cat;
            currentCatData = hub.categories[currentCat] || { label: currentCat, icon: '📂' };
            const isCollapsed = uiState.collapsedCategories.includes(currentCat);
            wallHtml += `
                <div class="category-group ${isCollapsed ? 'collapsed' : ''}">
                    <div class="category-header" onclick="toggleCategory('${currentCat}')">
                        <span class="cat-toggle">${isCollapsed ? '⊕' : '⊖'}</span>
                        <span class="cat-label">${currentCatData.icon} ${window.t ? window.t(currentCatData.label) : currentCatData.label}</span>
                        <span class="cat-badge">${catCounts[currentCat]}</span>
                        <div class="cat-line"></div>
                    </div>
                    <div class="category-content">
            `;
        }
        const activeClass = (activeTab === m.id) ? 'active' : '';
        const icon        = window.getIconForModule(m.id, m.label, m.icon);
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

    // 3. Render category filter pill bar
    renderFilterTabs();
}

window.renderConfigHub  = renderConfigHub;
window.renderFilterTabs = renderFilterTabs;
