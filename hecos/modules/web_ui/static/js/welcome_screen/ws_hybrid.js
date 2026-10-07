/**
 * ws_hybrid.js — Hybrid Welcome Transition Logic
 * Part of: welcome_screen/ module
 *
 * Manages the transition from the Main Welcome to the Avatar card
 * when the user clicks on the chat area, focuses the input, or
 * presses Ctrl+Shift.
 */
(function() {
    'use strict';

    let _listeners = null;

    /**
     * Set up hybrid mode listeners.
     * When triggered: fades out Main Welcome → reveals Avatar card.
     *
     * @param {HTMLElement} chatArea
     * @param {HTMLElement} mainEl      - The #welcome element
     * @param {HTMLElement} avatarEl    - The #hecos-welcome-screen container
     */
    function setup(chatArea, mainEl, avatarEl) {
        cleanup(); // Remove any previous listeners

        const handleTrigger = (forceAvatar = false) => {
            // Don't transition if real messages arrived
            const hasMsgs = Array.from(chatArea.children).some(
                el => el.classList.contains('msg') || el.classList.contains('hbs-presenter-line')
            );
            if (hasMsgs) { cleanup(); return; }

            const showingMain = mainEl && mainEl.style.display !== 'none';

            if (showingMain) {
                // Fade out Main Welcome -> Show Avatar
                mainEl.style.transition = 'opacity 0.25s ease-out';
                mainEl.style.opacity = '0';
                setTimeout(() => {
                    mainEl.style.display = 'none';
                    mainEl.style.opacity = '1';
                    mainEl.style.transition = '';
                    if (window.WelcomeAvatar) {
                        avatarEl = window.WelcomeAvatar.render(chatArea, { hidden: false });
                    }
                    if (avatarEl) {
                        avatarEl.style.display = 'flex';
                        setTimeout(() => {
                            if (window.WelcomeAvatar) window.WelcomeAvatar.animate();
                        }, 50);
                    }
                }, 250);
            } else if (!forceAvatar) {
                // Fade out Avatar -> Show Main Welcome
                if (avatarEl) {
                    const card = avatarEl.querySelector('#hecos-welcome-card');
                    const text = avatarEl.querySelector('#hecos-welcome-text');
                    if (card) card.classList.remove('is-flipped');
                    if (text) text.classList.remove('show');
                    
                    setTimeout(() => {
                        avatarEl.style.display = 'none';
                        if (mainEl) {
                            mainEl.style.opacity = '0';
                            mainEl.style.display = 'flex';
                            setTimeout(() => {
                                mainEl.style.transition = 'opacity 0.25s ease-out';
                                mainEl.style.opacity = '1';
                            }, 50);
                        }
                    }, 350); // wait for reverse flip
                }
            }
        };

        const onGlobalClick = (e) => {
            // Force avatar if clicking input or mic buttons
            if (e.target.closest('#user-input') || e.target.closest('#web-ptt-btn') || e.target.closest('#mic-btn')) {
                handleTrigger(true);
                return;
            }
            // Toggle if clicking on an empty area of the chat background
            if (e.target.closest('#chat-area') && !e.target.closest('.chip') && !e.target.closest('.dcc-view-header')) {
                handleTrigger(false);
            }
        };

        const onKeydown = (e) => {
            if ((e.key === 'Shift' && e.ctrlKey) || (e.key === 'Control' && e.shiftKey)) {
                handleTrigger();
            }
        };

        document.addEventListener('click', onGlobalClick);
        document.addEventListener('keydown', onKeydown);

        _listeners = { handleTrigger, onGlobalClick, onKeydown };

        // Expose manual trigger
        if (window.HecosWelcome) {
            window.HecosWelcome.triggerHybrid = () => {
                if (avatarEl && avatarEl.style.display === 'none') {
                    handleTrigger();
                }
            };
        }
    }

    /**
     * Remove all hybrid listeners (cleanup on transition or chat clear).
     */
    function cleanup() {
        if (!_listeners) return;
        const { input, handleTrigger, onGlobalClick, onKeydown } = _listeners;
        if (input) input.removeEventListener('focus', handleTrigger);
        document.removeEventListener('click', onGlobalClick);
        document.removeEventListener('keydown', onKeydown);
        _listeners = null;
    }

    window.WelcomeHybrid = { setup, cleanup };
})();
