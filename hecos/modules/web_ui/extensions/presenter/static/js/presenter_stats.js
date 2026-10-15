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

    window.HBSPresenterStats = {
        increment,
        getCounts,
        clear
    };

})();
