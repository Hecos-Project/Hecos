/**
 * image_gen autonomous panel JS
 */

async function loadIgenPresets(restoreValue) {
    try {
        const r = await fetch('/hecos/api/plugins/image_gen/presets');
        const d = await r.json();
        if (!d.ok) return;

        const sel = document.getElementById('igen-preset');
        if (!sel) return;

        const targetValue = restoreValue !== undefined ? restoreValue : sel.value;
        sel.innerHTML = '<option value="">— Select a preset —</option>';
        (d.presets || []).forEach(p => {
            const opt = document.createElement('option');
            opt.value = p.name;
            opt.textContent = (p.builtin ? '' : '👤 ') + p.name;
            opt.dataset.builtin = String(p.builtin);
            sel.appendChild(opt);
        });

        if (targetValue) sel.value = targetValue;
        checkIgenPresetUI();
    } catch (err) {
        console.warn('[igen] loadIgenPresets error:', err);
    }
}

function checkIgenPresetUI() {
    const sel = document.getElementById('igen-preset');
    const updateBtn = document.getElementById('igen-preset-update-btn');
    const deleteBtn = document.getElementById('igen-preset-delete-btn');
    if (!sel) return;

    const selectedOpt = sel.options[sel.selectedIndex];
    const isEmpty = !sel.value;
    const isBuiltin = selectedOpt ? (selectedOpt.dataset.builtin === 'true') : true;

    const show = !isEmpty && !isBuiltin;
    if (updateBtn) updateBtn.style.display = show ? 'inline-block' : 'none';
    if (deleteBtn) deleteBtn.style.display = show ? 'inline-block' : 'none';
}

async function loadIgenPreset() {
    const sel = document.getElementById('igen-preset');
    const name = sel ? sel.value : '';
    if (!name) {
        checkIgenPresetUI();
        return;
    }
    try {
        const r = await fetch('/hecos/api/plugins/image_gen/presets/load/' + encodeURIComponent(name));
        const d = await r.json();
        if (!d.ok) {
            alert('Error loading preset: ' + d.error);
            return;
        }
        applyIgenConfig(d.config);
        if (sel) sel.value = name;
        checkIgenPresetUI();
    } catch (err) {
        console.error('[igen] preset load error', err);
    }
}

async function saveIgenPreset() {
    const name = prompt('Name for this preset:');
    if (!name || !name.trim()) return;
    const config = collectIgenConfig();
    const r = await fetch('/hecos/api/plugins/image_gen/presets/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: name.trim(), config })
    });
    const d = await r.json();
    if (d.ok) {
        await loadIgenPresets(name.trim());
    } else {
        alert('Save failed: ' + d.error);
    }
}

async function updateIgenPreset() {
    const sel = document.getElementById('igen-preset');
    const name = sel ? sel.value : '';
    if (!name) return;
    const config = collectIgenConfig();
    const r = await fetch('/hecos/api/plugins/image_gen/presets/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, config })
    });
    const d = await r.json();
    if (d.ok) {
        const btn = document.getElementById('igen-preset-update-btn');
        if (btn) {
            btn.innerHTML = '✅ Saved!';
            setTimeout(() => { btn.innerHTML = '🔄 Update'; }, 1500);
        }
    } else {
        alert('Update failed: ' + d.error);
    }
}

async function deleteIgenPreset() {
    const name = document.getElementById('igen-preset') ? document.getElementById('igen-preset').value : '';
    if (!name) return;
    if (!confirm('Delete preset "' + name + '"?')) return;
    const r = await fetch('/hecos/api/plugins/image_gen/presets/delete/' + encodeURIComponent(name), { method: 'DELETE' });
    const d = await r.json();
    if (d.ok) {
        await loadIgenPresets('');
    } else {
        alert('Delete failed: ' + d.error);
    }
}

function onAspectRatioChanged() {
    const val = document.getElementById('igen-aspect-ratio').value;
    document.getElementById('igen-custom-dims').style.display = (val === 'custom') ? 'block' : 'none';
}

function collectIgenConfig() {
    const get = (id, def) => { const el = document.getElementById(id); return el ? el.value : def; };
    const chk = (id, def) => { const el = document.getElementById(id); return el ? el.checked : def; };
    return {
        provider: get('igen-provider', 'pollinations'),
        model: get('igen-model', 'flux'),
        aspect_ratio: get('igen-aspect-ratio', '1:1'),
        width: parseInt(get('igen-width', 1024)),
        height: parseInt(get('igen-height', 1024)),
        seed: parseInt(get('igen-seed', -1)),
        sampler: get('igen-sampler', 'euler'),
        scheduler: get('igen-scheduler', 'simple'),
        guidance_scale: parseFloat(get('igen-guidance', 0.0)),
        num_inference_steps: parseInt(get('igen-steps', 4)),
        enable_negative_prompt: chk('igen-use-neg-prompt', false),
        negative_prompt: get('igen-neg-prompt', ''),
        auto_enrich: chk('igen-auto-enrich', false),
        enrich_keywords: get('igen-enrich-keywords', ''),
        style: get('igen-style', 'none'),
        nologo: chk('igen-nologo', true),
        optimize_for_flux: chk('igen-optimize-flux', true),
        show_metadata_in_chat: chk('igen-show-metadata', false),
        enabled: chk('igen-enabled', true),
        api_key: get('igen-api-key', ''),
    };
}

