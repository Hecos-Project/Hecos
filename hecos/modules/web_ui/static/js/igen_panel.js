/**
 * image_gen — Plugin Panel JS (v1.0.3)
 * Auto-save on change (debounced). No manual save button needed.
 * Also hooks into Hecos global saveConfig() so the hub Save button works too.
 */

// ── Auto-save debouncer ────────────────────────────────────────────────────────
let _igenSaveTimer = null;

function _igenDebounceSave() {
    clearTimeout(_igenSaveTimer);
    _igenSaveTimer = setTimeout(() => { window.saveIgenConfig(true); }, 500);
}

// ── Custom UI Wrappers ─────────────────────────────────────────────────────────

function _igenAlert(msg, type='error') {
    if (window.showToast) window.showToast(msg, type);
    else console.error('[ImageGen]', msg);
}

function _igenConfirm(msg, onYes) {
    if (window.hpmShowConfirm) window.hpmShowConfirm(msg, 'Confirm', onYes);
    else if (confirm(msg)) onYes();
}

function _igenPrompt(msg, onSave) {
    const modalId = 'igen-custom-prompt-modal';
    let modal = document.getElementById(modalId);
    if (!modal) {
        modal = document.createElement('div');
        modal.id = modalId;
        modal.className = 'modal-bg';
        modal.style.cssText = 'position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.6); display:flex; align-items:center; justify-content:center; z-index:9999;';
        modal.innerHTML = `
            <div style="background:var(--bg2); border:1px solid var(--border); padding:24px; border-radius:12px; max-width:400px; width:90%; box-shadow:0 10px 30px rgba(0,0,0,0.5);">
                <h3 style="margin-top:0; color:var(--text);"><i class="fas fa-keyboard" style="margin-right:8px; color:var(--accent);"></i> Input Required</h3>
                <p id="${modalId}-text" style="margin:20px 0; color:var(--text); font-size:1.05em;"></p>
                <input type="text" id="${modalId}-input" class="config-input" style="width:100%; margin-bottom:20px; border:1px solid var(--border); background:var(--bg3); color:var(--text); padding:8px 12px; border-radius:6px;">
                <div style="display:flex; justify-content:flex-end; gap:10px;">
                    <button class="btn" id="${modalId}-cancel" style="border:1px solid var(--border); background:var(--bg3); color:var(--text); padding:8px 16px; border-radius:6px; cursor:pointer;">Cancel</button>
                    <button class="btn" style="background:var(--accent); color:white; border:none; padding:8px 16px; border-radius:6px; cursor:pointer;" id="${modalId}-save">Save</button>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
    }
    document.getElementById(modalId + '-text').textContent = msg;
    const input = document.getElementById(modalId + '-input');
    input.value = '';
    
    const cleanup = () => { modal.style.display = 'none'; };
    
    document.getElementById(modalId + '-cancel').onclick = cleanup;
    document.getElementById(modalId + '-save').onclick = () => {
        cleanup();
        const val = input.value.trim();
        if (val) onSave(val);
    };
    
    modal.style.display = 'flex';
    setTimeout(() => input.focus(), 100);
}

// ── Provider & Model Logic ─────────────────────────────────────────────────────

/**
 * Fetch models for the currently selected provider.
 * Retries automatically with exponential back-off if the API route is not yet
 * ready (happens right after a fresh install before Flask has registered routes).
 *
 * @param {boolean} userTriggered  - true when the user explicitly changed the provider
 * @param {number}  _attempt       - internal retry counter (do not pass manually)
 */
window.onProviderChanged = async function(userTriggered = false, _attempt = 0) {
    const provSel = document.getElementById('igen-provider');
    const modelSel = document.getElementById('igen-model');
    if (!provSel || !modelSel) return;

    const providers = [
        { id: 'pollinations',   name: 'Pollinations (Free, Fast)' },
        { id: 'gemini',         name: 'Google Gemini' },
        { id: 'gemini_native',  name: 'Google Gemini Native (Flash)' },
        { id: 'openai',         name: 'OpenAI DALL-E' },
        { id: 'stability',      name: 'Stability AI' },
        { id: 'airforce',       name: 'Airforce (Free)' },
        { id: 'huggingface',    name: 'Hugging Face Inference API' }
    ];

    if (provSel.options.length === 0) {
        providers.forEach(p => {
            const opt = document.createElement('option');
            opt.value = p.id;
            opt.textContent = p.name;
            provSel.appendChild(opt);
        });
        const initialProv = provSel.getAttribute('data-initial-val') || 'pollinations';
        provSel.value = initialProv;
    }

    const hfWrap = document.getElementById('igen-hf-explorer-wrapper');
    if (hfWrap) hfWrap.style.display = (provSel.value === 'huggingface') ? 'block' : 'none';

    // Show a subtle loading state on the model dropdown
    const statusEl = document.getElementById('igen-model-status');
    if (statusEl && _attempt === 0) statusEl.textContent = '⏳ loading...';

    try {
        const res = await fetch('/hecos/api/plugins/image_gen/models?provider=' + provSel.value);

        // Route not yet registered (404 or HTML error page) → retry with back-off
        if (!res.ok) {
            throw new Error(`HTTP ${res.status}`);
        }

        const data = await res.json();
        if (!data.ok) throw new Error(data.error || 'API returned ok=false');

        const currentSelection = userTriggered ? '' : modelSel.value;
        modelSel.innerHTML = '';
        if (data.models && data.models.length) {
            data.models.forEach(m => {
                const opt = document.createElement('option');
                opt.value = m;
                opt.textContent = m;
                modelSel.appendChild(opt);
            });
            if (currentSelection && data.models.includes(currentSelection)) {
                modelSel.value = currentSelection;
            }
        }
        if (statusEl) statusEl.textContent = '';

    } catch (e) {
        const MAX_RETRIES = 5;
        const RETRY_DELAY_MS = 800;
        if (_attempt < MAX_RETRIES) {
            if (statusEl) statusEl.textContent = `⏳ Retrying (${_attempt + 1}/${MAX_RETRIES})...`;
            console.warn(`[ImageGen] Models fetch failed (attempt ${_attempt + 1}): ${e.message}. Retrying in ${RETRY_DELAY_MS}ms...`);
            setTimeout(() => window.onProviderChanged(userTriggered, _attempt + 1), RETRY_DELAY_MS);
            return;
        }
        if (statusEl) statusEl.textContent = '⚠️ Could not load — click Refresh';
        console.error('[ImageGen] Fetch models error after all retries:', e);
    }

    if (userTriggered) _igenDebounceSave();
};

window.refreshImageModels = function() {
    window.onProviderChanged(false, 0);
};

/**
 * Reload the entire panel: presets + provider + models.
 * Exposed as window.reloadIgenPanel() and wired to the Refresh button.
 */
window.reloadIgenPanel = async function() {
    const btn = document.getElementById('igen-refresh-btn');
    if (btn) {
        btn.innerHTML = '<i class="fas fa-spinner fa-spin" style="font-size:13px;"></i> Loading...';
        btn.disabled = true;
    }
    try {
        // Re-apply saved config
        const res  = await fetch('/hecos/api/plugins/image_gen/config');
        const data = await res.json();
        const cfg  = data.image_gen || {};
        await window.loadIgenPresets(cfg.active_preset);
        window.applyIgenConfig(cfg);
        // Force reset provider list and re-fetch models
        const provSel = document.getElementById('igen-provider');
        if (provSel) provSel.innerHTML = '';
        await window.onProviderChanged(false, 0);
    } catch(e) {
        console.error('[ImageGen] reloadIgenPanel error:', e);
    } finally {
        if (btn) {
            btn.innerHTML = '<i class="fas fa-sync-alt" style="font-size:13px;"></i> Refresh';
            btn.disabled = false;
        }
    }
};

// ── Config Save ────────────────────────────────────────────────────────────────

window.saveIgenConfig = async function(silent = false) {
    const cfg = window.collectIgenConfig();
    const presetEl = document.getElementById('igen-preset');
    cfg.active_preset = presetEl ? presetEl.value : '';

    const statusEl = document.getElementById('igen-save-status');
    if (!silent && statusEl) {
        statusEl.textContent = 'Saving...';
        statusEl.style.color = 'var(--muted)';
    }

    try {
        const res = await fetch('/hecos/api/plugins/image_gen/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image_gen: cfg })
        });
        const data = await res.json();
        if (data.ok) {
            if (statusEl) {
                statusEl.textContent = '\u2713 Saved';
                statusEl.style.color = 'var(--ok, #2ecc71)';
                setTimeout(() => { statusEl.textContent = ''; }, 2000);
            }
        } else {
            console.error('[ImageGen] Save failed:', data.error);
            if (statusEl) {
                statusEl.textContent = 'Save error!';
                statusEl.style.color = 'var(--error, #e74c3c)';
            }
        }
    } catch (e) {
        console.error('[ImageGen] Save config error:', e);
    }
};

window.saveKeyToEnv = async function() {
    const keyInput = document.getElementById('igen-api-key');
    const provSel  = document.getElementById('igen-provider');
    if (!keyInput || !provSel) return;

    const key = keyInput.value.trim();
    if (!key) { _igenAlert('Please enter a key to save globally.'); return; }
    
    _igenConfirm('Save this API key to the global .env file for ' + provSel.value + '?', async () => {
        try {
            const res = await fetch('/hecos/api/plugins/image_gen/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ image_gen: {
                    _internal_save_to_env: true,
                    api_key: key,
                    provider: provSel.value,
                    api_key_comment: 'ImageGen Panel'
                }})
            });
            const data = await res.json();
            if (data.ok) {
                _igenAlert('Key saved globally to .env.', 'success');
                keyInput.value = '';
            } else {
                _igenAlert('Error saving key: ' + data.error);
            }
        } catch (e) {
            console.error(e);
            _igenAlert('Network error.');
        }
    });
};

// ── Collect & Apply Config ─────────────────────────────────────────────────────

window.collectIgenConfig = function() {
    const get = (id, def) => { const el = document.getElementById(id); return el ? el.value : def; };
    const chk = (id, def) => { const el = document.getElementById(id); return el ? el.checked : def; };
    return {
        provider:               get('igen-provider', 'pollinations'),
        model:                  get('igen-model', 'flux'),
        aspect_ratio:           get('igen-aspect-ratio', '1:1'),
        width:                  parseInt(get('igen-width', 1024)),
        height:                 parseInt(get('igen-height', 1024)),
        seed:                   parseInt(get('igen-seed', -1)),
        sampler:                get('igen-sampler', 'euler'),
        scheduler:              get('igen-scheduler', 'simple'),
        guidance_scale:         parseFloat(get('igen-guidance', 0.0)),
        num_inference_steps:    parseInt(get('igen-steps', 4)),
        enable_negative_prompt: chk('igen-use-neg-prompt', false),
        negative_prompt:        get('igen-neg-prompt', ''),
        auto_enrich:            chk('igen-auto-enrich', false),
        enrich_keywords:        get('igen-enrich-keywords', ''),
        style:                  get('igen-style', 'none'),
        nologo:                 chk('igen-nologo', true),
        optimize_for_flux:      chk('igen-optimize-flux', true),
        show_metadata:          chk('igen-show-metadata', false),
        routing_override:       get('igen-routing-override', ''),
        enabled:                chk('igen-enabled', true),
        api_key:                get('igen-api-key', ''),
    };
};

window.applyIgenConfig = function(cfg) {
    const set = (id, val) => { const el = document.getElementById(id); if (el) el.value = val; };
    const chk = (id, val) => { const el = document.getElementById(id); if (el) el.checked = !!val; };

    set('igen-provider',    cfg.provider    || 'pollinations');
    set('igen-model',       cfg.model       || 'flux');
    set('igen-aspect-ratio',cfg.aspect_ratio|| '1:1');
    set('igen-width',       cfg.width       || 1024);
    set('igen-height',      cfg.height      || 1024);
    set('igen-seed',        cfg.seed        ?? -1);
    set('igen-sampler',     cfg.sampler     || 'euler');
    set('igen-scheduler',   cfg.scheduler   || 'simple');
    set('igen-api-key',     cfg.api_key     || '');

    const guidance = cfg.guidance_scale ?? 0.0;
    set('igen-guidance', guidance);
    const gValEl = document.getElementById('igen-guidance-val');
    if (gValEl) gValEl.textContent = parseFloat(guidance).toFixed(1);

    const steps = cfg.num_inference_steps || 4;
    set('igen-steps', steps);
    const sValEl = document.getElementById('igen-steps-val');
    if (sValEl) sValEl.textContent = steps;

    chk('igen-use-neg-prompt',  cfg.enable_negative_prompt);
    set('igen-neg-prompt',      cfg.negative_prompt     || '');
    chk('igen-auto-enrich',     cfg.auto_enrich);
    set('igen-enrich-keywords', cfg.enrich_keywords     || '');
    set('igen-style',           cfg.style               || 'none');
    chk('igen-nologo',          cfg.nologo              ?? true);
    chk('igen-optimize-flux',   cfg.optimize_for_flux   ?? true);
    chk('igen-show-metadata',   cfg.show_metadata       ?? false);
    set('igen-routing-override', cfg.routing_override   || '');
    chk('igen-enabled',         cfg.enabled             ?? true);

    onAspectRatioChanged();
};

// ── Preset Logic ───────────────────────────────────────────────────────────────

window.loadIgenPresets = async function(restoreValue) {
    try {
        const r = await fetch('/hecos/api/plugins/image_gen/presets');
        const d = await r.json();
        if (!d.ok) return;

        const sel = document.getElementById('igen-preset');
        if (!sel) return;

        const targetValue = restoreValue !== undefined ? restoreValue : sel.value;
        sel.innerHTML = '<option value="">\u2014 Select a preset \u2014</option>';

        (d.presets || []).forEach(p => {
            const opt = document.createElement('option');
            opt.value = p.name;
            opt.textContent = (p.builtin ? '' : '\ud83d\udc64 ') + p.name;
            opt.dataset.builtin = String(p.builtin);
            sel.appendChild(opt);
        });

        if (targetValue) sel.value = targetValue;
        checkIgenPresetUI();
    } catch (err) {
        console.warn('[igen] loadIgenPresets error:', err);
    }
};

window.loadIgenPreset = async function() {
    const sel = document.getElementById('igen-preset');
    const name = sel ? sel.value : '';
    if (!name) { checkIgenPresetUI(); return; }

    try {
        const r = await fetch('/hecos/api/plugins/image_gen/presets/load/' + encodeURIComponent(name));
        const d = await r.json();
        if (!d.ok) { _igenAlert('Error loading preset: ' + d.error); return; }
        window.applyIgenConfig(d.config);
        if (sel) sel.value = name;
        checkIgenPresetUI();
        // Auto-save the newly selected preset as active
        _igenDebounceSave();
    } catch (err) {
        console.error('[igen] preset load error', err);
    }
};

window.saveIgenPreset = function() {
    _igenPrompt('Name for this preset:', async (name) => {
        const config = window.collectIgenConfig();
        const r = await fetch('/hecos/api/plugins/image_gen/presets/save', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: name, config })
        });
        const d = await r.json();
        if (d.ok) {
            await window.loadIgenPresets(name);
        } else {
            _igenAlert('Save failed: ' + d.error);
        }
    });
};

window.updateIgenPreset = async function() {
    const sel = document.getElementById('igen-preset');
    const name = sel ? sel.value : '';
    if (!name) return;
    const config = window.collectIgenConfig();
    const r = await fetch('/hecos/api/plugins/image_gen/presets/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, config })
    });
    const d = await r.json();
    if (d.ok) {
        const btn = document.getElementById('igen-preset-update-btn');
        if (btn) {
            btn.innerHTML = '\u2705 Saved!';
            setTimeout(() => { btn.innerHTML = '\ud83d\udd04 Update'; }, 1500);
        }
    } else {
        _igenAlert('Update failed: ' + d.error);
    }
};

window.deleteIgenPreset = async function() {
    const name = document.getElementById('igen-preset') ? document.getElementById('igen-preset').value : '';
    if (!name) return;
    
    const r = await fetch('/hecos/api/plugins/image_gen/presets/delete/' + encodeURIComponent(name), { method: 'DELETE' });
    const d = await r.json();
    if (d.ok) {
        await window.loadIgenPresets('');
    } else {
        _igenAlert('Delete failed: ' + d.error);
    }
};

window.checkIgenPresetUI = function() {
    const sel = document.getElementById('igen-preset');
    const updateBtn = document.getElementById('igen-preset-update-btn');
    const deleteBtn = document.getElementById('igen-preset-delete-btn');
    if (!sel) return;

    const selectedOpt = sel.options[sel.selectedIndex];
    const isEmpty    = !sel.value;
    const isBuiltin  = selectedOpt ? (selectedOpt.dataset.builtin === 'true') : true;
    const show = !isEmpty && !isBuiltin;
    if (updateBtn) updateBtn.style.display = show ? 'inline-block' : 'none';
    if (deleteBtn) deleteBtn.style.display = show ? 'inline-block' : 'none';
};

window.onAspectRatioChanged = function() {
    const val = document.getElementById('igen-aspect-ratio');
    const dims = document.getElementById('igen-custom-dims');
    if (val && dims) dims.style.display = (val.value === 'custom') ? 'block' : 'none';
};

// ── HF Explorer ────────────────────────────────────────────────────────────────

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
                  + '<div><strong>' + m.id + '</strong><br><small>\u2b07\ufe0f ' + m.downloads + ' | \u2764\ufe0f ' + m.likes + '</small></div>'
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

// ── Auto-save wiring ───────────────────────────────────────────────────────────

function _igenAttachAutoSave() {
    const fields = [
        'igen-aspect-ratio', 'igen-width', 'igen-height', 'igen-seed',
        'igen-sampler', 'igen-scheduler', 'igen-guidance', 'igen-steps',
        'igen-use-neg-prompt', 'igen-neg-prompt',
        'igen-auto-enrich', 'igen-enrich-keywords',
        'igen-style', 'igen-nologo', 'igen-show-metadata', 'igen-optimize-flux'
    ];
    fields.forEach(id => {
        const el = document.getElementById(id);
        if (!el) return;
        const evt = (el.type === 'checkbox' || el.tagName === 'SELECT') ? 'change' : 'input';
        el.addEventListener(evt, _igenDebounceSave);
    });
}

// ── Hook into Hecos global saveConfig ─────────────────────────────────────────
// When the user clicks the main "Save Configuration" button in the Hecos hub,
// we also save the image_gen plugin config silently.
function _igenHookGlobalSave() {
    if (typeof window.saveConfig !== 'function') return;
    const _orig = window.saveConfig;
    window.saveConfig = async function(silent = false) {
        await _orig.call(this, silent);
        await window.saveIgenConfig(true);
    };
}

// ── Bootstrap ──────────────────────────────────────────────────────────────────
// The HPM Asset Loader injects our JS *before* the panel HTML is merged into the
// hub. So we must wait for the key element to appear in the DOM before we init.

let _igenInitDone = false;

function _waitForIgenPanel(callback) {
    // If the element is already in the DOM (e.g. after a page refresh), run now.
    if (document.getElementById('igen-provider')) {
        callback();
        return;
    }
    // Otherwise watch for it to be inserted via the HPM hub merger.
    const observer = new MutationObserver((mutations, obs) => {
        if (document.getElementById('igen-provider')) {
            obs.disconnect();
            callback();
        }
    });
    observer.observe(document.body, { childList: true, subtree: true });
}

const initImageGenPanel = async () => {
    if (_igenInitDone) return;
    _igenInitDone = true;

    console.log('[ImageGen] Panel DOM ready — initializing...');
    try {
        const res  = await fetch('/hecos/api/plugins/image_gen/config');
        const data = await res.json();
        const cfg  = data.image_gen || {};

        // 1. Load presets (they may set active_preset)
        await window.loadIgenPresets(cfg.active_preset);

        // 2. Apply saved config to UI elements
        window.applyIgenConfig(cfg);

        // 3. Populate providers & models dropdowns
        await window.onProviderChanged(false);

        // 4. Wire auto-save to all inputs
        _igenAttachAutoSave();

        // 5. Hook global save button
        _igenHookGlobalSave();

        console.log('[ImageGen] Panel ready.');
    } catch (e) {
        console.error('[ImageGen] Bootstrap error:', e);
    }
};

// Wait for panel HTML to be in DOM, then init.
_waitForIgenPanel(initImageGenPanel);

// ── Auto-refresh when user returns to the tab after the panel was hidden ───────
// This catches the case where the panel was open before the API routes were ready.
document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible' && _igenInitDone) {
        const provSel = document.getElementById('igen-provider');
        // Only auto-refresh if the model dropdown is empty (routes not ready before)
        const modelSel = document.getElementById('igen-model');
        if (provSel && modelSel && modelSel.options.length === 0) {
            console.log('[ImageGen] Tab became visible with empty models — auto-refreshing...');
            window.onProviderChanged(false, 0);
        }
    }
});
