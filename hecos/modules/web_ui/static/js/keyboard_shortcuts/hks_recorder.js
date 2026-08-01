/**
 * hks_recorder.js — Hecos Keyboard Shortcuts Key Recorder
 * ─────────────────────────────────────────────────────────────────────────────
 * Interactive key capture widget for reassigning keyboard shortcuts.
 * Displays an input field in "listening" mode that captures the next
 * key combination pressed and returns it for assignment.
 *
 * API (window.HKS_RECORDER):
 *   capture(targetElement, onCapture, onCancel) — start capture mode
 *   stop()                                       — cancel capture
 *   isCapturing()                                — check if in capture mode
 *
 * Usage (in control panel):
 *   HKS_RECORDER.capture(myElement, (combo) => {
 *       // combo e.g. 'ctrl+shift+k'
 *       const result = HKS_BINDINGS.set('nav.chat', combo);
 *       if (!result.ok) { ... show conflict error ... }
 *   });
 *
 * Dependencies: hks_core.js
 * ─────────────────────────────────────────────────────────────────────────────
 */

(function () {
    'use strict';

    let _capturing = false;
    let _captureEl = null;
    let _onCapture = null;
    let _onCancel  = null;
    let _keydownHandler = null;

    // Keys that cannot be used as shortcuts (single modifiers)
    const IGNORED_KEYS = new Set([
        'Control', 'Alt', 'Shift', 'Meta', 'CapsLock', 'NumLock',
        'ScrollLock', 'Pause', 'Insert', 'ContextMenu'
    ]);

    // Browser-reserved combos that should be blocked
    const BLOCKED = new Set([
        'ctrl+w', 'ctrl+t', 'ctrl+n', 'ctrl+shift+n', 'ctrl+shift+t',
        'ctrl+l', 'ctrl+r', 'ctrl+s', 'ctrl+p', 'ctrl+a', 'ctrl+z',
        'ctrl+shift+j', 'ctrl+u', 'alt+f4'
    ]);

    // ── Capture logic ──────────────────────────────────────────────────────────

    function _start(targetEl, onCapture, onCancel) {
        if (_capturing) _stop();

        _capturing = true;
        _captureEl = targetEl;
        _onCapture = onCapture;
        _onCancel  = onCancel;

        // Visual feedback on the target element
        if (targetEl) {
            targetEl.classList.add('hks-capturing');
            targetEl.setAttribute('data-original', targetEl.textContent);
            targetEl.textContent = '🎹 Press keys…';
        }

        _keydownHandler = function(e) {
            e.preventDefault();
            e.stopPropagation();

            // Escape = cancel
            if (e.key === 'Escape') {
                _stop();
                if (_onCancel) _onCancel();
                return;
            }

            // Ignore single modifiers
            if (IGNORED_KEYS.has(e.key)) return;

            // Build combo
            const combo = window.HKS ? window.HKS.normalizeEvent(e) : _buildCombo(e);

            // Check blocked
            if (BLOCKED.has(combo)) {
                if (targetEl) {
                    targetEl.textContent = '🚫 Reserved by browser';
                    setTimeout(() => {
                        targetEl.textContent = '🎹 Press keys…';
                    }, 1500);
                }
                return;
            }

            // Done! Deliver the combo.
            _stop();
            if (_onCapture) _onCapture(combo);
        };

        document.addEventListener('keydown', _keydownHandler, { capture: true });

        // Click outside = cancel
        setTimeout(() => {
            document.addEventListener('mousedown', _onOutsideClick, { once: true });
        }, 100);
    }

    function _stop() {
        if (!_capturing) return;
        _capturing = false;

        if (_captureEl) {
            _captureEl.classList.remove('hks-capturing');
            const original = _captureEl.getAttribute('data-original');
            if (original !== null) {
                _captureEl.textContent = original;
                _captureEl.removeAttribute('data-original');
            }
        }

        if (_keydownHandler) {
            document.removeEventListener('keydown', _keydownHandler, { capture: true });
            _keydownHandler = null;
        }

        document.removeEventListener('mousedown', _onOutsideClick);

        _captureEl = null;
        _onCapture = null;
        _onCancel  = null;
    }

    function _onOutsideClick(e) {
        if (_captureEl && !_captureEl.contains(e.target)) {
            _stop();
            if (_onCancel) _onCancel();
        }
    }

    function _buildCombo(e) {
        const parts = [];
        if (e.ctrlKey || e.metaKey) parts.push('ctrl');
        if (e.altKey)                parts.push('alt');
        if (e.shiftKey)              parts.push('shift');
        if (!['Control', 'Alt', 'Shift', 'Meta'].includes(e.key)) {
            parts.push(e.key.toLowerCase());
        }
        return parts.join('+');
    }

    // ── Public API ────────────────────────────────────────────────────────────

    window.HKS_RECORDER = {
        /**
         * Start capturing a key combination.
         * @param {Element} targetEl — element to show capture state on
         * @param {function} onCapture(combo) — called with the captured combo string
         * @param {function} [onCancel] — called if user presses Escape or clicks away
         */
        capture: _start,

        /**
         * Immediately stop capturing.
         */
        stop: _stop,

        /**
         * Returns true if currently in capture mode.
         */
        isCapturing() { return _capturing; }
    };

    console.log('[HKS Recorder] Ready.');

})();
