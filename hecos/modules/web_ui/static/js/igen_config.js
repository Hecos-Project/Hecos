/**
 * igen_config.js — Image Gen Panel: Collect, Apply & Save Config
 * collectIgenConfig, applyIgenConfig, saveIgenConfig, saveKeyToEnv.
 */

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
            if (statusEl) { statusEl.textContent = 'Save error!'; statusEl.style.color = 'var(--error, #e74c3c)'; }
        }
    } catch (e) {
        console.error('[ImageGen] Save config error:', e);
    }
};

window.saveKeyToEnv = async function() {
    let keyInput = document.getElementById('igen-api-key');
    const provSel = document.getElementById('igen-provider');
    if (!provSel) return;

    if (provSel.value === 'horde') keyInput = document.getElementById('horde-api-key');
    if (!keyInput) return;

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
            if (data.ok) { _igenAlert('Key saved globally to .env.', 'success'); keyInput.value = ''; }
            else { _igenAlert('Error saving key: ' + data.error); }
        } catch (e) { console.error(e); _igenAlert('Network error.'); }
    });
};

// ── Collect & Apply Config ─────────────────────────────────────────────────────

window.collectIgenConfig = function() {
    const get = (id, def) => { const el = document.getElementById(id); return el ? el.value : def; };
    const chk = (id, def) => { const el = document.getElementById(id); return el ? el.checked : def; };
    return {
        provider:               get('igen-provider', 'pollinations'),
        hf_provider:            get('igen-hf-provider', 'hf-inference'),
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
        show_metadata_in_chat:  chk('igen-show-metadata', false),
        routing_override:       get('igen-routing-override', ''),
        enabled:                chk('igen-enabled', true),
        api_key:                get('igen-api-key', ''),
        horde_api_key:          get('horde-api-key', ''),
        horde_nsfw:             chk('horde-nsfw', true),
        horde_worker_blacklist: get('horde-worker-blacklist', ''),
        vae:                    get('igen-vae', ''),
        loras:                  Array.from(document.getElementById('igen-loras')?.selectedOptions || []).map(o => o.value),
        cloud_enabled:          chk('igen-cloud-enabled', false),
    };
};

window.applyIgenConfig = function(cfg) {
    const set = (id, val) => { const el = document.getElementById(id); if (el) el.value = val; };
    const chk = (id, val) => { const el = document.getElementById(id); if (el) el.checked = !!val; };

    const pEl = document.getElementById('igen-provider');
    if (pEl) { pEl.setAttribute('data-initial-val', cfg.provider || 'pollinations'); pEl.value = cfg.provider || 'pollinations'; }
    set('igen-hf-provider', cfg.hf_provider || 'hf-inference');
    const mEl = document.getElementById('igen-model');
    if (mEl) { mEl.setAttribute('data-initial-val', cfg.model || 'flux'); mEl.value = cfg.model || 'flux'; }
    set('igen-aspect-ratio',cfg.aspect_ratio|| '1:1');

    set('igen-width',       cfg.width       || 1024);
    set('igen-height',      cfg.height      || 1024);
    set('igen-seed',        cfg.seed        ?? -1);
    set('igen-sampler',     cfg.sampler     || 'euler');
    set('igen-scheduler',   cfg.scheduler   || 'simple');
    set('igen-api-key',     cfg.api_key     || '');
    set('horde-api-key',    cfg.horde_api_key || '');
    chk('horde-nsfw',       cfg.horde_nsfw !== undefined ? cfg.horde_nsfw : true);
    set('horde-worker-blacklist', cfg.horde_worker_blacklist || '');
    set('igen-vae',         cfg.vae || '');
    
    const lorasEl = document.getElementById('igen-loras');
    if (lorasEl && cfg.loras && Array.isArray(cfg.loras)) {
        Array.from(lorasEl.options).forEach(o => {
            o.selected = cfg.loras.includes(o.value);
        });
    }

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
    chk('igen-show-metadata',   cfg.show_metadata_in_chat ?? false);
    set('igen-routing-override', cfg.routing_override   || '');
    chk('igen-enabled',         cfg.enabled             ?? true);
    chk('igen-cloud-enabled',   cfg.cloud_enabled       ?? false);

    onAspectRatioChanged();
    if (window._applyCloudToggleState) window._applyCloudToggleState();
};
