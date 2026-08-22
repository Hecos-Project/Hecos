/**
 * document_maker — Plugin Panel JS
 * Auto-save on change (debounced 600ms). No manual save button.
 * Also hooks into Hecos global saveConfig() so the hub footer Save button works too.
 */

// ── Autosave debouncer ────────────────────────────────────────────────────────
let _docsSaveTimer = null;

window.docsDebounceSave = function() {
    clearTimeout(_docsSaveTimer);
    _docsSaveTimer = setTimeout(() => { window.saveDocsConfig(); }, 600);
};

// ── Load config ────────────────────────────────────────────────────────────────
window.loadDocsConfig = async function() {
    try {
        const res = await fetch('/hecos/api/plugins/document_maker/config');
        if (!res.ok) return;
        const data = await res.json();
        const el = document.getElementById('docs-pdf-save-path');
        if (el) el.value = data.pdf_save_path || 'media/documents';
    } catch(e) {
        console.warn('[DocsMaker] Failed to load config:', e);
    }
};

// ── Save config ────────────────────────────────────────────────────────────────
window.saveDocsConfig = async function(silent = false) {
    const pathEl = document.getElementById('docs-pdf-save-path');
    if (!pathEl) return;

    const payload = {
        pdf_save_path: pathEl.value.trim() || 'media/documents'
    };

    try {
        const res = await fetch('/hecos/api/plugins/document_maker/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (res.ok && !silent) {
            const statusEl = document.getElementById('docs-save-status');
            if (statusEl) {
                statusEl.style.display = 'flex';
                clearTimeout(window._docsSaveStatusTimer);
                window._docsSaveStatusTimer = setTimeout(() => {
                    statusEl.style.display = 'none';
                }, 2500);
            }
        }
    } catch(e) {
        console.error('[DocsMaker] Save error:', e);
        if (window.showToast) window.showToast('Document Maker: failed to save settings', 'error');
    }
};

// ── Hook into Hecos Central Hub global save button ─────────────────────────────
// The hub footer "Save" button calls window.saveConfig() globally.
// We wrap it to also save our plugin config.
(function() {
    const _origSaveConfig = window.saveConfig;
    window.saveConfig = async function(...args) {
        await window.saveDocsConfig(true);
        if (typeof _origSaveConfig === 'function') return _origSaveConfig(...args);
    };
})();

// ── Init on panel load ────────────────────────────────────────────────────────
(function init() {
    if (document.getElementById('docs-pdf-save-path')) {
        window.loadDocsConfig();
    } else {
        // Panel might be lazy-loaded — wait for DOM
        document.addEventListener('DOMContentLoaded', () => {
            if (document.getElementById('docs-pdf-save-path')) window.loadDocsConfig();
        });
    }
})();
