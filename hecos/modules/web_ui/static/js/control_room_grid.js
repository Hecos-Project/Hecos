/**
 * Hecos Control Room Grid Engine — Entry Point (GridStack.js)
 */
(function (global) {
    'use strict';

    const API = {
        ROOM:    '/api/widgets/room',
        LAYOUT:  '/api/widgets/room/layout',
        HEIGHT:  (id) => `/api/widgets/${id}/room_height`,
    };

    let _grid    = null;
    let _gsGrid  = null;
    let _editing = false;
    let _editBtn = null;
    let _saveTimer = null;
    let _refreshDelayTimer = null;
    let _ignoringRefreshesUntil = 0; // Lock to prevent race conditions during save
    let _context = 'sidebar';

    // ─── Cross-tab sync (runs immediately on load) ────────────────────────────
    if (global._roomGridSync) {
        global._roomGridSync.init();
    }

    const controlRoomGrid = {

        async init(gridEl, editBtn) {
            _grid   = gridEl;
            _editBtn = editBtn || null;
            _context = (_grid && _grid.id === 'home-grid') ? 'standalone' : 'sidebar';

            const initGS = (widthCheck = true) => {
                const w = _grid.offsetWidth;
                if (widthCheck && _context === 'sidebar' && w < 50) {
                    console.log(`[RoomGrid] Waiting for width... (Current: ${w}px)`);
                    setTimeout(() => initGS(), 250);
                    return;
                }

                const colCount = (_context === 'standalone' ? 6 : 2);
                _grid.setAttribute('gs-column', colCount);

                _gsGrid = GridStack.init({
                    column: colCount,
                    columnOpts: { breakpoints: [] }, // Important for sidebars
                    cellHeight: 110,
                    margin: 10,
                    handle: '.room-card-drag-handle',
                    resizable: { handles: 's' },
                    draggable: { scroll: true },
                    animate: true,
                    disableResize: true,
                    disableDrag: true,
                }, _grid);

                console.log(`[RoomGrid] GridStack initialized. Width: ${_grid.offsetWidth}px Context: ${_context}`);
                global._gsGrid = _gsGrid;

                _gsGrid.on('change', () => {
                    _ignoringRefreshesUntil = Date.now() + 1500;
                    this.persistLayout();
                });

                _gsGrid.on('resizestop', (event, el) => {
                    _ignoringRefreshesUntil = Date.now() + 2500;
                    const id = el.getAttribute('gs-id') || el.dataset.id;
                    const node = el.gridstackNode;
                    if (id && node && global._saveHeight) {
                        global._saveHeight(id, node.h);
                    }
                });

                this.refresh();
            };

            initGS();

            if (_editBtn) {
                _editBtn.addEventListener('click', () => this.toggleEditMode());
            }
        },

        getContext() { return _context; },

        debouncedRefresh() {
            if (_refreshDelayTimer) clearTimeout(_refreshDelayTimer);
            _refreshDelayTimer = setTimeout(() => { this.refresh(); }, 300);
        },

        async refresh() {
            if (!_grid || !_gsGrid) return;
            if (Date.now() < _ignoringRefreshesUntil) {
                console.log('[RoomGrid] Refresh skipped (lock active)');
                return;
            }
            try {
                const resp = await fetch(`${API.ROOM}?t=${Date.now()}&context=${_context}`);
                const data = await resp.json();
                if (!data.ok) throw new Error(data.error || 'API error');

                const widgets = Array.isArray(data.widgets) ? data.widgets : [];
                console.log(`[RoomGrid] [${_context}] Refreshing. Widgets:`, widgets.length);

                if (widgets.length === 0) {
                    _gsGrid.removeAll();
                    if (global._roomGridRender) global._roomGridRender.showEmpty(_grid);
                } else {
                    if (global._roomGridRender) {
                        global._roomGridRender.hideEmpty(_grid);
                        global._roomGridRender.render(_grid, widgets, _gsGrid);
                    }
                }
            } catch (err) {
                console.error('[RoomGrid] Refresh error:', err);
            }
        },

        toggleEditMode() {
            _editing = !_editing;
            if (_gsGrid) {
                _gsGrid.enableMove(_editing);
                _gsGrid.enableResize(_editing);
            }
            if (_grid) {
                _grid.classList.toggle('room-grid-editing', _editing);
            }
            if (_editBtn) {
                const isHomeBtn = _editBtn.id === 'home-edit-btn';
                _editBtn.innerHTML = _editing
                    ? (isHomeBtn ? '<i class="fas fa-check"></i><span>Done</span>' : '<i class="fas fa-check"></i>')
                    : (isHomeBtn ? '<i class="fas fa-pen-to-square"></i><span>Edit</span>' : '<i class="fas fa-pen-to-square"></i>');
                _editBtn.title = _editing ? 'Save layout' : 'Edit layout';
                _editBtn.classList.toggle('active', _editing);
            }
            if (!_editing) this.persistLayout();
        },

        isEditing() { return _editing; },

        persistLayout() {
            if (!_gsGrid) return;
            clearTimeout(_saveTimer);
            _saveTimer = setTimeout(async () => {
                const layout = _gsGrid.getGridItems().map(el => el.getAttribute('gs-id') || el.dataset.id).filter(Boolean);
                try {
                    await fetch(`${API.LAYOUT}?context=${_context}`, {
                        method: 'PATCH',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({ layout })
                    });
                    console.log(`[RoomGrid] [${_context}] Layout saved:`, layout);
                } catch (err) { console.warn('[RoomGrid] Layout save failed:', err); }
            }, 400);
        }
    };

    global.controlRoomGrid = controlRoomGrid;

})(window);
