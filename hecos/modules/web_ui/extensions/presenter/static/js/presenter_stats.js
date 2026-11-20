/**
 * Hecos Presenter — Statistics Engine
 * Tracks the total count of each event type handled by the Presenter.
 */
(function() {
    'use strict';

    const counts = {};

    function increment(type) {
        if (!type) type = 'system_info';
        if (!counts[type]) {
            counts[type] = 0;
        }
        counts[type]++;
        
        // Notify the UI to update
        if (window.HBSPresenterStatsUI && typeof window.HBSPresenterStatsUI.update === 'function') {
            window.HBSPresenterStatsUI.update(type, counts[type]);
        }
    }

    function getCounts() {
        return { ...counts };
    }

    function clear() {
        for (let key in counts) {
            delete counts[key];
        }
        if (window.HBSPresenterStatsUI && typeof window.HBSPresenterStatsUI.render === 'function') {
            window.HBSPresenterStatsUI.render();
        }
    }

    function syncFromDOM() {
        const emb = document.getElementById('hbs-presenter-embedded');
        if (!emb) return false;
        const lines = emb.querySelectorAll('.hbs-presenter-line');
        if (!lines || lines.length === 0) return false;

        for (let key in counts) {
            delete counts[key];
        }
        lines.forEach(line => {
            const type = line.dataset.logType || 'system_info';
            counts[type] = (counts[type] || 0) + 1;
        });

        if (window.HBSPresenterStatsUI && typeof window.HBSPresenterStatsUI.render === 'function') {
            window.HBSPresenterStatsUI.render();
        }
        return true;
    }

    window.HBSPresenterStats = {
        increment,
        getCounts,
        clear,
        syncFromDOM
    };

})();