function applyIgenConfig(cfg) {
    const set = (id, val) => { const el = document.getElementById(id); if (el) el.value = val; };
    const chk = (id, val) => { const el = document.getElementById(id); if (el) el.checked = !!val; };

    set('igen-provider', cfg.provider || 'pollinations');
    set('igen-model', cfg.model || 'flux');
    set('igen-aspect-ratio', cfg.aspect_ratio || '1:1');
    set('igen-width', cfg.width || 1024);
    set('igen-height', cfg.height || 1024);
    set('igen-seed', cfg.seed ?? -1);
    set('igen-sampler', cfg.sampler || 'euler');
    set('igen-scheduler', cfg.scheduler || 'simple');
    set('igen-api-key', cfg.api_key || '');

    const guidance = cfg.guidance_scale ?? 0.0;
    set('igen-guidance', guidance);
    const gValEl = document.getElementById('igen-guidance-val');
    if (gValEl) gValEl.textContent = parseFloat(guidance).toFixed(1);

    const steps = cfg.num_inference_steps || 4;
    set('igen-steps', steps);
    const sValEl = document.getElementById('igen-steps-val');
    if (sValEl) sValEl.textContent = steps;

    chk('igen-use-neg-prompt', cfg.enable_negative_prompt);
    set('igen-neg-prompt', cfg.negative_prompt || '');
    chk('igen-auto-enrich', cfg.auto_enrich);
    set('igen-enrich-keywords', cfg.enrich_keywords || '');
    set('igen-style', cfg.style || 'none');
    chk('igen-nologo', cfg.nologo ?? true);
    chk('igen-optimize-flux', cfg.optimize_for_flux ?? true);
    chk('igen-show-metadata', cfg.show_metadata_in_chat ?? false);
    chk('igen-enabled', cfg.enabled ?? true);

    onAspectRatioChanged();
    if (cfg.provider && typeof window.onProviderChanged === 'function') window.onProviderChanged();
}

// HF Explorer
async function searchHFHub() {
    const qEl = document.getElementById('igen-hf-search-q');
    const q = qEl ? qEl.value.trim() : '';
    const resContainer = document.getElementById('igen-hf-results');
    if (!resContainer) return;
    resContainer.innerHTML = '<div style="padding:10px; text-align:center; color:var(--muted); font-size:12px;">Searching...</div>';
    try {
        const res = await fetch('/hecos/api/plugins/image_gen/hf-search?q=' + encodeURIComponent(q));
        const data = await res.json();
        if (!data.ok) {
            resContainer.innerHTML = `<div style="padding:10px; color:var(--error, #e74c3c); font-size:12px;">Error: ${data.error}</div>`;
            return;
        }
        if (!data.models || data.models.length === 0) {
            resContainer.innerHTML = '<div style="padding:10px; text-align:center; color:var(--muted); font-size:12px;">No models found.</div>';
            return;
        }
        let html = '<div style="display:flex; flex-direction:column;">';
        data.models.forEach(m => {
            html += `<div style="display:flex;justify-content:space-between;padding:8px 10px;border-bottom:1px solid var(--border);">
                <div><strong>${m.id}</strong><br><small>⬇️ ${m.downloads} | ❤️ ${m.likes}</small></div>
                <button onclick="useHFModel('${m.id}')" style="padding:4px 10px;font-size:11px;border-radius:5px;cursor:pointer;">➕ Use</button>
            </div>`;
        });
        html += '</div>';
        resContainer.innerHTML = html;
    } catch (err) {
        resContainer.innerHTML = `<div style="padding:10px; color:#e74c3c; font-size:12px;">Network Error: ${err.message}</div>`;
    }
}

function useHFModel(modelId) {
    const sel = document.getElementById('igen-model');
    if (!sel) return;
    let exists = false;
    for (let opt of sel.options) { if (opt.value === modelId) { exists = true; break; } }
    if (!exists) {
        const opt = document.createElement('option');
        opt.value = modelId;
        opt.textContent = modelId;
        sel.appendChild(opt);
    }
    sel.value = modelId;
}

window.searchHFHub = searchHFHub;
window.useHFModel = useHFModel;
window.collectIgenConfig = collectIgenConfig;
window.applyIgenConfig = applyIgenConfig;
window.loadIgenPresets = loadIgenPresets;
window.loadIgenPreset = loadIgenPreset;
window.saveIgenPreset = saveIgenPreset;
window.updateIgenPreset = updateIgenPreset;
window.deleteIgenPreset = deleteIgenPreset;
window.checkIgenPresetUI = checkIgenPresetUI;
window.onAspectRatioChanged = onAspectRatioChanged;
