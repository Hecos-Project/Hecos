/**
 * igen_presets.js - Image Gen Panel: Preset Management
 * Now includes full config snapshot, Set as Default, and live config summary.
 */

window.loadIgenPresets = async function(restoreValue) {
    try {
        const r = await fetch('/hecos/api/plugins/image_gen/presets');
        const d = await r.json();
        if (!d.ok) return;

        const sel = document.getElementById('igen-preset');
        if (!sel) return;

        const targetValue = restoreValue !== undefined ? restoreValue : sel.value;
        sel.innerHTML = '<option value="">— Select a preset —</option>';

        const localGroup = document.createElement('optgroup');
        localGroup.label = "💻 Local Presets";
        const cloudGroup = document.createElement('optgroup');
        cloudGroup.label = "☁️ Cloud Presets (Built-in)";
        const userGroup = document.createElement('optgroup');
        userGroup.label = "👤 My Custom Presets";

        let defaultFound = false;

        (d.presets || []).forEach(p => {
            const opt = document.createElement('option');
            let text = p.name;
            if (p.is_default) {
                text = text + " ⭐ [Default]";
                defaultFound = true;
            }
            opt.value = p.name;
            opt.textContent = text;
            opt.dataset.builtin = String(p.builtin);
            opt.dataset.isDefault = String(p.is_default);

            if (!p.builtin) {
                userGroup.appendChild(opt);
            } else if (p.is_local) {
                localGroup.appendChild(opt);
            } else {
                cloudGroup.appendChild(opt);
            }
        });

        if (localGroup.children.length > 0) sel.appendChild(localGroup);
        if (cloudGroup.children.length > 0) sel.appendChild(cloudGroup);
        if (userGroup.children.length > 0)  sel.appendChild(userGroup);

        if (targetValue) sel.value = targetValue;
        checkIgenPresetUI();
        if (typeof window.updateIgenLiveSummary === 'function') window.updateIgenLiveSummary();
    } catch (err) {
        console.warn('[igen] loadIgenPresets error:', err);
    }
};

window.loadIgenPreset = async function() {
    const sel  = document.getElementById('igen-preset');
    const name = sel ? sel.value : '';
    if (!name) { checkIgenPresetUI(); return; }

    try {
        const r = await fetch('/hecos/api/plugins/image_gen/presets/load/' + encodeURIComponent(name));
        const d = await r.json();
        if (!d.ok) { _igenAlert('Error loading preset: ' + d.error); return; }
        
        // Disable auto-save temporarily while applying the preset
        window._igenDisableAutoSave = true;
        window.applyIgenConfig(d.config);
        
        // Await the provider and model fetch so DOM is actually ready
        if (typeof window.onProviderChanged === 'function') {
            await window.onProviderChanged(false);
        }
        
        window._igenDisableAutoSave = false;
        if (sel) sel.value = name;
        checkIgenPresetUI();
        if (typeof window.updateIgenLiveSummary === 'function') window.updateIgenLiveSummary();
        if (typeof window._igenDebounceSave === 'function') window._igenDebounceSave();

    } catch (err) {
        console.error('[igen] preset load error', err);
    }
};

window.saveIgenPreset = function() {
    _igenPrompt('Name for this new preset (saves full config):', async (name) => {
        const config = window.collectIgenConfig();
        const r = await fetch('/hecos/api/plugins/image_gen/presets/save', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, config })
        });
        const d = await r.json();
        if (d.ok) { 
            await window.loadIgenPresets(name); 
            _igenDebounceSave(); // Save active_preset
        } else { _igenAlert('Save failed: ' + d.error); }
    });
};

window.updateIgenPreset = async function() {
    const sel  = document.getElementById('igen-preset');
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
            btn.innerHTML = '✅ Saved!';
            setTimeout(() => { btn.innerHTML = '<i class="fas fa-sync"></i> Update'; }, 1500);
        }
    } else {
        _igenAlert('Update failed: ' + d.error);
    }
};

window.deleteIgenPreset = async function() {
    const name = document.getElementById('igen-preset')?.value || '';
    if (!name) return;

    _igenConfirm(`Delete preset '${name}'?`, async () => {
        const r = await fetch('/hecos/api/plugins/image_gen/presets/delete/' + encodeURIComponent(name), { method: 'DELETE' });
        const d = await r.json();
        if (d.ok) { await window.loadIgenPresets(''); _igenDebounceSave(); }
        else { _igenAlert('Delete failed: ' + d.error); }
    });
};

