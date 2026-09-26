/**
 * igen_providers.js - Image Gen Panel: Provider & Model Logic
 * Handles provider dropdown (Local Backends first, then Cloud),
 * model fetching with retry, key status check, tab visibility,
 * SwarmUI test, cloud enable toggle, and aspect ratio.
 */

// ── Tab switching ────────────────────────────────────────────────────────────

window.switchIgenTab = function(targetId, btn) {
    document.querySelectorAll('.igen-tab-pane').forEach(function(p) {
        p.style.display = 'none';
        p.classList.remove('igen-tab-pane-active');
    });
    document.querySelectorAll('.igen-tab-btn').forEach(function(b) {
        b.classList.remove('igen-tab-active');
    });
    var pane = document.getElementById(targetId);
    if (pane) { pane.style.display = 'block'; pane.classList.add('igen-tab-pane-active'); }
    if (btn) btn.classList.add('igen-tab-active');
};

// ── Provider Changed ─────────────────────────────────────────────────────────

window.onProviderChanged = async function(userTriggered, _attempt) {
    if (userTriggered === undefined) userTriggered = false;
    if (_attempt === undefined) _attempt = 0;

    var provSel  = document.getElementById('igen-provider');
    var modelSel = document.getElementById('igen-model');
    if (!provSel || !modelSel) return;

    // ── Populate provider list (Local Backends first) ────────────────────────
    var localProviders = [
        { id: 'swarmui',        name: '\uD83D\uDDA5\uFE0F SwarmUI (Local Backend)' },
    ];
    var cloudProviders = [
        { id: 'pollinations',   name: 'Pollinations (Free, Fast)' },
        { id: 'gemini',         name: 'Google Gemini' },
        { id: 'gemini_native',  name: 'Google Gemini Native (Flash)' },
        { id: 'openai',         name: 'OpenAI DALL-E' },
        { id: 'stability',      name: 'Stability AI' },
        { id: 'airforce',       name: 'Airforce (Free)' },
        { id: 'huggingface',    name: 'Hugging Face Inference API' },
        { id: 'horde',          name: '\uD83C\uDF10 AI Horde (Free / No Censorship)' },
    ];

    if (provSel.options.length === 0) {
        var localGroup = document.createElement('optgroup');
        localGroup.label = '\uD83D\uDCBB Local Backends';
        var cloudGroup = document.createElement('optgroup');
        cloudGroup.label = '\u2601\uFE0F Cloud Providers';

        localProviders.forEach(function(p) {
            var opt = document.createElement('option');
            opt.value = p.id; opt.textContent = p.name;
            localGroup.appendChild(opt);
        });
        cloudProviders.forEach(function(p) {
            var opt = document.createElement('option');
            opt.value = p.id; opt.textContent = p.name;
            cloudGroup.appendChild(opt);
        });
        provSel.appendChild(localGroup);
        provSel.appendChild(cloudGroup);

        var initialProv = provSel.getAttribute('data-initial-val') || 'swarmui';
        provSel.value = initialProv;
    }

    var isLocal  = (provSel.value === 'swarmui');
    var isHF     = (provSel.value === 'huggingface');
    var isHorde  = (provSel.value === 'horde');

    // ── Show/hide local backend panel ────────────────────────────────────────
    var localWrapper = document.getElementById('igen-local-backend-wrapper');
    if (localWrapper) localWrapper.style.display = isLocal ? 'block' : 'none';

    // ── Show/hide VAE + LoRA tabs ────────────────────────────────────────────
    var vaeTabBtn   = document.getElementById('igen-tab-btn-vae');
    var lorasTabBtn = document.getElementById('igen-tab-btn-loras');
    if (vaeTabBtn)   vaeTabBtn.style.display   = isLocal ? 'inline-flex' : 'none';
    if (lorasTabBtn) lorasTabBtn.style.display = isLocal ? 'inline-flex' : 'none';

    // If switching away from local while VAE/LoRA tab is active, reset to Model
    if (!isLocal) {
        var activePane = document.querySelector('.igen-tab-pane.igen-tab-pane-active');
        if (activePane && (activePane.id === 'igen-tab-vae' || activePane.id === 'igen-tab-loras')) {
            var modelBtn = document.querySelector('[data-target="igen-tab-model"]');
            window.switchIgenTab('igen-tab-model', modelBtn);
        }
    }

    // ── Show/hide HuggingFace sub-provider ───────────────────────────────────
    var hfProviderWrap = document.getElementById('igen-hf-provider-wrapper');
    if (hfProviderWrap) hfProviderWrap.style.display = isHF ? 'block' : 'none';

    var hfWrap = document.getElementById('igen-hf-explorer-wrapper');
    if (hfWrap) hfWrap.style.display = isHF ? 'block' : 'none';

    // ── Show/hide Horde panel ────────────────────────────────────────────────
    var hordeWrap = document.getElementById('igen-horde-wrapper');
    if (hordeWrap) hordeWrap.style.display = isHorde ? 'block' : 'none';
    if (isHorde && userTriggered) {
        setTimeout(function() { window.checkHordeAccount(); }, 500);
    }

    // ── Show/hide cloud panel & API key ─────────────────────────────────────
    var cloudWrapper   = document.getElementById('igen-cloud-wrapper');
    var apiKeyWrapper  = document.getElementById('igen-api-key-wrapper');
    var cloudProbeWrap = document.getElementById('igen-cloud-probe-wrapper');
    var nologoWrap     = document.getElementById('igen-nologo-wrapper');
    if (cloudWrapper) cloudWrapper.style.display = isLocal ? 'none' : 'block';
    if (cloudProbeWrap) cloudProbeWrap.style.display = isLocal ? 'none' : 'block';
    if (nologoWrap) nologoWrap.style.display = isLocal ? 'none' : 'flex';
    // For Horde: API key section is inside the horde block, so hide generic one
    if (apiKeyWrapper) apiKeyWrapper.style.display = isHorde ? 'none' : 'block';

    // ── Fetch models ─────────────────────────────────────────────────────────
    var statusEl = document.getElementById('igen-model-status');
    if (statusEl && _attempt === 0) statusEl.textContent = '\u23F3 loading...';

    try {
        var res = await fetch('/hecos/api/plugins/image_gen/models?provider=' + encodeURIComponent(provSel.value));
        if (!res.ok) throw new Error('HTTP ' + res.status);

        var data = await res.json();
        if (!data.ok) throw new Error(data.error || 'API returned ok=false');

        var currentSelection = userTriggered ? '' : (modelSel.getAttribute('data-initial-val') || modelSel.value);
        if (!userTriggered && modelSel.hasAttribute('data-initial-val')) {
            modelSel.removeAttribute('data-initial-val'); // Use only once
        }
        modelSel.innerHTML = '';
        if (data.models && data.models.length) {
            data.models.forEach(function(m) {
                var opt = document.createElement('option');
                opt.value = opt.textContent = m;
                modelSel.appendChild(opt);
            });
            if (currentSelection && data.models.includes(currentSelection)) {
                modelSel.value = currentSelection;
            }
        }

        // ── Fetch VAEs and LoRAs for SwarmUI ─────────────────────────────────
        if (isLocal && _attempt === 0) {
            try {
                var vSel = document.getElementById('igen-vae');
                var lSel = document.getElementById('igen-loras');
                var vCur = userTriggered ? '' : vSel.value;
                var lCur = userTriggered ? [] : Array.from(lSel.selectedOptions).map(function(o) { return o.value; });

                var vRes = await fetch('/hecos/api/plugins/image_gen/vaes');
                var vData = await vRes.json();

                var lRes = await fetch('/hecos/api/plugins/image_gen/local_compat_info');
                var lData = await lRes.json();

                window._swarmui_compat = lData;

                vSel.innerHTML = '<option value="">Default (Automatic)</option>';
                if (vData.ok && vData.models) {
                    vData.models.forEach(function(m) {
                        var o = document.createElement('option'); o.value = o.textContent = m;
                        vSel.appendChild(o);
                    });
                    if (vCur) vSel.value = vCur;
                }

                lSel.innerHTML = '';
                if (lData.ok && lData.loras) {
                    // Store full lora data globally for rendering
                    window._swarmui_loras_data = lData.loras;
                    // Pre-populate hidden select for save/load compatibility
                    lData.loras.forEach(function(m) {
                        var o = document.createElement('option');
                        o.value = m.name; o.textContent = m.name;
                        if (lCur.includes(m.name)) o.selected = true;
                        lSel.appendChild(o);
                    });
                }

                window.renderLoRAList();
                window.updateLoRACompatibility();

            } catch(ex) { console.warn('[ImageGen] Failed fetching VAEs/LoRAs:', ex); }
        }

        if (statusEl) statusEl.textContent = '';
        if (userTriggered) _igenDebounceSave();
        window._igenUpdateKeyStatus(provSel.value);

    } catch (e) {
        var MAX_RETRIES = 5, RETRY_DELAY_MS = 800;
        if (_attempt < MAX_RETRIES) {
            if (statusEl) statusEl.textContent = '\u23F3 Retrying (' + (_attempt+1) + '/' + MAX_RETRIES + ')...';
            console.warn('[ImageGen] Models fetch failed (attempt ' + (_attempt+1) + '): ' + e.message + '. Retrying...');
            setTimeout(function() { window.onProviderChanged(userTriggered, _attempt + 1); }, RETRY_DELAY_MS);
            return;
        }
        if (statusEl) statusEl.textContent = '\u26A0\uFE0F Could not load - click Refresh';
        console.error('[ImageGen] Fetch models error after all retries:', e);
        if (userTriggered) _igenDebounceSave();
        window._igenUpdateKeyStatus(provSel.value);
    }
};

