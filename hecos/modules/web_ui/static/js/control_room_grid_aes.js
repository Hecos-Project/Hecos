/**
 * Hecos Control Room - Aesthetic Module
 * Connects HecosAestheticPicker to room widgets.
 */
(function (global) {
    'use strict';

    global._roomGridOpenAes = function(e, id, btn) {
        if (!global.controlRoomGrid?.isEditing()) return;
        const item = document.querySelector(`.grid-stack-item[gs-id="${id}"], .grid-stack-item[data-id="${id}"]`);
        const card = item ? item.querySelector('.grid-stack-item-content') : null;
        if (!card) return;

        if (btn._popover) {
            btn._popover.remove(); btn._popover = null;
            btn.classList.remove('active'); card.classList.remove('aes-active');
            return;
        }

        document.querySelectorAll('.room-card-aes-popover').forEach(p => p.remove());
        document.querySelectorAll('.room-card-aes-btn.active').forEach(b => { b.classList.remove('active'); b._popover = null; });
        document.querySelectorAll('.room-widget-card.aes-active').forEach(c => c.classList.remove('aes-active'));

        const popover = document.createElement('div');
        popover.className = 'room-card-aes-popover';
        document.body.appendChild(popover); // Append to body to avoid overflow clipping
        
        // Dynamic positioning from button
        const rect = btn.getBoundingClientRect();
        popover.style.position = 'fixed'; // Use fixed for absolute top/left relative to viewport
        popover.style.top = (rect.bottom + 8) + 'px';
        popover.style.left = Math.min(window.innerWidth - 220, rect.left - 180) + 'px';

        card.classList.add('aes-active');
        btn._popover = popover;
        btn.classList.add('active');

        const closeHandler = (ev) => {
            if (!popover.contains(ev.target) && ev.target !== btn && !btn.contains(ev.target)) {
                popover.remove(); btn._popover = null;
                btn.classList.remove('active'); card.classList.remove('aes-active');
                document.removeEventListener('mousedown', closeHandler);
            }
        };
        setTimeout(() => document.addEventListener('mousedown', closeHandler), 10);

        const cfg = window.cfg || (window.parent && window.parent.cfg);
        const initialPrefs = cfg?.widgets?.per_widget?.[id] || {};
        const currentAes = {
            color: initialPrefs.bg_color || '',
            image: initialPrefs.bg_image || ''
        };

        if (typeof HecosAestheticPicker !== 'undefined') {
            new HecosAestheticPicker(popover, {
                showStyle: true,
                initialStyle: initialPrefs.theme || 'default',
                initialColor: initialPrefs.bg_color || '',
                initialImage: initialPrefs.bg_image || '',
                onStyleChange: async (style) => {
                    card.className = card.className.replace(/theme-\S+/g, '') + ' theme-' + style.replace('theme-', '');
                    if (global.controlRoomGrid) global.controlRoomGrid.lockRefresh(5000);
                    if (global._roomGridSync) global._roomGridSync.notify(id, 'theme', style);
                    _saveSingleAes(id, 'theme', style);
                },
                onColorLive: (hex) => card.style.setProperty('background-color', hex, 'important'),
                onColorChange: async (hex) => {
                    currentAes.color = hex;
                    card.style.setProperty('background-color', hex, 'important');
                    if (global.controlRoomGrid) global.controlRoomGrid.lockRefresh(5000);
                    if (global._roomGridSync) global._roomGridSync.notify(id, 'bg_color', hex);
                    _saveBulkAes(id, currentAes.color, currentAes.image);
                },
                onImageChange: async (path) => {
                    currentAes.image = path;
                    const url = `url('/media/file?path=${encodeURIComponent(path)}')`;
                    card.style.setProperty('background-image', url, 'important');
                    card.style.setProperty('background-size', 'cover', 'important'); 
                    card.style.setProperty('background-position', 'center', 'important');
                    if (global.controlRoomGrid) global.controlRoomGrid.lockRefresh(5000);
                    if (global._roomGridSync) global._roomGridSync.notify(id, 'bg_image', path);
                    _saveBulkAes(id, currentAes.color, currentAes.image);
                },
                onClearImage: async () => {
                    currentAes.image = '';
                    card.style.removeProperty('background-image');
                    if (global.controlRoomGrid) global.controlRoomGrid.lockRefresh(5000);
                    if (global._roomGridSync) global._roomGridSync.notify(id, 'bg_image', '');
                    _saveBulkAes(id, currentAes.color, '');
                },
                onReset: async () => {
                    try {
                        const resp = await fetch(`/api/widgets/${id}/aesthetics/reset`, { method: 'POST' });
                        if (resp.ok) {
                            card.style.removeProperty('background-color');
                            card.style.removeProperty('background-image');
                            card.style.removeProperty('background-size');
                            card.style.removeProperty('background-position');
                            card.className = card.className.replace(/theme-\S+/g, '') + ' theme-default';
                            if (global._roomGridSync) {
                                global._roomGridSync.notify(id, 'theme', 'default');
                                global._roomGridSync.notify(id, 'bg_color', '');
                                global._roomGridSync.notify(id, 'bg_image', '');
                            }
                            popover.remove(); btn._popover = null;
                            btn.classList.remove('active'); card.classList.remove('aes-active');
                        }
                    } catch (err) { console.warn('[RoomGrid] reset err:', err); }
                }
            });
        }
    };

    async function _saveSingleAes(id, field, val) {
         fetch(`/api/widgets/${id}/${field}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ [field]: val }) }).catch(() => {});
    }

    async function _saveBulkAes(id, color, image) {
         fetch(`/api/widgets/${id}/aesthetics`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ bg_color: color, bg_image: image }) }).catch(() => {});
    }

})(window);
