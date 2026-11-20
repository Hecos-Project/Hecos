/**
 * Hecos Control Room Grid Engine — Entry Point (GridStack.js)
 * Unified multi-page engine shared by Module A (Chat) and Module B (Standalone).
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
    let _isRendering = false;        // Guard so programmatic renders never trigger persistLayout
    let _lastRenderedPageId = null;
    let _refreshSeq = 0;             // Monotonic counter to drop stale in-flight fetches
    let _context = 'sidebar';

    // ─── Cross-tab sync (runs immediately on load) ────────────────────────────
    if (global._roomGridSync) {
        global._roomGridSync.init();
    }

    function _getActivePageId() {
        if (global.controlRoomPages && typeof global.controlRoomPages.getActivePageId === 'function') {
            return global.controlRoomPages.getActivePageId();
        }
        return localStorage.getItem('hecos_room_active_page') || '';
    }

    /**
     * Standalone column count matched to Chat Control Room's 25vw column width:
     *   Chat 2x = 50vw / 2 = 25vw per column
     *   Chat 1x = 25vw / 1 = 25vw per column
     *   Standalone desktop = 100vw / 4 = 25vw per column (identical width!)
     */
    function _getStandaloneCols() {
        const w = window.innerWidth || 1440;
        if (w <= 600) return 1;
        if (w <= 900) return 2;
        if (w <= 1200) return 3;
        return 4;
    }

    const controlRoomGrid = {

        async init(gridEl, editBtn) {
            _grid    = gridEl;
            _editBtn = editBtn || null;
            _context = (_grid && _grid.id === 'home-grid') ? 'standalone' : 'sidebar';

            if (global.controlRoomPages && typeof global.controlRoomPages.init === 'function') {
                global.controlRoomPages.init();
            }

            // Core GridStack initialization logic (extracted for reuse by ResizeObserver)
            const doInitGS = () => {
                if (_gsGrid) return;
                const panel = document.getElementById('control-room-panel');
                const colCount = (_context === 'standalone')
                    ? _getStandaloneCols()
                    : (panel && panel.classList.contains('mode-1col') ? 1 : 2);
                _grid.setAttribute('gs-column', colCount);

                _gsGrid = GridStack.init({
                    column: colCount,
                    columnOpts: { breakpoints: [] }, // Responsive handled explicitly for crisp parity
                    cellHeight: 110,
                    margin: 10,
                    handle: '.room-card-drag-handle',
                    resizable: { handles: 's' },
                    draggable: { scroll: true },
                    animate: true,
                    disableResize: true,
                    disableDrag: true,
                }, _grid);

                console.log(`[RoomGrid] GridStack initialized. Width: ${_grid.offsetWidth}px Context: ${_context} Cols: ${colCount}`);
                global._gsGrid = _gsGrid;

                // Keep Standalone responsive columns synced on viewport resize
                if (_context === 'standalone') {
                    let _winResizeTimer = null;
                    window.addEventListener('resize', () => {
                        clearTimeout(_winResizeTimer);
                        _winResizeTimer = setTimeout(() => {
                            if (!_gsGrid || !_grid) return;
                            const targetCols = _getStandaloneCols();
                            if (_gsGrid.getColumn() !== targetCols) {
                                _isRendering = true;
                                try {
                                    _grid.setAttribute('gs-column', targetCols);
                                    _gsGrid.column(targetCols, 'moveScale');
                                    _gsGrid.compact();
                                } finally {
                                    setTimeout(() => { _isRendering = false; }, 120);
                                }
                            } else if (typeof _gsGrid.onParentResize === 'function') {
                                _gsGrid.onParentResize();
                            }
                        }, 140);
                    });
                }

                _gsGrid.on('change', () => {
                    if (_isRendering || !_editing) return;
                    _ignoringRefreshesUntil = Date.now() + 1500;
                    this.persistLayout();
                });

                _gsGrid.on('resizestop', (event, el) => {
                    if (_isRendering) return;
                    _ignoringRefreshesUntil = Date.now() + 2500;
                    const id = el.getAttribute('gs-id') || el.dataset.id;
                    const node = el.gridstackNode;
                    if (id && node && global._saveHeight) {
                        global._saveHeight(id, node.h);
                    }
                });

                this.refresh({ force: true });
            };

            // If the sidebar panel is closed (width < 50px), use ResizeObserver instead
            // of a setTimeout busy-wait loop to avoid continuous forced browser reflows.
            if (_context === 'sidebar' && _grid.offsetWidth < 50) {
                let _roFallback;
                const ro = new ResizeObserver((entries) => {
                    for (const entry of entries) {
                        if (entry.contentRect.width >= 50) {
                            ro.disconnect();
                            clearTimeout(_roFallback);
                            doInitGS();
                        }
                    }
                });
                ro.observe(_grid);
                _roFallback = setTimeout(() => { ro.disconnect(); doInitGS(); }, 30000);
            } else {
                doInitGS();
            }

            if (_editBtn) {
                _editBtn.addEventListener('click', () => this.toggleEditMode());
            }
        },

        getContext() { return _context; },

        getActivePageId() { return _getActivePageId(); },

        debouncedRefresh() {
            if (_refreshDelayTimer) clearTimeout(_refreshDelayTimer);
            _refreshDelayTimer = setTimeout(() => { this.refresh(); }, 300);
        },

        async refresh(opts = {}) {
            if (!_grid || !_gsGrid) return;
            const force = Boolean(opts && opts.force);
            if (!force && Date.now() < _ignoringRefreshesUntil) {
                console.log('[RoomGrid] Refresh skipped (lock active)');
                return;
            }
            if (force && _refreshDelayTimer) {
                clearTimeout(_refreshDelayTimer);
                _refreshDelayTimer = null;
            }
            const seq = ++_refreshSeq;
            const reqPageId = (opts && opts.pageId) ? opts.pageId : _getActivePageId();
            const qs = new URLSearchParams({
                t: String(Date.now()),
                context: _context,
            });
            if (reqPageId) qs.set('page_id', reqPageId);

            try {
                const resp = await fetch(`${API.ROOM}?${qs.toString()}`);
                const data = await resp.json();
                if (seq !== _refreshSeq) return; // Stale response superseded by newer switch/refresh
                if (!data.ok) throw new Error(data.error || 'API error');

                if (global.controlRoomPages && Array.isArray(data.pages)) {
                    global.controlRoomPages.syncFromServer(
                        data.pages,
                        data.active_page_id,
                        data.available_widgets
                    );
                }

                const resolvedPageId = data.active_page_id || reqPageId || 'main';
                const activePageObj = Array.isArray(data.pages)
                    ? data.pages.find(p => p.id === resolvedPageId)
                    : null;
                const pageSwitched = (_lastRenderedPageId !== null && _lastRenderedPageId !== resolvedPageId);
                _lastRenderedPageId = resolvedPageId;

                const widgets = Array.isArray(data.widgets) ? data.widgets : [];
                console.log(`[RoomGrid] [${_context}] Page="${resolvedPageId}" Widgets:`, widgets.length);

                _isRendering = true;
                try {
                    if (widgets.length === 0) {
                        if (global._roomGridRender && typeof global._roomGridRender.clear === 'function') {
                            global._roomGridRender.clear(_grid, _gsGrid);
                        } else {
                            _gsGrid.removeAll(true, false);
                        }
                        if (global._roomGridRender) {
                            global._roomGridRender.showEmpty(_grid, activePageObj);
                        }
                    } else {
                        if (global._roomGridRender) {
                            global._roomGridRender.hideEmpty(_grid);
                            global._roomGridRender.render(_grid, widgets, _gsGrid, {
                                resetLayout: pageSwitched,
                            });
                        }
                    }
                    // Preserve edit mode drag/resize capabilities after page switches
                    _gsGrid.enableMove(_editing);
                    _gsGrid.enableResize(_editing);
                } finally {
                    // Release render guard after GridStack's synchronous/microtask change hooks settle
                    setTimeout(() => { _isRendering = false; }, 120);
                }
            } catch (err) {
                _isRendering = false;
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
            if (global.controlRoomPages && typeof global.controlRoomPages.setEditMode === 'function') {
                global.controlRoomPages.setEditMode(_editing);
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

        /**
         * Block automatic refreshes for `ms` milliseconds.
         * Call before any aesthetic save to prevent SSE-triggered re-renders
         * from overwriting live UI changes.
         */
        lockRefresh(ms = 5000) {
            _ignoringRefreshesUntil = Date.now() + ms;
            console.log(`[RoomGrid] Refresh locked for ${ms}ms`);
        },

        persistLayout() {
            if (!_gsGrid || _isRendering) return;
            clearTimeout(_saveTimer);
            _saveTimer = setTimeout(async () => {
                if (!_gsGrid || _isRendering) return;
                const pageId = _getActivePageId();
                // Sort visually top-to-bottom, left-to-right using GridStack coordinates
                const sortedItems = _gsGrid.getGridItems().slice().sort((a, b) => {
                    const na = a.gridstackNode || { y: 0, x: 0 };
                    const nb = b.gridstackNode || { y: 0, x: 0 };
                    return (na.y - nb.y) || (na.x - nb.x);
                });
                const layout = sortedItems.map(el => el.getAttribute('gs-id') || el.dataset.id).filter(Boolean);
                try {
                    const resp = await fetch(`${API.LAYOUT}?context=${_context}`, {
                        method: 'PATCH',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ layout, page_id: pageId })
                    });
                    if (resp.ok) {
                        console.log(`[RoomGrid] [${_context}] Layout saved for page "${pageId}":`, layout);
                        if (global._roomGridSync && typeof global._roomGridSync.notifyPagesChanged === 'function') {
                            global._roomGridSync.notifyPagesChanged('layout', { pageId, layout });
                        }
                    }
                } catch (err) { console.warn('[RoomGrid] Layout save failed:', err); }
            }, 400);
        }
    };

    global.controlRoomGrid = controlRoomGrid;

})(window);
