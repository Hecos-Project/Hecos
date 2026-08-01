/**
 * hks_overlay.js — Hecos Keyboard Shortcuts HUD Overlay (Cheatsheet)
 * ─────────────────────────────────────────────────────────────────────────────
 * A TMUX/VIM inspired semi-transparent overlay that shows all active keyboard
 * shortcuts. Activated with the '?' key or programmatically.
 *
 * API (window.HKS_OVERLAY):
 *   show()       — display the cheatsheet
 *   hide()       — hide the cheatsheet
 *   toggle()     — toggle visibility
 *   isVisible()  — returns boolean
 *
 * Dependencies: hks_core.js, hks_actions.js, hks_bindings.js
 * ─────────────────────────────────────────────────────────────────────────────
 */

(function () {
    'use strict';

    let _built = false;
    let _visible = false;
    let _overlay = null;

    // ── Build DOM ─────────────────────────────────────────────────────────────

    function _build() {
        if (_built || document.getElementById('hks-overlay')) return;
        _built = true;

        const el = document.createElement('div');
        el.id = 'hks-overlay';
        el.setAttribute('role', 'dialog');
        el.setAttribute('aria-modal', 'true');
        el.setAttribute('aria-label', 'Keyboard Shortcuts Reference');
        el.innerHTML = `
            <div class="hks-overlay-backdrop"></div>
            <div class="hks-overlay-panel">
                <div class="hks-overlay-header">
                    <div class="hks-overlay-title">
                        <i class="fas fa-keyboard"></i>
                        <span>Keyboard Shortcuts</span>
                        <span class="hks-overlay-context-badge" id="hks-ctx-badge">GLOBAL</span>
                    </div>
                    <button class="hks-overlay-close" id="hks-overlay-close" aria-label="Close">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                <div class="hks-overlay-body" id="hks-overlay-body">
                    <!-- Populated dynamically -->
                </div>
                <div class="hks-overlay-footer">
                    <span><kbd>?</kbd> Toggle this panel</span>
                    <span><kbd>Esc</kbd> Close</span>
                    <span><kbd>Ctrl+,</kbd> Edit shortcuts</span>
                </div>
            </div>
        `;
        document.body.appendChild(el);
        _overlay = el;

        // Close button
        document.getElementById('hks-overlay-close').addEventListener('click', _hide);

        // Backdrop click
        el.querySelector('.hks-overlay-backdrop').addEventListener('click', _hide);

        // Keyboard: Escape to close (handled by hks_actions close_modal)
        // But also handle directly for safety
        el.addEventListener('keydown', e => {
            if (e.key === 'Escape') { e.stopPropagation(); _hide(); }
        });
    }

    // ── Render content ────────────────────────────────────────────────────────

    function _render() {
        const body = document.getElementById('hks-overlay-body');
        if (!body) return;

        const actions  = window.HKS_ACTIONS ? window.HKS_ACTIONS.getAll() : [];
        const bindings = window.HKS_BINDINGS ? window.HKS_BINDINGS.getAll() : {};
        const ctx      = window.HKS ? window.HKS.getContext() : 'global';
        const cats     = window.HKS_ACTIONS ? window.HKS_ACTIONS.CATEGORIES : {};

        // Update context badge
        const badge = document.getElementById('hks-ctx-badge');
        if (badge) badge.textContent = ctx.toUpperCase();

        // Group actions by category
        const groups = {};
        actions.forEach(action => {
            const combo = bindings[action.id];
            if (!combo) return; // Skip unbound actions
            const cat = action.category;
            if (!groups[cat]) groups[cat] = [];
            groups[cat].push({ ...action, combo });
        });

        // Sort categories by order
        const sortedCats = Object.keys(groups).sort((a, b) => {
            const oa = cats[a] ? cats[a].order : 99;
            const ob = cats[b] ? cats[b].order : 99;
            return oa - ob;
        });

        body.innerHTML = '';

        if (sortedCats.length === 0) {
            body.innerHTML = '<div class="hks-overlay-empty">No shortcuts configured.</div>';
            return;
        }

        sortedCats.forEach(cat => {
            const catMeta = cats[cat] || { label: cat, icon: 'fas fa-circle' };
            const section = document.createElement('div');
            section.className = 'hks-overlay-section';
            section.innerHTML = `
                <div class="hks-overlay-section-title">
                    <i class="${catMeta.icon}"></i>
                    <span>${catMeta.label}</span>
                </div>
                <div class="hks-overlay-grid">
                    ${groups[cat].map(action => _renderItem(action)).join('')}
                </div>
            `;
            body.appendChild(section);
        });
    }

    function _renderItem(action) {
        const formatted = window.HKS_BINDINGS ?
            window.HKS_BINDINGS.formatCombo(action.combo) : action.combo;

        // Split combo into individual keys for display
        const keys = formatted.split('+').map(k =>
            `<kbd class="hks-key">${k}</kbd>`
        ).join('<span class="hks-key-sep">+</span>');

        return `
            <div class="hks-overlay-item">
                <div class="hks-item-keys">${keys}</div>
                <div class="hks-item-info">
                    <i class="${action.icon}"></i>
                    <span>${action.label}</span>
                </div>
            </div>
        `;
    }

    // ── Show / Hide ───────────────────────────────────────────────────────────

    function _show() {
        _build();
        _render();
        _visible = true;

        const panel = _overlay ? _overlay.querySelector('.hks-overlay-panel') : null;
        if (_overlay) {
            _overlay.classList.add('hks-overlay-visible');
            if (panel) {
                panel.classList.add('hks-overlay-panel-in');
            }
        }

        // Trap focus inside overlay
        const closeBtn = document.getElementById('hks-overlay-close');
        if (closeBtn) closeBtn.focus();
    }

    function _hide() {
        if (!_overlay) return;
        _visible = false;

        const panel = _overlay.querySelector('.hks-overlay-panel');
        _overlay.classList.remove('hks-overlay-visible');
        if (panel) panel.classList.remove('hks-overlay-panel-in');
    }

    function _toggle() {
        if (_visible) _hide(); else _show();
    }

    // ── Public API ────────────────────────────────────────────────────────────

    window.HKS_OVERLAY = {
        show:      _show,
        hide:      _hide,
        toggle:    _toggle,
        isVisible: () => _visible,
        refresh:   _render
    };

    // Init: pre-build DOM silently
    function _init() {
        _build();
        console.log('[HKS Overlay] Ready.');
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', _init);
    } else {
        _init();
    }

})();
