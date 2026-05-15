/**
 * Hecos Control Room - Render Module
 * Handles dynamic grid rendering and card generation.
 */
(function (global) {
    'use strict';

    const API = {
        FRAME: (id) => `/api/widgets/room/${id}/frame`,
    };

    const _render = (grid, widgets) => {
        if (!grid) return;
        const stable = [...grid.children].filter(c =>
            c.classList.contains('room-empty-state') ||
            c.classList.contains('room-loading') ||
            c.id === 'room-add-btn'
        );

        [...grid.children].forEach(c => {
            if (!stable.includes(c)) c.remove();
        });

        if (widgets.length === 0) {
            _showEmpty(grid);
        } else {
            _hideEmpty(grid);
            widgets.forEach(w => {
                const card = _makeCard(grid, w);
                grid.insertBefore(card, stable[0] || null);
            });
        }
        _ensureAddBtn(grid);
    };

    const _makeCard = (grid, w) => {
        const card = document.createElement('div');
        const themeVal = (w.theme || 'default').replace('theme-', '');
        card.className = `room-widget-card border-glow${w.room_span === 2 ? ' span-2' : ''} theme-${themeVal}`;
        if (w.room_height) card.style.minHeight = w.room_height + 'px';
        card.dataset.id = w.extension_id;
        card.dataset.span = w.room_span || 1;

        card.innerHTML = `
            <div class="room-card-chrome">
                <span class="room-card-drag-handle" title="Drag to reorder"><i class="fas fa-grip-vertical"></i></span>
                <button class="room-card-span-btn ${w.room_span === 2 ? 'active' : ''}"
                        onclick="event.stopPropagation(); _roomGridToggleSpan('${w.extension_id}', this)">
                    ${w.room_span === 2 ? '<i class="fas fa-compress-alt"></i> 2×' : '<i class="fas fa-expand-alt"></i> 1×'}
                </button>
                <button class="room-card-aes-btn" onclick="event.stopPropagation(); _roomGridOpenAes(event, '${w.extension_id}', this)">
                    <i class="fas fa-magic"></i>
                </button>
                <button class="room-card-remove-btn" onclick="event.stopPropagation(); _roomGridRemoveWidget('${w.extension_id}')">
                    <i class="fas fa-times"></i>
                </button>
            </div>
            <iframe src="${API.FRAME(w.extension_id)}?t=${Date.now()}" class="room-widget-iframe" loading="lazy" scrolling="no" frameborder="0" allowtransparency="true"></iframe>
            <div class="room-card-resize-handle" title="Resize" onmousedown="event.stopPropagation(); _roomGridStartResize(event, '${w.extension_id}')" ontouchstart="event.stopPropagation(); _roomGridStartResize(event, '${w.extension_id}')" ondblclick="event.stopPropagation(); _roomGridResetHeight('${w.extension_id}')">
                 <div class="drag-line"></div>
            </div>
        `;

        if (global._roomGridDrag) {
            global._roomGridDrag.bindEvents(card, grid);
        }

        return card;
    };

    const _showEmpty = (grid) => {
        let el = grid.querySelector('.room-empty-state');
        if (!el) {
            el = document.createElement('div');
            el.className = 'room-empty-state';
            el.innerHTML = `<i class="fas fa-th-large"></i><p>La Control Room è vuota.</p>`;
            grid.appendChild(el);
        }
        el.style.display = '';
    };

    const _hideEmpty = (grid) => {
        let el = grid.querySelector('.room-empty-state');
        if (el) el.style.display = 'none';
    };

    const _ensureAddBtn = (grid) => {
        if (grid.querySelector('#room-add-btn')) return;
        const btn = document.createElement('div');
        btn.id = 'room-add-btn'; btn.className = 'room-add-btn'; btn.innerHTML = `<i class="fas fa-plus"></i>`;
        btn.onclick = () => window.hecosOpenConfig ? window.hecosOpenConfig('#widgets') : window.open('/hecos/config/ui#widgets', '_blank');
        grid.appendChild(btn);
    };

    global._roomGridRender = {
        render: _render,
        showEmpty: _showEmpty,
        hideEmpty: _hideEmpty
    };

})(window);
