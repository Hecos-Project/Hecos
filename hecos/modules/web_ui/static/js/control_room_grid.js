/**
 * Hecos Control Room Grid Engine — Entry Point
 *
 * This file is the public orchestrator. All logic lives in the sub-modules:
 *  - control_room_grid_sync.js   → BroadcastChannel & local config sync
 *  - control_room_grid_drag.js   → Mouse & touch drag-and-drop
 *  - control_room_grid_render.js → Card generation & DOM rendering
 *  - control_room_grid_actions.js→ Span, remove, resize helpers
 *  - control_room_grid_aes.js    → Aesthetic picker integration
 *
 * Usage: controlRoomGrid.init(gridEl, editBtn)
 *
 * Sub-modules MUST be loaded before this file via index.html.
 */
(function (global) {
    'use strict';

    const API = {
        ROOM:   '/api/widgets/room',
        LAYOUT: '/api/widgets/room/layout',
    };

    // ─── State ────────────────────────────────────────────────────────────────
    let _grid = null;
    let _editing = false;
    let _editBtn = null;
    let _saveTimer = null;
    let _refreshDelayTimer = null;

    // ─── Initialize cross-tab sync (runs immediately on load) ─────────────────
    if (global._roomGridSync) {
        global._roomGridSync.init();
    }

    // ─── Public API ───────────────────────────────────────────────────────────
    const controlRoomGrid = {

        async init(gridEl, editBtn) {
            _grid = gridEl;
            _editBtn = editBtn || null;
            await this.refresh();

            if (_editBtn) {
                _editBtn.addEventListener('click', () => this.toggleEditMode());
            }
        },

        /**
         * Refreshes immediately, then again after 2s to catch backend latency.
         */
        debouncedRefresh() {
            this.refresh();
            if (_refreshDelayTimer) clearTimeout(_refreshDelayTimer);
            _refreshDelayTimer = setTimeout(() => this.refresh(), 2000);
        },

        async refresh() {
            if (!_grid) return;
            try {
                const resp = await fetch(`${API.ROOM}?t=${Date.now()}`);
                const data = await resp.json();
                if (!data.ok) throw new Error(data.error || 'API error');

                const widgets = Array.isArray(data.widgets) ? data.widgets : [];
                console.log('[RoomGrid] Widgets to render:', widgets.length);

                if (global._roomGridRender) {
                    global._roomGridRender.render(_grid, widgets);
                }

            } catch (err) {
                console.error('[RoomGrid] Refresh error:', err);
            }
        },

        toggleEditMode() {
            _editing = !_editing;
            if (_grid) {
                _grid.classList.toggle('room-grid-editing', _editing);
                _grid.querySelectorAll('.room-widget-card').forEach(c => {
                    c.draggable = _editing;
                });
            }

            if (_editBtn) {
                const isHomeBtn = _editBtn.id === 'home-edit-btn';
                if (isHomeBtn) {
                    _editBtn.innerHTML = _editing
                        ? '<i class="fas fa-check"></i><span>Done</span>'
                        : '<i class="fas fa-pen-to-square"></i><span>Edit</span>';
                } else {
                    _editBtn.innerHTML = _editing
                        ? '<i class="fas fa-check"></i>'
                        : '<i class="fas fa-pen-to-square"></i>';
                }
                _editBtn.title = _editing ? 'Save layout' : 'Edit layout';
                _editBtn.classList.toggle('active', _editing);
            }

            if (!_editing) this.persistLayout();
        },

        isEditing() { return _editing; },

        persistLayout() {
            if (!_grid) return;
            clearTimeout(_saveTimer);
            _saveTimer = setTimeout(async () => {
                const layout = [..._grid.querySelectorAll('.room-widget-card')].map(c => c.dataset.id);
                try {
                    await fetch(API.LAYOUT, {
                        method: 'PATCH',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({layout})
                    });
                    console.log('[RoomGrid] Layout saved:', layout);
                } catch (err) {
                    console.warn('[RoomGrid] Layout save failed:', err);
                }
            }, 400);
        },
    };

    global.controlRoomGrid = controlRoomGrid;

})(window);
