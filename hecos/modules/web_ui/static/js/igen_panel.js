/**
 * igen_panel.js
 * ─────────────────────────────────────────────────────────────────────────────
 * Hecos Image Generation — Config Panel Logic
 * Handles presets, config collect/apply, HuggingFace model explorer.
 * ─────────────────────────────────────────────────────────────────────────────
 */

// ─────────────────────────────────────────────────────────────────────────────
// Preset Helpers
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Loads all presets from the server and rebuilds the dropdown.
 * Returns a Promise so callers can await it before setting .value.
 * @param {string} [restoreValue] - preset name to select after reload
 */
async function loadIgenPresets(restoreValue) {
    try {
        const r = await fetch('/hecos/api/media/presets');
        const d = await r.json();
        if (!d.ok) return;

        const sel = document.getElementById('igen-preset');
        if (!sel) return;

        // Remember current selection if no explicit restore was requested
        const targetValue = restoreValue !== undefined ? restoreValue : sel.value;

        sel.innerHTML = '<option value="">— Select a preset —</option>';
        (d.presets || []).forEach(p => {
            const opt             = document.createElement('option');
            opt.value             = p.name;
            opt.textContent       = (p.builtin ? '' : '👤 ') + p.name;
            opt.dataset.builtin   = String(p.builtin);   // always "true" or "false"
            opt.dataset.name      = p.name;
            opt.title             = p.description || '';
            sel.appendChild(opt);
        });

        // Restore the previously selected value (if it still exists in the list)
        if (targetValue) {
            sel.value = targetValue;
            // If the option doesn't exist any more, .value will be "" — that's fine
        }

        checkIgenPresetUI();
    } catch (err) {
        console.warn('[igen] loadIgenPresets error:', err);
    }
}

/**
 * Show/hide the Update and Delete buttons based on whether the
 * currently selected preset is a user preset (not built-in, not empty).
 */
function checkIgenPresetUI() {
    const sel       = document.getElementById('igen-preset');
    const updateBtn = document.getElementById('igen-preset-update-btn');
    const deleteBtn = document.getElementById('igen-preset-delete-btn');
    if (!sel) return;

    const selectedOpt = sel.options[sel.selectedIndex];
    const isEmpty     = !sel.value;
    // dataset.builtin is set as the string "true" or "false"
    const isBuiltin   = selectedOpt ? (selectedOpt.dataset.builtin === 'true') : true;

    const show = !isEmpty && !isBuiltin;
    if (updateBtn) updateBtn.style.display = show ? 'inline-block' : 'none';
    if (deleteBtn) deleteBtn.style.display = show ? 'inline-block' : 'none';
}

/**
 * Called when the user picks a preset from the dropdown.
 * Loads the preset values from the server, applies them to the DOM,
 * then saves the full config (including active_preset) to YAML.
 */
async function loadIgenPreset() {
    const sel  = document.getElementById('igen-preset');
    const name = sel ? sel.value : '';
    if (!name) {
        // User chose "— Select a preset —" → just save active_preset as ""
        checkIgenPresetUI();
        if (typeof window.saveConfig === 'function') window.saveConfig(true);
        return;
    }

    try {
        const r = await fetch('/hecos/api/media/presets/load/' + encodeURIComponent(name));
        const d = await r.json();
        if (!d.ok) {
            alert('Error loading preset: ' + d.error);
            // Preset not found — remove it from the dropdown if it was a user preset
            await loadIgenPresets('');
            return;
        }

        // Apply preset values to the DOM WITHOUT triggering an auto-save from applyIgenConfig.
        // We pass { skipSave: true } so the function knows not to call saveConfig by itself.
        applyIgenConfig(d.config, { skipSave: true });

        // Now explicitly set active_preset in the DOM (applyIgenConfig doesn't touch the preset select)
        if (sel) sel.value = name;

        checkIgenPresetUI();

        // Single authoritative save — reads all DOM values including active_preset
        if (typeof window.saveConfig === 'function') {
            // Small delay so the browser commits all DOM mutations (selects, ranges, etc.)
            setTimeout(() => window.saveConfig(true), 80);
        }
    } catch (err) {
        console.error('[igen] loadIgenPreset error:', err);
        alert('Network error loading preset.');
    }
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
        // Reload the dropdown and select the new preset
        await loadIgenPresets(name.trim());
        // Update window.mediaConfig so future saves preserve the new preset
        if (window.mediaConfig && window.mediaConfig.image_gen) {
            if (!window.mediaConfig.image_gen.presets) window.mediaConfig.image_gen.presets = {};
            window.mediaConfig.image_gen.presets[name.trim()] = config;
        }
        checkIgenPresetUI();
        if (typeof window.saveConfig === 'function') window.saveConfig(true);
    } else {
        alert('Save failed: ' + d.error);
    }
}

