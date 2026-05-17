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
                if (!data) return;
                
                const isStructural = data.field === 'visible' || data.field === 'order' || !['theme','bg_color','bg_image'].includes(data.field);
                const myCtx = global.controlRoomGrid ? global.controlRoomGrid.getContext() : 'sidebar';
                if (isStructural && data.ctx && data.ctx !== myCtx) {
                     return; // Skip structural updates from other contexts
                }
                
                // Update local window.cfg immediately
                _syncLocalConfigNoBroadcast(data.id, data.field, data.value);

                // Snappy DOM update for aesthetics if grid exists
                const grid = document.querySelector('#room-grid, #home-grid');
                const card = grid?.querySelector(`.room-widget-card[data-id="${data.id}"]`);
                if (card) {
                    if (data.field === 'theme') {
                        const themeVal = (data.value || 'default').replace('theme-', '');
                        card.className = card.className.replace(/theme-\S+/g, '') + ' theme-' + themeVal;
                    } else if (data.field === 'bg_color') {
                        card.style.backgroundColor = data.value;
                    } else if (data.field === 'bg_image') {
                        card.style.backgroundImage = data.value ? `url('/media/file?path=${encodeURIComponent(data.value)}')` : 'none';
                        card.style.backgroundSize = 'cover';
                        card.style.backgroundPosition = 'center';
                    }
                }

                // If it's a structural change, refresh
                if (isStructural) {
                    if (global.controlRoomGrid) global.controlRoomGrid.debouncedRefresh();
                }
            };
            window.addEventListener('storage', (e) => {
                if (e.key === 'hecos_room_sync') {
                    if (global.controlRoomGrid) global.controlRoomGrid.debouncedRefresh();
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
