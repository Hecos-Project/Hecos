/**
 * Hecos Control Room - Actions Module (GridStack.js)
 * Handles widget operations: span toggle, remove from current page, height save/reset.
 * Resize is handled natively by GridStack.
 */
(function (global) {
    'use strict';

    const API = {
        SPAN:    (id) => `/api/widgets/${id}/room_span`,
        VISIBLE: (id) => `/api/widgets/${id}/room_visible`,
        HEIGHT:  (id) => `/api/widgets/${id}/room_height`,
    };

    const _getCtx = () => global.controlRoomGrid ? global.controlRoomGrid.getContext() : 'sidebar';
    const _getGrid = () => global._gsGrid || null;
    const _getActivePageId = () => global.controlRoomGrid ? global.controlRoomGrid.getActivePageId() : '';

    // ── Layout persistence (delegates to unified grid engine) ─────────────────
    const _persistLayout = () => {
        if (global.controlRoomGrid && typeof global.controlRoomGrid.persistLayout === 'function') {
            global.controlRoomGrid.persistLayout();
        }
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
        if (global.controlRoomGrid) global.controlRoomGrid.lockRefresh(2000);

        try {
            const resp = await fetch(`${API.SPAN(id)}?context=${_getCtx()}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ span: newSpan })
            });
            if ((await resp.json()).ok) {
                const currentCols = gsGrid.getColumn();
                gsGrid.update(card, { w: (newSpan === 2 && currentCols > 1) ? 2 : 1 });
                if (global._roomGridSync) global._roomGridSync.notify(id, 'room_span', newSpan, _getCtx());
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

    // ── Remove widget from the ACTIVE page ────────────────────────────────────
    global._roomGridRemoveWidget = async function (id) {
        const gsGrid = _getGrid();
        const pageId = _getActivePageId();
        if (global.controlRoomGrid) global.controlRoomGrid.lockRefresh(1200);

        try {
            const resp = await fetch(`${API.VISIBLE(id)}?context=${_getCtx()}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ visible: false, page_id: pageId })
            });
            const data = await resp.json();
            if (data.ok) {
                if (global._roomGridSync) {
                    global._roomGridSync.notify(id, 'room_visible', Boolean(data.room_visible), _getCtx());
                    if (typeof global._roomGridSync.notifyPagesChanged === 'function') {
                        global._roomGridSync.notifyPagesChanged('remove_widget', { pageId, widgetId: id });
                    }
                }
                const card = document.querySelector(`.grid-stack-item[gs-id="${id}"], .grid-stack-item[data-id="${id}"]`);
                if (card) {
                    const content = card.querySelector('.room-widget-card');
                    if (content) { content.style.opacity = '0'; content.style.transform = 'scale(0.92)'; }
                    setTimeout(() => {
                        if (gsGrid) gsGrid.removeWidget(card, false);
                        else card.remove();
                        if (global.controlRoomGrid) {
                            global.controlRoomGrid.refresh({ force: true, pageId });
                        }
                    }, 220);
                } else if (global.controlRoomGrid) {
                    global.controlRoomGrid.refresh({ force: true, pageId });
                }
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
