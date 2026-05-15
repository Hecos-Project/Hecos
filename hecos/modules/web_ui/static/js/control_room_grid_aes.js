/**
 * Hecos Control Room - Aesthetic Module
 * Connects HecosAestheticPicker to room widgets.
 */
(function (global) {
    'use strict';

    global._roomGridOpenAes = function(e, id, btn) {
        if (!global.controlRoomGrid?.isEditing()) return;
        const card = document.querySelector(`.room-widget-card[data-id="${id}"]`);
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
        card.appendChild(popover);
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
        const prefs = cfg?.widgets?.per_widget?.[id] || {};

        if (typeof HecosAestheticPicker !== 'undefined') {
            new HecosAestheticPicker(popover, {
                showStyle: true,
                initialStyle: prefs.theme || 'default',
                initialColor: prefs.bg_color || '',
                initialImage: prefs.bg_image || '',
                onStyleChange: async (style) => {
                    card.className = card.className.replace(/theme-\S+/g, '') + ' theme-' + style.replace('theme-', '');
                    if (global._roomGridSync) global._roomGridSync.notify(id, 'theme', style);
                    _saveSingleAes(id, 'theme', style);
                },
                onColorLive: (hex) => card.style.backgroundColor = hex,
                onColorChange: async (hex) => {
                    card.style.backgroundColor = hex;
                    if (global._roomGridSync) global._roomGridSync.notify(id, 'bg_color', hex);
                    _saveBulkAes(id, hex, prefs.bg_image);
                },
                onImageChange: async (path) => {
                    card.style.backgroundImage = `url('/media/file?path=${encodeURIComponent(path)}')`;
                    card.style.backgroundSize = 'cover'; card.style.backgroundPosition = 'center';
                    if (global._roomGridSync) global._roomGridSync.notify(id, 'bg_image', path);
                    _saveBulkAes(id, prefs.bg_color, path);
                },
                onClearImage: async () => {
                    card.style.backgroundImage = 'none';
                    if (global._roomGridSync) global._roomGridSync.notify(id, 'bg_image', '');
                    _saveBulkAes(id, prefs.bg_color, '');
                },
                onReset: async () => {
                    try {
                        const resp = await fetch(`/api/widgets/${id}/aesthetics/reset`, { method: 'POST' });
                        if (resp.ok) {
                            card.style.backgroundColor = ''; card.style.backgroundImage = '';
                            card.className = card.className.replace(/theme-\S+/g, '') + ' theme-default';
                            if (global._roomGridSync) {
                                global._roomGridSync.notify(id, 'theme', 'default');
                                global._roomGridSync.notify(id, 'bg_color', null);
                                global._roomGridSync.notify(id, 'bg_image', null);
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
