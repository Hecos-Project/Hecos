/**
 * doc_preview.js
 * Fullscreen visual editor overlay for generated documents (HTML -> PDF) using GrapeJS.
 */

window._docPreviewGrapeEditor = null;
window._docPreviewCurrentPath = null;

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

// A4 at 96dpi: 210mm = ~794px wide, 297mm = ~1122px tall
const A4_HEIGHT_PX = 1122;

function _injectPageBreakLines(editor) {
    try {
        const canvas = editor.Canvas;
        const frame = canvas.getFrameEl ? canvas.getFrameEl() : null;
        if (!frame) return;
        const iframeDoc = frame.contentDocument || frame.contentWindow.document;
        if (!iframeDoc) return;

        // Remove any previously injected lines
        iframeDoc.querySelectorAll('.gjs-page-break-line').forEach(el => el.remove());

        const body = iframeDoc.body;
        const totalHeight = body.scrollHeight;
        const numBreaks = Math.floor(totalHeight / A4_HEIGHT_PX);

        // Inject a positioned parent if body isn't already positioned
        if (getComputedStyle(body).position === 'static') {
            body.style.position = 'relative';
        }

        for (let i = 1; i <= numBreaks; i++) {
            const topPx = i * A4_HEIGHT_PX;
            const line = iframeDoc.createElement('div');
            line.className = 'gjs-page-break-line';
            line.style.top = topPx + 'px';
            line.style.left = '0';
            line.style.right = '0';

            const label = iframeDoc.createElement('span');
            label.className = 'gjs-page-break-label';
            label.textContent = `── Pag ${i} / Pag ${i + 1} ──`;
            line.appendChild(label);

            body.appendChild(line);
        }
    } catch(e) {
        console.warn('[DocPreview] Could not inject page break lines:', e);
    }
}

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
                            <i class="fas fa-save"></i> Salva & Rigenera PDF
                        </button>
                    </div>
                </div>
                <div class="doc-preview-body">
                    <div id="doc-preview-grapes-container"></div>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
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
                    body { margin: 0 auto !important; padding: 20mm !important; width: 210mm !important; min-height: 297mm; font-family: sans-serif; background: #ffffff; color: #000; box-sizing: border-box; box-shadow: 0 0 10px rgba(0,0,0,0.1); }
                    [data-gjs-type] { outline: 1px dashed transparent; transition: outline .15s; }
                    [data-gjs-type]:hover { outline: 1px dashed rgba(0,212,255,0.5); }
                    .gjs-page-break-line {
                        position: absolute;
                        left: 0; right: 0;
                        height: 0;
                        border-top: 2px dashed rgba(255, 80, 80, 0.75);
                        z-index: 9999;
                        pointer-events: none;
                        box-sizing: border-box;
                    }
                    .gjs-page-break-label {
                        position: absolute;
                        left: 50%;
                        transform: translateX(-50%) translateY(-14px);
                        background: rgba(255, 80, 80, 0.85);
                        color: #fff;
                        font-size: 11px;
                        font-family: monospace;
                        font-weight: bold;
                        padding: 1px 10px;
                        border-radius: 3px;
                        white-space: nowrap;
                        pointer-events: none;
                    }
                    ${parsed.styles}
                `
            });

            window._docPreviewGrapeEditor.on('load', () => {
                window._docPreviewGrapeEditor.setComponents(parsed.body);
                const wrapper = window._docPreviewGrapeEditor.getWrapper();
                if (wrapper) wrapper.setStyle({ "background-color": "#ffffff" });
                if (saveBtn) saveBtn.innerHTML = '<i class="fas fa-save"></i> Save & Regenerate PDF';
                // Inject page break indicator lines after a short delay (let content render)
                setTimeout(() => _injectPageBreakLines(window._docPreviewGrapeEditor), 800);
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
    setTimeout(() => _injectPageBreakLines(window._docPreviewGrapeEditor), 500);
};

window.closeDocPreview = function() {
    const modal = document.getElementById('doc-preview-modal');
    if (modal) modal.classList.remove('active');
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
            window.closeDocPreview();
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