async function updateIgenPreset() {
    const sel  = document.getElementById('igen-preset');
    const name = sel ? sel.value : '';
    if (!name) return;
    const config = collectIgenConfig();
    const r = await fetch('/hecos/api/media/presets/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, config }),
    });
    const d = await r.json();
    if (d.ok) {
        // Update window.mediaConfig so future saves preserve the updated preset
        if (window.mediaConfig && window.mediaConfig.image_gen) {
            if (!window.mediaConfig.image_gen.presets) window.mediaConfig.image_gen.presets = {};
            window.mediaConfig.image_gen.presets[name] = config;
        }
        const btn = document.getElementById('igen-preset-update-btn');
        if (btn) {
            btn.innerHTML         = '✅ Saved!';
            btn.style.color       = '#2ecc71';
            btn.style.borderColor = '#2ecc71';
            btn.style.background  = 'rgba(46,204,113,0.1)';
            setTimeout(() => {
                btn.innerHTML         = '🔄 Update';
                btn.style.color       = 'var(--accent)';
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
    const name = document.getElementById('igen-preset') ? document.getElementById('igen-preset').value : '';
    if (!name) { alert('Select a user preset to delete.'); return; }
    if (!confirm('Delete preset "' + name + '"?')) return;
    const r = await fetch('/hecos/api/media/presets/delete/' + encodeURIComponent(name), { method: 'DELETE' });
    const d = await r.json();
    if (d.ok) {
        // Remove from local cache so future saves don't resurrect it
        if (window.mediaConfig && window.mediaConfig.image_gen && window.mediaConfig.image_gen.presets) {
            delete window.mediaConfig.image_gen.presets[name];
        }
        await loadIgenPresets('');
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
        sampler:                   get('igen-sampler',          'euler'),
        scheduler:                 get('igen-scheduler',        'simple'),
        guidance_scale:            parseFloat(get('igen-guidance', 0.0)),
        num_inference_steps:       parseInt(get('igen-steps',   4)),
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

/**
 * Applies a config object to all DOM fields.
 * @param {Object} cfg - config values to apply
 * @param {Object} [opts] - options
 * @param {boolean} [opts.skipSave] - if true, do NOT call saveConfig after applying
 */
function applyIgenConfig(cfg, opts = {}) {
    const set = (id, val) => { const el = document.getElementById(id); if (el) el.value   = val; };
    const chk = (id, val) => { const el = document.getElementById(id); if (el) el.checked = !!val; };

    set('igen-provider',            cfg.provider              || 'pollinations');
    set('igen-model',               cfg.model                 || 'flux');
    set('igen-aspect-ratio',        cfg.aspect_ratio          || '1:1');
    set('igen-width',               cfg.width                 || 1024);
    set('igen-height',              cfg.height                || 1024);
    set('igen-seed',                cfg.seed                  ?? -1);
    set('igen-sampler',             cfg.sampler               || 'euler');
    set('igen-scheduler',           cfg.scheduler             || 'simple');

    // Guidance: use ?? so that 0.0 is preserved (not replaced by fallback)
    const guidance = cfg.guidance_scale ?? 0.0;
    set('igen-guidance', guidance);
    const gValEl = document.getElementById('igen-guidance-val');
    if (gValEl) gValEl.textContent = parseFloat(guidance).toFixed(1);

    const steps = cfg.num_inference_steps || 4;
    set('igen-steps', steps);
    const sValEl = document.getElementById('igen-steps-val');
    if (sValEl) sValEl.textContent = steps;

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

    // Only auto-save if the caller hasn't opted out
    if (!opts.skipSave && typeof window.saveConfig === 'function') {
        // Defer so the browser commits all DOM mutations first.
        setTimeout(() => window.saveConfig(true), 80);
    }
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
// Bootstrap — fires on DOMContentLoaded
// ─────────────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    // Add change listener to the preset dropdown so checkIgenPresetUI runs whenever the user picks a preset
    const presetSel = document.getElementById('igen-preset');
    if (presetSel) {
        presetSel.addEventListener('change', () => checkIgenPresetUI());
    }
    // Initial preset list load is handled by populateMediaUI() in config_media_logic.js
    // which is async and awaits loadIgenPresets() before setting the active preset value.
});

// ─────────────────────────────────────────────────────────────────────────────
// Expose public API
// ─────────────────────────────────────────────────────────────────────────────
window.searchHFHub       = searchHFHub;
window.useHFModel        = useHFModel;
window.collectIgenConfig = collectIgenConfig;
window.applyIgenConfig   = applyIgenConfig;
window.loadIgenPresets   = loadIgenPresets;
window.loadIgenPreset    = loadIgenPreset;
window.saveIgenPreset    = saveIgenPreset;
window.updateIgenPreset  = updateIgenPreset;
window.deleteIgenPreset  = deleteIgenPreset;
window.checkIgenPresetUI = checkIgenPresetUI;
window.onAspectRatioChanged = onAspectRatioChanged;
