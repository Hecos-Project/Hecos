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
function _hexToRgb(hex) {
    if (!hex) return '100,100,100';
    var result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
    return result ? `${parseInt(result[1], 16)}, ${parseInt(result[2], 16)}, ${parseInt(result[3], 16)}` : '100,100,100';
}

/**
 * Safe translation helper: returns the localized string from window.I18N or window.t,
 * or fallbackEn if the key is missing (never returns a raw technical key).
 */
function _hubT(key, fallbackEn) {
    if (window.I18N && window.I18N[key]) return window.I18N[key];
    if (typeof window.t === 'function') {
        const val = window.t(key);
        if (val && val !== key) return val;
    }
    return fallbackEn;
}

// Ensure HPM_TYPE_META is always synchronously defined even before external scripts finish loading
if (!window.HPM_TYPE_META) {
    window.HPM_TYPE_META = {
        plugin:      { label: 'Plugins',      shortLabel: 'Plugins', icon: 'fa-plug',              color: '#3b82f6', order: 1 },
        app:         { label: 'Apps',         shortLabel: 'Apps',    icon: 'fa-th-large',          color: '#8b5cf6', order: 2 },
        system_app:  { label: 'System App',   shortLabel: 'System',  icon: 'fa-layer-group',       color: '#66fcf1', order: 3 },
        widget:      { label: 'Widgets',      shortLabel: 'Widgets', icon: 'fa-expand-arrows-alt', color: '#f59e0b', order: 4 },
        library:     { label: 'Libraries',    shortLabel: 'Libs',    icon: 'fa-book',              color: '#8b5cf6', order: 5 },
        persona:     { label: 'Personas',     shortLabel: 'Soul',    icon: 'fa-user-astronaut',    color: '#ec4899', order: 6 },
        theme:       { label: 'Themes',       shortLabel: 'Themes',  icon: 'fa-palette',           color: '#10b981', order: 7 },
        extension:   { label: 'Extensions',   shortLabel: 'Ext',     icon: 'fa-puzzle-piece',      color: '#45a29e', order: 8 },
        playbook:    { label: 'Playbooks',    shortLabel: 'Books',   icon: 'fa-book-open',         color: '#06b6d4', order: 8.5 },
        skill_pack:  { label: 'Skill Packs',  shortLabel: 'Skills',  icon: 'fa-graduation-cap',   color: '#f97316', order: 9 },
        core_module: { label: 'Core Modules', shortLabel: 'Core',    icon: 'fa-microchip',         color: '#ff4444', order: 10 },
        other:       { label: 'Other',        shortLabel: 'Other',   icon: 'fa-cube',              color: '#6b7280', order: 11 }
    };
}

window.hpmGetModuleTypeBadge = function(m, isTab = false) {
    if (!window.HPM_TYPE_META) return '';
    let type = (m.moduleType || '').toLowerCase().trim();
    if (m.isCore) type = 'core_module';
    if (!type && m.isHpm) type = 'plugin';
    if (!type) return '';
    
    let meta = window.HPM_TYPE_META[type];
    if (!meta && type === 'core_module') {
        meta = { label: 'Core', shortLabel: 'Core', icon: 'fa-microchip', color: '#ff4444' };
    } else if (!meta) {
        meta = window.HPM_TYPE_META['other'];
    }
    
    if (!meta) return '';

    const label = window.t ? (window.t(meta.shortLabel) || window.t(meta.label) || meta.label) : (meta.shortLabel || meta.label);

    if (isTab) {
        return `<span class="type-badge" style="margin-left:6px; background:rgba(${_hexToRgb(meta.color)}, 0.15); color:${meta.color}; font-size:10px; width:20px; height:20px; border-radius:50%; display:inline-flex; justify-content:center; align-items:center;" title="${label}"><i class="fas ${meta.icon}"></i></span>`;
    }

    return `<div class="module-type-badge" style="position:absolute; top:8px; left:8px; background:rgba(${_hexToRgb(meta.color)}, 0.15); color:${meta.color}; font-size:10px; width:22px; height:22px; border-radius:50%; display:flex; justify-content:center; align-items:center;" title="${label}">
        <i class="fas ${meta.icon}"></i>
    </div>`;
};

// ── NEW Modules & Category Badge Tracking (with 3-day auto-expire TTL & click clearing) ──
window.hpmGetCleanNewPanels = function() {
    const TTL_MS = 3 * 24 * 60 * 60 * 1000; // 3 days (72h)
    const now = Date.now();
    let panels = [];
    let timestamps = {};
    try { panels = JSON.parse(localStorage.getItem('hpm_new_panels') || '[]'); } catch(e) {}
    try { timestamps = JSON.parse(localStorage.getItem('hpm_new_panels_ts') || '{}'); } catch(e) {}

    let modified = false;
    const validPanels = [];
    const validTimestamps = {};

    panels.forEach(id => {
        if (!id) return;
        const ts = timestamps[id];
        if (!ts) {
            // First time seen with new TTL mechanism: give it full 3-day window from now
            validPanels.push(id);
            validTimestamps[id] = now;
            modified = true;
        } else if (now - ts < TTL_MS) {
            validPanels.push(id);
            validTimestamps[id] = ts;
        } else {
            // Expired after 3 days!
            modified = true;
        }
    });

    if (modified) {
        try {
            localStorage.setItem('hpm_new_panels', JSON.stringify(validPanels));
            localStorage.setItem('hpm_new_panels_ts', JSON.stringify(validTimestamps));
        } catch(e) {}
    }

    return { panels: validPanels, timestamps: validTimestamps };
};

