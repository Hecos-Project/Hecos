/**
 * Hecos Control Room - Actions Module
 * Handles widget operations (span, remove, resize) and persistence.
 */
(function (global) {
    'use strict';

    const API = {
        LAYOUT: '/api/widgets/room/layout',
        SPAN: (id) => `/api/widgets/${id}/room_span`,
        VISIBLE: (id) => `/api/widgets/${id}/room_visible`,
        HEIGHT: (id) => `/api/widgets/${id}/room_height`,
    };

    let _saveTimer = null;
    
    const _getCtx = () => global.controlRoomGrid ? global.controlRoomGrid.getContext() : 'sidebar';

    const _persistLayout = () => {
        const grid = document.querySelector('#room-grid, #home-grid');
        if (!grid) return;
        clearTimeout(_saveTimer);
        _saveTimer = setTimeout(async () => {
            const layout = [...grid.querySelectorAll('.room-widget-card')].map(c => c.dataset.id);
            try {
                await fetch(`${API.LAYOUT}?context=${_getCtx()}`, {
                    method: 'PATCH',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({layout})
                });
            } catch (err) { console.warn('[RoomGrid] Layout save failed:', err); }
        }, 400);
    };

    global._roomGridToggleSpan = async function (id, btn) {
        const card = btn.closest('.room-widget-card');
        const newSpan = card.dataset.span === '2' ? 1 : 2;
        try {
            const resp = await fetch(`${API.SPAN(id)}?context=${_getCtx()}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ span: newSpan })
            });
            if ((await resp.json()).ok) {
                card.dataset.span = newSpan;
                card.classList.toggle('span-2', newSpan === 2);
                if (global._roomGridSync) global._roomGridSync.notify(id, 'room_span', newSpan, _getCtx());
                btn.innerHTML = newSpan === 2 ? '<i class="fas fa-compress-alt"></i> 2×' : '<i class="fas fa-expand-alt"></i> 1×';
                btn.classList.toggle('active', newSpan === 2);
                _persistLayout();
            }
        } catch (err) { console.warn('[RoomGrid] span error:', err); }
    };

    global._roomGridRemoveWidget = async function (id) {
        try {
            const resp = await fetch(`${API.VISIBLE(id)}?context=${_getCtx()}`, {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ visible: false })
            });
            if ((await resp.json()).ok) {
                if (global._roomGridSync) global._roomGridSync.notify(id, 'room_visible', false, _getCtx());
                const card = document.querySelector(`.room-widget-card[data-id="${id}"]`);
                if (card) {
                    card.style.opacity = '0';
                    card.style.transform = 'scale(0.92)';
                    setTimeout(() => {
                        card.remove();
                        const grid = document.querySelector('#room-grid, #home-grid');
                        if (grid && !grid.querySelectorAll('.room-widget-card').length && global._roomGridRender) global._roomGridRender.showEmpty(grid);
                    }, 280);
                }
                localStorage.setItem('hecos_room_sync', Date.now());
            }
        } catch (err) { console.warn('[RoomGrid] remove error:', err); }
    };

    global._roomGridStartResize = function(e, id) {
        if (!global.controlRoomGrid?.isEditing()) return;
        e.preventDefault();
        const card = document.querySelector(`.room-widget-card[data-id="${id}"]`);
        if (!card) return;
        const startY = e.type.includes('touch') ? e.touches[0].clientY : e.clientY;
        const startRowSpan = parseInt(card.style.gridRowEnd?.replace('span', '') || 1);
        const cardRect = card.getBoundingClientRect();
        
        const line = document.createElement('div');
        line.className = 'room-resize-indicator-line';
        document.body.appendChild(line);
        
        // CSS grid auto-rows is set to approx 200px. We use 200 + gap as snap
        const rowHeight = 212; 

        const onMove = (mv) => {
            const currentY = mv.type.includes('touch') ? mv.touches[0].clientY : mv.clientY;
            let totalHeight = cardRect.height + (currentY - startY);
            
            // Snap to grid row spans
            let rows = Math.max(1, Math.round(totalHeight / rowHeight));
            card.style.gridRowEnd = `span ${rows}`;
            
            const r = card.getBoundingClientRect();
            line.style.cssText = `top:${r.bottom}px; left:${r.left}px; width:${r.width}px;`;
        };

        const onEnd = async () => {
            ['mousemove','mouseup','touchmove','touchend'].forEach(evt => document.removeEventListener(evt, evt.includes('move') ? onMove : onEnd));
            line.remove();
            
            let h = null;
            if (card.style.gridRowEnd && card.style.gridRowEnd.includes('span')) {
                let rows = parseInt(card.style.gridRowEnd.replace('span', '').trim());
                if(rows > 1) {
                    h = (rows * rowHeight) - 12; // remove single gap to get absolute height
                }
            }
            
            card.style.minHeight = h ? h + 'px' : '';
            
            try {
                await fetch(`${API.HEIGHT(id)}?context=${_getCtx()}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ height: h }) });
                if (global._roomGridSync) global._roomGridSync.notify(id, 'room_height', h, _getCtx());
            } catch (err) { console.warn('[RoomGrid] height save err:', err); }
        };

        ['mousemove','mouseup','touchmove','touchend'].forEach(evt => document.addEventListener(evt, evt.includes('move') ? onMove : onEnd, {passive: !evt.includes('move')}));
    };

    global._roomGridResetHeight = async function(id) {
        if (!global.controlRoomGrid?.isEditing()) return;
        const card = document.querySelector(`.room-widget-card[data-id="${id}"]`);
        if (!card) return;
        card.style.minHeight = '';
        card.style.gridRowEnd = '';
        try {
            await fetch(`${API.HEIGHT(id)}?context=${_getCtx()}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ height: null }) });
            if (global._roomGridSync) global._roomGridSync.notify(id, 'room_height', null, _getCtx());
        } catch (err) { console.warn('[RoomGrid] reset height err:', err); }
    };

    global._persistLayout = _persistLayout;

})(window);
