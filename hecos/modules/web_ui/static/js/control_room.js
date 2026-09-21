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
    const STORAGE_WIDTH_KEY = 'hecos-room-width';
    const API_URL     = '/api/widgets/room';

    let _isOpen   = false;
    let _loaded   = false;  // true after first successful load
    let _widthState = localStorage.getItem(STORAGE_WIDTH_KEY) || '2x'; 

    // ── DOM refs ────────────────────────────────────────────────────
    function _panel()   { return document.getElementById('control-room-panel'); }
    function _grid()    { return document.getElementById('room-grid'); }
    function _btn()     { return document.getElementById('sidebar-expand-btn'); }
    function _chevron() { return document.getElementById('sidebar-expand-chevron'); }

    // ── Toggle ──────────────────────────────────────────────────────
    function toggle() {
        _isOpen ? close() : open();
    }

    function applyWidthState() {
        const panel = _panel();
        if (!panel) return;
        const btnSpan = document.querySelector('#room-width-btn span');
        
        if (_widthState === '1x') {
            panel.style.width = '25vw';
            panel.classList.add('mode-1col');
            if (btnSpan) btnSpan.textContent = '1x';
            if (window._gsGrid) {
                window._gsGrid.column(1, 'moveScale');
                setTimeout(() => window._gsGrid.onParentResize(), 400);
            }
        } else if (_widthState === '2x') {
            panel.style.width = '50vw';
            panel.classList.remove('mode-1col');
            if (btnSpan) btnSpan.textContent = '2x';
            if (window._gsGrid) {
                window._gsGrid.column(2, 'moveScale');
                setTimeout(() => window._gsGrid.onParentResize(), 400);
            }
        } else {
            // Custom pixel width from dragging
            panel.style.width = _widthState;
            const w = parseInt(_widthState, 10);
            const cols = w < 500 ? 1 : 2;
            panel.classList.toggle('mode-1col', cols === 1);
            if (btnSpan) btnSpan.textContent = cols + 'x';
            if (window._gsGrid) {
                window._gsGrid.column(cols, 'moveScale');
                setTimeout(() => window._gsGrid.onParentResize(), 400);
            }
        }
    }

    function toggleWidth() {
        if (!_isOpen) {
            open();
            return;
        }
        const panel = _panel();
        const currentW = panel.offsetWidth;
        if (currentW < 500) {
            _widthState = '2x';
        } else {
            _widthState = '1x';
        }
        localStorage.setItem(STORAGE_WIDTH_KEY, _widthState);
        applyWidthState();
        fixGrid();
        setTimeout(fixGrid, 400);
    }

    const fixGrid = () => {
        if (window._gsGrid) {
            console.log('[ControlRoom] GridStack layout recalculation triggered.');
            if (typeof window._gsGrid.onParentResize === 'function') window._gsGrid.onParentResize();
            
            // Threshold: midpoint between 25vw and 50vw
            const threshold = window.innerWidth * 0.375;
            const panel = _panel();
            if (panel && _isOpen) {
                const cols = panel.offsetWidth < threshold ? 1 : 2;
                panel.classList.toggle('mode-1col', cols === 1);
                window._gsGrid.column(cols, 'moveScale');
            }
        }
    };

    function open() {
        _isOpen = true;
        const panel = _panel();
        const btn   = _btn();
        if (panel) panel.classList.add('open');
        if (btn)   btn.classList.add('active');
        
        applyWidthState();
        
        // Let the new grid engine handle loading
        if (window.controlRoomGrid && !_loaded) {
            window.controlRoomGrid.refresh();
            _loaded = true;
        }

        fixGrid(); // Immediate (might be 0 width but helps pre-load)
        setTimeout(fixGrid, 150); // Mid-transition
        setTimeout(fixGrid, 450); // Post-transition
        setTimeout(fixGrid, 800); // Sanity check
        
        localStorage.setItem(STORAGE_KEY, '1');
    }

    function close() {
        _isOpen = false;
        const panel = _panel();
        const btn   = _btn();
        if (panel) {
            panel.classList.remove('open');
            panel.style.width = ''; // clear inline style to let CSS close it
        }
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

    // ── HPM package events: reset loaded flag so next open always re-fetches ──
    (function() {
        const _hpmChannel = new BroadcastChannel('hecos_widgets');
        _hpmChannel.onmessage = (e) => {
            if (e.data && e.data.type === 'widgets_reload_request') {
                _loaded = false;
                if (_isOpen && window.controlRoomGrid) {
                    window.controlRoomGrid.debouncedRefresh();
                }
            }
        };
    })();

    // localStorage cross-tab sync (structural changes only)
    window.addEventListener('storage', (e) => {
        if (e.key === 'hecos_sidebar_sync' || e.key === 'hecos_room_sync') refresh();
    });

    // ── Resizer Drag Logic ──────────────────────────────────────────
    document.addEventListener('DOMContentLoaded', () => {
        const resizer = document.getElementById('room-resizer');
        const panel = _panel();
        let startX = 0;
        let startWidth = 0;

        if (resizer && panel) {
            resizer.addEventListener('mousedown', (e) => {
                e.preventDefault();
                startX = e.clientX;
                startWidth = panel.offsetWidth;
                panel.classList.add('dragging');
                document.addEventListener('mousemove', onMouseMove);
                document.addEventListener('mouseup', onMouseUp);
            });
        }

        function onMouseMove(e) {
            // panel expands to the right, so moving mouse right increases width
            const deltaX = e.clientX - startX;
            let newWidth = startWidth + deltaX;
            
            // Snap to closed
            if (newWidth < 150) {
                newWidth = 0;
            }
            // Enforce minimum open width
            if (newWidth > 0 && newWidth < 280) {
                newWidth = 280; 
            }
            
            if (newWidth === 0) {
                if (_isOpen) close();
            } else {
                panel.style.width = newWidth + 'px';
                if (!_isOpen) {
                    _isOpen = true;
                    panel.classList.add('open');
                    const btn = _btn();
                    if (btn) btn.classList.add('active');
                    localStorage.setItem(STORAGE_KEY, '1');
                }
                
                // Dynamically update columns based on width
                const threshold = window.innerWidth * 0.375;
                let col = newWidth < threshold ? 1 : 2;
                panel.classList.toggle('mode-1col', col === 1);
                if (window._gsGrid) {
                    if (window._gsGrid.getColumn() !== col) {
                        window._gsGrid.column(col, 'moveScale');
                        const btnSpan = document.querySelector('#room-width-btn span');
                        if (btnSpan) btnSpan.textContent = col + 'x';
                    }
                    if (typeof window._gsGrid.onParentResize === 'function') {
                        window._gsGrid.onParentResize();
                    }
                }
            }
        }

        function onMouseUp(e) {
            panel.classList.remove('dragging');
            document.removeEventListener('mousemove', onMouseMove);
            document.removeEventListener('mouseup', onMouseUp);
            if (_isOpen) {
                _widthState = panel.style.width;
                localStorage.setItem(STORAGE_WIDTH_KEY, _widthState);
                fixGrid();
            }
        }

        // Restore state on load
        if (localStorage.getItem(STORAGE_KEY) === '1') {
            setTimeout(open, 200);
        }
    });

    // ── Public API ──────────────────────────────────────────────────
    return { toggle, toggleWidth, open, close, refresh };

})();