window.hpmMarkCategorySeen = function(catId) {
    if (!catId || catId === 'ALL') return;
    try {
        let seenCats = JSON.parse(localStorage.getItem('hpm_seen_categories') || '{}');
        seenCats[catId] = Date.now();
        localStorage.setItem('hpm_seen_categories', JSON.stringify(seenCats));
    } catch(e) {}
    // Remove glowing badge immediately from DOM
    const btnBadge = document.querySelector(`.filter-btn[onclick*="'${catId}'"] .btn-badge`);
    if (btnBadge) btnBadge.classList.remove('badge-new');
    const catBadge = document.querySelector(`.category-group[data-cat-id="${catId}"] .cat-badge`);
    if (catBadge) catBadge.classList.remove('badge-new');
};

window.hpmGetNewCategories = function(modules) {
    const { panels: newPanels, timestamps: newPanelsTs } = window.hpmGetCleanNewPanels();
    let seenCats = {};
    try { seenCats = JSON.parse(localStorage.getItem('hpm_seen_categories') || '{}'); } catch(e) {}

    const newCats = new Set();
    const catMaxTs = {};

    (modules || []).forEach(m => {
        if (m && m.cat && newPanels.includes(m.id)) {
            const ts = newPanelsTs[m.id] || 0;
            if (!catMaxTs[m.cat] || ts > catMaxTs[m.cat]) {
                catMaxTs[m.cat] = ts;
            }
        }
    });

    Object.keys(catMaxTs).forEach(catId => {
        const catSeen = seenCats[catId] || 0;
        if (catMaxTs[catId] > catSeen) {
            newCats.add(catId);
        }
    });

    return { newPanels, newCats };
};

function renderFilterTabs() {
    const container = document.getElementById('config-filter-tabs');
    const hub       = window.CONFIG_HUB;
    if (!container || !hub) return;

    const userRole = (window.currentUser && window.currentUser.role) || 'user';
    const cfgReady = window.cfg && Object.keys(window.cfg).length > 0;

    const allVisible = hub.modules.filter(m => {
        if (m.adminOnly && userRole !== 'admin') return false;
        if (m.isExtension && m.parentPluginTag) {
            if (cfgReady) {
                const parent = window.cfg.plugins && window.cfg.plugins[m.parentPluginTag];
                if (!parent || parent.enabled === false) return false;
                const extId = m.pluginTag.replace(m.parentPluginTag + '_', '').toLowerCase();
                const extState = (parent.extensions || {})[extId];
                if (extState && extState.enabled === false) return false;
            }
            return (window._panelCache[m.id] || !!window.LAZY_PANEL_IDS?.has(m.id) || !!document.getElementById('tab-' + m.id));
        }
        if (cfgReady && m.pluginTag) {
            const p = window.cfg.plugins && window.cfg.plugins[m.pluginTag];
            if (p && p.enabled === false) return false;
        }
        const inCache   = !!window._panelCache[m.id];
        const inLazySet = !!(window.LAZY_PANEL_IDS && window.LAZY_PANEL_IDS.has(m.id));
        const hasPanel  = !!document.getElementById('tab-' + m.id);
        const isMapped  = !!(hub.tagMap && hub.tagMap[m.pluginTag]);
        const isCore    = !!m.isCore;
        return (inCache || inLazySet || hasPanel || isMapped || isCore);
    });

    const counts = { 'ALL': allVisible.length };
    allVisible.forEach(m => { counts[m.cat] = (counts[m.cat] || 0) + 1; });

    // Determine which categories have at least one unacknowledged NEW module (< 3 days TTL)
    const { newPanels: _ftNewPanels, newCats: _ftNewCats } = window.hpmGetNewCategories(allVisible);

    let html = `
        <button class="filter-btn ${window.activeCategoryFilter === 'ALL' ? 'active' : ''}" onclick="setCategoryFilter('ALL')">
            <span><i class="fas fa-star"></i></span> ${_hubT('hub_filter_all', 'All')}
            <span class="btn-badge">${counts['ALL']}</span>
        </button>
    `;

    Object.keys(hub.categories).forEach(catId => {
        const cat         = hub.categories[catId];
        const activeClass = (window.activeCategoryFilter === catId) ? 'active' : '';
        const count       = counts[catId] || 0;
        if (count === 0) return;
        const _ftCatIsNew = _ftNewCats.has(catId);
        html += `
            <button class="filter-btn ${activeClass}" onclick="setCategoryFilter('${catId}')">
                <span>${cat.icon}</span> ${window.t ? window.t(cat.label) : catId}
                <span class="btn-badge${_ftCatIsNew ? ' badge-new' : ''}">${count}</span>
            </button>
        `;
    });

    container.innerHTML = html;
}

/**
 * Main Hub render — builds tab bar, wall cards, and filter bar.
 */
