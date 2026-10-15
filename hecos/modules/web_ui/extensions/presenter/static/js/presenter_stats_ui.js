/**
 * Hecos Presenter — Statistics UI
 * Renders an Excel-style summary of events in the header.
 */
(function() {
    'use strict';

    function getContainer() {
        return document.getElementById('hbs-presenter-stats-container');
    }

    function render() {
        const header = document.querySelector('.hbs-presenter-header');
        if (!header) return;

        let container = getContainer();
        if (!container) {
            container = document.createElement('div');
            container.id = 'hbs-presenter-stats-container';
            // Styling it like a mini Excel table / data row
            container.style.cssText = `
                display: flex;
                align-items: center;
                gap: 8px;
                margin-left: 12px;
                padding: 2px 6px;
                background: rgba(0, 0, 0, 0.25);
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 4px;
                font-family: monospace;
                font-size: 10px;
                color: var(--muted);
                overflow-x: hidden;
            `;
            
            // Insert it right after the title
            const titleEl = header.querySelector('.hbs-presenter-title');
            if (titleEl && titleEl.nextSibling) {
                header.insertBefore(container, titleEl.nextSibling);
            } else {
                header.appendChild(container);
            }
        }

        const counts = window.HBSPresenterStats ? window.HBSPresenterStats.getCounts() : {};
        container.innerHTML = '';
        
        if (Object.keys(counts).length === 0) {
            container.style.display = 'none';
            return;
        }
        
        container.style.display = 'flex';

        // Get metadata for coloring/icons
        const meta = window.HBSPresenterState ? window.HBSPresenterState.TYPE_META : {};

        for (const [type, count] of Object.entries(counts)) {
            const m = meta[type] || meta['default'] || { color: '#ccc', icon: 'fas fa-info-circle' };
            
            const cell = document.createElement('div');
            cell.id = `hbs-stat-${type}`;
            cell.title = type;
            cell.style.cssText = `
                display: flex;
                align-items: center;
                gap: 4px;
                padding-right: 6px;
                border-right: 1px solid rgba(255, 255, 255, 0.1);
            `;
            // Remove border from last element
            if (Object.keys(counts).indexOf(type) === Object.keys(counts).length - 1) {
                cell.style.borderRight = 'none';
            }

            cell.innerHTML = `
                <i class="${m.icon}" style="color: ${m.color}; font-size: 9px;"></i>
                <span class="stat-value" style="color: var(--text); font-weight: 600;">${count}</span>
            `;
            container.appendChild(cell);
        }
    }

    function update(type, count) {
        let container = getContainer();
        // If container doesn't exist, we haven't rendered yet
        if (!container) {
            render();
            return;
        }
        
        const cellId = `hbs-stat-${type}`;
        let cell = document.getElementById(cellId);
        
        if (cell) {
            // Update existing cell
            const valEl = cell.querySelector('.stat-value');
            if (valEl) {
                valEl.textContent = count;
                // Add a small flash effect
                valEl.style.color = '#fff';
                valEl.style.textShadow = '0 0 4px #fff';
                setTimeout(() => {
                    valEl.style.color = 'var(--text)';
                    valEl.style.textShadow = 'none';
                }, 300);
            }
        } else {
            // New type appeared, re-render the whole container to add it
            render();
        }
    }

    window.HBSPresenterStatsUI = {
        render,
        update
    };

})();
