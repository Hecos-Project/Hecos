/**
 * Hecos Control Room - Actions Module (GridStack.js)
 * Handles widget operations: span toggle, remove, height reset.
 * Resize is now handled natively by GridStack.
 */
(function (global) {
    'use strict';

    const API = {
        LAYOUT:  '/api/widgets/room/layout',
        SPAN:    (id) => `/api/widgets/${id}/room_span`,
        VISIBLE: (id) => `/api/widgets/${id}/room_visible`,
        HEIGHT:  (id) => `/api/widgets/${id}/room_height`,
    };

    let _saveTimer = null;
    const _getCtx = () => global.controlRoomGrid ? global.controlRoomGrid.getContext() : 'sidebar';
    const _getGrid = () => global._gsGrid || null;

    // ── Layout persistence ────────────────────────────────────────────────────
    const _persistLayout = () => {
        const gsGrid = _getGrid();
        if (!gsGrid) return;
        clearTimeout(_saveTimer);
        _saveTimer = setTimeout(async () => {
            const layout = gsGrid.getGridItems().map(el => el.getAttribute('gs-id') || el.dataset.id).filter(Boolean);
            try {
                await fetch(`${API.LAYOUT}?context=${_getCtx()}`, {
                    method: 'PATCH',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ layout })
                });
                console.log('[RoomGrid] Layout saved:', layout);
            } catch (err) { console.warn('[RoomGrid] Layout save failed:', err); }
        }, 400);
    };

    // ── Span toggle ───────────────────────────────────────────────────────────
    global._roomGridToggleSpan = async function (id, btn) {
        const gsGrid = _getGrid();
        const card = document.querySelector(`.grid-stack-item[gs-id="${id}"], .grid-stack-item[data-id="${id}"]`);
        if (!gsGrid || !card) {
            console.warn(`[RoomGrid] ToggleSpan failed: card ${id} not found.`);
            return;
        }

        const node = card.gridstackNode;
        const newSpan = node && node.w === 2 ? 1 : 2;

        try {
            const resp = await fetch(`${API.SPAN(id)}?context=${_getCtx()}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ span: newSpan })
            });
            if ((await resp.json()).ok) {
                gsGrid.update(card, { w: newSpan });
                if (global._roomGridSync) global._roomGridSync.notify(id, 'room_span', newSpan, _getCtx());
                const content = card.querySelector('.room-widget-card');
                if (btn) {
                    btn.innerHTML = newSpan === 2
                        ? '<i class="fas fa-compress-alt"></i> 2×'
                        : '<i class="fas fa-expand-alt"></i> 1×';
                    btn.classList.toggle('active', newSpan === 2);
                }
                _persistLayout();
            }
        } catch (err) { console.warn('[RoomGrid] span error:', err); }
    };

    // ── Remove widget ─────────────────────────────────────────────────────────
    global._roomGridRemoveWidget = async function (id) {
        const gsGrid = _getGrid();
        try {
            const resp = await fetch(`${API.VISIBLE(id)}?context=${_getCtx()}`, {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ visible: false })
            });
            if ((await resp.json()).ok) {
                if (global._roomGridSync) global._roomGridSync.notify(id, 'room_visible', false, _getCtx());
                const card = document.querySelector(`.grid-stack-item[gs-id="${id}"], .grid-stack-item[data-id="${id}"]`);
                if (card) {
                    const content = card.querySelector('.room-widget-card');
                    if (content) { content.style.opacity = '0'; content.style.transform = 'scale(0.92)'; }
                    setTimeout(() => {
                        if (gsGrid) gsGrid.removeWidget(card, false);
                        else card.remove();
                        // Show empty if nothing left
                        const grid = document.querySelector('#room-grid, #home-grid');
                        if (grid && !grid.querySelectorAll('.grid-stack-item').length && global._roomGridRender) {
                            global._roomGridRender.showEmpty(grid);
                        }
                    }, 280);
                }
                localStorage.setItem('hecos_room_sync', Date.now());
            }
        } catch (err) { console.warn('[RoomGrid] remove error:', err); }
    };

    // ── Reset height (double-click on old resize handle, kept for compat) ─────
    global._roomGridResetHeight = async function (id) {
        const gsGrid = _getGrid();
        const card = document.querySelector(`.grid-stack-item[gs-id="${id}"], .grid-stack-item[data-id="${id}"]`);
        if (!gsGrid || !card) return;
        const defaultH = global._roomGridRender?.DEFAULT_H || 3;
        gsGrid.update(card, { h: defaultH });
        try {
            await fetch(`${API.HEIGHT(id)}?context=${_getCtx()}`, {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ height: null })
            });
            if (global._roomGridSync) global._roomGridSync.notify(id, 'room_height', null, _getCtx());
        } catch (err) { console.warn('[RoomGrid] reset height err:', err); }
    };

    global._saveHeight = async function (id, h) {
        const pxHeight = h * 110; 
        try {
            const resp = await fetch(`${API.HEIGHT(id)}?context=${_getCtx()}`, {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ height: pxHeight })
            });
            if ((await resp.json()).ok) {
                 // Wait a bit before notifying others to let DB sync
                 setTimeout(() => {
                    if (global._roomGridSync) global._roomGridSync.notify(id, 'room_height', pxHeight, _getCtx());
                 }, 400);
            }
        } catch (err) { console.warn('[RoomGrid] save height err:', err); }
    };

    // ── Compatibility: old _roomGridStartResize is no longer needed ───────────
    global._roomGridStartResize = function () {
        // No-op: GridStack handles resize natively
    };

    global._persistLayout = _persistLayout;

})(window);