// Per-category page size (max cards shown when paginated)
// ── Hub Pagination Architecture: Default (Top Bar) & Per-Category Override ──
// Global default cards per page (controlled via the top search-bar dropdown)
const _savedDefPageSize = localStorage.getItem('hub_default_page_size') || localStorage.getItem('hub_cat_page_size');
window.HUB_DEFAULT_PAGE_SIZE = parseInt(_savedDefPageSize, 10) || 6;
window.HUB_CAT_PAGE_SIZE = window.HUB_DEFAULT_PAGE_SIZE; // backward-compat

// Per-category custom overrides: { [catId]: number }
let _savedCatPerPage = {};
try { _savedCatPerPage = JSON.parse(localStorage.getItem('hub_cat_per_page') || '{}'); } catch(e) {}
window.HUB_CAT_PER_PAGE = _savedCatPerPage;

window.hubGetCatPageSize = function(catId) {
    if (window.HUB_CAT_PER_PAGE && window.HUB_CAT_PER_PAGE[catId]) {
        return window.HUB_CAT_PER_PAGE[catId];
    }
    return window.HUB_DEFAULT_PAGE_SIZE || 6;
};

window.hubSetDefaultPageSize = function(size) {
    size = parseInt(size, 10);
    if (isNaN(size) || size < 4) size = 4;
    if (size > 100) size = 100;
    window.HUB_DEFAULT_PAGE_SIZE = size;
    window.HUB_CAT_PAGE_SIZE = size;
    try { localStorage.setItem('hub_default_page_size', size); } catch(e) {}
    const sel = document.getElementById('hub-default-page-size-select');
    if (sel) sel.value = String(size);
    renderConfigHub();
};

window.hubSetCatPageSize = function(catId, size) {
    if (size === 'default') {
        delete window.HUB_CAT_PER_PAGE[catId];
    } else {
        size = parseInt(size, 10);
        if (!isNaN(size) && size >= 4) {
            window.HUB_CAT_PER_PAGE[catId] = size;
        }
    }
    try { localStorage.setItem('hub_cat_per_page', JSON.stringify(window.HUB_CAT_PER_PAGE)); } catch(e) {}
    renderConfigHub();
};

// Backward-compat bridge
window.hubSetPageSize = function(size) {
    window.hubSetDefaultPageSize(size);
};

// Per-category current page: { catId: pageNumber (1-based) }
if (!window.HUB_CAT_PAGES) window.HUB_CAT_PAGES = {};
// Track active category for keyboard arrow navigation
window.HUB_LAST_ACTIVE_CAT = null;

// Categories that have pagination explicitly activated by user.
// Default is EMPTY (Show all by default), unless user clicked "Pagina"
let _savedPagCats = [];
try { _savedPagCats = JSON.parse(localStorage.getItem('hub_paginated_cats') || '[]'); } catch(e) {}
window.HUB_PAGINATED_CATS = new Set(_savedPagCats);

window.hubCatTogglePagination = function(catId) {
    window.HUB_LAST_ACTIVE_CAT = catId;
    if (window.HUB_PAGINATED_CATS.has(catId)) {
        window.HUB_PAGINATED_CATS.delete(catId);
    } else {
        window.HUB_PAGINATED_CATS.add(catId);
        if (!window.HUB_CAT_PAGES[catId]) window.HUB_CAT_PAGES[catId] = 1;
    }
    try {
        localStorage.setItem('hub_paginated_cats', JSON.stringify(Array.from(window.HUB_PAGINATED_CATS)));
    } catch(e) {}
    renderConfigHub();
};

window.hubCatPage = function(catId, delta) {
    window.HUB_LAST_ACTIVE_CAT = catId;
    // Automatically activate pagination if user uses arrow keys or page buttons
    if (!window.HUB_PAGINATED_CATS.has(catId)) {
        window.HUB_PAGINATED_CATS.add(catId);
        try {
            localStorage.setItem('hub_paginated_cats', JSON.stringify(Array.from(window.HUB_PAGINATED_CATS)));
        } catch(e) {}
    }
    const cur = window.HUB_CAT_PAGES[catId] || 1;
    window.HUB_CAT_PAGES[catId] = Math.max(1, cur + delta);
    renderConfigHub();
};

window.hubCatSetPage = function(catId, page) {
    window.HUB_LAST_ACTIVE_CAT = catId;
    if (!window.HUB_PAGINATED_CATS.has(catId)) {
        window.HUB_PAGINATED_CATS.add(catId);
        try {
            localStorage.setItem('hub_paginated_cats', JSON.stringify(Array.from(window.HUB_PAGINATED_CATS)));
        } catch(e) {}
    }
    window.HUB_CAT_PAGES[catId] = Math.max(1, parseInt(page, 10) || 1);
    renderConfigHub();
};

