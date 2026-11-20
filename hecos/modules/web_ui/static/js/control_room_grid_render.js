/**
 * Hecos Control Room - Render Module (GridStack.js v10)
 */
(function (global) {
    'use strict';

    const FRAME_URL = (id) => `/api/widgets/room/${id}/frame`;
    const DEFAULT_H = 3;

    function _pxToRows(px) {
        if (!px) return DEFAULT_H;
        return Math.max(1, Math.ceil((px - 5) / 110));
    }

    function _tr(key, fallback) {
        if (typeof global.t === 'function') {
            const val = global.t(key);
            if (val && val !== key) return val;
        }
        return fallback;
    }

    function _esc(str) {
        return String(str == null ? '' : str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    function _getVisualOrder(gsGrid) {
        return gsGrid.getGridItems().slice().sort((a, b) => {
            const na = a.gridstackNode || { y: 0, x: 0 };
            const nb = b.gridstackNode || { y: 0, x: 0 };
            return (na.y - nb.y) || (na.x - nb.x);
        }).map(el => el.getAttribute('gs-id') || el.dataset.id).filter(Boolean);
    }

    /**
     * Safely clears ALL widgets from GridStack AND DOM.
     * IMPORTANT: In GridStack v10, removeAll() relies on engine._notify() to
     * remove DOM elements, which is a NO-OP while batchUpdate(true) is active!
     * Always clear OUTSIDE batchUpdate and defensively remove any stray DOM items.
     */
    const _clear = (grid, gsGrid) => {
        if (gsGrid) {
            gsGrid.removeAll(true, false);
        }
        if (grid) {
            grid.querySelectorAll(':scope > .grid-stack-item').forEach(el => el.remove());
        }
    };

    const _render = (grid, widgets, gsGrid, opts = {}) => {
        if (!grid || !gsGrid) return;

        // Context-aware column count
        const currentCols = gsGrid.getColumn();
        const resetLayout = Boolean(opts && opts.resetLayout);

        const newOrder = widgets.map(w => w.extension_id);
        const existingOrder = _getVisualOrder(gsGrid);
        const orderChanged = existingOrder.length > 0
            && (existingOrder.length === newOrder.length)
            && existingOrder.some((id, idx) => id !== newOrder[idx]);

        console.log(`[RoomGrid] Render Start. Context: ${currentCols} cols. Widgets: ${widgets.length} Reset: ${resetLayout} Reorder: ${orderChanged}`);

        // 1. Perform removals OUTSIDE batchUpdate so GridStack v10 actually deletes DOM nodes
        if (resetLayout || orderChanged) {
            _clear(grid, gsGrid);
        } else {
            const newIds = new Set(newOrder);
            gsGrid.getGridItems().forEach(el => {
                const id = el.getAttribute('gs-id') || el.dataset.id;
                if (!id || !newIds.has(id)) {
                    gsGrid.removeWidget(el, true, false);
                }
            });
            // Sweep any orphaned DOM items not tracked by GridStack
            grid.querySelectorAll(':scope > .grid-stack-item').forEach(el => {
                const id = el.getAttribute('gs-id') || el.dataset.id;
                if (!id || !newIds.has(id) || !el.gridstackNode) {
                    el.remove();
                }
            });
        }

        const movePageTitle = _tr('room_page_move_widget', 'Move or copy to another page');
        const removeTitle = _tr('room_page_remove_from_page', 'Remove from this page');

        // 2. Add or Update inside batchUpdate for smooth packing
        gsGrid.batchUpdate(true);
        try {
            widgets.forEach(w => {
                const id = w.extension_id;
                const gsW = (w.room_span === 2 && currentCols > 1) ? 2 : 1;
                const gsH = _pxToRows(w.room_height);
                const theme = (w.theme || 'default').replace('theme-', '');

                let el = gsGrid.getGridItems().find(item => (item.getAttribute('gs-id') === id || item.dataset.id === id));

                const contentHtml = `
                    <div class="room-card-chrome">
                        <span class="room-card-drag-handle" title="Drag to reorder"><i class="fas fa-grip-vertical"></i></span>
                        <button class="room-card-span-btn ${w.room_span === 2 ? 'active' : ''}"
                                title="${w.room_span === 2 ? 'Switch to 1× width' : 'Expand to 2× width'}"
                                onclick="event.stopPropagation(); _roomGridToggleSpan('${_esc(id)}', this)">
                            ${w.room_span === 2 ? '<i class="fas fa-compress-alt"></i> 2\u00d7' : '<i class="fas fa-expand-alt"></i> 1\u00d7'}
                        </button>
                        <button class="room-card-page-btn"
                                title="${_esc(movePageTitle)}"
                                onclick="event.stopPropagation(); _roomGridOpenPageMenu(event, '${_esc(id)}', this)">
                            <i class="fas fa-arrow-right-arrow-left"></i>
                        </button>
                        <button class="room-card-aes-btn"
                                title="Customize appearance"
                                onclick="event.stopPropagation(); _roomGridOpenAes(event, '${_esc(id)}', this)">
                            <i class="fas fa-magic"></i>
                        </button>
                        <button class="room-card-remove-btn"
                                title="${_esc(removeTitle)}"
                                onclick="event.stopPropagation(); _roomGridRemoveWidget('${_esc(id)}')">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>
                    <iframe src="${FRAME_URL(id)}?t=${Date.now()}"
                            class="room-widget-iframe" loading="lazy" scrolling="no"
                            frameborder="0" allowtransparency="true"
                            allow="camera; microphone; display-capture; autoplay; clipboard-write; fullscreen"></iframe>
                `;

                const applyStyles = (node) => {
                    if (!node) return;
                    const baseClasses = 'grid-stack-item-content room-widget-card border-glow';
                    const isAesActive = node.classList.contains('aes-active') ? ' aes-active' : '';
                    node.className = `${baseClasses} theme-${theme}${isAesActive}`;

                    if (w.bg_color) {
                        node.style.setProperty('background-color', w.bg_color, 'important');
                    } else {
                        node.style.removeProperty('background-color');
                    }

                    if (w.bg_image) {
                        const url = `url('/media/file?path=${encodeURIComponent(w.bg_image)}')`;
                        node.style.setProperty('background-image', url, 'important');
                        node.style.setProperty('background-size', 'cover', 'important');
                        node.style.setProperty('background-position', 'center', 'important');
                    } else {
                        node.style.removeProperty('background-image');
                    }
                };

                if (el) {
                    const node = el.gridstackNode;
                    if (node && (node.w !== gsW || node.h !== gsH)) {
                        gsGrid.update(el, { w: gsW, h: gsH });
                    }
                    const spanBtn = el.querySelector('.room-card-span-btn');
                    if (spanBtn) {
                        spanBtn.classList.toggle('active', w.room_span === 2);
                        spanBtn.innerHTML = w.room_span === 2
                            ? '<i class="fas fa-compress-alt"></i> 2\u00d7'
                            : '<i class="fas fa-expand-alt"></i> 1\u00d7';
                    }
                    applyStyles(el.querySelector('.grid-stack-item-content'));
                } else {
                    const newEl = gsGrid.addWidget({
                        id: id,
                        w: gsW,
                        h: gsH,
                        autoPosition: true,
                        content: contentHtml
                    });

                    if (newEl) {
                        newEl.setAttribute('data-id', id);
                        applyStyles(newEl.querySelector('.grid-stack-item-content'));
                    }
                }
            });

            gsGrid.column(currentCols, 'none');
            gsGrid.compact();
        } finally {
            gsGrid.batchUpdate(false);
        }
    };

    const _showEmpty = (grid, pageInfo) => {
        if (grid) {
            grid.style.flex = '0 0 0px';
            grid.style.minHeight = '0px';
            grid.style.height = '0px';
            grid.style.padding = '0';
            grid.style.overflow = 'hidden';
        }
        let el = document.getElementById('room-empty-state');
        if (!el) {
            el = document.createElement('div');
            el.id = 'room-empty-state';
            el.className = 'room-empty-state';
            grid.insertAdjacentElement('afterend', el);
        }
        const icon = (pageInfo && typeof pageInfo.icon === 'string' && /^fa-[a-z0-9-]+$/.test(pageInfo.icon))
            ? pageInfo.icon
            : 'fa-th-large';
        const emptyTitle = _tr('room_page_empty_title', 'No widgets on this page yet');
        const ctaLabel = _tr('room_page_empty_cta', 'Add Widgets');
        const subtitle = pageInfo && pageInfo.name
            ? `${_esc(emptyTitle)} — <strong>${_esc(pageInfo.name)}</strong>`
            : _esc(emptyTitle);

        el.innerHTML = `
            <i class="fas ${icon}"></i>
            <p>${subtitle}</p>
            <button type="button" class="cr-empty-add-btn" id="cr-empty-add-btn">
                <i class="fas fa-plus"></i>
                <span>${_esc(ctaLabel)}</span>
            </button>
        `;
        const ctaBtn = el.querySelector('#cr-empty-add-btn');
        if (ctaBtn) {
            ctaBtn.addEventListener('click', () => {
                if (global.controlRoomPages && typeof global.controlRoomPages.openWidgetPickerModal === 'function') {
                    global.controlRoomPages.openWidgetPickerModal();
                } else if (typeof global.hecosOpenConfig === 'function') {
                    global.hecosOpenConfig('#widgets');
                }
            });
        }
        el.style.flex = '1';
        el.style.display = 'flex';
    };

    const _hideEmpty = (grid) => {
        if (grid) {
            grid.style.flex = '';
            grid.style.minHeight = '';
            grid.style.height = '';
            grid.style.padding = '';
            grid.style.overflow = '';
        }
        const el = document.getElementById('room-empty-state');
        if (el) el.style.display = 'none';
    };

    global._roomGridRender = { render: _render, clear: _clear, showEmpty: _showEmpty, hideEmpty: _hideEmpty, pxToRows: _pxToRows, DEFAULT_H };

})(window);