window.setIgenDefaultPreset = async function() {
    const sel = document.getElementById('igen-preset');
    const name = sel ? sel.value : '';
    // Empty name clears the default
    
    try {
        const r = await fetch('/hecos/api/plugins/image_gen/presets/set-default', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name })
        });
        const d = await r.json();
        if (d.ok) {
            await window.loadIgenPresets(name);
        } else {
            _igenAlert('Failed to set default: ' + d.error);
        }
    } catch (e) {
        console.error(e);
        _igenAlert('Network error.');
    }
};

window.checkIgenPresetUI = function() {
    const sel       = document.getElementById('igen-preset');
    const updateBtn = document.getElementById('igen-preset-update-btn');
    const deleteBtn = document.getElementById('igen-preset-delete-btn');
    const defaultBtn = document.getElementById('igen-preset-default-btn');
    if (!sel) return;

    const selectedOpt = sel.options[sel.selectedIndex];
    const isEmpty    = !sel.value;
    const isBuiltin  = selectedOpt ? (selectedOpt.dataset.builtin === 'true') : true;
    const isDefault  = selectedOpt ? (selectedOpt.dataset.isDefault === 'true') : false;
    
    const showCustomActions = !isEmpty && !isBuiltin;
    
    if (updateBtn) updateBtn.style.display = showCustomActions ? 'inline-flex' : 'none';
    if (deleteBtn) deleteBtn.style.display = showCustomActions ? 'inline-flex' : 'none';
    
    // Builtin presets can also be set as default!
    if (defaultBtn) {
        defaultBtn.style.display = !isEmpty ? 'inline-flex' : 'none';
        if (isDefault) {
            defaultBtn.innerHTML = '<i class="fas fa-star" style="color:#fbbf24;"></i> Default';
            defaultBtn.onclick = () => window.setIgenDefaultPreset(''); // Click again to clear
            defaultBtn.title = "Clear default";
        } else {
            defaultBtn.innerHTML = '<i class="far fa-star"></i> Set as Default';
            defaultBtn.onclick = () => window.setIgenDefaultPreset();
            defaultBtn.title = "Load this preset automatically on startup";
        }
    }
};

// -- Live Summary -----------------------------------------------------------

window.updateIgenLiveSummary = function() {
    const summEl = document.getElementById('igen-live-summary');
    if (!summEl) return;
    
    const c = window.collectIgenConfig();
    if (!c) return;
    
    let html = '';
    const row = (label, val, warn=false) => {
        if (!val) return;
        html += `<div style="display:flex; justify-content:space-between; margin-bottom:2px;">
            <span style="color:var(--muted);">${label}:</span>
            <span style="${warn?'color:#e74c3c; font-weight:bold;': 'font-weight:500;'} text-align:right;">${val}</span>
        </div>`;
    };
    
    row('Provider', c.provider === 'swarmui' ? 'SwarmUI (Local)' : c.provider);
    row('Model', c.model);
    
    if (c.provider === 'swarmui') {
        row('VAE', c.vae || 'Default');
        if (c.loras && c.loras.length) row('LoRAs', c.loras.length + ' active');
        row('Sampler', c.sampler);
        row('Scheduler', c.scheduler);
    }
    
    const neg = c.enable_negative_prompt ? '✅ ON' : '❌ OFF';
    const enrich = c.auto_enrich ? '✅ ON' : '❌ OFF';
    
    row('Steps / CFG', `${c.num_inference_steps}  |  ${c.guidance_scale.toFixed(1)}`);
    row('Size', `${c.width}x${c.height} (${c.aspect_ratio})`);
    row('Neg Prompt', neg);
    row('Enrich', enrich);
    
    summEl.innerHTML = html;
};

// Hook into any config change to update summary
document.addEventListener('DOMContentLoaded', () => {
    document.addEventListener('change', (e) => {
        if (e.target.closest('#tab-igen')) {
            window.updateIgenLiveSummary();
        }
    });
    document.addEventListener('input', (e) => {
        if (e.target.closest('#tab-igen') && (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT')) {
            // Debounce summary update for sliders/text
            clearTimeout(window._summDebounce);
            window._summDebounce = setTimeout(window.updateIgenLiveSummary, 200);
        }
    });
});
