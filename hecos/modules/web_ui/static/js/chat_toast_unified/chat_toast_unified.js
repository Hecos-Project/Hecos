/**
 * chat_toast_unified.js
 * Unifies all UI transient popups (shortcuts, copy actions, warnings) into a single 
 * premium pill-shaped toast in the top-center of the screen.
 * Also pipes all these notifications into the Presenter as system logs.
 */

(function () {
    'use strict';

    let _el = null;
    let _hideTimer = null;

    // Inject CSS for the unified toast
    function _injectCSS() {
        if (document.getElementById('unified-toast-css')) return;
        const style = document.createElement('style');
        style.id = 'unified-toast-css';
        style.textContent = `
            #chat-toast-unified {
                position: fixed;
                top: 40%;
                left: 50%;
                transform: translate(-50%, -50%) scale(0.9);
                background: rgba(var(--surface-rgb), 0.9);
                backdrop-filter: blur(10px);
                border: 1px solid var(--border);
                color: var(--text);
                padding: 12px 24px;
                border-radius: 50px;
                box-shadow: 0 4px 20px rgba(0,0,0,0.4);
                display: flex;
                align-items: center;
                gap: 10px;
                z-index: 10000;
                font-family: var(--font-family, sans-serif);
                font-size: 15px;
                transition: opacity 0.3s ease, transform 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
                opacity: 0;
                pointer-events: none;
            }
            #chat-toast-unified.visible {
                opacity: 1;
                transform: translate(-50%, -50%) scale(1);
            }
            #chat-toast-unified-icon {
                font-size: 16px;
                color: var(--accent);
            }
            #chat-toast-unified-msg {
                font-weight: 500;
            }
        `;
        document.head.appendChild(style);
    }

    // Build the DOM element
    function _buildElement() {
        _injectCSS();
        if (document.getElementById('chat-toast-unified')) {
            _el = document.getElementById('chat-toast-unified');
            return;
        }

        const toast = document.createElement('div');
        toast.id = 'chat-toast-unified';
        toast.innerHTML = `
            <i id="chat-toast-unified-icon" class="fas fa-info-circle"></i>
            <span id="chat-toast-unified-msg"></span>
        `;
        document.body.appendChild(toast);
        _el = toast;
    }

    let _enabled = true;

    /**
     * Show a unified toast message
     * @param {string} msg - The message to display
     * @param {string} iconClass - (Optional) FontAwesome icon class (e.g. 'fas fa-check')
     * @param {number} duration - (Optional) Duration in ms
     * @param {string} bgColor - (Optional) Custom CSS background color
     */
    function show(msg, iconClass = 'fas fa-info-circle', duration = 3000, bgColor = null) {
        if (!_enabled) return;
        if (!_el) _buildElement();

        const iconEl = document.getElementById('chat-toast-unified-icon');
        const msgEl = document.getElementById('chat-toast-unified-msg');

        iconEl.className = iconClass;
        msgEl.textContent = msg;

        // Apply custom color or revert to default
        if (bgColor) {
            _el.style.background = bgColor;
        } else {
            _el.style.background = 'rgba(var(--surface-rgb), 0.9)';
        }

        // Reset animation
        _el.classList.remove('visible');
        
        // Force reflow
        void _el.offsetWidth; 
        
        _el.classList.add('visible');

        // Send to Presenter
        _logToPresenter(msg);

        // Auto-hide
        clearTimeout(_hideTimer);
        if (duration > 0) {
            _hideTimer = setTimeout(() => {
                _el.classList.remove('visible');
            }, duration);
        }
    }

    /**
     * Manually hide the unified toast
     */
    function hide() {
        if (!_el) return;
        clearTimeout(_hideTimer);
        _el.classList.remove('visible');
    }

    // Send the log to the event bus for the Presenter to pick up
    function _logToPresenter(msg) {
        if (window.hecos && window.hecos.core && window.hecos.core.events && window.hecos.core.events.bus) {
            window.hecos.core.events.bus.dispatchEvent(new CustomEvent('hecos:system:toast', {
                detail: { message: msg }
            }));
        }
    }

    // Hook into Keyboard Shortcuts (HKS) to replace the old hks_toast
    function _hookHKSEvents() {
        if (window.HKS) {
            window.HKS.on('action', ({ actionId, combo }) => {
                // Don't show toast for cheatsheet/modal to avoid recursion
                // Also ignore ptt_trigger here, as it's handled natively by audio_recorder.js (with infinite duration)
                if (actionId === 'ui.show_cheatsheet' || actionId === 'ui.close_modal' || actionId === 'ui.ptt_trigger') return;

                const action = window.HKS_ACTIONS ? window.HKS_ACTIONS.find(actionId) : null;
                const label  = action ? action.label : actionId;
                const icon   = action ? action.icon  : 'fas fa-keyboard';
                const comboDisplay = window.HKS_BINDINGS ? window.HKS_BINDINGS.formatCombo(combo) : combo;

                show(`[${comboDisplay}] Triggered: ${label}`, icon);
            });
        }
    }

    // Expose API
    window.UnifiedToast = {
        show: show,
        hide: hide,
        setEnabled: function(val) { _enabled = Boolean(val); }
    };

    // Override global showToast to redirect to UnifiedToast
    window.showToast = function(msg, duration, typeOrIcon) {
        let icon = 'fas fa-info-circle';
        if (typeOrIcon === 'error') icon = 'fas fa-exclamation-triangle';
        else if (typeOrIcon === 'success') icon = 'fas fa-check-circle';
        else if (typeOrIcon && typeOrIcon.startsWith('fa')) icon = typeOrIcon;
        // The old showToast uses just (msg, duration), or sometimes (msg, type)
        // Some places call: showToast(msg, 'info') => duration was second arg
        // Let's normalize it:
        let dur = typeof duration === 'number' ? duration : 2500;
        let typ = typeof duration === 'string' ? duration : typeOrIcon;
        
        if (typ === 'error') icon = 'fas fa-exclamation-triangle';
        else if (typ === 'warning') icon = 'fas fa-exclamation-triangle';
        else if (typ === 'success') icon = 'fas fa-check-circle';

        show(msg, icon, dur);
    };
    
    // Also override HKS_TOAST to prevent the old one from showing
    window.HKS_TOAST = {
        show: function(actionId, combo) {
            // Already handled by _hookHKSEvents, this is a fallback intercept
        },
        hide: function() {
            if (_el) _el.classList.remove('visible');
        },
        setEnabled: function() {}
    };

    // Initialize
    function _init() {
        _buildElement();
        _hookHKSEvents();
        
        // Respect user preference for keyboard shortcuts toast
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
        
        // Remove old elements if they exist
        const oldChatToast = document.getElementById('chat-toast');
        if (oldChatToast) oldChatToast.remove();
        
        const oldHksToast = document.getElementById('hks-toast');
        if (oldHksToast) oldHksToast.remove();

        // Print shortcuts to Presenter on startup
        setTimeout(() => {
            if (window.HKS_ACTIONS && window.HKS_BINDINGS) {
                const parts = [];
                for (const action of window.HKS_ACTIONS.all()) {
                    const combo = window.HKS_BINDINGS.getCombo(action.id);
                    if (combo) {
                        parts.push(`[${window.HKS_BINDINGS.formatCombo(combo)}] ${action.label}`);
                    }
                }
                if (parts.length > 0) {
                    _logToPresenter(`⌨️ Shortcuts: ${parts.join('  •  ')}`);
                }
            }
        }, 1500);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', _init);
    } else {
        _init();
    }

})();
