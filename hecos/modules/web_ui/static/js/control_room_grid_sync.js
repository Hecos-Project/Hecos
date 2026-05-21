/**
 * Hecos Control Room - Sync Module
 * Handles cross-tab synchronization and local config updates.
 */
(function (global) {
    'use strict';

    let _widgetChannel = null;

    const _syncLocalConfigNoBroadcast = (widgetId, field, value) => {
        const cfg = window.cfg || (window.parent && window.parent.cfg);
        if (!cfg) return;
        if (!cfg.widgets) cfg.widgets = { per_widget: {} };
        if (!cfg.widgets.per_widget) cfg.widgets.per_widget = {};
        if (!cfg.widgets.per_widget[widgetId]) cfg.widgets.per_widget[widgetId] = {};
        cfg.widgets.per_widget[widgetId][field] = value;
    };

    const _initGlobalSync = () => {
        if (!_widgetChannel) {
            _widgetChannel = new BroadcastChannel('hecos_widgets');
            _widgetChannel.onmessage = (event) => {
                const data = event.data;
                if (!data || data.type !== 'widget_update') return;
                
                // Snappy DOM update for aesthetics if grid exists
                const grid = document.querySelector('#room-grid, #home-grid');
                if (grid) {
                    const item = grid.querySelector(`.grid-stack-item[gs-id="${data.id}"], .grid-stack-item[data-id="${data.id}"]`);
                    const card = item ? item.querySelector('.grid-stack-item-content') : null;
                    if (card) {
                        if (data.field === 'theme') {
                            const themeVal = (data.value || 'default').replace('theme-', '');
                            card.className = card.className.replace(/theme-\S+/g, '') + ' theme-' + themeVal;
                        } else if (data.field === 'bg_color') {
                            card.style.setProperty('background-color', data.value, 'important');
                        } else if (data.field === 'bg_image') {
                            const url = data.value ? `url('/media/file?path=${encodeURIComponent(data.value)}')` : 'none';
                            card.style.setProperty('background-image', url, 'important');
                            card.style.setProperty('background-size', 'cover', 'important');
                            card.style.setProperty('background-position', 'center', 'important');
                        }
                    }
                }

                // Important: Always update local cfg before potential refresh
                _syncLocalConfigNoBroadcast(data.id, data.field, data.value);

                // If structural, trigger refresh
                const isStructural = data.field === 'room_visible' || data.field === 'room_span' || data.field === 'room_order' || data.field === 'room_height';
                if (isStructural && global.controlRoomGrid) {
                    global.controlRoomGrid.debouncedRefresh();
                }
            };

            window.addEventListener('storage', (e) => {
                if (e.key === 'hecos_room_sync' && global.controlRoomGrid) {
                    global.controlRoomGrid.debouncedRefresh();
                }
            });
        }
    };

    global._roomGridSync = {
        init: _initGlobalSync,
        notify: (id, field, value, ctx) => {
            _syncLocalConfigNoBroadcast(id, field, value);
            if (_widgetChannel) {
                _widgetChannel.postMessage({ type: 'widget_update', id, field, value, ctx });
            }
        },
        syncLocal: _syncLocalConfigNoBroadcast
    };

})(window);
