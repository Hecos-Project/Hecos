/**
 * Hecos Control Room — Module A Logic
 * control_room.js
 *
 * Scope: Expandable inline panel (#control-room-panel).
 * Dependencies: BroadcastChannel 'hecos_widgets' (shared with sidebar_widgets.js)
 *               /api/widgets/room endpoint
 * Zero coupling to Module B (home.js).
 */

window.controlRoom = (function () {
    'use strict';

    const STORAGE_KEY = 'hecos-room-open';
    const API_URL     = '/api/widgets/room';

    let _isOpen   = false;
    let _loaded   = false;  // true after first successful load

    // ── DOM refs ────────────────────────────────────────────────────
    function _panel()   { return document.getElementById('control-room-panel'); }
    function _grid()    { return document.getElementById('room-grid'); }
    function _btn()     { return document.getElementById('sidebar-expand-btn'); }
    function _chevron() { return document.getElementById('sidebar-expand-chevron'); }

    // ── Toggle ──────────────────────────────────────────────────────
    function toggle() {
        _isOpen ? close() : open();
    }

    function open() {
        _isOpen = true;
        const panel = _panel();
        const btn   = _btn();
        if (panel) panel.classList.add('open');
        if (btn)   btn.classList.add('active');
        
        // Let the new grid engine handle loading
        if (window.controlRoomGrid && !_loaded) {
            window.controlRoomGrid.refresh();
            _loaded = true;
        }
        
        localStorage.setItem(STORAGE_KEY, '1');
    }

    function close() {
        _isOpen = false;
        const panel = _panel();
        const btn   = _btn();
        if (panel) panel.classList.remove('open');
        if (btn)   btn.classList.remove('active');
        localStorage.setItem(STORAGE_KEY, '0');
    }

    // Public refresh (called on widget sync events)
    function refresh() {
        if (_isOpen && window.controlRoomGrid) {
            window.controlRoomGrid.refresh();
        } else {
            _loaded = false;  // stale, will reload next open
        }
    }

    // ── BroadcastChannel sync (shared channel, module is independent listener) ─
    try {
        const _channel = new BroadcastChannel('hecos_widgets');
        _channel.onmessage = () => {
            console.log('[ControlRoom] Widget sync signal received.');
            refresh();
        };
    } catch (e) {
        // BroadcastChannel not available (unlikely in modern browsers)
        console.warn('[ControlRoom] BroadcastChannel unavailable:', e);
    }

    // localStorage cross-tab sync
    window.addEventListener('storage', (e) => {
        if (e.key === 'hecos_sidebar_sync' || e.key === 'hecos_room_sync') refresh();
    });

    // ── Restore state on load ───────────────────────────────────────
    document.addEventListener('DOMContentLoaded', () => {
        if (localStorage.getItem(STORAGE_KEY) === '1') {
            // Small delay so sidebar layout is painted first
            setTimeout(open, 200);
        }
    });

    // ── Public API ──────────────────────────────────────────────────
    return { toggle, open, close, refresh };

})();
