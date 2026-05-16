/**
 * standalone_logs_engine.js
 * ─────────────────────────────────────────────────────────────────────────────
 * Hecos Standalone Logs — Page Logic
 * Handles: layout persistence (save/load/reset), card height calculation,
 * persistence controls injection, connection monitoring and auto-reconnect.
 * No Jinja2 dependencies — reads data from window globals set by the
 * bootstrap partial (_standalone_logs_bootstrap.html).
 * ─────────────────────────────────────────────────────────────────────────────
 */

// ─────────────────────────────────────────────────────────────────────────────
// Global Overrides (patching functions from config_logs_engine.js)
// ─────────────────────────────────────────────────────────────────────────────

// Global utility used by logs engine
window.escapeHtml = function(text) {
    if (!text) return "";
    return text.toString()
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");
};

// Override forceTrimLines to also update card height
const _originalForceTrimLines = window.forceTrimLines;
window.forceTrimLines = function(inputEl) {
    if (typeof _originalForceTrimLines === 'function') {
        _originalForceTrimLines(inputEl);
    }
    updateCardDynamicHeight(inputEl.closest('.log-window-card'), parseInt(inputEl.value));
};

// Override addLogWindow to set height on creation
const _originalAddLogWindow = window.addLogWindow;
window.addLogWindow = function(source, level) {
    if (typeof _originalAddLogWindow === 'function') {
        _originalAddLogWindow(source, level);
        const w = window.activeLogWindows[window.activeLogWindows.length - 1];
        if (w) {
            const maxL = w.element.querySelector('.w-max-lines');
            if (maxL) updateCardDynamicHeight(w.element, parseInt(maxL.value));
        }
    }
};

// ─────────────────────────────────────────────────────────────────────────────
// Card Height Calculation
// ─────────────────────────────────────────────────────────────────────────────

function updateCardDynamicHeight(card, maxLines) {
    if (!card) return;
    // Header (~45) + Search (~45) + Footer (~45) + Padding/Borders (~25) = ~160px
    // Line height in logs.css is ~22px per line
    const estimatedHeight = 160 + (maxLines * 22);
    const finalMaxHeight  = Math.min(Math.max(estimatedHeight, 180), 900);
    card.style.maxHeight  = finalMaxHeight + 'px';
}

// ─────────────────────────────────────────────────────────────────────────────
// Persistence Controls Injection
// ─────────────────────────────────────────────────────────────────────────────

function injectPersistenceControls() {
    const controlsRow = document.querySelector('.log-grid-controls');
    if (!controlsRow) return;

    const pBlock = document.createElement('div');
    pBlock.style.cssText = 'display:flex; gap:8px; align-items:center; margin-left:15px; border-left:1px solid var(--border); padding-left:15px;';
    pBlock.innerHTML = `
        <button class="btn btn-primary" onclick="saveStandaloneLayout()" title="Save current windows and layout" style="padding:4px 12px; font-size:11px; background:var(--accent); border:none; color:var(--bg);">
          <i class="fas fa-save"></i> Save Layout
        </button>
        <button class="btn btn-secondary" onclick="resetStandaloneLayout()" title="Reset to default" style="padding:4px 10px; font-size:11px; color:var(--red); border-color:rgba(var(--red-rgb), 0.3);">
          <i class="fas fa-undo"></i> Reset
        </button>
    `;
    const group1 = controlsRow.firstElementChild;
    if (group1) group1.appendChild(pBlock);
}

// ─────────────────────────────────────────────────────────────────────────────
// Layout Persistence (Save / Load / Reset)
// ─────────────────────────────────────────────────────────────────────────────

const LAYOUT_KEY = 'hecos-standalone-logs-layout';

window.saveStandaloneLayout = function() {
    const layout = document.getElementById('log-grid-layout').value;
    const config = {
        layout,
        windows: window.activeLogWindows.map(w => {
            const termEl  = w.element.querySelector('.w-search-term');
            const timeEl  = w.element.querySelector('.w-search-time');
            const autoSc  = w.element.querySelector('.w-autoscroll');
            const striped = w.element.querySelector('.w-striped-btn');
            const maxL    = w.element.querySelector('.w-max-lines');
            return {
                source:     w.source,
                level:      w.level,
                filterQ:    termEl  ? termEl.value       : w.filterQ,
                filterT:    timeEl  ? timeEl.value       : w.filterT,
                autoscroll: autoSc  ? autoSc.checked     : true,
                striped:    striped ? striped.checked    : false,
                maxLines:   maxL    ? parseInt(maxL.value) : 500,
            };
        }),
    };
    localStorage.setItem(LAYOUT_KEY, JSON.stringify(config));
    showToast("✅ Layout Persistent Saved!");
};

