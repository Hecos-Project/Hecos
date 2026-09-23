/**
 * doc_preview.js
 * Fullscreen visual editor overlay for generated documents (HTML -> PDF) using GrapeJS.
 */

window._docPreviewGrapeEditor = null;
window._docPreviewCurrentPath = null;
window._docPreviewIsDirty = false;

function _loadGrapeJS(callback) {
    if (typeof grapesjs !== 'undefined') {
        callback();
        return;
    }
    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = 'https://unpkg.com/grapesjs@0.21.13/dist/css/grapes.min.css';
    document.head.appendChild(link);

    const script = document.createElement('script');
    script.src = 'https://unpkg.com/grapesjs@0.21.13/dist/grapes.min.js';
    script.onload = () => {
        const p1 = document.createElement('script');
        p1.src = 'https://unpkg.com/grapesjs-blocks-basic';
        p1.onload = () => {
            const p2 = document.createElement('script');
            p2.src = 'https://unpkg.com/grapesjs-plugin-forms';
            p2.onload = callback;
            document.head.appendChild(p2);
        };
        document.head.appendChild(p1);
    };
    document.head.appendChild(script);
}

// Removed fake page break logic as requested.

function _parseHtmlForPreview(html) {
    if (!html) return { styles: '', body: '' };

    // 1. Rewrite file:/// URLs for browser compatibility in GrapeJS
    // Playwright uses file:///C:/... which browsers block. We route it through Hecos API.
    let htmlString = html.replace(/(src|url)\s*=\s*(["']?)file:\/\/\/([^"'>\s]+)(["']?)/gi, function(match, attr, q1, path, q2) {
        // Only rewrite if it looks like a local absolute path
        if (/^[a-zA-Z]:/.test(path) || path.startsWith('/')) {
            return attr + '=' + q1 + '/api/local_file?path=' + encodeURIComponent(path) + q2;
        }
        return match;
    });
    
    // Replace CSS url(file:///...) patterns
    htmlString = htmlString.replace(/url\(\s*(["']?)file:\/\/\/([^)"']+)(["']?)\s*\)/gi, function(match, q1, path, q2) {
        if (/^[a-zA-Z]:/.test(path) || path.startsWith('/')) {
            return 'url(' + q1 + '/api/local_file?path=' + encodeURIComponent(path) + q2 + ')';
        }
        return match;
    });

    const parser = new DOMParser();
    const doc = parser.parseFromString(htmlString, 'text/html');
    const styleTexts = [];
    doc.querySelectorAll('style').forEach(el => styleTexts.push(el.textContent));
    doc.querySelectorAll('script').forEach(s => s.remove());
    const bodyHtml = doc.body ? doc.body.innerHTML : htmlString;
    window._docPreviewOriginalCss = styleTexts.join('\n'); // Store globally for saving
    return { styles: window._docPreviewOriginalCss, body: bodyHtml };
}