// Self-contained dynamic stylesheet injection for pagination (bulletproof against CSS cache)
(function ensureHubPaginationStyles() {
    if (document.getElementById('hub-cat-pagination-dyn-css')) return;
    const st = document.createElement('style');
    st.id = 'hub-cat-pagination-dyn-css';
    st.textContent = `
        .btn-badge.badge-new, .cat-badge.badge-new {
            background: var(--accent, #6c8cff) !important;
            color: #ffffff !important;
            border-color: var(--accent, #6c8cff) !important;
            font-weight: 800 !important;
            box-shadow: 0 0 8px rgba(var(--accent-rgb, 108, 140, 255), 0.6) !important;
            animation: hubBadgeNewPulse 2s ease-in-out infinite !important;
        }
        @keyframes hubBadgeNewPulse {
            0%, 100% {
                box-shadow: 0 0 0 0 rgba(var(--accent-rgb, 108, 140, 255), 0.7), 0 0 8px rgba(var(--accent-rgb, 108, 140, 255), 0.4);
                transform: scale(1);
            }
            50% {
                box-shadow: 0 0 0 3px rgba(var(--accent-rgb, 108, 140, 255), 0), 0 0 12px rgba(var(--accent-rgb, 108, 140, 255), 0.85);
                transform: scale(1.1);
            }
        }
        .cat-pagination-wrap {
            display: inline-flex !important;
            align-items: center !important;
            gap: 8px !important;
            margin-left: 12px !important;
            user-select: none !important;
            z-index: 2 !important;
            flex-shrink: 0 !important;
        }
        .cat-page-arrow-btn {
            width: 32px !important;
            height: 28px !important;
            min-width: 32px !important;
            border-radius: 8px !important;
            border: 1.5px solid var(--accent, #6c8cff) !important;
            background: rgba(var(--accent-rgb, 108, 140, 255), 0.14) !important;
            color: var(--accent, #6c8cff) !important;
            font-size: 13px !important;
            font-weight: 900 !important;
            cursor: pointer !important;
            display: inline-flex !important;
            align-items: center !important;
            justify-content: center !important;
            transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
            box-shadow: 0 0 8px rgba(var(--accent-rgb, 108, 140, 255), 0.25) !important;
            flex-shrink: 0 !important;
            padding: 0 !important;
            outline: none !important;
        }
        .cat-page-arrow-btn i {
            color: var(--accent, #6c8cff) !important;
            font-size: 13px !important;
            font-weight: 900 !important;
            transition: color 0.2s ease !important;
        }
        .cat-page-arrow-btn:hover:not(:disabled) {
            background: var(--accent, #6c8cff) !important;
            color: #ffffff !important;
            border-color: var(--accent, #6c8cff) !important;
            box-shadow: 0 0 14px rgba(var(--accent-rgb, 108, 140, 255), 0.6) !important;
            transform: scale(1.08) !important;
        }
        .cat-page-arrow-btn:hover:not(:disabled) i {
            color: #ffffff !important;
        }
        .cat-page-arrow-btn:active:not(:disabled) {
            transform: scale(0.95) !important;
        }
        .cat-page-arrow-btn:disabled {
            opacity: 0.22 !important;
            cursor: not-allowed !important;
            border-color: rgba(255, 255, 255, 0.1) !important;
            color: var(--muted, #6b7280) !important;
            box-shadow: none !important;
            background: transparent !important;
            pointer-events: none !important;
        }
        .cat-page-arrow-btn:disabled i {
            color: var(--muted, #6b7280) !important;
        }
        .cat-page-pills-pill {
            display: inline-flex !important;
            align-items: center !important;
            gap: 3px !important;
            background: var(--bg3, #1c2033) !important;
            padding: 2px 6px !important;
            border-radius: 14px !important;
            border: 1px solid var(--border, #252b46) !important;
            height: 28px !important;
            box-sizing: border-box !important;
        }
        .cat-page-pill {
            background: transparent !important;
            border: 1px solid transparent !important;
            color: var(--muted, #6b7280) !important;
            font-size: 11px !important;
            font-weight: 700 !important;
            min-width: 20px !important;
            height: 20px !important;
            border-radius: 10px !important;
            cursor: pointer !important;
            display: inline-flex !important;
            align-items: center !important;
            justify-content: center !important;
            padding: 0 5px !important;
            transition: all 0.15s ease !important;
        }
        .cat-page-pill:hover:not(.active) {
            color: var(--text, #e2e8f0) !important;
            background: rgba(255, 255, 255, 0.08) !important;
        }
        .cat-page-pill.active {
            background: var(--accent, #6c8cff) !important;
            color: #ffffff !important;
            border-color: var(--accent, #6c8cff) !important;
            box-shadow: 0 0 8px rgba(var(--accent-rgb, 108, 140, 255), 0.45) !important;
        }
        .cat-show-all-btn {
            background: transparent !important;
            border: 1.5px solid rgba(var(--accent-rgb, 108, 140, 255), 0.45) !important;
            color: var(--accent, #6c8cff) !important;
            font-size: 10px !important;
            font-weight: 700 !important;
            text-transform: uppercase !important;
            letter-spacing: 0.5px !important;
            padding: 0 10px !important;
            border-radius: 8px !important;
            cursor: pointer !important;
            transition: all 0.2s ease !important;
            white-space: nowrap !important;
            height: 28px !important;
            display: inline-flex !important;
            align-items: center !important;
        }
        .cat-show-all-btn:hover {
            background: rgba(var(--accent-rgb, 108, 140, 255), 0.2) !important;
            border-color: var(--accent, #6c8cff) !important;
            color: #ffffff !important;
            box-shadow: 0 0 10px rgba(var(--accent-rgb, 108, 140, 255), 0.4) !important;
        }
        .cat-page-size-select {
            background: var(--bg2, #141726) !important;
            border: 1px solid var(--border, #252b46) !important;
            color: var(--muted, #6b7280) !important;
            font-size: 10.5px !important;
            font-weight: 700 !important;
            padding: 0 6px !important;
            border-radius: 8px !important;
            height: 28px !important;
            cursor: pointer !important;
            outline: none !important;
            transition: all 0.2s ease !important;
        }
        .cat-page-size-select:hover {
            border-color: var(--accent, #6c8cff) !important;
            color: var(--text, #e2e8f0) !important;
        }
        .cat-activate-pag-btn {
            display: inline-flex !important;
            align-items: center !important;
            gap: 5px !important;
            margin-left: 10px !important;
            padding: 3px 9px !important;
            background: rgba(var(--accent-rgb, 108, 140, 255), 0.08) !important;
            border: 1px dashed rgba(var(--accent-rgb, 108, 140, 255), 0.4) !important;
            border-radius: 8px !important;
            color: var(--accent, #6c8cff) !important;
            font-size: 10px !important;
            font-weight: 700 !important;
            letter-spacing: 0.3px !important;
            cursor: pointer !important;
            transition: all 0.2s ease !important;
            user-select: none !important;
            height: 24px !important;
        }
        .cat-activate-pag-btn:hover {
            background: rgba(var(--accent-rgb, 108, 140, 255), 0.18) !important;
            border-style: solid !important;
            border-color: var(--accent, #6c8cff) !important;
            box-shadow: 0 0 8px rgba(var(--accent-rgb, 108, 140, 255), 0.35) !important;
        }
    `;
    if (document.head) document.head.appendChild(st);
})();

