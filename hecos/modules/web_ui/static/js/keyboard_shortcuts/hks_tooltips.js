/**
 * hks_tooltips.js — Hecos Dynamic Shortcut Tooltips
 * -----------------------------------------------------------------------------
 * Reads current keyboard bindings from HKS_BINDINGS and applies them as
 * descriptive 	itle attributes on all relevant UI buttons and links.
 * When the user remaps a shortcut, calling applyShortcutTooltips() again
 * will update all titles instantly.
 *
 * Auto-refresh: called on DOMContentLoaded + after every HKS_BINDINGS.save()
 * -----------------------------------------------------------------------------
 */

(function () {
    'use strict';

    function _fmtCombo(combo) {
        if (!combo) return null;
        const parts = combo.split('+').map(k => {
            const map = {
                ctrl: 'Ctrl', shift: 'Shift', alt: 'Alt', meta: 'Meta',
                escape: 'Esc', enter: 'Enter', tab: 'Tab',
                backspace: 'Backspace', delete: 'Del', space: 'Space',
                arrowup: 'Up', arrowdown: 'Down', arrowleft: 'Left', arrowright: 'Right',
            };
            return map[k.toLowerCase()] || k.toUpperCase();
        });
        return '[' + parts.join('+') + ']';
    }

    function _hint(actionId) {
        if (!window.HKS_BINDINGS) return '';
        const combo = window.HKS_BINDINGS.get(actionId);
        const fmt = _fmtCombo(combo);
        return fmt ? '  ' + fmt : '';
    }

    function _setTitle(elementId, description, actionId) {
        const el = document.getElementById(elementId);
        if (!el) return;
        const hint = _hint(actionId);
        el.title = hint ? description + hint : description;
    }

    function _setTitleAll(selector, description, actionId) {
        const hint = _hint(actionId);
        const title = hint ? description + hint : description;
        document.querySelectorAll(selector).forEach(el => { el.title = title; });
    }

    window.applyShortcutTooltips = function () {
        if (!window.HKS_BINDINGS) return;

        // Topbar
        _setTitle('sidebar-toggle-btn',    'Toggle Sidebar',                     'ui.toggle_sidebar');
        _setTitle('topbar-hub-link',        'Open Central Hub',                   'nav.hub');
        _setTitle('topbar-drive-link',      'Open Drive',                         'nav.drive');
        _setTitle('topbar-flows-link',      'Open Flows',                         'nav.flows');
        _setTitle('topbar-stop-voice-btn',  'Stop Voice Output',                  'ui.close_modal');

        // Sidebar audio controls
        _setTitle('mic-btn',               'Toggle Microphone',                  'ui.toggle_mic');
        _setTitle('tts-btn',               'Toggle Voice Output',                'ui.toggle_voice');
        _setTitle('ptt-btn',               'Toggle Push-To-Talk',                'ui.toggle_ptt');
        _setTitle('sidebar-stop-voice-btn','Stop Voice Output',                  'ui.close_modal');

        // Sidebar navigation (mobile only)
        _setTitle('sidebar-hub-link',      'Open Central Hub',                   'nav.hub');
        _setTitle('sidebar-drive-link',    'Open Drive',                         'nav.drive');
        _setTitle('sidebar-flows-link',    'Open Flows',                         'nav.flows');

        // Sidebar action buttons
        _setTitle('sidebar-expand-btn',    'Open Control Room',                  'ui.toggle_room');
        _setTitle('sidebar-hpm-btn',       'Install and manage modules',         'nav.packages');

        // History panel
        _setTitle('ch-new-chat-btn',       'Start a new chat session',           'ui.new_chat');

        // Quick Config status pills (no stable IDs, use selector)
        _setTitleAll('.status-pill.clickable', 'Open Quick Config',              'nav.quick_config');

        // ── CENTRAL HUB (config_panel & core_header) ─────────────────────────
        _setTitle('hdr-nav-chat',      'Open Chat',             'nav.chat');
        _setTitle('hdr-nav-room',      'Open Control Room',     'nav.home');
        _setTitle('hdr-nav-drive',     'Open Drive',            'nav.drive');
        _setTitle('hdr-nav-flows',     'Open Flows',            'nav.flows');
        _setTitle('btn-reboot-system', 'Restart Hecos System',  'sys.reboot');
    };

    document.addEventListener('DOMContentLoaded', () => {
        setTimeout(window.applyShortcutTooltips, 0);
    });

    // Monkey-patch HKS_BINDINGS to auto-refresh tooltips on every change
    const _waitForBindings = setInterval(() => {
        if (!window.HKS_BINDINGS) return;
        clearInterval(_waitForBindings);

        const _patchMethod = (name) => {
            const orig = window.HKS_BINDINGS[name].bind(window.HKS_BINDINGS);
            window.HKS_BINDINGS[name] = function (...args) {
                const result = orig(...args);
                setTimeout(window.applyShortcutTooltips, 50);
                return result;
            };
        };

        _patchMethod('save');
        _patchMethod('reset');
        _patchMethod('resetAll');
        _patchMethod('forceSet');

        console.log('[HKS Tooltips] Hooked into HKS_BINDINGS.');
        window.applyShortcutTooltips();
    }, 50);

})();
