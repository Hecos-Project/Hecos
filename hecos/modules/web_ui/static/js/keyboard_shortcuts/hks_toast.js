/**
 * hks_toast.js — Hecos Keyboard Shortcuts Toast Feedback
 * ─────────────────────────────────────────────────────────────────────────────
 * Displays a brief visual toast when a shortcut is triggered, showing the
 * action name and the key combination pressed. Inspired by i3/Sway WM overlays.
 *
 * API (window.HKS_TOAST):
 *   show(actionId, combo)  — display a toast for an action
 *   hide()                 — immediately hide current toast
 *   setEnabled(bool)       — enable/disable toasts
 *
 * Dependencies: hks_core.js, hks_actions.js, hks_bindings.js
 * ─────────────────────────────────────────────────────────────────────────────
 */

(function () {
    'use strict';

    let _el = null;
    let _hideTimer = null;
    let _enabled = true;

    // ── Build DOM ─────────────────────────────────────────────────────────────

    function _buildElement() {
        if (document.getElementById('hks-toast')) return;

        const toast = document.createElement('div');
        toast.id = 'hks-toast';
        toast.setAttribute('role', 'status');
        toast.setAttribute('aria-live', 'polite');
        toast.innerHTML = `
            <div class="hks-toast-inner">
                <i id="hks-toast-icon" class="fas fa-keyboard"></i>
                <div class="hks-toast-content">
                    <span id="hks-toast-label"></span>
                    <span id="hks-toast-combo"></span>
                </div>
            </div>
        `;
        document.body.appendChild(toast);
        _el = toast;
    }

    // ── Show / Hide ───────────────────────────────────────────────────────────

    function _show(actionId, combo) {
        if (!_enabled) return;
        if (!_el) _buildElement();
        if (!_el) return;

        const action = window.HKS_ACTIONS ? window.HKS_ACTIONS.find(actionId) : null;
        const label  = action ? action.label : actionId;
        const icon   = action ? action.icon  : 'fas fa-keyboard';
        const comboDisplay = window.HKS_BINDINGS ? window.HKS_BINDINGS.formatCombo(combo) : combo;

        // Update content
        const iconEl = document.getElementById('hks-toast-icon');
        if (iconEl) iconEl.className = icon;
        const labelEl = document.getElementById('hks-toast-label');
        if (labelEl) labelEl.textContent = label;
        const comboEl = document.getElementById('hks-toast-combo');
        if (comboEl) comboEl.textContent = comboDisplay;

        // Reset animation
        _el.classList.remove('hks-toast-visible', 'hks-toast-fade');
        requestAnimationFrame(() => {
            _el.classList.add('hks-toast-visible');
        });

        // Auto-hide
        clearTimeout(_hideTimer);
        _hideTimer = setTimeout(_hide, 1600);
    }

    function _hide() {
        if (!_el) return;
        _el.classList.remove('hks-toast-visible');
        _el.classList.add('hks-toast-fade');
        clearTimeout(_hideTimer);
    }

    // ── Hook into HKS events ──────────────────────────────────────────────────

    function _hookEvents() {
        if (!window.HKS) return;
        window.HKS.on('action', ({ actionId, combo }) => {
            // Don't show toast for cheatsheet/toast-related actions to avoid recursion
            if (actionId === 'ui.show_cheatsheet') return;
            _show(actionId, combo);
        });
    }

    // ── Public API ────────────────────────────────────────────────────────────

    window.HKS_TOAST = {
        show: _show,
        hide: _hide,
        setEnabled(val) { _enabled = Boolean(val); }
    };

    // Init
    function _init() {
        _buildElement();
        _hookEvents();

        // Respect user preference
        if (window.HKS_BINDINGS) {
            _enabled = window.HKS_BINDINGS.getPref('toastEnabled') !== false;
        }

        // Update when prefs change
        if (window.HKS) {
            window.HKS.on('prefs_change', (prefs) => {
                if (typeof prefs.toastEnabled !== 'undefined') {
                    _enabled = prefs.toastEnabled;
                }
            });
        }

        console.log('[HKS Toast] Initialized.');
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', _init);
    } else {
        _init();
    }

})();