window.renderHubCatPagination = function(catId, page, totalPages, isPaginated) {
    const defaultSize = window.HUB_DEFAULT_PAGE_SIZE || 6;
    const hasOverride = !!(window.HUB_CAT_PER_PAGE && window.HUB_CAT_PER_PAGE[catId]);
    const catPageSize = window.hubGetCatPageSize(catId);
    const pageLabel   = _hubT('hub_page', 'page');
    const safeTotalPages = Math.max(1, totalPages || 1);

    // Show All by default: render compact button to activate pagination
    if (!isPaginated) {
        const pageWord = safeTotalPages === 1 ? _hubT('hub_page', 'page') : _hubT('hub_pages', 'pages');
        const countInfo = safeTotalPages > 1 ? ` (${safeTotalPages} ${pageWord})` : '';
        return `
            <button class="cat-activate-pag-btn" onclick="event.stopPropagation(); hubCatTogglePagination('${catId}')" title="${_hubT('hub_paginate_cat_tip', 'Paginate this category')}">
                <i class="fas fa-layer-group" style="font-size:9px;"></i> ${_hubT('hub_paginate', 'Paginate')}${countInfo}
            </button>
        `;
    }

    // When paginated: ALWAYS render full navigation controls even if totalPages <= 1 so user can change page size or show all
    let pills = '';
    if (safeTotalPages <= 5) {
        for (let i = 1; i <= safeTotalPages; i++) {
            pills += `<button class="cat-page-pill ${page === i ? 'active' : ''}" onclick="event.stopPropagation(); hubCatSetPage('${catId}', ${i})">${i}</button>`;
        }
    } else {
        let pages = [1];
        if (page > 3) pages.push('...');
        for (let i = Math.max(2, page - 1); i <= Math.min(safeTotalPages - 1, page + 1); i++) {
            pages.push(i);
        }
        if (page < safeTotalPages - 2) pages.push('...');
        pages.push(safeTotalPages);

        pills = pages.map(p => {
            if (p === '...') return `<span class="cat-page-dots" style="font-size:10px;color:var(--muted);padding:0 2px;">…</span>`;
            return `<button class="cat-page-pill ${page === p ? 'active' : ''}" onclick="event.stopPropagation(); hubCatSetPage('${catId}', ${p})">${p}</button>`;
        }).join('');
    }

    const prevDisabled = page <= 1;
    const nextDisabled = page >= safeTotalPages;

    const prevInline = prevDisabled
        ? 'opacity:0.25 !important; cursor:not-allowed !important; border-color:rgba(255,255,255,0.1) !important; color:var(--muted,#6b7280) !important; background:transparent !important; box-shadow:none !important;'
        : 'border-color:var(--accent,#6c8cff) !important; color:var(--accent,#6c8cff) !important; background:rgba(var(--accent-rgb,108,140,255),0.14) !important; box-shadow:0 0 8px rgba(var(--accent-rgb,108,140,255),0.25) !important; cursor:pointer !important;';

    const nextInline = nextDisabled
        ? 'opacity:0.25 !important; cursor:not-allowed !important; border-color:rgba(255,255,255,0.1) !important; color:var(--muted,#6b7280) !important; background:transparent !important; box-shadow:none !important;'
        : 'border-color:var(--accent,#6c8cff) !important; color:var(--accent,#6c8cff) !important; background:rgba(var(--accent-rgb,108,140,255),0.14) !important; box-shadow:0 0 8px rgba(var(--accent-rgb,108,140,255),0.25) !important; cursor:pointer !important;';

    return `
        <div class="cat-pagination-wrap" onclick="event.stopPropagation()">
            <button class="cat-page-arrow-btn prev" style="width:32px; height:28px; border-radius:8px; border:1.5px solid; ${prevInline} display:inline-flex; align-items:center; justify-content:center;" onclick="event.stopPropagation(); hubCatPage('${catId}', -1)" ${prevDisabled ? 'disabled' : ''} title="${_hubT('hub_prev_page', 'Previous page (Left Arrow)')}">
                <i class="fas fa-chevron-left" style="font-size:13px; font-weight:900; color:inherit;"></i>
            </button>
            <div class="cat-page-pills-pill">
                ${pills}
            </div>
            <button class="cat-page-arrow-btn next" style="width:32px; height:28px; border-radius:8px; border:1.5px solid; ${nextInline} display:inline-flex; align-items:center; justify-content:center;" onclick="event.stopPropagation(); hubCatPage('${catId}', 1)" ${nextDisabled ? 'disabled' : ''} title="${_hubT('hub_next_page', 'Next page (Right Arrow)')}">
                <i class="fas fa-chevron-right" style="font-size:13px; font-weight:900; color:inherit;"></i>
            </button>
            <button class="cat-show-all-btn" onclick="event.stopPropagation(); hubCatTogglePagination('${catId}')" title="${_hubT('hub_show_all_tip', 'Show all cards (disable pagination)')}">
                ${_hubT('hub_show_all', 'Show All')}
            </button>
            <select class="cat-page-size-select" onchange="event.stopPropagation(); hubSetCatPageSize('${catId}', this.value);" title="${_hubT('hub_cards_per_page', 'Cards per page')}">
                <option value="default" ${!hasOverride ? 'selected' : ''}>Default (${defaultSize})</option>
                <option value="4" ${hasOverride && catPageSize === 4 ? 'selected' : ''}>4 / ${pageLabel}</option>
                <option value="6" ${hasOverride && catPageSize === 6 ? 'selected' : ''}>6 / ${pageLabel}</option>
                <option value="8" ${hasOverride && catPageSize === 8 ? 'selected' : ''}>8 / ${pageLabel}</option>
                <option value="12" ${hasOverride && catPageSize === 12 ? 'selected' : ''}>12 / ${pageLabel}</option>
                <option value="18" ${hasOverride && catPageSize === 18 ? 'selected' : ''}>18 / ${pageLabel}</option>
                <option value="24" ${hasOverride && catPageSize === 24 ? 'selected' : ''}>24 / ${pageLabel}</option>
            </select>
        </div>
    `;
};

