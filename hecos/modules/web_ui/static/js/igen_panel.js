/**
 * igen_panel.js
 * ─────────────────────────────────────────────────────────────────────────────
 * Hecos Image Generation — Config Panel Logic
 * Handles presets, config collect/apply, HuggingFace model explorer.
 * Functions onProviderChanged(), refreshImageModels(), checkCustomModelSelect(),
 * removeSelectedHFModel(), refineDraftPrompt(), sendPromptToChat() are
 * implemented in config_media_logic.js / config_manifest.js (existing files).
 * ─────────────────────────────────────────────────────────────────────────────
 */

// ─────────────────────────────────────────────────────────────────────────────
// Preset Helpers
// ─────────────────────────────────────────────────────────────────────────────

async function loadIgenPresets() {
    const r   = await fetch('/hecos/api/media/presets');
    const d   = await r.json();
    if (!d.ok) return;
    const sel     = document.getElementById('igen-preset');
    const current = sel.value;
    sel.innerHTML  = '<option value="">— Select a preset —</option>';
    (d.presets || []).forEach(p => {
        const opt = document.createElement('option');
        opt.value             = p.name;
        opt.textContent       = (p.builtin ? '' : '👤 ') + p.name;
        opt.dataset.builtin   = p.builtin;
        opt.title             = p.description || '';
        sel.appendChild(opt);
    });
    if (current) sel.value = current;
    checkIgenPresetUI();
}

function checkIgenPresetUI() {
    const sel       = document.getElementById('igen-preset');
    const updateBtn = document.getElementById('igen-preset-update-btn');
    const deleteBtn = document.getElementById('igen-preset-delete-btn');
    if (!sel || sel.selectedIndex < 0) return;

    const opt       = sel.options[sel.selectedIndex];
    const isBuiltin = opt.dataset.builtin === "true";
    const isEmpty   = opt.value === "";

    const show = !isEmpty && !isBuiltin;
    if (updateBtn) updateBtn.style.display = show ? 'inline-block' : 'none';
    if (deleteBtn) deleteBtn.style.display = show ? 'inline-block' : 'none';
}

async function loadIgenPreset() {
    const name = document.getElementById('igen-preset').value;
    if (!name) return;
    const r = await fetch('/hecos/api/media/presets/load/' + encodeURIComponent(name));
    const d = await r.json();
    if (!d.ok) { alert('Error loading preset: ' + d.error); return; }
    applyIgenConfig(d.config);
    checkIgenPresetUI();
}

async function saveIgenPreset() {
    const name = prompt('Name for this preset:');
    if (!name || !name.trim()) return;
    const config = collectIgenConfig();
    const r = await fetch('/hecos/api/media/presets/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: name.trim(), config }),
    });
    const d = await r.json();
    if (d.ok) {
        await loadIgenPresets();
        document.getElementById('igen-preset').value = name.trim();
        checkIgenPresetUI();
        if (typeof window.saveConfig === 'function') window.saveConfig(true);
    } else {
        alert('Save failed: ' + d.error);
    }
}

async function updateIgenPreset() {
    const sel  = document.getElementById('igen-preset');
    const name = sel.value;
    if (!name) return;
    const config = collectIgenConfig();
    const r = await fetch('/hecos/api/media/presets/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, config }),
    });
    const d = await r.json();
    if (d.ok) {
        const btn = document.getElementById('igen-preset-update-btn');
        if (btn) {
            btn.innerHTML    = '✅ Saved!';
            btn.style.color  = '#2ecc71';
            btn.style.borderColor = '#2ecc71';
            btn.style.background  = 'rgba(46,204,113,0.1)';
            setTimeout(() => {
                btn.innerHTML    = '🔄 Update';
                btn.style.color  = 'var(--accent)';
                btn.style.borderColor = 'var(--accent)';
                btn.style.background  = 'rgba(var(--accent-rgb,100,100,255),0.1)';
            }, 1500);
        }
        if (typeof window.saveConfig === 'function') window.saveConfig(true);
    } else {
        alert('Update failed: ' + d.error);
    }
}

