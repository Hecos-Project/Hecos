/**
 * igen_profiles.js — Image Gen Panel: Global Config Profiles
 * Save, load, delete, and set-default profiles that persist all parameters
 * across restarts including model, provider, preset, VAE, LoRAs, etc.
 */

// ── Load profile list ────────────────────────────────────────────────────────

window.loadIgenProfiles = async function() {
    try {
        const r = await fetch('/hecos/api/plugins/image_gen/profiles');
        const d = await r.json();
        if (!d.ok) return;

        const sel = document.getElementById('igen-profile-select');
        if (!sel) return;

        const current = sel.value;
        sel.innerHTML = '<option value="">— No profile selected —</option>';

        (d.profiles || []).forEach(function(p) {
            const opt = document.createElement('option');
            opt.value = p.name;
            opt.textContent = (p.is_default ? '⭐ ' : '') + p.name;
            opt.dataset.isDefault = String(p.is_default);
            sel.appendChild(opt);
        });

        if (current) sel.value = current;
        _updateProfileButtons();
        _updateDefaultBadge();
    } catch (err) {
        console.warn('[igen] loadIgenProfiles error:', err);
    }
};

// ── Load a profile's config ──────────────────────────────────────────────────

window.loadIgenProfile = async function() {
    const sel = document.getElementById('igen-profile-select');
    const name = sel ? sel.value : '';
    if (!name) {
        _updateProfileButtons();
        return;
    }

    try {
        const r = await fetch('/hecos/api/plugins/image_gen/profiles/load/' + encodeURIComponent(name));
        const d = await r.json();
        if (!d.ok) {
            _igenAlert('Error loading profile: ' + d.error);
            return;
        }

        // Apply profile config to the UI
        // First trigger provider change if provider differs
        const provSel = document.getElementById('igen-provider');
        const modelSel = document.getElementById('igen-model');

        if (d.config.provider && provSel) {
            provSel.setAttribute('data-initial-val', d.config.provider);
            provSel.value = d.config.provider;
        }
        if (d.config.model && modelSel) {
            modelSel.setAttribute('data-initial-val', d.config.model);
        }

        // Reload provider to fetch correct model list
        _igenLoadingConfig = true;
        await window.onProviderChanged(false);
        window.applyIgenConfig(d.config);
        _igenLoadingConfig = false;

        // Also set the preset selector if the profile has one
        if (d.config.active_preset) {
            const presetSel = document.getElementById('igen-preset');
            if (presetSel) presetSel.value = d.config.active_preset;
        }

        _updateProfileButtons();
        _igenAlert('Profile "' + name + '" loaded.', 'success');

        // Auto-save to persist the loaded profile's values
        window.saveIgenConfig(true);
    } catch (err) {
        console.error('[igen] profile load error:', err);
    }
};

// ── Save current config as a new profile ─────────────────────────────────────

window.saveIgenProfile = function() {
    window._igenPrompt('Name for this profile:', async function(name) {
        const config = window.collectIgenConfig();
        // Also capture active_preset
        const presetEl = document.getElementById('igen-preset');
        if (presetEl) config.active_preset = presetEl.value;

        const r = await fetch('/hecos/api/plugins/image_gen/profiles/save', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: name, config: config, set_as_default: false })
        });
        const d = await r.json();
        if (d.ok) {
            await window.loadIgenProfiles();
            var sel = document.getElementById('igen-profile-select');
            if (sel) sel.value = name;
            _updateProfileButtons();
            window._igenAlert('Profile "' + name + '" saved.', 'success');
        } else {
            window._igenAlert('Save failed: ' + d.error);
        }
    });
};

// ── Update existing profile ──────────────────────────────────────────────────

window.updateIgenProfile = async function() {
    const sel = document.getElementById('igen-profile-select');
    const name = sel ? sel.value : '';
    if (!name) return;

    const config = window.collectIgenConfig();
    const presetEl = document.getElementById('igen-preset');
    if (presetEl) config.active_preset = presetEl.value;

    const r = await fetch('/hecos/api/plugins/image_gen/profiles/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: name, config: config, set_as_default: false })
    });
    const d = await r.json();
    if (d.ok) {
        var btn = document.getElementById('igen-profile-update-btn');
        if (btn) {
            btn.innerHTML = '<i class="fas fa-check"></i> Updated!';
            btn.style.borderColor = 'var(--ok, #2ecc71)';
            btn.style.color = 'var(--ok, #2ecc71)';
            setTimeout(function() {
                btn.innerHTML = '<i class="fas fa-sync"></i> Update';
                btn.style.borderColor = '';
                btn.style.color = '';
            }, 1500);
        }
    } else {
        _igenAlert('Update failed: ' + d.error);
    }
};