// ── Key Status ───────────────────────────────────────────────────────────────

window._igenUpdateKeyStatus = async function(provider) {
    var stEl = document.getElementById('igen-key-source-text');
    if (!stEl) return;

    if (provider === 'pollinations' || provider === 'airforce' || provider === 'swarmui') {
        stEl.textContent = provider === 'swarmui' ? 'Local backend (no key needed)' : 'Free provider (no key needed)';
        stEl.parentElement.style.color = 'var(--ok, #2ecc71)';
        return;
    }
    if (provider === 'horde') {
        var hasKey = (document.getElementById('horde-api-key') && document.getElementById('horde-api-key').value.trim().length > 0);
        stEl.textContent = hasKey ? 'Horde key configured' : 'Anonymous (no key)';
        stEl.parentElement.style.color = hasKey ? 'var(--ok, #2ecc71)' : 'var(--muted)';
        return;
    }

    stEl.textContent = 'Checking...';
    stEl.parentElement.style.color = 'var(--muted)';
    try {
        var r = await fetch('/hecos/api/plugins/image_gen/key_status?provider=' + encodeURIComponent(provider));
        var d = await r.json();
        if (d.ok) {
            stEl.textContent = d.source;
            stEl.parentElement.style.color = (d.source.includes('invalid') || d.source.includes('Not found'))
                ? 'var(--error, #e74c3c)' : 'var(--ok, #2ecc71)';
        } else {
            stEl.textContent = 'Unknown';
        }
    } catch(e) {
        stEl.textContent = 'Unknown';
    }
};


