/**
 * ws_chips.js — Welcome Screen Chip Renderer
 * Part of: welcome_screen/ module
 *
 * Bridge between the Welcome Screen and the DCC engine.
 * Strategy:
 *   1. Render static chips immediately (instant UX).
 *   2. When DCC fetch completes (async), swap to dynamic chips.
 */
(function() {
    'use strict';

    const STATIC_CHIPS = [
        { icon: 'fas fa-chart-bar',    labelKey: 'webui_chat_chip_report',  prompt: 'Give me a system report' },
        { icon: 'fas fa-puzzle-piece', labelKey: 'webui_chat_chip_plugins', prompt: 'What modules do you have available?' },
        { icon: 'fas fa-rocket',       labelKey: 'webui_chat_chip_program', prompt: 'Open Chrome' },
        { icon: 'fas fa-globe',        labelKey: 'webui_chat_chip_web',     prompt: 'Search online for the latest news' },
    ];

    /** Reference to the chips wrapper rendered into the current welcome */
    let _mountedWrapper = null;
    let _mountedContainer = null;

    /**
     * Render chips into a container.
     * Shows static chips immediately, then replaces with DCC chips when ready.
     */
    function render(container) {
        _mountedContainer = container;

        // If DCC is already ready (pre-fetched before welcome rendered), use it directly
        if (window.DccEngine && window.DccEngine.isReady()) {
            _mountedWrapper = window.DccEngine.renderChips(container);
            return _mountedWrapper;
        }

        // DCC not ready yet — render static chips as placeholder
        _mountedWrapper = renderStatic(container);

        // Poll for DCC readiness and swap chips once loaded
        _waitForDcc();

        return _mountedWrapper;
    }

    /**
     * Wait for DccEngine to become ready, then swap out static chips.
     */
    function _waitForDcc() {
        let attempts = 0;
        const maxAttempts = 30; // 3 seconds max wait
        const interval = setInterval(() => {
            attempts++;
            if (window.DccEngine && window.DccEngine.isReady()) {
                clearInterval(interval);
                _swapToDynamic();
                return;
            }
            if (attempts >= maxAttempts) {
                clearInterval(interval);
                console.log('[WelcomeChips] DCC not available, keeping static chips.');
            }
        }, 100);
    }

    /**
     * Replace static chips with DCC dynamic chips.
     */
    function _swapToDynamic() {
        if (!_mountedContainer || !window.DccEngine) return;

        // Only swap if the chips wrapper is still in the DOM (welcome not dismissed)
        if (!_mountedWrapper || !_mountedWrapper.isConnected) return;

        const newWrapper = window.DccEngine.renderChips(_mountedContainer);
        if (newWrapper && _mountedWrapper && _mountedWrapper.isConnected) {
            _mountedWrapper.replaceWith(newWrapper);
            _mountedWrapper = newWrapper;
        }
    }

    /**
     * Render the 4 static fallback chips.
     */
    function renderStatic(container) {
        const wrapper = document.createElement('div');
        wrapper.className = 'quick-chips';

        STATIC_CHIPS.forEach(chip => {
            const el = document.createElement('div');
            el.className = 'chip';
            const label = (window.I18N && window.I18N[chip.labelKey]) || chip.labelKey;
            el.innerHTML = `<i class="${chip.icon}"></i> ${label}`;
            el.addEventListener('click', () => {
                if (window.HecosWelcome) window.HecosWelcome.startPrompt(chip.prompt);
            });
            wrapper.appendChild(el);
        });

        container.appendChild(wrapper);
        return wrapper;
    }

    window.WelcomeChips = { render, renderStatic, STATIC_CHIPS };
})();
