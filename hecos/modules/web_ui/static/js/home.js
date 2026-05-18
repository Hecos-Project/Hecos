/**
 * Hecos Control Room — Module B Logic
 * home.js
 *
 * Scope: /home standalone page only.
 * All widget rendering and sync is handled by control_room_grid.js +
 * control_room_grid_sync.js.  This file only handles the SSE
 * widgets_refresh signal (which is not intercepted by the grid engine)
 * and the FOUC-prevention theme init.
 */

(function () {
    'use strict';

    // ── SSE: widgets_refresh → debouncedRefresh ────────────────────
    // The BroadcastChannel + localStorage listeners already live inside
    // control_room_grid_sync.js.  We only add the SSE listener here
    // because home.js does not load chat_events.js (which normally
    // handles this for the Hub / Chat pages).
    const _initSSE = () => {
        const evtSrc = new EventSource('/api/events');
        evtSrc.onmessage = (e) => {
            try {
                const ev = JSON.parse(e.data);
                if (ev.type === 'widgets_refresh') {
                    console.log('[Home-Sync] SSE widgets_refresh — calling debouncedRefresh.');
                    if (window.controlRoomGrid) window.controlRoomGrid.debouncedRefresh();
                }
                // Route other events to any registered handler (e.g. reminders)
                if (window._hecosSSEHandlers && window._hecosSSEHandlers[ev.type]) {
                    window._hecosSSEHandlers[ev.type](ev);
                }
            } catch (_) {}
        };
        evtSrc.onerror = () => {
            evtSrc.close();
            setTimeout(_initSSE, 5000);
        };
    };
    _initSSE();

    // ── Theme init (prevent FOUC) ──────────────────────────────────
    (function () {
        const auto  = localStorage.getItem('hecos-ui-auto-theme') === 'true';
        const saved = localStorage.getItem('hecos-ui-theme') || 'cyberpunk';
        const theme = auto ? 'native' : saved;
        if (theme && theme !== 'default') {
            document.body.classList.add('theme-' + theme);
        }
    })();

})();