// ── Test SwarmUI backend ─────────────────────────────────────────────────────

window.testSwarmUIBackend = async function() {
    var btn      = document.getElementById('igen-local-test-btn');
    var box      = document.getElementById('igen-local-test-results');
    var badge    = document.getElementById('igen-local-status-badge');
    var badgeTxt = document.getElementById('igen-local-status-text');
    if (!btn || !box) return;

    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Testing...';
    box.style.display = 'block';
    box.innerHTML = '<div style="color:var(--muted); text-align:center; padding:8px;">\u23f3 Connecting to SwarmUI on localhost:7801...</div>';

    if (badge) {
        badge.style.background   = 'rgba(255,200,0,0.1)';
        badge.style.borderColor  = 'rgba(255,200,0,0.3)';
        badge.style.color        = '#fbbf24';
        badge.querySelector('i').style.color = '#fbbf24';
    }
    if (badgeTxt) badgeTxt.textContent = 'Testing...';

    try {
        var res = await fetch('/hecos/api/plugins/image_gen/local_status');
        var data = await res.json();

        var ok    = data.ok === true;
        var icon  = ok ? '\u2705' : '\u274c';
        var color = ok ? '#2ecc71' : '#e74c3c';

        var statusLine = data.status_text || (ok ? 'SwarmUI reachable' : 'SwarmUI unreachable');
        var html  = '<div style="color:' + color + '; font-weight:700; margin-bottom:6px;">' + icon + ' ' + statusLine + '</div>';

        if (data.version)  html += '<div style="color:var(--muted);">\uD83D\uDD16 Version: ' + data.version + '</div>';
        if (data.url)      html += '<div style="color:var(--muted);">\uD83D\uDD17 URL: <code>' + data.url + '</code></div>';
        if (data.models_count !== undefined) html += '<div style="color:var(--muted);">\uD83E\uDDE0 Models loaded: ' + data.models_count + '</div>';
        if (data.error)    html += '<div style="color:#e74c3c; margin-top:6px; font-size:11px;">' + data.error + '</div>';
        if (data.message && !data.error)  html += '<div style="color:var(--muted); margin-top:6px; font-size:11px;">' + data.message + '</div>';

        box.innerHTML = html;

        if (badge) {
            badge.style.background  = ok ? 'rgba(16,185,129,0.1)'  : 'rgba(231,76,60,0.1)';
            badge.style.borderColor = ok ? 'rgba(16,185,129,0.3)'  : 'rgba(231,76,60,0.3)';
            badge.style.color       = ok ? '#34d399'                : '#e74c3c';
            badge.querySelector('i').style.color = ok ? '#34d399' : '#e74c3c';
        }
        if (badgeTxt) badgeTxt.textContent = ok ? 'Online' : 'Offline';

    } catch (e) {
        box.innerHTML = '<div style="color:#e74c3c;">\u274c Network error: ' + e.message + '</div>';
        if (badge) {
            badge.style.background  = 'rgba(231,76,60,0.1)';
            badge.style.borderColor = 'rgba(231,76,60,0.3)';
            badge.style.color       = '#e74c3c';
        }
        if (badgeTxt) badgeTxt.textContent = 'Error';
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-stethoscope"></i> Test SwarmUI Connection';
    }
};

