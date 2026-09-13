/**
 * Quick Config HUD - Lazy Loader
 * Included in the main chat bundle. Loads actual HUD logic and styles only when opened.
 */

window.openQuickConfig = function() {
    // 1. Play sound
    try {
        const audio = new Audio('/assets/sounds/beep-6.mp3');
        audio.volume = window.globalTTSVolume ? (window.globalTTSVolume / 100) : 0.5;
        audio.play().catch(e => console.log('Audio play prevented:', e));
    } catch(e) {}

    // 2. Load CSS if not already loaded
    if (!document.getElementById('qc-styles')) {
        const link = document.createElement('link');
        link.id = 'qc-styles';
        link.rel = 'stylesheet';
        link.href = '/static/css/quick_config/qc_styles.css?v=' + Date.now();
        document.head.appendChild(link);
    }

    // 3. Load Main Logic if not already loaded
    if (!window.qcIsLoaded) {
        // We load API first, then Main
        const loadScript = (src) => new Promise((resolve) => {
            const s = document.createElement('script');
            s.src = src + '?v=' + Date.now();
            s.onload = resolve;
            document.body.appendChild(s);
        });

        Promise.all([
            loadScript('/static/js/quick_config/qc_api.js'),
            loadScript('/static/js/quick_config/qc_main.js')
        ]).then(() => {
            window.qcIsLoaded = true;
            if (window._qcInitAndShow) window._qcInitAndShow();
        });
    } else {
        if (window._qcInitAndShow) window._qcInitAndShow();
    }
};

window.closeQuickConfig = function() {
    const overlay = document.getElementById('qc-hud-overlay');
    if (overlay) overlay.classList.add('qc-hud-hidden');
};

document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        const overlay = document.getElementById('qc-hud-overlay');
        if (overlay && !overlay.classList.contains('qc-hud-hidden')) {
            window.closeQuickConfig();
            e.stopPropagation(); // prevent other escape handlers if HUD is open
        }
    }
});