window.openDocPreview = async function(filePath) {
    window._docPreviewCurrentPath = filePath;
    
    // Create modal if it doesn't exist
    let modal = document.getElementById('doc-preview-modal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'doc-preview-modal';
        modal.className = 'doc-preview-overlay';
        modal.innerHTML = `
            <div class="doc-preview-container">
                <div class="doc-preview-header">
                    <div class="doc-preview-title">
                        <i class="fas fa-magic"></i> Document Visual Editor
                        <span id="doc-preview-filename" style="font-size:0.8em; opacity:0.6; margin-left:10px;"></span>
                    </div>
                    <div class="doc-preview-actions" style="display: flex; align-items: center; gap: 8px;">
                        <div style="display: flex; align-items: center; background: rgba(0,0,0,0.2); padding: 4px; border-radius: 6px; border: 1px solid rgba(255,255,255,0.1);">
                            <button onclick="window.undoDocPreview()" title="Annulla (Ctrl+Z)" style="background: transparent; border: none; color: #fff; cursor: pointer; padding: 4px 8px; border-radius: 4px;"><i class="fas fa-undo"></i></button>
                            <button onclick="window.redoDocPreview()" title="Ripeti (Ctrl+Y)" style="background: transparent; border: none; color: #fff; cursor: pointer; padding: 4px 8px; border-radius: 4px;"><i class="fas fa-redo"></i></button>
                        </div>
                        <div style="display: flex; align-items: center; background: rgba(0,0,0,0.2); padding: 4px; border-radius: 6px; border: 1px solid rgba(255,255,255,0.1);">
                            <button onclick="window.zoomDocPreview(-10)" title="Zoom Out" style="background: transparent; border: none; color: #fff; cursor: pointer; padding: 4px 8px; border-radius: 4px;"><i class="fas fa-search-minus"></i></button>
                            <span id="doc-preview-zoom-label" style="font-size: 0.9em; min-width: 45px; text-align: center; color: #fff; font-weight: bold;">100%</span>
                            <button onclick="window.zoomDocPreview(10)" title="Zoom In" style="background: transparent; border: none; color: #fff; cursor: pointer; padding: 4px 8px; border-radius: 4px;"><i class="fas fa-search-plus"></i></button>
                        </div>
                        <button onclick="window.restoreDocPreview()" title="Ripristina la versione originale del documento" style="background: rgba(239,68,68,0.15); border: 1px solid rgba(239,68,68,0.4); color: #fca5a5; padding: 6px 12px; border-radius: 4px; cursor: pointer; font-family: inherit; font-size: 0.9em; transition: background 0.2s;"><i class="fas fa-history"></i> Ripristina</button>
                        <button onclick="window.closeDocPreview()" style="background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.2); color: #fff; padding: 6px 12px; border-radius: 4px; cursor: pointer; font-family: inherit; font-size: 0.9em; transition: background 0.2s;">Annulla</button>
                        <button onclick="window.saveAndRegenerateDoc()" id="doc-preview-save-btn" style="background: #3b82f6; border: 1px solid #2563eb; color: #fff; padding: 6px 12px; border-radius: 4px; cursor: pointer; font-family: inherit; font-size: 0.9em; font-weight: bold; transition: background 0.2s;">
                            <i class="fas fa-save"></i> Salva &amp; Rigenera PDF
                        </button>
                    </div>
                </div>
                <div class="doc-preview-body">
                    <div id="doc-preview-grapes-container"></div>
                </div>
            </div>

            <!-- Confirm close dialog -->
            <div class="doc-preview-confirm-overlay" id="doc-preview-confirm-overlay" style="display:none; position:absolute; inset:0; background:rgba(0,0,0,0.65); z-index:10000; display:none; align-items:center; justify-content:center;">
                <div class="doc-preview-confirm-box" style="background:#1e1e2e; border:1px solid rgba(255,255,255,0.15); border-radius:12px; padding:32px 36px; max-width:420px; text-align:center; box-shadow:0 20px 60px rgba(0,0,0,0.5);">
                    <div style="font-size:2.5em; margin-bottom:12px;">⚠️</div>
                    <div style="font-size:1.15em; font-weight:700; color:#fff; margin-bottom:10px;">Unsaved changes</div>
                    <div style="font-size:0.9em; color:rgba(255,255,255,0.65); margin-bottom:24px; line-height:1.6;">You have unsaved changes. If you close now, all your edits will be lost.</div>
                    <div style="display:flex; gap:12px; justify-content:center;">
                        <button onclick="document.getElementById('doc-preview-confirm-overlay').style.display='none'" style="background:rgba(255,255,255,0.1); border:1px solid rgba(255,255,255,0.2); color:#fff; padding:8px 20px; border-radius:6px; cursor:pointer; font-size:0.9em;">Stay</button>
                        <button onclick="window._docPreviewForceClose()" style="background:#ef4444; border:1px solid #dc2626; color:#fff; padding:8px 20px; border-radius:6px; cursor:pointer; font-size:0.9em; font-weight:bold;">Close without saving</button>
                    </div>
                </div>
            </div>
        `;
        document.body.appendChild(modal);

        // ESC key handler — registered only once, checks dirty state
        document.addEventListener('keydown', function _docEscHandler(e) {
            if (e.key === 'Escape') {
                const m = document.getElementById('doc-preview-modal');
                if (m && m.classList.contains('active')) {
                    e.preventDefault();
                    e.stopPropagation();
                    window.closeDocPreview();
                }
            }
        });
    }

    // --- BACKUP: store the original HTML in sessionStorage as a safety net ---
    window._docPreviewCurrentPath = filePath;
    const filenameSpan = document.getElementById('doc-preview-filename');
    if (filenameSpan) filenameSpan.textContent = filePath.split(/[\\/]/).pop();

    modal.classList.add('active');
    
    // Show loading on save button
    const saveBtn = document.getElementById('doc-preview-save-btn');
    if (saveBtn) saveBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Loading...';

    try {
        const res = await fetch('/hecos/api/plugins/document_maker/preview?path=' + encodeURIComponent(filePath));
        const data = await res.json();
        if (!data.ok) throw new Error(data.error);

        // Store original HTML as backup in sessionStorage so user can always restore
        sessionStorage.setItem('doc_backup_' + filePath, data.html);

        window._docPreviewIsDirty = false;

        _loadGrapeJS(() => {
            const parsed = _parseHtmlForPreview(data.html);
            
            if (window._docPreviewGrapeEditor) {
                window._docPreviewGrapeEditor.destroy();
                document.getElementById('doc-preview-grapes-container').innerHTML = '';
            }

            window._docPreviewGrapeEditor = grapesjs.init({
                container: '#doc-preview-grapes-container',
                height: '100%',
                width: '100%',
                fromElement: false,
                storageManager: false,
                plugins: ['gjs-blocks-basic', 'grapesjs-plugin-forms'],
                pluginsOpts: {
                    'gjs-blocks-basic': { flexGrid: true }
                },
                canvasCss: `
                    body { margin: 0 auto !important; padding: 20mm !important; width: 210mm !important; min-height: 297mm; box-sizing: border-box; box-shadow: 0 0 10px rgba(0,0,0,0.15); }
                    [data-gjs-type] { outline: 1px dashed transparent; transition: outline .15s; }
                    [data-gjs-type]:hover { outline: 1px dashed rgba(0,212,255,0.5); }

                    ${parsed.styles}
                `
            });

            window._docPreviewGrapeEditor.on('load', () => {
                window._docPreviewGrapeEditor.setComponents(parsed.body);
                // Reset dirty state on load
                window._docPreviewIsDirty = false;
                window._docPreviewGrapeEditor.UndoManager.clear();
                // Track changes to set dirty flag
                window._docPreviewGrapeEditor.on('change:changesCount', () => {
                    window._docPreviewIsDirty = true;
                });
                // Do NOT force background: the document's own CSS (in parsed.styles) controls it
                if (saveBtn) saveBtn.innerHTML = '<i class="fas fa-save"></i> Save & Regenerate PDF';
            });
        });
    } catch(e) {
        console.error("Preview error:", e);
        if (window.showToast) window.showToast("Failed to load document preview", "error");
        if (saveBtn) saveBtn.innerHTML = '<i class="fas fa-exclamation-triangle"></i> Error';
    }
};

