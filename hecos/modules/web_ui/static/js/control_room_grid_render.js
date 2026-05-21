/**
 * Hecos Control Room - Render Module (GridStack.js v10)
 */
(function (global) {
    'use strict';

    const FRAME_URL = (id) => `/api/widgets/room/${id}/frame`;
    const DEFAULT_H = 3;

    function _pxToRows(px) {
        if (!px) return DEFAULT_H;
        // Use ceil to ensure we have enough space if the calculation is fractional
        return Math.max(1, Math.ceil((px - 5) / 110));
    }

    const _render = (grid, widgets, gsGrid) => {
        if (!grid || !gsGrid) return;
        
        // Context-aware column count
        const currentCols = gsGrid.getColumn();
        console.log(`[RoomGrid] Render Start. Context: ${currentCols} cols. Widgets: ${widgets.length}`);

        // 1. Remove stale widgets
        const newIds = new Set(widgets.map(w => w.extension_id));
        gsGrid.getGridItems().forEach(el => {
            const id = el.getAttribute('gs-id') || el.dataset.id;
            if (id && !newIds.has(id)) {
                console.log(`[RoomGrid] Removing stale widget: ${id}`);
                gsGrid.removeWidget(el, true);
            } else if (!id) {
                console.warn('[RoomGrid] Removing item with no ID:', el);
                gsGrid.removeWidget(el, true);
            }
        });

        // 2. Add or Update
        widgets.forEach(w => {
            const id = w.extension_id;
            // Support 1x spanned width in 2-col sidebar, or varying widths in multi-col home
            const gsW = (w.room_span === 2 && currentCols > 1) ? 2 : 1;
            const gsH = _pxToRows(w.room_height);
            console.log(`[RoomGrid] Widget ${id}: room_height=${w.room_height} -> gsH=${gsH}`);
            const theme = (w.theme || 'default').replace('theme-', '');
            
            const bgStyle = w.bg_color ? `background-color:${w.bg_color};` : '';
            const imgStyle = w.bg_image ? `background-image:url('/media/file?path=${encodeURIComponent(w.bg_image)}'); background-size:cover; background-position:center;` : '';

            let el = gsGrid.getGridItems().find(item => (item.getAttribute('gs-id') === id || item.dataset.id === id));

            const contentHtml = `
                <div class="room-card-chrome">
                    <span class="room-card-drag-handle" title="Drag to reorder"><i class="fas fa-grip-vertical"></i></span>
                    <button class="room-card-span-btn ${w.room_span === 2 ? 'active' : ''}"
                            onclick="event.stopPropagation(); _roomGridToggleSpan('${id}', this)">
                        ${w.room_span === 2 ? '<i class="fas fa-compress-alt"></i> 2\u00d7' : '<i class="fas fa-expand-alt"></i> 1\u00d7'}
                    </button>
                    <button class="room-card-aes-btn" onclick="event.stopPropagation(); _roomGridOpenAes(event, '${id}', this)">
                        <i class="fas fa-magic"></i>
                    </button>
                    <button class="room-card-remove-btn" onclick="event.stopPropagation(); _roomGridRemoveWidget('${id}')">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                <iframe src="${FRAME_URL(id)}?t=${Date.now()}"
                        class="room-widget-iframe" loading="lazy" scrolling="no"
                        frameborder="0" allowtransparency="true"></iframe>
            `;

            if (el) {
                // Update
                const node = el.gridstackNode;
                if (node && (node.w !== gsW || node.h !== gsH)) {
                    gsGrid.update(el, { w: gsW, h: gsH });
                }
                const contentNode = el.querySelector('.grid-stack-item-content');
                if (contentNode) {
                    contentNode.className = `grid-stack-item-content room-widget-card border-glow theme-${theme}`;
                    contentNode.style.cssText = `${bgStyle} ${imgStyle}`;
                }
            } else {
                // Add
                console.log(`[RoomGrid] addWidget: ${id} (${gsW}x${gsH})`);
                const newEl = gsGrid.addWidget({
                    id: id,
                    w: gsW,
                    h: gsH,
                    autoPosition: true,
                    content: contentHtml
                });
                
                if (newEl) {
                    newEl.setAttribute('data-id', id);
                    const contentNode = newEl.querySelector('.grid-stack-item-content');
                    if (contentNode) {
                        contentNode.className += ` room-widget-card border-glow theme-${theme}`;
                        if (bgStyle || imgStyle) contentNode.style.cssText += ` ${bgStyle} ${imgStyle}`;
                    }
                }
            }
        });

        // Maintain the desired column count without forcing a hardcoded value
        gsGrid.column(currentCols, 'none');
        gsGrid.compact();
    };

    const _showEmpty = (grid) => {
        let el = document.getElementById('room-empty-state');
        if (!el) {
            el = document.createElement('div');
            el.id = 'room-empty-state'; el.className = 'room-empty-state';
            el.innerHTML = `<i class="fas fa-th-large"></i><p>Control Room vuota.</p>`;
            grid.insertAdjacentElement('afterend', el);
        }
        el.style.display = 'flex';
    };

    const _hideEmpty = (grid) => {
        const el = document.getElementById('room-empty-state');
        if (el) el.style.display = 'none';
    };

    global._roomGridRender = { render: _render, showEmpty: _showEmpty, hideEmpty: _hideEmpty, pxToRows: _pxToRows, DEFAULT_H };

})(window);
