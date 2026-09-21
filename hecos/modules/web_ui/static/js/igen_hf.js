/**
 * igen_hf.js — Image Gen Panel: Hugging Face Model Explorer
 * searchHFHub, useHFModel, checkCustomModelSelect, removeSelectedHFModel.
 */

window.searchHFHub = async function() {
    const qEl = document.getElementById('igen-hf-search-q');
    const q   = qEl ? qEl.value.trim() : '';
    const box = document.getElementById('igen-hf-results');
    if (!box) return;
    box.innerHTML = '<div style="padding:10px; text-align:center; color:var(--muted); font-size:12px;">Searching...</div>';
    try {
        const res  = await fetch('/hecos/api/plugins/image_gen/hf-search?q=' + encodeURIComponent(q));
        const data = await res.json();
        if (!data.ok) {
            box.innerHTML = '<div style="padding:10px; color:#e74c3c; font-size:12px;">Error: ' + data.error + '</div>';
            return;
        }
        if (!data.models || !data.models.length) {
            box.innerHTML = '<div style="padding:10px; text-align:center; color:var(--muted); font-size:12px;">No models found.</div>';
            return;
        }
        let html = '<div style="display:flex; flex-direction:column;">';
        data.models.forEach(m => {
            html += '<div style="display:flex;justify-content:space-between;padding:8px 10px;border-bottom:1px solid var(--border);">'
                  + '<div><strong>' + m.id + '</strong><br><small>\u2B07\uFE0F ' + m.downloads + ' | \u2764\uFE0F ' + m.likes + '</small></div>'
                  + '<button onclick="useHFModel(\'' + m.id + '\')" style="padding:4px 10px;font-size:11px;border-radius:5px;cursor:pointer;">\u2795 Use</button>'
                  + '</div>';
        });
        html += '</div>';
        box.innerHTML = html;
    } catch (err) {
        box.innerHTML = '<div style="padding:10px; color:#e74c3c; font-size:12px;">Network Error: ' + err.message + '</div>';
    }
};

window.useHFModel = function(modelId) {
    const sel = document.getElementById('igen-model');
    if (!sel) return;
    let exists = false;
    for (const opt of sel.options) { if (opt.value === modelId) { exists = true; break; } }
    if (!exists) {
        const opt = document.createElement('option');
        opt.value = opt.textContent = modelId;
        sel.appendChild(opt);
    }
    sel.value = modelId;
    _igenDebounceSave();
};

window.checkCustomModelSelect = function() { _igenDebounceSave(); };

window.removeSelectedHFModel = function() {
    const sel = document.getElementById('igen-model');
    if (!sel || sel.selectedIndex < 0) return;
    const val = sel.value;

    _igenConfirm('Remove "' + val + '" from the list?', () => {
        sel.remove(sel.selectedIndex);
        _igenDebounceSave();
    });
};
