/**
 * ws_core.js — Welcome Screen Orchestrator
 * Part of: welcome_screen/ module
 *
 * Public API: window.HecosWelcome
 *   .show()           — Render the appropriate welcome based on mode
 *   .remove()         — Remove all welcome elements
 *   .hide()           — Hide all welcome elements
 *   .startPrompt(t)   — Execute a chip prompt
 *   .triggerHybrid()   — Manually trigger hybrid transition (set by ws_hybrid)
 *
 * Reads welcome mode from: window.cfg?.plugins?.WEB_UI?.chatui_welcome_mode
 * Modes: 'classic' | 'avatar' | 'hybrid' (default)
 *
 * Dependencies (loaded before this file):
 *   ws_chips.js   → window.WelcomeChips
 *   ws_main.js    → window.WelcomeMain
 *   ws_avatar.js  → window.WelcomeAvatar
 *   ws_hybrid.js  → window.WelcomeHybrid
 */
(function() {
    'use strict';

    /**
     * Get current welcome mode from config.
     */
    function getMode() {
        return window.cfg?.plugins?.WEB_UI?.chatui_welcome_mode || 'hybrid';
    }

    /**
     * Show the welcome screen. Idempotent — safe to call multiple times.
     * Removes previous state and re-renders based on current mode & soul.
     */
    function show(isUpdate = false) {
        const chatArea = document.getElementById('chat-area');
        if (!chatArea) return;

        // Don't show if chat already has real messages
        const messages = Array.from(chatArea.children).filter(
            el => el.classList.contains('msg') || el.classList.contains('hbs-presenter-line')
        );
        if (messages.length > 0) return;

        const mode = getMode();

        let isHybridAvatarVisible = false;
        if (mode === 'hybrid') {
            const oldMain = document.getElementById('welcome');
            if (oldMain && oldMain.style.display === 'none') {
                isHybridAvatarVisible = true;
            }
        }

        // Clean up previous avatar welcome
        if (window.WelcomeAvatar) window.WelcomeAvatar.remove();
        if (window.WelcomeHybrid) window.WelcomeHybrid.cleanup();

        // ── CLASSIC: only Main Welcome (logo + chips) ──
        if (mode === 'classic') {
            if (window.WelcomeMain) window.WelcomeMain.render(chatArea);
            if (window.WelcomeMain) window.WelcomeMain.show();
            return;
        }

        // ── AVATAR: only Avatar 3D card ──
        if (mode === 'avatar') {
            if (window.WelcomeMain) window.WelcomeMain.hide();
            if (window.WelcomeAvatar) {
                if (isUpdate) {
                    window.WelcomeAvatar.render(chatArea, { hidden: false, flipped: true });
                } else {
                    window.WelcomeAvatar.render(chatArea, { hidden: false });
                    setTimeout(() => window.WelcomeAvatar.animate(), 100);
                }
            }
            return;
        }

        // ── HYBRID: Main first, then Avatar on interaction ──
        const mainEl = window.WelcomeMain ? window.WelcomeMain.render(chatArea) : null;
        
        if (isHybridAvatarVisible) {
            if (window.WelcomeMain) window.WelcomeMain.hide();
        } else {
            if (window.WelcomeMain) window.WelcomeMain.show();
        }

        if (window.WelcomeAvatar) {
            const avatarEl = window.WelcomeAvatar.render(chatArea, { hidden: !isHybridAvatarVisible, flipped: isHybridAvatarVisible });
            if (window.WelcomeHybrid && mainEl && avatarEl) {
                window.WelcomeHybrid.setup(chatArea, mainEl, avatarEl);
            }
            if (isHybridAvatarVisible) {
                avatarEl.style.display = 'flex';
                // We don't animate anymore, the flipped flag renders it already flipped
            } else if (isUpdate) {
                // The persona was changed while on the main welcome screen.
                // Trigger the hybrid transition so the user sees the new persona card flip in!
                setTimeout(() => {
                    if (window.HecosWelcome.triggerHybrid) window.HecosWelcome.triggerHybrid();
                }, 10);
            }
        }
    }

    /**
     * Remove all welcome elements from the DOM.
     */
    function remove() {
        if (window.WelcomeAvatar) window.WelcomeAvatar.remove();
        if (window.WelcomeHybrid) window.WelcomeHybrid.cleanup();
        // Main welcome is just hidden, not removed (it gets reused)
        if (window.WelcomeMain) window.WelcomeMain.hide();
    }

    /**
     * Hide all welcome elements (without removing from DOM).
     */
    function hide() {
        if (window.WelcomeMain) window.WelcomeMain.hide();
        if (window.WelcomeAvatar) window.WelcomeAvatar.remove();
        if (window.WelcomeHybrid) window.WelcomeHybrid.cleanup();
    }

    /**
     * Execute a chip prompt — types text into the input and sends.
     */
    function startPrompt(text) {
        if (window.userInput) {
            window.userInput.value = text;
            if (window.autoResize) window.autoResize(window.userInput);
            if (window.sendMessage) window.sendMessage();
        }
    }

    // ── Public API ──
    window.HecosWelcome = {
        show,
        remove,
        hide,
        startPrompt,
        triggerHybrid: null  // Set dynamically by ws_hybrid.js
    };

    // Auto-init: render the welcome on page load
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', show);
    } else {
        // DOM already ready (script loaded at bottom of body)
        show();
    }

})();