async function deleteIgenPreset() {
    const name = document.getElementById('igen-preset').value;
    if (!name) { alert('Select a user preset to delete.'); return; }
    if (!confirm('Delete preset "' + name + '"?')) return;
    const r = await fetch('/hecos/api/media/presets/delete/' + encodeURIComponent(name), { method: 'DELETE' });
    const d = await r.json();
    if (d.ok) {
        await loadIgenPresets();
        document.getElementById('igen-preset').value = '';
        checkIgenPresetUI();
        if (typeof window.saveConfig === 'function') window.saveConfig(true);
    } else {
        alert('Delete failed: ' + d.error);
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// Aspect Ratio Helper
// ─────────────────────────────────────────────────────────────────────────────

function onAspectRatioChanged() {
    const val = document.getElementById('igen-aspect-ratio').value;
    document.getElementById('igen-custom-dims').style.display = (val === 'custom') ? 'block' : 'none';
}

// ─────────────────────────────────────────────────────────────────────────────
// Config Collect / Apply
// ─────────────────────────────────────────────────────────────────────────────

function collectIgenConfig() {
    const get = (id, def) => { const el = document.getElementById(id); return el ? el.value : def; };
    const chk = (id, def) => { const el = document.getElementById(id); return el ? el.checked : def; };
    return {
        provider:                  get('igen-provider',         'pollinations'),
        model:                     get('igen-model',            'flux'),
        aspect_ratio:              get('igen-aspect-ratio',     '1:1'),
        width:                     parseInt(get('igen-width',   1024)),
        height:                    parseInt(get('igen-height',  1024)),
        seed:                      parseInt(get('igen-seed',    -1)),
        sampler:                   get('igen-sampler',          'euler_a'),
        scheduler:                 get('igen-scheduler',        'euler'),
        guidance_scale:            parseFloat(get('igen-guidance', 7.5)),
        num_inference_steps:       parseInt(get('igen-steps',   30)),
        enable_negative_prompt:    chk('igen-use-neg-prompt',   false),
        negative_prompt:           get('igen-neg-prompt',       ''),
        auto_enrich:               chk('igen-auto-enrich',      false),
        enrich_keywords:           get('igen-enrich-keywords',  ''),
        style:                     get('igen-style',            'none'),
        nologo:                    chk('igen-nologo',           true),
        optimize_for_flux:         chk('igen-optimize-flux',    true),
        flux_refiner_instructions: get('igen-flux-instructions', ''),
        enabled:                   chk('igen-enabled',          true),
    };
}

function applyIgenConfig(cfg) {
    const set = (id, val) => { const el = document.getElementById(id); if (el) el.value   = val; };
    const chk = (id, val) => { const el = document.getElementById(id); if (el) el.checked = !!val; };
    set('igen-provider',            cfg.provider              || 'pollinations');
    set('igen-model',               cfg.model                 || 'flux');
    set('igen-aspect-ratio',        cfg.aspect_ratio          || '1:1');
    set('igen-width',               cfg.width                 || 1024);
    set('igen-height',              cfg.height                || 1024);
    set('igen-seed',                cfg.seed                  ?? -1);
    set('igen-sampler',             cfg.sampler               || 'euler_a');
    set('igen-scheduler',           cfg.scheduler             || 'euler');
    set('igen-guidance',            cfg.guidance_scale        ?? 7.5);
    document.getElementById('igen-guidance-val').textContent = cfg.guidance_scale ?? 7.5;
    set('igen-steps',               cfg.num_inference_steps   || 30);
    document.getElementById('igen-steps-val').textContent = cfg.num_inference_steps || 30;
    chk('igen-use-neg-prompt',      cfg.enable_negative_prompt);
    set('igen-neg-prompt',          cfg.negative_prompt       || '');
    chk('igen-auto-enrich',         cfg.auto_enrich);
    set('igen-enrich-keywords',     cfg.enrich_keywords       || '');
    set('igen-style',               cfg.style                 || 'none');
    chk('igen-nologo',              cfg.nologo                ?? true);
    chk('igen-optimize-flux',       cfg.optimize_for_flux     ?? true);
    set('igen-flux-instructions',   cfg.flux_refiner_instructions || '');
    chk('igen-enabled',             cfg.enabled               ?? true);
    onAspectRatioChanged();
    if (cfg.provider && typeof onProviderChanged === 'function') onProviderChanged();
    if (typeof window.saveConfig === 'function') window.saveConfig(true);
}

// ─────────────────────────────────────────────────────────────────────────────
// HuggingFace Hub Explorer
// ─────────────────────────────────────────────────────────────────────────────

async function searchHFHub() {
    const qEl          = document.getElementById('igen-hf-search-q');
    const q            = qEl ? qEl.value.trim() : '';
    const resContainer = document.getElementById('igen-hf-results');
    if (!resContainer) return;
    resContainer.innerHTML = '<div style="padding:10px; text-align:center; color:var(--muted); font-size:12px;">Searching...</div>';
    try {
        const res  = await fetch('/hecos/api/media/hf-search?q=' + encodeURIComponent(q));
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
            let badgeCol = "var(--text)", badgeBg = "var(--bg3)";
            if      (m.arch === "Flux")   { badgeCol = "#ff9800"; badgeBg = "rgba(255,152,0,0.1)"; }
            else if (m.arch === "SDXL")   { badgeCol = "#4caf50"; badgeBg = "rgba(76,175,80,0.1)"; }
            else if (m.arch === "SD 1.5") { badgeCol = "#2196f3"; badgeBg = "rgba(33,150,243,0.1)"; }

            let extraBadges = "";
            if (m.is_nsfw)               extraBadges += `<span style="font-size:9px;padding:1px 4px;border-radius:4px;border:1px solid rgba(231,76,60,0.5);background:rgba(231,76,60,0.1);color:#e74c3c;margin-left:4px;" title="Not suitable for all audiences">🔞 NSFW</span>`;
            if (m.is_gated)              extraBadges += `<span style="font-size:9px;padding:1px 4px;border-radius:4px;border:1px solid rgba(155,89,182,0.5);background:rgba(155,89,182,0.1);color:#9b59b6;margin-left:4px;" title="Requires HF Pro/Login">🔒 Gated</span>`;
            if (m.inference_status !== "warm") extraBadges += `<span style="font-size:9px;padding:1px 4px;border-radius:4px;border:1px solid rgba(52,152,219,0.5);background:rgba(52,152,219,0.1);color:#3498db;margin-left:4px;" title="Model is sleeping. Will take 30-60s to wake up on first generation">❄️ Cold</span>`;

            html += `<div style="display:flex;justify-content:space-between;align-items:center;padding:8px 10px;border-bottom:1px solid var(--border);">
                <div style="display:flex;flex-direction:column;overflow:hidden;" title="${m.id}">
                    <div style="display:flex;align-items:center;gap:6px;">
                        <strong style="font-size:12px;white-space:nowrap;text-overflow:ellipsis;overflow:hidden;color:var(--text);">${m.id}</strong>
                    </div>
                    <div style="display:flex;align-items:center;flex-wrap:wrap;margin-top:3px;">
                        <span style="font-size:9px;padding:1px 4px;border-radius:4px;border:1px solid ${badgeCol};background:${badgeBg};color:${badgeCol};white-space:nowrap;">${m.arch}</span>
                        ${extraBadges}
                    </div>
                    <span style="font-size:10px;color:var(--muted);margin-top:4px;">⬇️ ${m.downloads > 1000 ? (m.downloads/1000).toFixed(1)+'k' : m.downloads} | ❤️ ${m.likes}</span>
                </div>
                <button onclick="useHFModel('${m.id}')" style="padding:4px 10px;font-size:11px;border-radius:5px;border:1px solid var(--border);background:var(--bg3);color:var(--text);cursor:pointer;flex-shrink:0;margin-left:8px;">➕ Use</button>
            </div>`;
        });
        html += '</div>';
        resContainer.innerHTML = html;
    } catch (err) {
        resContainer.innerHTML = `<div style="padding:10px; color:var(--error, #e74c3c); font-size:12px;">Network Error: ${err.message}</div>`;
    }
}

function useHFModel(modelId) {
    const sel = document.getElementById('igen-model');
    if (!sel) return;
    let exists = false;
    for (let opt of sel.options) { if (opt.value === modelId) { exists = true; break; } }
    if (!exists) {
        const opt       = document.createElement('option');
        opt.value       = modelId;
        opt.textContent = modelId;
        sel.appendChild(opt);
    }
    sel.value               = modelId;
    sel.style.transition    = "border-color 0.2s, box-shadow 0.2s";
    sel.style.borderColor   = "var(--accent)";
    sel.style.boxShadow     = "0 0 5px var(--accent)";
    setTimeout(() => { sel.style.borderColor = ""; sel.style.boxShadow = ""; }, 800);
}

// ─────────────────────────────────────────────────────────────────────────────
// Bootstrap
// ─────────────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', loadIgenPresets);

// Expose public API
window.searchHFHub  = searchHFHub;
window.useHFModel   = useHFModel;
window.collectIgenConfig = collectIgenConfig;
window.applyIgenConfig   = applyIgenConfig;
