/**
 * igen_presets.js — Image Gen Panel: Preset Management
 * loadIgenPresets, loadIgenPreset, saveIgenPreset, updateIgenPreset,
 * deleteIgenPreset, checkIgenPresetUI — with Local / Cloud / User grouping.
 */

window.loadIgenPresets = async function(restoreValue) {
    try {
        const r = await fetch('/hecos/api/plugins/image_gen/presets');
        const d = await r.json();
        if (!d.ok) return;

        const sel = document.getElementById('igen-preset');
        if (!sel) return;

        const targetValue = restoreValue !== undefined ? restoreValue : sel.value;
        sel.innerHTML = '<option value="">\u2014 Select a preset \u2014</option>';

        const localGroup = document.createElement('optgroup');
        localGroup.label = "\uD83D\uDCBB Local Presets";
        const cloudGroup = document.createElement('optgroup');
        cloudGroup.label = "\u2601\uFE0F Cloud Presets (Built-in)";
        const userGroup = document.createElement('optgroup');
        userGroup.label = "\uD83D\uDC64 My Custom Presets";

        (d.presets || []).forEach(p => {
            const opt = document.createElement('option');
            opt.value = p.name;
            opt.textContent = p.name;
            opt.dataset.builtin = String(p.builtin);

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
        window.applyIgenConfig(d.config);
        if (sel) sel.value = name;
        checkIgenPresetUI();
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
            body: JSON.stringify({ name, config })
        });
        const d = await r.json();
        if (d.ok) { await window.loadIgenPresets(name); }
        else { _igenAlert('Save failed: ' + d.error); }
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
            btn.innerHTML = '\u2705 Saved!';
            setTimeout(() => { btn.innerHTML = '\uD83D\uDD04 Update'; }, 1500);
        }
    } else {
        _igenAlert('Update failed: ' + d.error);
    }
};

window.deleteIgenPreset = async function() {
    const name = document.getElementById('igen-preset')?.value || '';
    if (!name) return;

    const r = await fetch('/hecos/api/plugins/image_gen/presets/delete/' + encodeURIComponent(name), { method: 'DELETE' });
    const d = await r.json();
    if (d.ok) { await window.loadIgenPresets(''); }
    else { _igenAlert('Delete failed: ' + d.error); }
};

window.checkIgenPresetUI = function() {
    const sel       = document.getElementById('igen-preset');
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