// ── Delete a profile ─────────────────────────────────────────────────────────

window.deleteIgenProfile = function() {
    const name = document.getElementById('igen-profile-select')?.value || '';
    if (!name) return;

    _igenConfirm('Delete profile "' + name + '"? This cannot be undone.', async function() {
        const r = await fetch('/hecos/api/plugins/image_gen/profiles/delete/' + encodeURIComponent(name), { method: 'DELETE' });
        const d = await r.json();
        if (d.ok) {
            await window.loadIgenProfiles();
            _igenAlert('Profile "' + name + '" deleted.', 'success');
        } else {
            _igenAlert('Delete failed: ' + d.error);
        }
    });
};

// ── Set / Clear default profile ──────────────────────────────────────────────

window.setIgenDefaultProfile = async function() {
    const sel = document.getElementById('igen-profile-select');
    const name = sel ? sel.value : '';
    if (!name) return;

    // Check if this profile is already the default — if so, clear it
    const selectedOpt = sel.options[sel.selectedIndex];
    const isAlreadyDefault = selectedOpt && selectedOpt.dataset.isDefault === 'true';

    const newDefault = isAlreadyDefault ? '' : name;

    const r = await fetch('/hecos/api/plugins/image_gen/profiles/set-default', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: newDefault })
    });
    const d = await r.json();
    if (d.ok) {
        await window.loadIgenProfiles();
        if (newDefault) {
            sel.value = name;
        }
        _updateProfileButtons();
        _updateDefaultBadge();
        _igenAlert(
            newDefault
                ? 'Profile "' + name + '" set as default. It will be loaded on every restart.'
                : 'Default profile cleared.',
            'success'
        );
    } else {
        _igenAlert('Failed: ' + d.error);
    }
};

// ── Helpers ──────────────────────────────────────────────────────────────────

function _updateProfileButtons() {
    var sel       = document.getElementById('igen-profile-select');
    var loadBtn   = document.getElementById('igen-profile-load-btn');
    var updateBtn = document.getElementById('igen-profile-update-btn');
    var deleteBtn = document.getElementById('igen-profile-delete-btn');
    var defaultBtn = document.getElementById('igen-profile-default-btn');
    if (!sel) return;

    var hasSelection = !!sel.value;
    if (loadBtn)   loadBtn.disabled   = !hasSelection;
    if (updateBtn) updateBtn.disabled = !hasSelection;
    if (deleteBtn) deleteBtn.disabled = !hasSelection;
    if (defaultBtn) defaultBtn.disabled = !hasSelection;

    // Update default button icon/text
    if (defaultBtn && hasSelection) {
        var selectedOpt = sel.options[sel.selectedIndex];
        var isDefault = selectedOpt && selectedOpt.dataset.isDefault === 'true';
        defaultBtn.innerHTML = isDefault
            ? '<i class="fas fa-star"></i> Unset Default'
            : '<i class="far fa-star"></i> Set as Default';
        defaultBtn.title = isDefault
            ? 'Remove this profile as the startup default'
            : 'Load this profile automatically on every restart';
    }
}

function _updateDefaultBadge() {
    var badge = document.getElementById('igen-profile-default-badge');
    var sel = document.getElementById('igen-profile-select');
    if (!badge || !sel) return;

    // Find the default profile name
    var defaultName = '';
    Array.from(sel.options).forEach(function(opt) {
        if (opt.dataset.isDefault === 'true') {
            defaultName = opt.value;
        }
    });

    if (defaultName) {
        badge.innerHTML = '<i class="fas fa-star" style="color:#fbbf24;"></i> Default: <strong>' + defaultName + '</strong>';
        badge.style.display = 'flex';
    } else {
        badge.style.display = 'none';
    }
}
