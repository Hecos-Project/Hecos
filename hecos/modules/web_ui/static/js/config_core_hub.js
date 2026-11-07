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
        <button type="button" class="filter-btn ${window.activeCategoryFilter === 'ALL' ? 'active' : ''}" data-filter-cat="ALL" onclick="setCategoryFilter('ALL')">
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
            <button type="button" class="filter-btn ${activeClass}" data-filter-cat="${catId}" onclick="setCategoryFilter('${catId}')">
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
const _rawDefSize = localStorage.getItem('hub_default_page_size') || localStorage.getItem('hub_cat_page_size');
let _savedDefPageSize = parseInt(_rawDefSize, 10);
const _allowedPageSizes = [5, 10, 15, 20, 25];
if (!_savedDefPageSize || !_allowedPageSizes.includes(_savedDefPageSize)) {
    if (!_savedDefPageSize || _savedDefPageSize <= 5) _savedDefPageSize = 5;
    else if (_savedDefPageSize <= 10) _savedDefPageSize = 10;
    else if (_savedDefPageSize <= 15) _savedDefPageSize = 15;
    else if (_savedDefPageSize <= 20) _savedDefPageSize = 20;
    else _savedDefPageSize = 25;
    try { localStorage.setItem('hub_default_page_size', _savedDefPageSize); } catch(e) {}
}
window.HUB_DEFAULT_PAGE_SIZE = _savedDefPageSize;
window.HUB_CAT_PAGE_SIZE = window.HUB_DEFAULT_PAGE_SIZE; // backward-compat

// Per-category custom overrides: { [catId]: number }
let _savedCatPerPage = {};
try {
    _savedCatPerPage = JSON.parse(localStorage.getItem('hub_cat_per_page') || '{}');
    let dirty = false;
    for (const [k, v] of Object.entries(_savedCatPerPage)) {
        if (!_allowedPageSizes.includes(v)) {
            if (v <= 5) _savedCatPerPage[k] = 5;
            else if (v <= 10) _savedCatPerPage[k] = 10;
            else if (v <= 15) _savedCatPerPage[k] = 15;
            else if (v <= 20) _savedCatPerPage[k] = 20;
            else _savedCatPerPage[k] = 25;
            dirty = true;
        }
    }
    if (dirty) {
        localStorage.setItem('hub_cat_per_page', JSON.stringify(_savedCatPerPage));
    }
} catch(e) {}
window.HUB_CAT_PER_PAGE = _savedCatPerPage;

window.hubGetCatPageSize = function(catId) {
    if (window.HUB_CAT_PER_PAGE && window.HUB_CAT_PER_PAGE[catId]) {
        return window.HUB_CAT_PER_PAGE[catId];
    }
    return window.HUB_DEFAULT_PAGE_SIZE || 5;
};

