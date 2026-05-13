/**
 * Hecos Control Room — Module B Logic
 * home.js
 *
 * Scope: /home standalone page only.
 * Dependencies: BroadcastChannel 'hecos_widgets', /api/widgets/room
 * Zero coupling to Module A (control_room.js).
 */

(function () {
    'use strict';

    const API_URL = '/api/widgets/room';

    // ── Load widgets into #home-grid ────────────────────────────────
    async function loadWidgets() {
        const grid = document.getElementById('home-grid');
        if (!grid) return;

        grid.innerHTML = `
            <div class="room-loading">
                <i class="fas fa-spinner fa-spin" style="opacity:0.5;"></i>
                <span style="opacity:0.5;">Loading widgets…</span>
            </div>`;

        try {
            const resp = await fetch(`${API_URL}?t=${Date.now()}`);
            if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
            const data = await resp.json();
            if (data.ok) {
                grid.innerHTML = data.html;
                console.log('[Home] Widgets loaded.');
            } else {
                _showError(grid, data.error || 'Unknown error');
            }
        } catch (err) {
            console.error('[Home] Load error:', err);
            _showError(grid, err.message);
        }
    }

    function _showError(grid, msg) {
        grid.innerHTML = `
            <div class="room-empty-state">
                <i class="fas fa-exclamation-triangle" style="color:var(--red);"></i>
                <p>Could not load widgets<br><small style="opacity:0.6;">${msg}</small></p>
            </div>`;
    }

    // ── Synchronization (Shared with Sidebar via SSE \u0026 Broadcast) ────────
    try {
        const channel = new BroadcastChannel('hecos_widgets');
        channel.onmessage = () => {
            console.log('[Home-Sync] BroadcastChannel signal — refreshing.');
            loadWidgets();
        };
    } catch (e) {
        console.warn('[Home-Sync] BroadcastChannel unavailable:', e);
    }

    // SSE listener (proven method for sidebar)
    const _initSSE = () => {
        const evtSrc = new EventSource('/api/events');
        evtSrc.onmessage = (e) => {
            const ev = JSON.parse(e.data);
            if (ev.type === 'widgets_refresh') {
                console.log('[Home-Sync] SSE refresh signal received.');
                loadWidgets();
            }
        };
        evtSrc.onerror = () => {
            evtSrc.close();
            setTimeout(_initSSE, 5000); // Reconnect
        };
    };
    _initSSE();

    // localStorage cross-tab sync (fallback)
    window.addEventListener('storage', (e) => {
        if (e.key === 'hecos_sidebar_sync' || e.key === 'hecos_room_sync') loadWidgets();
    });

    // ── Theme init (matches chat.html FOUC prevention pattern) ─────
    (function () {
        const autoTheme = localStorage.getItem('hecos-ui-auto-theme') === 'true';
        const savedTheme = localStorage.getItem('hecos-ui-theme') || 'cyberpunk';
        const theme = autoTheme ? 'native' : savedTheme;
        if (theme && theme !== 'default') {
            document.body.classList.add('theme-' + theme);
        }
    })();

    // ── Init ────────────────────────────────────────────────────────
    document.addEventListener('DOMContentLoaded', loadWidgets);

})();