window.zoomDocPreview = function(delta) {
    if (!window._docPreviewGrapeEditor) return;
    const canvas = window._docPreviewGrapeEditor.Canvas;
    let currentZoom = canvas.getZoom(); // usually 100 on new GrapeJS, or 1.0 depending on version
    if (currentZoom < 10) currentZoom *= 100; // Normalization if it's 1.0 based
    let newZoom = currentZoom + delta;
    if (newZoom < 20) newZoom = 20;
    if (newZoom > 300) newZoom = 300;
    canvas.setZoom(newZoom);
    document.getElementById('doc-preview-zoom-label').innerText = Math.round(newZoom) + '%';
};

window.undoDocPreview = function() {
    if (!window._docPreviewGrapeEditor) return;
    window._docPreviewGrapeEditor.UndoManager.undo();
};

window.redoDocPreview = function() {
    if (!window._docPreviewGrapeEditor) return;
    window._docPreviewGrapeEditor.UndoManager.redo();
};

window.restoreDocPreview = function() {
    if (!window._docPreviewGrapeEditor || !window._docPreviewCurrentPath) return;
    const backupHtml = sessionStorage.getItem('doc_backup_' + window._docPreviewCurrentPath);
    if (!backupHtml) {
        if (window.showToast) window.showToast('Nessun backup disponibile per questo documento.', 'warning');
        return;
    }
    const confirmed = confirm('⚠️ Vuoi ripristinare la versione originale del documento?\n\nTutte le modifiche non salvate andranno perse, ma il file su disco NON verrà sovrascritto finché non clicchi "Salva & Rigenera PDF".');
    if (!confirmed) return;

    const parsed = _parseHtmlForPreview(backupHtml);
    window._docPreviewGrapeEditor.UndoManager.clear();
    window._docPreviewGrapeEditor.setComponents(parsed.body);
    if (window.showToast) window.showToast('Documento ripristinato alla versione originale.', 'success');
};