window.hubSetDefaultPageSize = function(size) {
    size = parseInt(size, 10);
    if (isNaN(size) || size < 5) size = 5;
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
        if (!isNaN(size) && size >= 5) {
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
    const grp = document.querySelector(`.category-group[data-cat-id="${catId}"]`);
    const maxP = grp ? (parseInt(grp.dataset.totalPages, 10) || 999) : 999;
    window.HUB_CAT_PAGES[catId] = Math.max(1, Math.min(maxP, cur + delta));
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
        /* ── Hub 2D Keyboard Focus Ring (.hub-kb-focus) ── */
        .filter-btn.hub-kb-focus {
            outline: 2px solid var(--accent, #6c8cff) !important;
            outline-offset: 2px !important;
            box-shadow: 0 0 0 4px rgba(var(--accent-rgb, 108, 140, 255), 0.25), 0 0 14px rgba(var(--accent-rgb, 108, 140, 255), 0.5) !important;
            color: var(--text, #e2e8f0) !important;
            transform: translateY(-1px) !important;
            position: relative !important;
            z-index: 5 !important;
        }
        .cat-pagination-wrap.hub-kb-focus,
        .cat-activate-pag-btn.hub-kb-focus,
        .category-header.hub-kb-focus {
            outline: 2px solid var(--accent, #6c8cff) !important;
            outline-offset: 2px !important;
            border-radius: 10px !important;
            box-shadow: 0 0 0 3px rgba(var(--accent-rgb, 108, 140, 255), 0.25), 0 0 12px rgba(var(--accent-rgb, 108, 140, 255), 0.45) !important;
        }
        .module-card.hub-kb-focus,
        button.tab.hub-kb-focus {
            outline: 2px solid var(--accent, #6c8cff) !important;
            outline-offset: 2px !important;
            border-color: var(--accent, #6c8cff) !important;
            background: var(--bg3, #1c2033) !important;
            color: var(--text, #e2e8f0) !important;
            box-shadow: 0 0 0 4px rgba(var(--accent-rgb, 108, 140, 255), 0.25), 0 6px 18px rgba(var(--accent-rgb, 108, 140, 255), 0.35) !important;
            transform: translateY(-3px) !important;
            z-index: 5 !important;
        }
    `;
    if (document.head) document.head.appendChild(st);
})();

window.renderHubCatPagination = function(catId, page, totalPages, isPaginated) {
    const defaultSize = window.HUB_DEFAULT_PAGE_SIZE || 5;
    const hasOverride = !!(window.HUB_CAT_PER_PAGE && window.HUB_CAT_PER_PAGE[catId]);
    const catPageSize = window.hubGetCatPageSize(catId);
    const pageLabel   = _hubT('hub_page', 'page');
    const safeTotalPages = Math.max(1, totalPages || 1);

    // Show All by default: render compact button to activate pagination
    if (!isPaginated) {
        const pageWord = safeTotalPages === 1 ? _hubT('hub_page', 'page') : _hubT('hub_pages', 'pages');
        const countInfo = safeTotalPages > 1 ? ` (${safeTotalPages} ${pageWord})` : '';
        return `
            <button type="button" class="cat-activate-pag-btn" data-pag-cat="${catId}" onclick="event.stopPropagation(); hubCatTogglePagination('${catId}')" title="${_hubT('hub_paginate_cat_tip', 'Paginate this category')}">
                <i class="fas fa-layer-group" style="font-size:9px;"></i> ${_hubT('hub_paginate', 'Paginate')}${countInfo}
            </button>
        `;
    }

    // When paginated: ALWAYS render full navigation controls even if totalPages <= 1 so user can change page size or show all
    let pills = '';
    if (safeTotalPages <= 5) {
        for (let i = 1; i <= safeTotalPages; i++) {
            pills += `<button type="button" class="cat-page-pill ${page === i ? 'active' : ''}" onclick="event.stopPropagation(); hubCatSetPage('${catId}', ${i})">${i}</button>`;
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
            return `<button type="button" class="cat-page-pill ${page === p ? 'active' : ''}" onclick="event.stopPropagation(); hubCatSetPage('${catId}', ${p})">${p}</button>`;
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
        <div class="cat-pagination-wrap" data-pag-cat="${catId}" onclick="event.stopPropagation()">
            <button type="button" class="cat-page-arrow-btn prev" style="width:32px; height:28px; border-radius:8px; border:1.5px solid; ${prevInline} display:inline-flex; align-items:center; justify-content:center;" onclick="event.stopPropagation(); hubCatPage('${catId}', -1)" ${prevDisabled ? 'disabled' : ''} title="${_hubT('hub_prev_page', 'Previous page (Left Arrow)')}">
                <i class="fas fa-chevron-left" style="font-size:13px; font-weight:900; color:inherit;"></i>
            </button>
            <div class="cat-page-pills-pill">
                ${pills}
            </div>
            <button type="button" class="cat-page-arrow-btn next" style="width:32px; height:28px; border-radius:8px; border:1.5px solid; ${nextInline} display:inline-flex; align-items:center; justify-content:center;" onclick="event.stopPropagation(); hubCatPage('${catId}', 1)" ${nextDisabled ? 'disabled' : ''} title="${_hubT('hub_next_page', 'Next page (Right Arrow)')}">
                <i class="fas fa-chevron-right" style="font-size:13px; font-weight:900; color:inherit;"></i>
            </button>
            <button type="button" class="cat-show-all-btn" onclick="event.stopPropagation(); hubCatTogglePagination('${catId}')" title="${_hubT('hub_show_all_tip', 'Show all cards (disable pagination)')}">
                ${_hubT('hub_show_all', 'Show All')}
            </button>
            <select class="cat-page-size-select" onchange="event.stopPropagation(); hubSetCatPageSize('${catId}', this.value);" title="${_hubT('hub_cards_per_page', 'Cards per page')}">
                <option value="default" ${!hasOverride ? 'selected' : ''}>Default (${defaultSize})</option>
                <option value="5" ${hasOverride && catPageSize === 5 ? 'selected' : ''}>5 / ${pageLabel}</option>
                <option value="10" ${hasOverride && catPageSize === 10 ? 'selected' : ''}>10 / ${pageLabel}</option>
                <option value="15" ${hasOverride && catPageSize === 15 ? 'selected' : ''}>15 / ${pageLabel}</option>
                <option value="20" ${hasOverride && catPageSize === 20 ? 'selected' : ''}>20 / ${pageLabel}</option>
                <option value="25" ${hasOverride && catPageSize === 25 ? 'selected' : ''}>25 / ${pageLabel}</option>
            </select>
        </div>
    `;
};

// ── Hub 2D Keyboard Navigation (Filters ↔ Pagination ↔ Cards/Tabs) ──────────
if (!window.HUB_KB_STATE) {
    window.HUB_KB_STATE = {
        active: false,       // true ONLY when user explicitly clicked inside Hub navigation zones
        visible: false,      // true once user presses an arrow key (shows .hub-kb-focus ring)
        zone: null,          // 'filters' | 'pagination' | 'cards'
        filterCat: null,     // 'ALL' | catId
        catId: null,         // category ID for 'pagination' or 'cards'
        moduleId: null       // module ID for 'cards'
    };
}

function _getActiveHubContainer() {
    const wall = document.getElementById('config-wall');
    const tabs = document.getElementById('config-tabs-bar');
    if (typeof viewMode !== 'undefined' && viewMode === 'wall') return wall;
    if (wall && wall.offsetParent !== null) return wall;
    return tabs;
}

function _getHubFilterButtons() {
    const container = document.getElementById('config-filter-tabs');
    if (!container || container.offsetParent === null) return [];
    return Array.from(container.querySelectorAll('.filter-btn[data-filter-cat]'));
}

function _getHubCategoryGroups() {
    const hubEl = _getActiveHubContainer();
    if (!hubEl || hubEl.offsetParent === null) return [];
    return Array.from(hubEl.querySelectorAll('.category-group[data-cat-id]'));
}

function _hasGroupPagControls(group) {
    if (!group) return false;
    return !!group.querySelector('.cat-pagination-wrap, .cat-activate-pag-btn');
}

function _getHubGroupItems(group) {
    if (!group || group.classList.contains('collapsed')) return [];
    return Array.from(group.querySelectorAll('.module-card[data-mod-id], button.tab[data-mod-id]'))
        .filter(el => el.offsetParent !== null);
}

function _getHubVisualRows(items) {
    const rows = [];
    const ROW_TOLERANCE_PX = 18;
    items.forEach(el => {
        const rect = el.getBoundingClientRect();
        const centerY = rect.top + rect.height / 2;
        const centerX = rect.left + rect.width / 2;
        let row = rows.find(r => Math.abs(r.centerY - centerY) <= ROW_TOLERANCE_PX);
        if (!row) {
            row = { centerY, entries: [] };
            rows.push(row);
        }
        row.entries.push({ el, centerX, centerY, modId: el.dataset.modId });
    });
    rows.sort((a, b) => a.centerY - b.centerY);
    rows.forEach(r => r.entries.sort((a, b) => a.centerX - b.centerX));
    return rows;
}

function _pickClosestInRow(row, targetX) {
    let best = row.entries[0];
    let bestDist = Math.abs(best.centerX - targetX);
    for (let i = 1; i < row.entries.length; i++) {
        const d = Math.abs(row.entries[i].centerX - targetX);
        if (d < bestDist) {
            best = row.entries[i];
            bestDist = d;
        }
    }
    return best;
}

function _isAnyHubOverlayOpen() {
    if (document.getElementById('hwp-overlay')) return true;
    const overlaySelectors = [
        '#hdcs-overlay',
        '#zs-results',
        '#zs-settings-panel',
        '.hks-modal',
        '.hecos-gallery-overlay',
        '.modal.open',
        '[role="dialog"]'
    ];
    for (const sel of overlaySelectors) {
        const els = document.querySelectorAll(sel);
        for (const el of els) {
            if (!el || el.offsetParent === null) continue;
            const cs = window.getComputedStyle(el);
            if (cs.display !== 'none' && cs.visibility !== 'hidden') return true;
        }
    }
    return false;
}

window.hubClearKbFocus = function() {
    if (window.HUB_KB_STATE) {
        window.HUB_KB_STATE.active = false;
        window.HUB_KB_STATE.visible = false;
    }
    document.querySelectorAll('.hub-kb-focus').forEach(el => el.classList.remove('hub-kb-focus'));
};

window.syncHubKbFocus = function(scrollToTarget = false) {
    document.querySelectorAll('.hub-kb-focus').forEach(el => el.classList.remove('hub-kb-focus'));
    const st = window.HUB_KB_STATE;
    if (!st || !st.active || !st.visible) return;

    let targetEl = null;

    if (st.zone === 'filters') {
        const fc = st.filterCat || window.activeCategoryFilter || 'ALL';
        targetEl = document.querySelector(`#config-filter-tabs .filter-btn[data-filter-cat="${fc}"]`)
                || document.querySelector('#config-filter-tabs .filter-btn[data-filter-cat]');
    } else {
        const hubContainer = _getActiveHubContainer();
        if (hubContainer) {
            if (st.zone === 'pagination' && st.catId) {
                const grp = hubContainer.querySelector(`.category-group[data-cat-id="${st.catId}"]`);
                if (grp) {
                    targetEl = grp.querySelector('.cat-pagination-wrap, .cat-activate-pag-btn')
                            || grp.querySelector('.category-header');
                }
            } else if (st.zone === 'cards') {
                if (st.moduleId) {
                    targetEl = hubContainer.querySelector(
                        `.module-card[data-mod-id="${st.moduleId}"], button.tab[data-mod-id="${st.moduleId}"]`
                    );
                }
                if (!targetEl && st.catId) {
                    const grp = hubContainer.querySelector(`.category-group[data-cat-id="${st.catId}"]`);
                    const items = _getHubGroupItems(grp);
                    if (items.length > 0) {
                        targetEl = items[0];
                        st.moduleId = targetEl.dataset.modId;
                    }
                }
            }
        }
    }

    if (targetEl) {
        targetEl.classList.add('hub-kb-focus');
        if (scrollToTarget) {
            targetEl.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'nearest' });
        }
    }
};

function _enterHubGroupFromTop(group, preferredX = null) {
    const st = window.HUB_KB_STATE;
    const cid = group.dataset.catId;
    window.HUB_LAST_ACTIVE_CAT = cid;

    if (_hasGroupPagControls(group) || group.classList.contains('collapsed')) {
        st.zone = 'pagination';
        st.catId = cid;
        st.moduleId = null;
        return;
    }

    const items = _getHubGroupItems(group);
    if (items.length > 0) {
        st.zone = 'cards';
        st.catId = cid;
        if (preferredX !== null) {
            const rows = _getHubVisualRows(items);
            st.moduleId = _pickClosestInRow(rows[0], preferredX).modId;
        } else {
            st.moduleId = items[0].dataset.modId;
        }
    } else {
        st.zone = 'pagination';
        st.catId = cid;
        st.moduleId = null;
    }
}

function _enterHubGroupFromBottom(group, preferredX = null) {
    const st = window.HUB_KB_STATE;
    const cid = group.dataset.catId;
    window.HUB_LAST_ACTIVE_CAT = cid;

    const items = _getHubGroupItems(group);
    if (items.length > 0) {
        const rows = _getHubVisualRows(items);
        const lastRow = rows[rows.length - 1];
        st.zone = 'cards';
        st.catId = cid;
        st.moduleId = (preferredX !== null)
            ? _pickClosestInRow(lastRow, preferredX).modId
            : lastRow.entries[0].modId;
    } else {
        st.zone = 'pagination';
        st.catId = cid;
        st.moduleId = null;
    }
}

if (!window._hubKeyNavAttached) {
    window._hubKeyNavAttached = true;

    // Track hovered category for convenience
    document.addEventListener('mouseover', (e) => {
        const group = e.target.closest?.('.category-group[data-cat-id]');
        if (group && group.dataset.catId) {
            window.HUB_LAST_ACTIVE_CAT = group.dataset.catId;
        }
    });

    // Strict contextual activation/deactivation via mouse pointer
    document.addEventListener('mousedown', (e) => {
        const t = e.target;
        if (!t || typeof t.closest !== 'function') return;

        // Never hijack native selects/inputs (including .cat-page-size-select)
        if (t.closest('select, input, textarea, [contenteditable="true"]')) {
            window.hubClearKbFocus();
            return;
        }

        // Zone 1: Category Filter Pills
        const filterBtn = t.closest('#config-filter-tabs .filter-btn[data-filter-cat]');
        if (filterBtn) {
            const fc = filterBtn.dataset.filterCat;
            window.HUB_KB_STATE = {
                active: true,
                visible: false,
                zone: 'filters',
                filterCat: fc,
                catId: fc !== 'ALL' ? fc : null,
                moduleId: null
            };
            document.querySelectorAll('.hub-kb-focus').forEach(el => el.classList.remove('hub-kb-focus'));
            return;
        }

        // Zone 2: Category Pagination / Header
        const pagOrHdr = t.closest(
            '#config-tabs-bar .cat-pagination-wrap, #config-tabs-bar .cat-activate-pag-btn, #config-tabs-bar .category-header, ' +
            '#config-wall .cat-pagination-wrap, #config-wall .cat-activate-pag-btn, #config-wall .category-header'
        );
        if (pagOrHdr) {
            const grp = pagOrHdr.closest('.category-group[data-cat-id]');
            const cid = grp ? grp.dataset.catId : null;
            if (cid) {
                window.HUB_LAST_ACTIVE_CAT = cid;
                window.HUB_KB_STATE = {
                    active: true,
                    visible: false,
                    zone: 'pagination',
                    filterCat: window.activeCategoryFilter || 'ALL',
                    catId: cid,
                    moduleId: null
                };
                document.querySelectorAll('.hub-kb-focus').forEach(el => el.classList.remove('hub-kb-focus'));
                return;
            }
        }

        // Zone 3: Module Cards (Wall) or Tabs (Tabs bar)
        const cardOrTab = t.closest('#config-wall .module-card[data-mod-id], #config-tabs-bar button.tab[data-mod-id]');
        if (cardOrTab) {
            const modId = cardOrTab.dataset.modId;
            const cid = cardOrTab.dataset.modCat || cardOrTab.closest('.category-group[data-cat-id]')?.dataset.catId || null;
            if (cid) window.HUB_LAST_ACTIVE_CAT = cid;
            window.HUB_KB_STATE = {
                active: true,
                visible: false,
                zone: 'cards',
                filterCat: window.activeCategoryFilter || 'ALL',
                catId: cid,
                moduleId: modId
            };
            document.querySelectorAll('.hub-kb-focus').forEach(el => el.classList.remove('hub-kb-focus'));
            return;
        }

        // Any click outside Hub zones (e.g. inside #panel-container, search bar, header, save-bar) immediately releases Hub nav
        window.hubClearKbFocus();
    }, true);

    // Release Hub keyboard focus immediately if focus moves into config panels or any form control
    document.addEventListener('focusin', (e) => {
        const t = e.target;
        if (!t || typeof t.closest !== 'function') return;
        const tag = (t.tagName || '').toUpperCase();
        if (['INPUT', 'TEXTAREA', 'SELECT'].includes(tag) || t.isContentEditable) {
            window.hubClearKbFocus();
            return;
        }
        if (t.closest('#panel-container, #hecos-search-bar, header, .save-bar')) {
            window.hubClearKbFocus();
        }
    });

    // Main 2D Keyboard Navigator
    document.addEventListener('keydown', (e) => {
        const st = window.HUB_KB_STATE;
        if (!st || !st.active) return;

        const navKeys = ['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown', 'Enter', ' ', 'Escape'];
        if (!navKeys.includes(e.key)) return;
        if (e.ctrlKey || e.altKey || e.metaKey || e.shiftKey) return;

        const activeEl = document.activeElement;
        const tag = ((activeEl && activeEl.tagName) || '').toUpperCase();
        if (['INPUT', 'TEXTAREA', 'SELECT'].includes(tag) || activeEl?.isContentEditable) {
            window.hubClearKbFocus();
            return;
        }
        if (activeEl && activeEl.closest?.('#panel-container, #hecos-search-bar, header, .save-bar')) {
            window.hubClearKbFocus();
            return;
        }
        if (_isAnyHubOverlayOpen()) return;

        // Escape: release Hub keyboard focus
        if (e.key === 'Escape') {
            if (st.visible) {
                e.preventDefault();
                e.stopPropagation();
            }
            window.hubClearKbFocus();
            return;
        }

        // Enter / Space: execute action on focused element ONLY if keyboard ring is visible
        if (e.key === 'Enter' || e.key === ' ') {
            if (!st.visible) return;
            e.preventDefault();
            e.stopPropagation();

            if (st.zone === 'cards' && st.moduleId) {
                if (typeof window.showTab === 'function') window.showTab(st.moduleId);
            } else if (st.zone === 'pagination' && st.catId) {
                const hubEl = _getActiveHubContainer();
                const grp = hubEl ? hubEl.querySelector(`.category-group[data-cat-id="${st.catId}"]`) : null;
                if (grp && _hasGroupPagControls(grp)) {
                    window.hubCatTogglePagination(st.catId);
                } else if (grp && typeof window.toggleCategory === 'function') {
                    window.toggleCategory(st.catId);
                }
                window.syncHubKbFocus(true);
            } else if (st.zone === 'filters') {
                const fc = st.filterCat || window.activeCategoryFilter || 'ALL';
                if (typeof window.setCategoryFilter === 'function') window.setCategoryFilter(fc);
                window.syncHubKbFocus(true);
            }
            return;
        }

        // Arrow Keys: prevent native page scroll & blur any stale Hub <button> focus
        e.preventDefault();
        e.stopPropagation();
        if (activeEl && activeEl !== document.body && typeof activeEl.blur === 'function') {
            activeEl.blur();
        }

        // ── ZONE 1: Category Filters ──────────────────────────────────────────
        if (st.zone === 'filters') {
            const btns = _getHubFilterButtons();
            if (btns.length === 0) return;
            const curFilter = st.filterCat || window.activeCategoryFilter || 'ALL';
            let idx = btns.findIndex(b => b.dataset.filterCat === curFilter);
            if (idx === -1) idx = 0;

            if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
                const delta = (e.key === 'ArrowRight') ? 1 : -1;
                const nextIdx = (idx + delta + btns.length) % btns.length;
                const nextCat = btns[nextIdx].dataset.filterCat;
                st.visible = true;
                st.filterCat = nextCat;
                st.catId = (nextCat !== 'ALL') ? nextCat : null;
                st.moduleId = null;
                if (typeof window.setCategoryFilter === 'function') {
                    window.setCategoryFilter(nextCat);
                }
                window.syncHubKbFocus(true);
            } else if (e.key === 'ArrowDown') {
                if (!window.activeCategoryFilter && typeof window.setCategoryFilter === 'function') {
                    window.setCategoryFilter(curFilter);
                }
                const groups = _getHubCategoryGroups();
                if (groups.length > 0) {
                    st.visible = true;
                    _enterHubGroupFromTop(groups[0]);
                    window.syncHubKbFocus(true);
                }
            } else if (e.key === 'ArrowUp') {
                st.visible = true;
                window.syncHubKbFocus(true);
            }
            return;
        }

        // ── ZONE 2: Category Pagination / Header ──────────────────────────────
        if (st.zone === 'pagination') {
            const groups = _getHubCategoryGroups();
            if (groups.length === 0) {
                st.zone = 'filters';
                st.visible = true;
                window.syncHubKbFocus(true);
                return;
            }
            let gIdx = groups.findIndex(g => g.dataset.catId === st.catId);
            if (gIdx === -1) {
                gIdx = 0;
                st.catId = groups[0].dataset.catId;
            }
            const group = groups[gIdx];
            st.visible = true;

            if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
                const delta = (e.key === 'ArrowRight') ? 1 : -1;
                if (_hasGroupPagControls(group)) {
                    if (!window.HUB_PAGINATED_CATS.has(st.catId)) {
                        window.hubCatTogglePagination(st.catId);
                    } else {
                        window.hubCatPage(st.catId, delta);
                    }
                }
                window.syncHubKbFocus(true);
            } else if (e.key === 'ArrowDown') {
                const items = _getHubGroupItems(group);
                if (items.length > 0) {
                    st.zone = 'cards';
                    st.moduleId = items[0].dataset.modId;
                } else if (gIdx + 1 < groups.length) {
                    _enterHubGroupFromTop(groups[gIdx + 1]);
                }
                window.syncHubKbFocus(true);
            } else if (e.key === 'ArrowUp') {
                if (gIdx > 0) {
                    _enterHubGroupFromBottom(groups[gIdx - 1]);
                } else {
                    st.zone = 'filters';
                    st.filterCat = window.activeCategoryFilter || 'ALL';
                    st.moduleId = null;
                }
                window.syncHubKbFocus(true);
            }
            return;
        }

        // ── ZONE 3: Cards / Module Tabs ───────────────────────────────────────
        if (st.zone === 'cards') {
            const groups = _getHubCategoryGroups();
            if (groups.length === 0) {
                st.zone = 'filters';
                st.visible = true;
                window.syncHubKbFocus(true);
                return;
            }
            let gIdx = groups.findIndex(g => g.dataset.catId === st.catId);
            if (gIdx === -1 && st.moduleId) {
                gIdx = groups.findIndex(g => !!g.querySelector(`[data-mod-id="${st.moduleId}"]`));
            }
            if (gIdx === -1) gIdx = 0;

            const group = groups[gIdx];
            st.catId = group.dataset.catId;
            window.HUB_LAST_ACTIVE_CAT = st.catId;

            const items = _getHubGroupItems(group);
            if (items.length === 0) {
                st.zone = 'pagination';
                st.moduleId = null;
                st.visible = true;
                window.syncHubKbFocus(true);
                return;
            }

            let itemIdx = items.findIndex(el => el.dataset.modId === st.moduleId);
            if (itemIdx === -1) itemIdx = 0;
            st.visible = true;

            if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
                const delta = (e.key === 'ArrowRight') ? 1 : -1;
                const nextIdx = itemIdx + delta;

                if (nextIdx >= 0 && nextIdx < items.length) {
                    st.moduleId = items[nextIdx].dataset.modId;
                    window.syncHubKbFocus(true);
                } else if (window.HUB_PAGINATED_CATS.has(st.catId)) {
                    const curPage = parseInt(group.dataset.curPage, 10) || (window.HUB_CAT_PAGES[st.catId] || 1);
                    const totalPages = parseInt(group.dataset.totalPages, 10) || 1;
                    if (delta > 0 && curPage < totalPages) {
                        window.HUB_CAT_PAGES[st.catId] = curPage + 1;
                        st.moduleId = null;
                        renderConfigHub(typeof viewMode !== 'undefined' ? viewMode : 'tabs');
                        const newHub = _getActiveHubContainer();
                        const newGrp = newHub ? newHub.querySelector(`.category-group[data-cat-id="${st.catId}"]`) : null;
                        const newItems = _getHubGroupItems(newGrp);
                        if (newItems.length > 0) st.moduleId = newItems[0].dataset.modId;
                        window.syncHubKbFocus(true);
                    } else if (delta < 0 && curPage > 1) {
                        window.HUB_CAT_PAGES[st.catId] = curPage - 1;
                        st.moduleId = null;
                        renderConfigHub(typeof viewMode !== 'undefined' ? viewMode : 'tabs');
                        const newHub = _getActiveHubContainer();
                        const newGrp = newHub ? newHub.querySelector(`.category-group[data-cat-id="${st.catId}"]`) : null;
                        const newItems = _getHubGroupItems(newGrp);
                        if (newItems.length > 0) st.moduleId = newItems[newItems.length - 1].dataset.modId;
                        window.syncHubKbFocus(true);
                    } else {
                        window.syncHubKbFocus(true);
                    }
                } else {
                    window.syncHubKbFocus(true);
                }
            } else if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
                const rows = _getHubVisualRows(items);
                let rIdx = 0;
                let curEntry = rows[0].entries[0];
                for (let r = 0; r < rows.length; r++) {
                    const found = rows[r].entries.find(en => en.modId === st.moduleId);
                    if (found) {
                        rIdx = r;
                        curEntry = found;
                        break;
                    }
                }

                if (e.key === 'ArrowDown') {
                    if (rIdx + 1 < rows.length) {
                        st.moduleId = _pickClosestInRow(rows[rIdx + 1], curEntry.centerX).modId;
                    } else if (gIdx + 1 < groups.length) {
                        _enterHubGroupFromTop(groups[gIdx + 1], curEntry.centerX);
                    }
                } else {
                    if (rIdx - 1 >= 0) {
                        st.moduleId = _pickClosestInRow(rows[rIdx - 1], curEntry.centerX).modId;
                    } else if (_hasGroupPagControls(group)) {
                        st.zone = 'pagination';
                        st.moduleId = null;
                    } else if (gIdx > 0) {
                        _enterHubGroupFromBottom(groups[gIdx - 1], curEntry.centerX);
                    } else {
                        st.zone = 'filters';
                        st.filterCat = window.activeCategoryFilter || 'ALL';
                        st.moduleId = null;
                    }
                }
                window.syncHubKbFocus(true);
            }
        }
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
            window.HUB_CAT_PAGES[currentTabCat] = _catPage;
            const _isPaginated    = window.HUB_PAGINATED_CATS.has(currentTabCat);
            const _needsPag       = _isPaginated || _catTotal > 5;
            const _pagHtml        = _needsPag ? window.renderHubCatPagination(currentTabCat, _catPage, _catTotalPages, _isPaginated) : '';
            tabsHtml += `
                <div class="category-group ${isCollapsed ? 'collapsed' : ''}" data-cat-id="${currentTabCat}" data-cur-page="${_catPage}" data-total-pages="${_catTotalPages}">
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
        if (_mVisible) tabsHtml += `<button type="button" class="tab ${activeClass}" data-mod-id="${m.id}" data-mod-cat="${currentTabCat}" onclick="showTab('${m.id}')">${icon} ${window.t ? window.t(m.label) : m.label} ${typeBadge} ${badgeHtml}</button>`;
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
            window.HUB_CAT_PAGES[currentCat] = _catPageWall;
            const _isPaginatedWall    = window.HUB_PAGINATED_CATS.has(currentCat);
            const _needsPagWall       = _isPaginatedWall || _catTotalWall > 5;
            const _pagHtmlWall        = _needsPagWall ? window.renderHubCatPagination(currentCat, _catPageWall, _catTotalPagesWall, _isPaginatedWall) : '';
            wallHtml += `
                <div class="category-group ${isCollapsed ? 'collapsed' : ''}" data-cat-id="${currentCat}" data-cur-page="${_catPageWall}" data-total-pages="${_catTotalPagesWall}">
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
                <div class="module-card ${activeClass}" data-mod-id="${m.id}" data-mod-cat="${currentCat}" onclick="showTab('${m.id}')" style="position:relative;">
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
    // Restore virtual keyboard highlight across DOM re-renders without scroll jumps
    if (typeof window.syncHubKbFocus === 'function') {
        window.syncHubKbFocus(false);
    }
}

window.renderConfigHub  = renderConfigHub;
window.renderFilterTabs = renderFilterTabs;