// Keyboard ArrowLeft / ArrowRight navigation
if (!window._hubKeyNavAttached) {
    window._hubKeyNavAttached = true;

    // Track hovered category for keyboard navigation
    document.addEventListener('mouseover', (e) => {
        const group = e.target.closest?.('.category-group');
        if (group && group.dataset && group.dataset.catId) {
            window.HUB_LAST_ACTIVE_CAT = group.dataset.catId;
        }
    });

    document.addEventListener('keydown', (e) => {
        if (e.key !== 'ArrowLeft' && e.key !== 'ArrowRight') return;

        // Skip if typing in an input / textarea / select
        const activeEl = document.activeElement;
        const tag = (activeEl && activeEl.tagName) || '';
        if (['INPUT', 'TEXTAREA', 'SELECT'].includes(tag) || activeEl?.isContentEditable) return;
        if (e.ctrlKey || e.altKey || e.metaKey || e.shiftKey) return;

        // Determine target category
        let targetCat = null;
        if (window.activeCategoryFilter && window.activeCategoryFilter !== 'ALL') {
            targetCat = window.activeCategoryFilter;
        } else if (window.HUB_LAST_ACTIVE_CAT) {
            targetCat = window.HUB_LAST_ACTIVE_CAT;
        } else if (window.activeTab && window.CONFIG_HUB && window.CONFIG_HUB.modules) {
            const m = window.CONFIG_HUB.modules.find(mod => mod.id === window.activeTab);
            if (m && m.cat) targetCat = m.cat;
        }

        if (!targetCat && window.CONFIG_HUB && window.CONFIG_HUB.categories) {
            const allCats = Object.keys(window.CONFIG_HUB.categories);
            targetCat = allCats.find(c => window.HUB_PAGINATED_CATS && window.HUB_PAGINATED_CATS.has(c)) || allCats[0];
        }

        if (!targetCat) return;

        const delta = (e.key === 'ArrowRight') ? 1 : -1;
        e.preventDefault();
        window.hubCatPage(targetCat, delta);
    });
}

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
    // When window.cfg is not yet loaded (empty {}), show ALL modules that
    // are in LAZY_PANEL_IDS. This makes the menu visible immediately at page load
    // before any network requests complete. A second renderConfigHub() call after
    // cfg is loaded will correctly hide disabled plugins.
    const cfgReady = window.cfg && Object.keys(window.cfg).length > 0;

    const visibleModules = hub.modules.filter(m => {
        if (m.adminOnly && userRole !== 'admin') return false;

        if (m.isExtension && m.parentPluginTag) {
            if (cfgReady) {
                const parent = window.cfg.plugins && window.cfg.plugins[m.parentPluginTag];
                if (!parent || parent.enabled === false) return false;
                const extId    = m.pluginTag.replace(m.parentPluginTag + '_', '').toLowerCase();
                const extState = (parent.extensions || {})[extId];
                if (extState && extState.enabled === false) return false;
            }
            return (_panelCache[m.id] || !!window.LAZY_PANEL_IDS?.has(m.id) || !!document.getElementById('tab-' + m.id));
        }

        if (cfgReady && m.pluginTag) {
            const p = window.cfg.plugins && window.cfg.plugins[m.pluginTag];
            if (p && p.enabled === false) return false;
        }

        const inCache   = !!_panelCache[m.id];
        const inLazySet = !!(window.LAZY_PANEL_IDS && window.LAZY_PANEL_IDS.has(m.id));
        const hasPanel  = !!document.getElementById('tab-' + m.id);
        const isMapped  = !!(hub.tagMap && hub.tagMap[m.pluginTag]);
        const isMcp     = (m.cat === 'MCP');
        const isCore    = !!m.isCore;
        // HPM packages: if cfg is ready and the plugin is not explicitly disabled, show it.
        // This covers the case where mergeHubPanels hasn't run yet (Phase 0 render)
        // but the package is installed and enabled in system.yaml.
        const isHpmEnabled = !!(m.isHpm && cfgReady && m.pluginTag && (() => {
            const p = window.cfg.plugins && window.cfg.plugins[m.pluginTag];
            return !p || p.enabled !== false;
        })());
        
        return (inCache || inLazySet || hasPanel || isMapped || isCore || isHpmEnabled);
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
                    
                    // Strip existing HTML <i> tags at the start so we don't render two
                    cleanText = cleanText.replace(/^<i[^>]*><\/i>\s*/i, '');
                    // Strip emojis
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

    const { newPanels, newCats } = window.hpmGetNewCategories(filteredModules);

    // 1. Render TABS bar
    let tabsHtml = '';
    let currentTabCat = null;
    const _hubCatIdxMap = {};  // per-cat item index counter for pagination
    filteredModules.forEach(m => {
        if (m.cat !== currentTabCat) {
            if (currentTabCat !== null) tabsHtml += `</div></div>`;
            currentTabCat = m.cat;
            const catData   = hub.categories[currentTabCat] || { label: currentTabCat, icon: '📂' };
            const isCollapsed = uiState.collapsedCategories.includes(currentTabCat);
            const catHasNew       = newCats.has(currentTabCat);
            const _catTotal       = catCounts[currentTabCat] || 0;
            const _catPageSize    = window.hubGetCatPageSize(currentTabCat);
            const _catTotalPages  = Math.ceil(_catTotal / _catPageSize);
            const _catPage        = Math.max(1, Math.min(window.HUB_CAT_PAGES[currentTabCat] || 1, _catTotalPages || 1));
            const _isPaginated    = window.HUB_PAGINATED_CATS.has(currentTabCat);
            const _needsPag       = _isPaginated || _catTotal > 4;
            const _pagHtml        = _needsPag ? window.renderHubCatPagination(currentTabCat, _catPage, _catTotalPages, _isPaginated) : '';
            tabsHtml += `
                <div class="category-group ${isCollapsed ? 'collapsed' : ''}" data-cat-id="${currentTabCat}">
                    <div class="category-header" onclick="toggleCategory('${currentTabCat}')">
                        <span class="cat-toggle">${isCollapsed ? '⊕' : '⊖'}</span>
                        <span class="cat-label">${catData.icon} ${window.t ? window.t(catData.label) : catData.label}</span>
                        <span class="cat-badge${catHasNew ? ' badge-new' : ''}">${_catTotal}</span>
                        ${_pagHtml}
                        <div class="cat-line"></div>
                    </div>
                    <div class="category-content tabs">
            `;
        }
        // Per-cat pagination: track which items are on the current page (show all by default)
        _hubCatIdxMap[currentTabCat] = (_hubCatIdxMap[currentTabCat] === undefined) ? 0 : _hubCatIdxMap[currentTabCat] + 1;
        const _mIdx     = _hubCatIdxMap[currentTabCat];
        const _catPageSize2 = window.hubGetCatPageSize(currentTabCat);
        const _catTotalPages2 = Math.ceil((catCounts[currentTabCat] || 0) / _catPageSize2);
        const _catP2    = Math.max(1, Math.min(window.HUB_CAT_PAGES[currentTabCat] || 1, _catTotalPages2 || 1));
        const _isPag2   = window.HUB_PAGINATED_CATS.has(currentTabCat);
        const _pgStart  = (_catP2 - 1) * _catPageSize2;
        const _pgEnd    = _pgStart + _catPageSize2;
        const _mVisible = !_isPag2 || (_mIdx >= _pgStart && _mIdx < _pgEnd);

        const activeClass = (activeTab === m.id) ? 'active' : '';
        const icon        = window.getIconForModule(m.id, m.label, m.icon);
        const isNew       = newPanels.includes(m.id);
        const badgeHtml   = isNew ? `<span class="new-badge" style="margin-left:6px; background:var(--accent); color:white; font-size:9px; padding:2px 5px; border-radius:10px; font-weight:800; animation:hpmPulse 2s infinite;">NEW</span>` : '';
        const typeBadge   = window.hpmGetModuleTypeBadge(m, true);
        if (_mVisible) tabsHtml += `<button class="tab ${activeClass}" onclick="showTab('${m.id}')">${icon} ${window.t ? window.t(m.label) : m.label} ${typeBadge} ${badgeHtml}</button>`;
    });
    if (filteredModules.length > 0) tabsHtml += `</div></div>`;
    tabsBar.innerHTML = tabsHtml;

    // 2. Render WALL cards
    let wallHtml = '';
    let currentCat = null, currentCatData = null;
    const _hubCatIdxMapWall = {};  // per-cat item index counter for wall pagination
    filteredModules.forEach(m => {
        if (m.cat !== currentCat) {
            if (currentCat !== null) wallHtml += `</div></div>`;
            currentCat     = m.cat;
            currentCatData = hub.categories[currentCat] || { label: currentCat, icon: '📂' };
            const isCollapsed = uiState.collapsedCategories.includes(currentCat);
            const catHasNew   = newCats.has(currentCat);
            const _catTotalWall       = catCounts[currentCat] || 0;
            const _catPageSizeWall    = window.hubGetCatPageSize(currentCat);
            const _catTotalPagesWall  = Math.ceil(_catTotalWall / _catPageSizeWall);
            const _catPageWall        = Math.max(1, Math.min(window.HUB_CAT_PAGES[currentCat] || 1, _catTotalPagesWall || 1));
            const _isPaginatedWall    = window.HUB_PAGINATED_CATS.has(currentCat);
            const _needsPagWall       = _isPaginatedWall || _catTotalWall > 4;
            const _pagHtmlWall        = _needsPagWall ? window.renderHubCatPagination(currentCat, _catPageWall, _catTotalPagesWall, _isPaginatedWall) : '';
            wallHtml += `
                <div class="category-group ${isCollapsed ? 'collapsed' : ''}" data-cat-id="${currentCat}">
                    <div class="category-header" onclick="toggleCategory('${currentCat}')">
                        <span class="cat-toggle">${isCollapsed ? '⊕' : '⊖'}</span>
                        <span class="cat-label">${currentCatData.icon} ${window.t ? window.t(currentCatData.label) : currentCatData.label}</span>
                        <span class="cat-badge${catHasNew ? ' badge-new' : ''}">${_catTotalWall}</span>
                        ${_pagHtmlWall}
                        <div class="cat-line"></div>
                    </div>
                    <div class="category-content">
            `;
        }
        // Per-cat pagination for wall: track which items are on current page (show all by default)
        _hubCatIdxMapWall[currentCat] = (_hubCatIdxMapWall[currentCat] === undefined) ? 0 : _hubCatIdxMapWall[currentCat] + 1;
        const _mIdxWall          = _hubCatIdxMapWall[currentCat];
        const _catPageSizeWall2  = window.hubGetCatPageSize(currentCat);
        const _catTotalPagesWall2 = Math.ceil((catCounts[currentCat] || 0) / _catPageSizeWall2);
        const _catPWall          = Math.max(1, Math.min(window.HUB_CAT_PAGES[currentCat] || 1, _catTotalPagesWall2 || 1));
        const _isPagWall2        = window.HUB_PAGINATED_CATS.has(currentCat);
        const _pgStartWall       = (_catPWall - 1) * _catPageSizeWall2;
        const _pgEndWall         = _pgStartWall + _catPageSizeWall2;
        const _mVisibleWall      = !_isPagWall2 || (_mIdxWall >= _pgStartWall && _mIdxWall < _pgEndWall);

        const activeClass = (activeTab === m.id) ? 'active' : '';
        const icon        = window.getIconForModule(m.id, m.label, m.icon);
        const isNew       = newPanels.includes(m.id);
        const badgeHtml   = isNew ? `<div class="new-badge" style="position:absolute; top:8px; right:8px; background:var(--accent); color:white; font-size:9px; padding:2px 6px; border-radius:10px; font-weight:800; animation:hpmPulse 2s infinite; box-shadow:0 0 5px var(--accent);">NEW</div>` : '';
        const typeBadge   = window.hpmGetModuleTypeBadge(m, false);
        if (_mVisibleWall) {
            wallHtml += `
                <div class="module-card ${activeClass}" onclick="showTab('${m.id}')" style="position:relative;">
                    ${badgeHtml}
                    ${typeBadge}
                    <div class="m-icon">${icon}</div>
                    <div class="m-label">${window.t ? window.t(m.label) : m.label}</div>
                    <div class="m-cat">${window.t ? window.t(currentCatData.label) : currentCat}</div>
                </div>
            `;
        }
    });
    if (filteredModules.length > 0) wallHtml += `</div></div>`;
    wallArea.innerHTML = wallHtml;

    // 3. Render category filter pill bar
    renderFilterTabs();
    // Keep top default page size selector in sync
    const defSel = document.getElementById('hub-default-page-size-select');
    if (defSel && window.HUB_DEFAULT_PAGE_SIZE) {
        defSel.value = String(window.HUB_DEFAULT_PAGE_SIZE);
    }
}

window.renderConfigHub  = renderConfigHub;
window.renderFilterTabs = renderFilterTabs;