window.closeDocPreview = function() {
    if (window._docPreviewIsDirty) {
        const overlay = document.getElementById('doc-preview-confirm-overlay');
        if (overlay) {
            overlay.style.display = 'flex';
            return;
        }
    }
    window._docPreviewForceClose();
};

window._docPreviewForceClose = function() {
    const modal = document.getElementById('doc-preview-modal');
    if (modal) modal.classList.remove('active');
    const overlay = document.getElementById('doc-preview-confirm-overlay');
    if (overlay) overlay.style.display = 'none';
    window._docPreviewIsDirty = false;
};

window.saveAndRegenerateDoc = async function() {
    if (!window._docPreviewGrapeEditor || !window._docPreviewCurrentPath) return;
    
    const saveBtn = document.getElementById('doc-preview-save-btn');
    if (saveBtn) {
        saveBtn.disabled = true;
        saveBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saving...';
    }

    try {
        let html = window._docPreviewGrapeEditor.getHtml();
        const css = window._docPreviewGrapeEditor.getCss();
        
        // GrapeJS sometimes outputs literal '\n' sequences if it encounters weird text nodes, strip them.
        html = html.replace(/\\n/g, '');

        // REVERT /api/local_file?path= back to file:///
        html = html.replace(/\/api\/local_file\?path=([^"'>\s]+)/gi, function(match, encodedPath) {
            return 'file:///' + decodeURIComponent(encodedPath);
        });

        const originalCss = window._docPreviewOriginalCss || '';

        // Wrap in full HTML document
        const fullHtml = `<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
${originalCss}
${css}
</style>
</head>
<body>
${html}
</body>
</html>`;

        const res = await fetch('/hecos/api/plugins/document_maker/preview', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                path: window._docPreviewCurrentPath,
                html: fullHtml
            })
        });
        const data = await res.json();
        
        if (data.ok) {
            if (window.showToast) window.showToast("Document saved and PDF regenerated!", "success");
            window._docPreviewIsDirty = false;
            window._docPreviewForceClose();
        } else {
            throw new Error(data.error);
        }
    } catch(e) {
        console.error("Save error:", e);
        if (window.showToast) window.showToast("Failed to save document: " + e.message, "error");
    } finally {
        if (saveBtn) {
            saveBtn.disabled = false;
            saveBtn.innerHTML = '<i class="fas fa-save"></i> Save & Regenerate PDF';
        }
    }
};
