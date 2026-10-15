/**
 * dcc_core.js — Dynamic Capability Chips Core
 * Part of: extensions/dcc/
 *
 * Fetches chip data from /api/dcc/chips and exposes DccEngine API.
 * Implements window.DccEngine so that ws_chips.js can delegate to it.
 *
 * Public API (window.DccEngine):
 *   .isReady()          → bool
 *   .getData()          → full DCC hierarchy object
 *   .renderChips(el)    → renders L1 into el, returns the wrapper
 *   .refresh()          → re-fetches from server and re-renders if mounted
 */
(function () {
    'use strict';

    let _data = null;
    let _ready = false;
    let _loading = false;
    let _mountedContainer = null;  // element where chips were last rendered

    /**
     * Fetch chips from the API.
     */
    async function _fetchChips() {
        if (_loading) return;
        _loading = true;
        try {
            const res = await fetch('/api/dcc/chips', { credentials: 'same-origin' });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const data = await res.json();
            if (data.ok && Array.isArray(data.categories)) {
                _data = data;
                _ready = true;
                console.log(`[DCC] Loaded ${data.categories.length} categories, ${data.featured?.length || 0} featured.`);
            }
        } catch (e) {
            console.warn('[DCC] Failed to load chips:', e);
            _ready = false;
        } finally {
            _loading = false;
        }
    }

    function isReady() { return _ready; }
    function getData() { return _data; }

    /**
     * Render chips into a container element.
     * Called by ws_chips.js when DCC is ready.
     * @param {HTMLElement} container
     * @returns {HTMLElement} the chips wrapper
     */
    function renderChips(container) {
        _mountedContainer = container;
        if (window.DccRender) {
            return window.DccRender.render(container, _data);
        }
        // Fallback if dcc_render.js not loaded yet
        console.warn('[DCC] DccRender not available, falling back to static chips.');
        if (window.WelcomeChips) return window.WelcomeChips.renderStatic(container);
        return null;
    }

    /**
     * Refresh: re-fetch from server and re-render if chips are mounted.
     */
    async function refresh() {
        await _fetchChips();
        if (_mountedContainer && _ready && window.DccRender) {
            // Remove old chips wrapper and re-render
            const old = _mountedContainer.querySelector('.dcc-nav-container');
            if (old) old.remove();
            window.DccRender.render(_mountedContainer, _data);
        }
    }

    // Pre-fetch on load so chips are ready when the welcome renders
    _fetchChips();

    window.DccEngine = { isReady, getData, renderChips, refresh };
})();
