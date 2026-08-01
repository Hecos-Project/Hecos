/**
 * hks_actions.js — Hecos Keyboard Shortcuts Action Registry
 * ─────────────────────────────────────────────────────────────────────────────
 * Defines all available actions that can be bound to keyboard shortcuts.
 * Each action has a unique ID, metadata (label, icon, category), and a handler.
 *
 * This module registers all handlers with the HKS core engine and exposes
 * the action catalog via window.HKS_ACTIONS for the control panel UI.
 *
 * Dependencies: hks_core.js (must be loaded first)
 * ─────────────────────────────────────────────────────────────────────────────
 */

(function () {
    'use strict';

    // ── Action Catalog ────────────────────────────────────────────────────────
    // Each action: { id, label, icon, category, description, contexts, handler }

    const ACTIONS = [

        // ── NAVIGATION ────────────────────────────────────────────────────────

        {
            id: 'nav.chat',
            label: 'Open Chat',
            icon: 'fas fa-comment-dots',
            category: 'navigation',
            description: 'Navigate to the Chat interface',
            contexts: ['global', 'hub', 'home'],
            handler: function() {
                window.open('/chat', '_blank', 'noopener');
            }
        },

        {
            id: 'nav.hub',
            label: 'Open Central Hub',
            icon: 'fas fa-cog',
            category: 'navigation',
            description: 'Navigate to the Central Hub (Config)',
            contexts: ['global', 'chat', 'home'],
            handler: function() {
                window.open('/hecos/config/ui', '_blank', 'noopener');
            }
        },

        {
            id: 'nav.home',
            label: 'Open Control Room',
            icon: 'fas fa-th-large',
            category: 'navigation',
            description: 'Navigate to the Control Room dashboard',
            contexts: ['global', 'chat', 'hub'],
            handler: function() {
                window.open('/', '_blank', 'noopener');
            }
        },

        {
            id: 'nav.backend',
            label: 'Open Models/Backend',
            description: 'Navigate to Backend Settings',
            icon: 'fas fa-server',
            category: 'navigation',
            contexts: ['global', 'chat', 'hub', 'home'],
            handler: () => {
                if (window.HKS && window.HKS.getContext() === 'hub') {
                    if (window.switchTab) window.switchTab('backend');
                } else {
                    window.open('/hecos/config#backend', '_blank');
                }
            }
        },

        {
            id: 'nav.ia',
            label: 'Open Personalities (Soul)',
            description: 'Navigate to IA/Soul Settings',
            icon: 'fas fa-brain',
            category: 'navigation',
            contexts: ['global', 'chat', 'hub', 'home'],
            handler: () => {
                if (window.HKS && window.HKS.getContext() === 'hub') {
                    if (window.switchTab) window.switchTab('ia');
                } else {
                    window.open('/hecos/config#ia', '_blank');
                }
            }
        },

        {
            id: 'nav.voice',
            label: 'Open Voice Settings',
            description: 'Navigate to Voice Engine Settings',
            icon: 'fas fa-volume-up',
            category: 'navigation',
            contexts: ['global', 'chat', 'hub', 'home'],
            handler: () => {
                if (window.HKS && window.HKS.getContext() === 'hub') {
                    if (window.switchTab) window.switchTab('voice');
                } else {
                    window.open('/hecos/config#voice', '_blank');
                }
            }
        },

        {
            id: 'nav.help',
            label: 'Open Help',
            description: 'Navigate to Help/About panel',
            icon: 'fas fa-question-circle',
            category: 'navigation',
            contexts: ['global', 'chat', 'hub', 'home'],
            handler: () => {
                if (window.HKS && window.HKS.getContext() === 'hub') {
                    if (window.switchTab) window.switchTab('help');
                } else {
                    window.open('/hecos/config#help', '_blank');
                }
            }
        },

        {
            id: 'nav.packages',
            label: 'Package Manager (HPM)',
            icon: 'fas fa-box-open',
            category: 'navigation',
            description: 'Open the Hecos Package Manager tab',
            contexts: ['global', 'chat', 'hub', 'home'],
            handler: function() {
                const ctx = window.HKS ? window.HKS.getContext() : 'global';
                if (ctx === 'hub') {
                    // Already in hub — activate HPM tab if available
                    if (typeof window.activateTab === 'function') {
                        window.activateTab('packages');
                    } else if (typeof window.navigateToTab === 'function') {
                        window.navigateToTab('packages');
                    } else {
                        // Try clicking the tab link
                        const tab = document.querySelector('[data-tab="packages"], [href="#packages"]');
                        if (tab) tab.click();
                    }
                } else {
                    window.open('/hecos/config/ui#packages', '_blank', 'noopener');
                }
            }
        },

        {
            id: 'nav.drive',
            label: 'Open Drive',
            icon: 'fas fa-hdd',
            category: 'navigation',
            description: 'Open Hecos Drive (if installed)',
            contexts: ['global', 'chat', 'hub', 'home'],
            handler: function() {
                window.open('/drive', '_blank', 'noopener');
            }
        },

        {
            id: 'nav.flows',
            label: 'Open Flows',
            icon: 'fas fa-project-diagram',
            category: 'navigation',
            description: 'Open Hecos Flows (if installed)',
            contexts: ['global', 'chat', 'hub', 'home'],
            handler: function() {
                window.open('/flows', '_blank', 'noopener');
            }
        },

        {
            id: 'nav.shortcuts',
            label: 'Keyboard Shortcuts Panel',
            icon: 'fas fa-keyboard',
            category: 'navigation',
            description: 'Open the Keyboard Shortcuts control panel',
            contexts: ['global', 'chat', 'hub', 'home'],
            handler: function() {
                const ctx = window.HKS ? window.HKS.getContext() : 'global';
                if (ctx === 'hub') {
                    // Navigate to shortcuts tab in hub
                    if (typeof window.navigateToTab === 'function') {
                        window.navigateToTab('shortcuts');
                    } else {
                        const tab = document.querySelector('[data-tab="shortcuts"]');
                        if (tab) tab.click();
                    }
                } else {
                    window.open('/hecos/config/ui#shortcuts', '_blank', 'noopener');
                }
            }
        },

        // ── CHAT UI ───────────────────────────────────────────────────────────

        {
            id: 'ui.toggle_room',
            label: 'Toggle Room Panel',
            icon: 'fas fa-sidebar',
            category: 'chat',
            description: 'Show/hide the detachable Control Room panel in Chat',
            contexts: ['chat'],
            handler: function() {
                // Try control_room.js API first
                if (typeof window.controlRoom !== 'undefined' && typeof window.controlRoom.toggle === 'function') {
                    window.controlRoom.toggle();
                    return;
                }
                // Fallback: click the room toggle button
                const btn = document.getElementById('room-toggle-btn') ||
                            document.querySelector('[data-action="toggle-room"]') ||
                            document.querySelector('.room-toggle-btn');
                if (btn) btn.click();
            }
        },

        {
            id: 'ui.toggle_sidebar',
            label: 'Toggle Chat Sidebar',
            icon: 'fas fa-bars',
            category: 'chat',
            description: 'Show/hide the chat history sidebar',
            contexts: ['chat'],
            handler: function() {
                const sidebar = document.getElementById('sidebar');
                if (!sidebar) return;
                sidebar.classList.toggle('open');
                // Also handle mobile overlay
                const overlay = document.getElementById('mobile-overlay');
                if (overlay) overlay.classList.toggle('active', sidebar.classList.contains('open'));
            }
        },

        {
            id: 'ui.toggle_mic',
            label: 'Toggle Microphone',
            description: 'Turn the microphone on or off (WebRTC/Chat)',
            icon: 'fas fa-microphone',
            category: 'chat',
            contexts: ['chat'],
            handler: () => {
                const btn = document.getElementById('mic-btn') || document.querySelector('.mic-btn');
                if (btn) btn.click();
                else console.log('[HKS] Mic toggle requested, but button not found.');
            }
        },

        {
            id: 'ui.toggle_voice',
            label: 'Toggle Voice Output',
            description: 'Turn TTS voice output on or off',
            icon: 'fas fa-volume-up',
            category: 'chat',
            contexts: ['chat'],
            handler: () => {
                const btn = document.getElementById('voice-output-btn');
                if (btn) btn.click();
            }
        },

        {
            id: 'ui.toggle_ptt',
            label: 'Toggle Push To Talk Mode',
            description: 'Enable or disable PTT mode',
            icon: 'fas fa-headset',
            category: 'chat',
            contexts: ['chat'],
            handler: () => {
                const btn = document.getElementById('ptt-mode-btn');
                if (btn) btn.click();
            }
        },

        {
            id: 'ui.ptt_trigger',
            label: 'Push To Talk (Hold)',
            description: 'Hold Ctrl+Shift to talk (while PTT is enabled)',
            icon: 'fas fa-walkie-talkie',
            category: 'chat',
            contexts: ['chat'],
            handler: () => {
                // Handled implicitly via keydown/keyup events in chat.js
                // This entry is mostly to show it in the Cheatsheet HUD
                console.log('[HKS] PTT key combo pressed.');
            }
        },

        {
            id: 'ui.new_chat',
            label: 'New Conversation',
            icon: 'fas fa-plus',
            category: 'chat',
            description: 'Start a fresh conversation',
            contexts: ['chat'],
            handler: function() {
                if (typeof window.newChat === 'function') {
                    window.newChat();
                    return;
                }
                const btn = document.getElementById('new-chat-btn') ||
                            document.querySelector('[data-action="new-chat"]') ||
                            document.querySelector('.new-chat-btn');
                if (btn) btn.click();
            }
        },

        {
            id: 'ui.focus_input',
            label: 'Focus Chat Input',
            icon: 'fas fa-keyboard',
            category: 'chat',
            description: 'Move keyboard focus to the chat input field',
            contexts: ['chat'],
            handler: function() {
                const input = document.getElementById('user-input') ||
                              document.querySelector('textarea.chat-input') ||
                              document.querySelector('#chat-input');
                if (input) {
                    input.focus();
                    input.setSelectionRange(input.value.length, input.value.length);
                }
            }
        },

        {
            id: 'ui.toggle_history',
            label: 'Toggle History Panel',
            icon: 'fas fa-history',
            category: 'chat',
            description: 'Show/hide the chat history panel',
            contexts: ['chat'],
            handler: function() {
                const panel = document.getElementById('chat-history-panel') ||
                              document.querySelector('.chat-history-panel');
                if (panel) {
                    panel.classList.toggle('open');
                    panel.classList.toggle('visible');
                } else {
                    // Try history toggle button
                    const btn = document.getElementById('history-panel-toggle') ||
                                document.querySelector('[data-action="toggle-history"]');
                    if (btn) btn.click();
                }
            }
        },

        {
            id: 'ui.copy_last',
            label: 'Copy Last AI Response',
            icon: 'fas fa-copy',
            category: 'chat',
            description: 'Copy the most recent AI response to clipboard',
            contexts: ['chat'],
            handler: function() {
                // Find the last AI bubble
                const aiMessages = document.querySelectorAll('.message-bubble.ai, .bubble-ai, [data-role="ai"]');
                if (aiMessages.length === 0) return;
                const last = aiMessages[aiMessages.length - 1];
                const text = last.innerText || last.textContent || '';
                if (text) {
                    navigator.clipboard.writeText(text.trim()).then(() => {
                        if (typeof window.showToast === 'function') {
                            window.showToast('Last response copied!', 'success');
                        }
                    }).catch(() => {
                        if (typeof window.showToast === 'function') {
                            window.showToast('Could not copy', 'error');
                        }
                    });
                }
            }
        },

        // ── SYSTEM UI ─────────────────────────────────────────────────────────

        {
            id: 'ui.fullscreen',
            label: 'Toggle Fullscreen',
            icon: 'fas fa-expand',
            category: 'system',
            description: 'Toggle browser fullscreen mode',
            contexts: ['global', 'chat', 'hub', 'home'],
            handler: function() {
                if (!document.fullscreenElement) {
                    document.documentElement.requestFullscreen().catch(err => {
                        console.warn('[HKS] Fullscreen error:', err);
                    });
                } else {
                    document.exitFullscreen().catch(err => {
                        console.warn('[HKS] Exit fullscreen error:', err);
                    });
                }
            }
        },

        {
            id: 'ui.open_hdcs',
            label: 'Command Palette (HDCS)',
            icon: 'fas fa-terminal',
            category: 'system',
            description: 'Open the universal command palette',
            contexts: ['global', 'chat', 'hub', 'home'],
            handler: () => {
                if (window.HecosCmd && typeof window.HecosCmd.open === 'function') {
                    window.HecosCmd.open();
                }
            }
        },

        {
            id: 'sys.reboot',
            label: 'Reboot System',
            description: 'Ask for confirmation and reboot Hecos',
            icon: 'fas fa-power-off',
            category: 'system',
            contexts: ['global', 'chat', 'hub', 'home'],
            handler: () => {
                if (confirm('Reboot Hecos System?')) {
                    fetch('/api/system/reboot', { method: 'POST' })
                    .then(res => res.json())
                    .then(data => {
                        if (data.ok) alert('System is rebooting...');
                        else alert('Error: ' + (data.error || 'Unknown'));
                    });
                }
            }
        },

        {
            id: 'ui.show_cheatsheet',
            label: 'Show Shortcuts Cheatsheet',
            icon: 'fas fa-question-circle',
            category: 'system',
            description: 'Display the keyboard shortcuts HUD overlay',
            contexts: ['global', 'chat', 'hub', 'home'],
            handler: function() {
                if (window.HKS_OVERLAY && typeof window.HKS_OVERLAY.toggle === 'function') {
                    window.HKS_OVERLAY.toggle();
                }
            }
        },

        {
            id: 'ui.close_modal',
            label: 'Close Panel / Modal',
            icon: 'fas fa-times',
            category: 'system',
            description: 'Close the currently active panel, modal, or overlay',
            contexts: ['global', 'chat', 'hub', 'home'],
            handler: function() {
                // Try to close HKS overlay first
                if (window.HKS_OVERLAY && window.HKS_OVERLAY.isVisible()) {
                    window.HKS_OVERLAY.hide();
                    return;
                }
                // Try to close HDCS spotlight
                if (window.HecosCmd && typeof window.HecosCmd.close === 'function') {
                    const overlay = document.getElementById('hdcs-overlay');
                    if (overlay && overlay.style.display !== 'none') {
                        window.HecosCmd.close();
                        return;
                    }
                }
                // Click any visible close button
                const closeBtn = document.querySelector(
                    '.modal.active .btn-close, .overlay.active .close-btn, ' +
                    '.panel.open .close-btn, [aria-label="Close"]:not([hidden])'
                );
                if (closeBtn) {
                    closeBtn.click();
                    return;
                }
                // Dispatch generic Escape event to the DOM
                document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
            }
        },

        // ── FOCUS CYCLING ─────────────────────────────────────────────────────

        {
            id: 'focus.next',
            label: 'Focus Next Area (Tab cycle)',
            icon: 'fas fa-arrow-right',
            category: 'navigation',
            description: 'Move focus to the next main UI area',
            contexts: ['global', 'chat', 'hub', 'home'],
            handler: function() {
                if (window.HKS) window.HKS.cycleFocus(false);
            }
        },

        {
            id: 'focus.prev',
            label: 'Focus Previous Area (Tab cycle)',
            icon: 'fas fa-arrow-left',
            category: 'navigation',
            description: 'Move focus to the previous main UI area',
            contexts: ['global', 'chat', 'hub', 'home'],
            handler: function() {
                if (window.HKS) window.HKS.cycleFocus(true);
            }
        }

    ];

    // ── Registration ──────────────────────────────────────────────────────────

    function _registerAll() {
        if (!window.HKS) {
            console.error('[HKS Actions] HKS core not loaded! Cannot register actions.');
            return;
        }
        ACTIONS.forEach(action => {
            window.HKS.register(action.id, action.handler, { contexts: action.contexts });
        });
        console.log(`[HKS Actions] Registered ${ACTIONS.length} actions.`);
    }

    // ── Public API ────────────────────────────────────────────────────────────

    window.HKS_ACTIONS = {
        /**
         * Get all available actions as an array (for the UI).
         */
        getAll() { return ACTIONS; },

        /**
         * Get actions grouped by category.
         */
        getByCategory() {
            const groups = {};
            ACTIONS.forEach(a => {
                if (!groups[a.category]) groups[a.category] = [];
                groups[a.category].push(a);
            });
            return groups;
        },

        /**
         * Find action by ID.
         */
        find(id) { return ACTIONS.find(a => a.id === id) || null; },

        /**
         * Category display names and order.
         */
        CATEGORIES: {
            navigation: { order: 1, label: 'Navigation', icon: 'fas fa-compass' },
            chat:       { order: 2, label: 'Chat & Voice', icon: 'fas fa-comments' },
            system:     { order: 3, label: 'System',     icon: 'fas fa-cogs' }
        }
    };

    // Register after core is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', _registerAll);
    } else {
        _registerAll();
    }

})();
