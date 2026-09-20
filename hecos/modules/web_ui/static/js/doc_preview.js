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
    script.onload = callback;
    document.head.appendChild(script);
}

function _parseHtmlForPreview(html) {
    if (!html) return { styles: '', body: '' };
    const parser = new DOMParser();
    const doc = parser.parseFromString(html, 'text/html');
    const styleTexts = [];
    doc.querySelectorAll('style').forEach(el => styleTexts.push(el.textContent));
    const bodyHtml = doc.body ? doc.body.innerHTML : html;
    return { styles: styleTexts.join('\n'), body: bodyHtml };
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
                    <div class="doc-preview-actions">
                        <button class="hecos-btn sm" onclick="window.closeDocPreview()">Cancel</button>
                        <button class="hecos-btn sm primary" onclick="window.saveAndRegenerateDoc()" id="doc-preview-save-btn">
                            <i class="fas fa-save"></i> Save & Regenerate PDF
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
                plugins: [],
                panels: { defaults: [] },
                canvasCss: `
                    body { margin: 0; padding: 20px; font-family: sans-serif; background: #ffffff; color: #000; }
                    [data-gjs-type] { outline: 1px dashed transparent; transition: outline .15s; }
                    [data-gjs-type]:hover { outline: 1px dashed rgba(0,212,255,0.5); }
                    ${parsed.styles}
                `
            });

            window._docPreviewGrapeEditor.on('load', () => {
                window._docPreviewGrapeEditor.setComponents(parsed.body);
                // Reset styling/variables in wrapper to avoid dark theme bleed
                const wrapper = window._docPreviewGrapeEditor.getWrapper();
                if (wrapper) wrapper.setStyle({ "background-color": "#ffffff" });
                if (saveBtn) saveBtn.innerHTML = '<i class="fas fa-save"></i> Save & Regenerate PDF';
            });
        });
    } catch(e) {
        console.error("Preview error:", e);
        if (window.showToast) window.showToast("Failed to load document preview", "error");
        if (saveBtn) saveBtn.innerHTML = '<i class="fas fa-exclamation-triangle"></i> Error';
    }
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
        const html = window._docPreviewGrapeEditor.getHtml();
        const css = window._docPreviewGrapeEditor.getCss();
        // Wrap in full HTML document
        const fullHtml = `<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>${css}</style>
</head>
<body>${html}</body>
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
