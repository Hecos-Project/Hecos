/**
 * hks_core.js — Hecos Keyboard Shortcuts Engine
 * ─────────────────────────────────────────────────────────────────────────────
 * Core engine for the HKS (Hecos Keyboard Shortcuts System).
 * Handles global keydown events, context awareness, priority dispatch, and
 * conflict detection. Designed to work across all WebUI pages (chat, hub, home).
 *
 * API (window.HKS):
 *   HKS.register(actionId, handler, opts)  — register an action handler
 *   HKS.unregister(actionId)               — remove an action handler
 *   HKS.setContext(contextName)            — set the active context
 *   HKS.getContext()                       — get the active context
 *   HKS.trigger(actionId)                  — programmatically fire an action
 *   HKS.isInputFocused()                   — check if a text input has focus
 *   HKS.on(event, callback)                — subscribe to HKS events
 *   HKS.off(event, callback)               — unsubscribe from HKS events
 *
 * Contexts: 'global', 'chat', 'hub', 'home'
 * ─────────────────────────────────────────────────────────────────────────────
 */

(function () {
    'use strict';

    // ── State ─────────────────────────────────────────────────────────────────

    let _context = 'global';
    let _handlers = {};      // actionId → { handler, opts }
    let _enabled  = true;
    let _listeners = {};     // event name → [callbacks]

    // Tags that indicate user is typing — shortcuts should mostly be suppressed
    const INPUT_TAGS = new Set(['INPUT', 'TEXTAREA', 'SELECT']);

    // Keys that are ALWAYS intercepted even inside inputs
    const ALWAYS_CAPTURE = new Set(['Escape', 'F1', 'F2', 'F3', 'F4', 'F5', 'F6',
                                    'F7', 'F8', 'F9', 'F10', 'F12']);

    // Browser-reserved combos we must never steal
    const BROWSER_RESERVED = new Set([
        'ctrl+w', 'ctrl+t', 'ctrl+n', 'ctrl+shift+n', 'ctrl+shift+t',
        'ctrl+l', 'ctrl+r', 'ctrl+shift+j', 'ctrl+u', 'ctrl+s',
        'alt+F4', 'ctrl+f5'
    ]);

    // ── Internal helpers ──────────────────────────────────────────────────────

    /**
     * Normalize a KeyboardEvent into a canonical combo string.
     * e.g. Ctrl+Shift+K → 'ctrl+shift+k'
     *      F5            → 'f5'
     *      Escape        → 'escape'
     */
    function _normalizeEvent(e) {
        const parts = [];
        if (e.ctrlKey  || e.metaKey)  parts.push('ctrl');
        if (e.altKey)                  parts.push('alt');
        if (e.shiftKey)                parts.push('shift');

        const key = e.key;
        // Avoid duplicating modifier names in key
        if (!['Control', 'Alt', 'Shift', 'Meta'].includes(key)) {
            parts.push(key.toLowerCase());
        }
        return parts.join('+');
    }

    /**
     * Check if user is currently typing in an input field.
     */
    function _isInputFocused() {
        const el = document.activeElement;
        return el && (INPUT_TAGS.has(el.tagName) || el.isContentEditable);
    }

    /**
     * Emit an internal event to all registered listeners.
     */
    function _emit(event, data) {
        const cbs = _listeners[event] || [];
        cbs.forEach(cb => { try { cb(data); } catch (e) { console.warn('[HKS] Listener error:', e); } });
    }

    // ── Main keydown handler ──────────────────────────────────────────────────

    function _onKeydown(e) {
        if (!_enabled) return;

        const combo = _normalizeEvent(e);

        // Never steal browser-reserved combos
        if (BROWSER_RESERVED.has(combo)) return;

        const inInput = _isInputFocused();

        // If user is in an input, only allow ALWAYS_CAPTURE keys
        if (inInput && !ALWAYS_CAPTURE.has(e.key) && !e.ctrlKey && !e.altKey) return;

        // Get bindings (from hks_bindings.js — loaded separately)
        const bindings = window.HKS_BINDINGS ? window.HKS_BINDINGS.getAll() : {};

        // Find which action matches this combo
        let matchedActionId = null;
        for (const [actionId, boundCombo] of Object.entries(bindings)) {
            if (boundCombo === combo) {
                matchedActionId = actionId;
                break;
            }
        }

        if (!matchedActionId) return;

        // Check if handler is registered
        const entry = _handlers[matchedActionId];
        if (!entry) return;

        // Check context
        const opts = entry.opts || {};
        const allowedContexts = opts.contexts || ['global', 'chat', 'hub', 'home'];
        if (!allowedContexts.includes('global') && !allowedContexts.includes(_context)) return;

        // Execute!
        e.preventDefault();
        e.stopPropagation();

        try {
            entry.handler(e, matchedActionId, combo);
            _emit('action', { actionId: matchedActionId, combo, context: _context });
        } catch (err) {
            console.error('[HKS] Handler error for action:', matchedActionId, err);
        }
    }

    // ── Focus cycling (Tab key) ────────────────────────────────────────────────

    let _focusZones = [];
    let _focusIndex = -1;

    function _registerFocusZones(zones) {
        _focusZones = zones;
        _focusIndex = -1;
    }

    function _cycleFocus(reverse = false) {
        // Filter visible zones
        const visible = _focusZones.filter(sel => {
            const el = typeof sel === 'string' ? document.querySelector(sel) : sel;
            return el && el.offsetParent !== null;
        });

        if (visible.length === 0) return false;

        if (reverse) {
            _focusIndex = (_focusIndex - 1 + visible.length) % visible.length;
        } else {
            _focusIndex = (_focusIndex + 1) % visible.length;
        }

        const sel = visible[_focusIndex];
        const el = typeof sel === 'string' ? document.querySelector(sel) : sel;
        if (el) {
            el.focus({ preventScroll: false });
            el.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
            _emit('focus_cycle', { index: _focusIndex, element: el, context: _context });
            return true;
        }
        return false;
    }

    // ── Public API ────────────────────────────────────────────────────────────

    const HKS = {

        /**
         * Register a handler for an action.
         * @param {string} actionId — unique action ID (e.g. 'nav.chat')
         * @param {function} handler — function(event, actionId, combo)
         * @param {object} opts — { contexts: ['global','chat'] }
         */
        register(actionId, handler, opts = {}) {
            _handlers[actionId] = { handler, opts };
        },

        /**
         * Unregister a handler.
         */
        unregister(actionId) {
            delete _handlers[actionId];
        },

        /**
         * Set the active context for this page.
         * @param {string} ctx — 'global' | 'chat' | 'hub' | 'home'
         */
        setContext(ctx) {
            const prev = _context;
            _context = ctx;
            if (prev !== ctx) _emit('context_change', { from: prev, to: ctx });
            console.log(`[HKS] Context set to: ${ctx}`);
        },

        /**
         * Get current context.
         */
        getContext() {
            return _context;
        },

        /**
         * Programmatically trigger an action by ID.
         */
        trigger(actionId) {
            const entry = _handlers[actionId];
            if (entry) {
                try {
                    entry.handler(null, actionId, null);
                    _emit('action', { actionId, combo: null, context: _context, programmatic: true });
                } catch (err) {
                    console.error('[HKS] Error triggering action:', actionId, err);
                }
            } else {
                console.warn('[HKS] No handler for action:', actionId);
            }
        },

        /**
         * Check if a text input currently has focus.
         */
        isInputFocused: _isInputFocused,

        /**
         * Enable or disable the entire HKS system.
         */
        setEnabled(value) {
            _enabled = Boolean(value);
            _emit('enabled_change', { enabled: _enabled });
        },

        isEnabled() { return _enabled; },

        /**
         * Register focusable zones for Tab cycling.
         * @param {Array<string|Element>} zones — CSS selectors or DOM elements
         */
        registerFocusZones(zones) {
            _registerFocusZones(zones);
        },

        /**
         * Cycle focus to next/prev zone.
         */
        cycleFocus(reverse = false) {
            return _cycleFocus(reverse);
        },

        /**
         * Subscribe to HKS internal events.
         * Events: 'action', 'context_change', 'focus_cycle', 'enabled_change'
         */
        on(event, callback) {
            if (!_listeners[event]) _listeners[event] = [];
            _listeners[event].push(callback);
        },

        off(event, callback) {
            if (!_listeners[event]) return;
            _listeners[event] = _listeners[event].filter(cb => cb !== callback);
        },

        /**
         * Normalize a KeyboardEvent into a combo string. Useful for the recorder.
         */
        normalizeEvent: _normalizeEvent,

        /**
         * Check if a combo is browser-reserved.
         */
        isBrowserReserved(combo) {
            return BROWSER_RESERVED.has(combo);
        },

        /**
         * Get all registered action IDs.
         */
        getRegisteredActions() {
            return Object.keys(_handlers);
        },

        VERSION: '1.0.0'
    };

    // ── Init ──────────────────────────────────────────────────────────────────

    function _init() {
        document.addEventListener('keydown', _onKeydown, { capture: true });
        console.log('[HKS] Core engine initialized. Version:', HKS.VERSION);
        _emit('ready', { version: HKS.VERSION });
    }

    // Expose globally
    window.HKS = HKS;

    // Init when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', _init);
    } else {
        _init();
    }

})();