// ── Cloud enabled toggle ─────────────────────────────────────────────────────

window.onCloudEnabledChanged = function() {
    var chk     = document.getElementById('igen-cloud-enabled');
    var wrapper = document.getElementById('igen-cloud-wrapper');
    if (!chk || !wrapper) return;
    if (chk.checked) {
        wrapper.classList.remove('cloud-disabled');
    } else {
        wrapper.classList.add('cloud-disabled');
    }
    _igenDebounceSave();
};

// ── Cloud Providers Toggle ───────────────────────────────────────────────────

window._onCloudToggle = function(enabled) {
    var provSel = document.getElementById('igen-provider');
    if (!provSel) return;

    // Disable/enable all cloud options in the dropdown
    var _cloudIds = ['pollinations','gemini','gemini_native','openai','stability','airforce','huggingface','horde'];
    Array.from(provSel.options).forEach(function(opt) {
        if (_cloudIds.indexOf(opt.value) !== -1) {
            opt.disabled = !enabled;
            if (!enabled && opt.selected) {
                // Force switch to swarmui
                provSel.value = 'swarmui';
            }
        }
    });

    // Also disable optgroups visually
    Array.from(provSel.querySelectorAll('optgroup')).forEach(function(g) {
        if (g.label && g.label.indexOf('Cloud') !== -1) {
            g.disabled = !enabled;
        }
    });

    // Only trigger provider change if NOT during a bulk reload (prevents race condition)
    if (!_igenLoadingConfig) {
        window.onProviderChanged(true, 0);
    }
};

// Apply cloud toggle state after config loads
window._applyCloudToggleState = function() {
    var chk = document.getElementById('igen-cloud-enabled');
    if (chk) window._onCloudToggle(chk.checked);
};

// ── Other helpers ────────────────────────────────────────────────────────────

window.refreshImageModels = function() { window.onProviderChanged(false, 0); };

window.onAspectRatioChanged = function() {
    var val  = document.getElementById('igen-aspect-ratio');
    var dims = document.getElementById('igen-custom-dims');
    if (val && dims) dims.style.display = (val.value === 'custom') ? 'block' : 'none';
};

window.reloadIgenPanel = async function() {
    var btn = document.getElementById('igen-refresh-btn');
    if (btn) { btn.innerHTML = '<i class="fas fa-spinner fa-spin" style="font-size:13px;"></i> Loading...'; btn.disabled = true; }
    try {
        _igenLoadingConfig = true;

        // 1. Fetch config from server
        var res  = await fetch('/hecos/api/plugins/image_gen/config');
        var data = await res.json();
        var cfg  = data.image_gen || {};

        // 2. Load presets and profiles (dropdowns)
        await window.loadIgenPresets(cfg.active_preset);
        if (typeof window.loadIgenProfiles === 'function') {
            await window.loadIgenProfiles();
        }

        // 3. Set initial values BEFORE rebuilding provider dropdown
        var provSel = document.getElementById('igen-provider');
        var modelSel = document.getElementById('igen-model');
        if (provSel && cfg.provider) provSel.setAttribute('data-initial-val', cfg.provider);
        if (modelSel && cfg.model)   modelSel.setAttribute('data-initial-val', cfg.model);

        // 4. Clear and rebuild provider dropdown + fetch models/VAEs/LoRAs
        if (provSel) provSel.innerHTML = '';
        await window.onProviderChanged(false, 0);

        // 5. Apply all config values (sliders, checkboxes, etc.)
        //    _igenLoadingConfig is still true so _onCloudToggle won't fire onProviderChanged again
        window.applyIgenConfig(cfg);

        _igenLoadingConfig = false;
    } catch(e) {
        _igenLoadingConfig = false;
        console.error('[ImageGen] reloadIgenPanel error:', e);
    } finally {
        if (btn) { btn.innerHTML = '<i class="fas fa-sync-alt" style="font-size:13px;"></i> Refresh'; btn.disabled = false; }
    }
};
