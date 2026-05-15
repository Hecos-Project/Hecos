/**
 * Hecos Control Room Grid Engine - Orchestrator
 * Main entry point for the modularized grid system.
 */
(function (global) {
    'use strict';

    const API = {
        ROOM: '/api/widgets/room',
    };

    let _grid = null;
    let _editing = false;
    let _editBtn = null;
    let _refreshDelayTimer = null;

    const controlRoomGrid = {
        async init(gridEl, editBtn) {
            _grid = gridEl;
            _editBtn = editBtn || null;
            if (global._roomGridSync) global._roomGridSync.init();
            await this.refresh();

            if (_editBtn) {
                _editBtn.addEventListener('click', () => this.toggleEditMode());
            }
        },

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
                if (global._roomGridRender) global._roomGridRender.render(_grid, widgets);
            } catch (err) { console.error('[RoomGrid] Refresh error:', err); }
        },

        toggleEditMode() {
            _editing = !_editing;
            if (_grid) _grid.classList.toggle('room-grid-editing', _editing);
            
            if (_editBtn) {
                const isHomeBtn = _editBtn.id === 'home-edit-btn';
                _editBtn.innerHTML = _editing
                    ? `<i class="fas fa-check"></i>${isHomeBtn ? '<span>Done</span>' : ''}`
                    : `<i class="fas fa-pen-to-square"></i>${isHomeBtn ? '<span>Edit</span>' : ''}`;
                _editBtn.title = _editing ? 'Save layout' : 'Edit layout';
                _editBtn.classList.toggle('active', _editing);
            }
            
            _grid?.querySelectorAll('.room-widget-card').forEach(c => c.draggable = _editing);
            if (!_editing && global._persistLayout) global._persistLayout();
        },

        isEditing() { return _editing; },
        persistLayout: () => global._persistLayout?.()
    };

    global.controlRoomGrid = controlRoomGrid;

})(window);
