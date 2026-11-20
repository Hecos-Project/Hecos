/**
 * Hecos Presenter — Statistics UI
 * Renders an Excel-style summary of events in the subbar.
 */
(function() {
    'use strict';

    function getContainer() {
        const emb = document.getElementById('hbs-presenter-embedded');
        if (emb) {
            const c = emb.querySelector('#hbs-presenter-stats-container');
            if (c) return c;
        }
        return document.getElementById('hbs-presenter-stats-container');
    }

    function render() {
        const container = getContainer();
        if (!container) return;

        // In NetSearch sidebar, hide stats container completely
        const isNetSearch = container.closest('.netsearch-presenter-embedded') || 
                            container.closest('.search-copilot') || 
                            (window.location && window.location.pathname.includes('/netsearch'));
        if (isNetSearch) {
            container.style.display = 'none';
            return;
        }

        let counts = window.HBSPresenterStats ? window.HBSPresenterStats.getCounts() : {};
        if (Object.keys(counts).length === 0 && window.HBSPresenterStats && typeof window.HBSPresenterStats.syncFromDOM === 'function') {
            window.HBSPresenterStats.syncFromDOM();
            counts = window.HBSPresenterStats.getCounts();
        }

        container.innerHTML = '';

        if (Object.keys(counts).length === 0) {
            container.style.display = 'inline-flex';
            container.title = 'No notification events recorded yet';
            container.innerHTML = `
                <span style="display:inline-flex; align-items:center; gap:4px; opacity:0.55; font-size:9.5px; padding:1px 4px; user-select:none;">
                    <i class="fas fa-chart-bar" style="font-size:9px;"></i>
                    <span>0 events</span>
                </span>
            `;
            return;
        }

        container.style.display = 'inline-flex';

        // Get metadata for coloring/icons
        const meta = window.HBSPresenterState ? window.HBSPresenterState.TYPE_META : {};
        const entries = Object.entries(counts);

        entries.forEach(([type, count], idx) => {
            const m = meta[type] || meta['default'] || { color: '#ccc', icon: 'fas fa-info-circle', tooltip: type };
            const label = m.tooltip || type;
            
            const cell = document.createElement('div');
            cell.id = `hbs-stat-${type}`;
            cell.className = 'hbs-presenter-stat-cell';
            cell.title = `${count} ${label}`;
            cell.style.cssText = `
                display: inline-flex;
                align-items: center;
                gap: 4px;
                padding: 1px 6px;
                cursor: default;
                user-select: none;
                transition: background 0.15s ease;
            `;
            if (idx < entries.length - 1) {
                cell.style.borderRight = '1px solid rgba(255, 255, 255, 0.1)';
            }

            cell.innerHTML = `
                <i class="${m.icon}" style="color: ${m.color}; font-size: 9.5px;"></i>
                <span class="stat-value" style="color: var(--text); font-weight: 600; font-size: 10px;">${count}</span>
            `;
            container.appendChild(cell);
        });
    }

    function update(type, count) {
        let container = getContainer();
        if (!container) {
            render();
            return;
        }

        const isNetSearch = container.closest('.netsearch-presenter-embedded') || 
                            container.closest('.search-copilot') || 
                            (window.location && window.location.pathname.includes('/netsearch'));
        if (isNetSearch) return;

        const cellId = `hbs-stat-${type}`;
        let cell = container.querySelector(`#${cellId}`);

        if (cell) {
            const valEl = cell.querySelector('.stat-value');
            if (valEl) {
                valEl.textContent = count;
                valEl.style.color = '#fff';
                valEl.style.textShadow = '0 0 4px #fff';
                setTimeout(() => {
                    valEl.style.color = 'var(--text)';
                    valEl.style.textShadow = 'none';
                }, 300);
            }
            const meta = window.HBSPresenterState ? window.HBSPresenterState.TYPE_META : {};
            const m = meta[type] || meta['default'] || {};
            cell.title = `${count} ${m.tooltip || type}`;
        } else {
            render();
        }
    }

    window.HBSPresenterStatsUI = {
        render,
        update
    };

})();