window.loadStandaloneLayout = async function() {
    const raw = localStorage.getItem(LAYOUT_KEY);
    if (!raw) {
        if (window.addLogWindow) window.addLogWindow('LIVE');
        return;
    }
    try {
        const config    = JSON.parse(raw);
        const grid      = document.getElementById('log-grid');
        if (grid) grid.innerHTML = '';

        const layoutSel = document.getElementById('log-grid-layout');
        if (layoutSel) {
            layoutSel.value = config.layout || 'auto';
            if (window.updateLogGridLayout) window.updateLogGridLayout();
        }

        for (const wData of config.windows) {
            window.addLogWindow(wData.source, wData.level);
            const w = window.activeLogWindows[window.activeLogWindows.length - 1];
            if (w) {
                w.filterQ = wData.filterQ || '';
                w.filterT = wData.filterT || '';

                const termEl  = w.element.querySelector('.w-search-term');
                const timeEl  = w.element.querySelector('.w-search-time');
                const autoSc  = w.element.querySelector('.w-autoscroll');
                const striped = w.element.querySelector('.w-striped-btn');
                const maxL    = w.element.querySelector('.w-max-lines');

                if (termEl)  termEl.value     = w.filterQ;
                if (timeEl)  timeEl.value     = w.filterT;
                if (autoSc)  autoSc.checked   = wData.autoscroll !== false;
                if (striped) {
                    striped.checked = !!wData.striped;
                    if (striped.checked) w.body.classList.add('striped-rows');
                }
                if (maxL) {
                    maxL.value = wData.maxLines || 500;
                    updateCardDynamicHeight(w.element, maxL.value);
                }
                if (w.source !== 'LIVE' && window.loadLogTailIntoWindow) {
                    window.loadLogTailIntoWindow(w, w.source);
                }
            }
        }
    } catch (e) {
        console.error("Load layout failed", e);
        if (window.addLogWindow) {
            window.addLogWindow('LIVE');
            const w = window.activeLogWindows[window.activeLogWindows.length - 1];
            if (w) updateCardDynamicHeight(w.element, 500);
        }
    }
};

window.resetStandaloneLayout = function() {
    if (confirm("Reset layout to defaults? All custom windows and filters will be lost.")) {
        localStorage.removeItem(LAYOUT_KEY);
        window.location.reload();
    }
};

// ─────────────────────────────────────────────────────────────────────────────
// Toast Notification
// ─────────────────────────────────────────────────────────────────────────────

function showToast(msg) {
    const toast = document.getElementById('status-toast');
    if (!toast) return;
    toast.textContent = msg;
    toast.classList.add('show');
    setTimeout(() => toast.classList.remove('show'), 3000);
}

// ─────────────────────────────────────────────────────────────────────────────
// Connection Monitor & Auto-Reconnect
// ─────────────────────────────────────────────────────────────────────────────

function startConnectionMonitor() {
    setInterval(() => {
        if (window.logEvtSource && window.logEvtSource.readyState === 2) {
            handleDisconnect();
        }
    }, 2000);
}

let isReconnecting = false;
function handleDisconnect() {
    if (isReconnecting) return;
    isReconnecting = true;

    document.getElementById('connection-lost-banner').style.display = 'block';
    let countdown  = 5;
    const timerElem = document.getElementById('reconnect-timer');

    const pingLoop = setInterval(async () => {
        countdown--;
        if (countdown > 0) {
            if (timerElem) timerElem.textContent = countdown;
            return;
        }
        try {
            const res = await fetch('/api/logs/files');
            if (res.ok) {
                clearInterval(pingLoop);
                window.location.reload();
            }
        } catch (e) {
            countdown = 5;
            if (timerElem) timerElem.textContent = countdown;
        }
    }, 1000);
}

// ─────────────────────────────────────────────────────────────────────────────
// Bootstrap
// ─────────────────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', async () => {
    const tabLogs = document.getElementById('tab-logs');
    if (tabLogs) {
        tabLogs.classList.add('active');
        const redundantBtn = tabLogs.querySelector('a[href="/hecos/logs"]');
        if (redundantBtn) redundantBtn.style.display = 'none';
        injectPersistenceControls();
    }

    if (window.refreshLogFiles) await window.refreshLogFiles();

    loadStandaloneLayout();
    startConnectionMonitor();
});
