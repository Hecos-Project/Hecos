/**
 * ws_main.js — Main Welcome Screen
 * Part of: welcome_screen/ module
 *
 * Renders the primary welcome: Hecos logo, greeting title,
 * subtitle, and quick-action chips.
 * This is the MAIN welcome — the first thing users see.
 */
(function() {
    'use strict';

    /**
     * Render the Main Welcome into the chat area.
     * @param {HTMLElement} chatArea
     * @returns {HTMLElement|null} The welcome element, or null if it already exists
     */
    function render(chatArea) {
        // Reuse existing element if present
        let el = document.getElementById('welcome');
        if (el) {
            chatArea.appendChild(el);
            el.style.display = 'flex';
            // Destroy old chips and rebuild fresh (so shuffle randomizes)
            const oldNav = el.querySelector('.dcc-nav-container');
            if (oldNav) oldNav.remove();
            const oldChips = el.querySelector('.quick-chips');
            if (oldChips) oldChips.remove();
            if (window.WelcomeChips) {
                window.WelcomeChips.render(el);
            }
            return el;
        }

        // Build from scratch
        el = document.createElement('div');
        el.id = 'welcome';

        const I = window.I18N || {};

        // Logo
        const logoWrap = document.createElement('div');
        logoWrap.className = 'welcome-logo';
        const logoImg = document.createElement('img');
        logoImg.src = '/assets/Hecos_Logo_SQR_NBG_LogoOnly.png';
        logoImg.alt = 'Hecos Logo';
        logoWrap.appendChild(logoImg);
        el.appendChild(logoWrap);

        // Title
        const title = document.createElement('div');
        title.className = 'welcome-title';
        title.textContent = I['webui_chat_welcome_title'] || 'Welcome';
        el.appendChild(title);

        // Subtitle
        const sub = document.createElement('div');
        sub.className = 'welcome-sub';
        sub.textContent = I['webui_chat_welcome_sub'] || 'Always by your side. The soul of the system at your service.';
        el.appendChild(sub);

        // Chips (via ws_chips.js)
        if (window.WelcomeChips) {
            window.WelcomeChips.render(el);
        }

        chatArea.appendChild(el);
        return el;
    }

    /**
     * Hide the Main Welcome.
     */
    function hide() {
        const el = document.getElementById('welcome');
        if (el) el.style.display = 'none';
    }

    /**
     * Show the Main Welcome (if it exists in the DOM).
     */
    function show() {
        const el = document.getElementById('welcome');
        if (el) el.style.display = 'flex';
    }

    window.WelcomeMain = { render, hide, show };
})();
