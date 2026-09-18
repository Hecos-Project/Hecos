/**
 * igen_core.js - Image Gen Panel: Core Bootstrap & Utilities
 * Auto-save debouncer, custom UI helpers, global save hook, panel bootstrap.
 */

// -- Auto-save debouncer --
let _igenSaveTimer = null;
let _igenLoadingConfig = false;  // Guard: skip auto-save during initial config apply

function _igenDebounceSave() {
    if (_igenLoadingConfig) return;  // Don't save while loading config
    clearTimeout(_igenSaveTimer);
    _igenSaveTimer = setTimeout(function() { window.saveIgenConfig(true); }, 500);
}

// -- Custom UI Wrappers --

function _igenAlert(msg, type) {
    type = type || 'error';
    if (window.showToast) window.showToast(msg, type);
    else console.error('[ImageGen]', msg);
}

function _igenConfirm(msg, onYes) {
    if (window.hpmShowConfirm) window.hpmShowConfirm(msg, 'Confirm', onYes);
    else if (confirm(msg)) onYes();
}

function _igenPrompt(msg, onSave) {
    var modalId = 'igen-custom-prompt-modal';
    var modal = document.getElementById(modalId);
    if (!modal) {
        modal = document.createElement('div');
        modal.id = modalId;
        modal.className = 'modal-bg';
        modal.style.cssText = 'position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.6); display:flex; align-items:center; justify-content:center; z-index:9999;';
        modal.innerHTML = '<div style="background:var(--bg2); border:1px solid var(--border); padding:24px; border-radius:12px; max-width:400px; width:90%; box-shadow:0 10px 30px rgba(0,0,0,0.5);">' +
            '<h3 style="margin-top:0; color:var(--text);"><i class="fas fa-keyboard" style="margin-right:8px; color:var(--accent);"></i> Input Required</h3>' +
            '<p id="' + modalId + '-text" style="margin:20px 0; color:var(--text); font-size:1.05em;"></p>' +
            '<input type="text" id="' + modalId + '-input" class="config-input" style="width:100%; margin-bottom:20px; border:1px solid var(--border); background:var(--bg3); color:var(--text); padding:8px 12px; border-radius:6px;">' +
            '<div style="display:flex; justify-content:flex-end; gap:10px;">' +
            '<button class="btn" id="' + modalId + '-cancel" style="border:1px solid var(--border); background:var(--bg3); color:var(--text); padding:8px 16px; border-radius:6px; cursor:pointer;">Cancel</button>' +
            '<button class="btn" style="background:var(--accent); color:white; border:none; padding:8px 16px; border-radius:6px; cursor:pointer;" id="' + modalId + '-save">Save</button>' +
            '</div></div>';
        document.body.appendChild(modal);
    }
    document.getElementById(modalId + '-text').textContent = msg;
    var input = document.getElementById(modalId + '-input');
    input.value = '';

    var cleanup = function() { modal.style.display = 'none'; };

    document.getElementById(modalId + '-cancel').onclick = cleanup;
    document.getElementById(modalId + '-save').onclick = function() {
        cleanup();
        var val = input.value.trim();
        if (val) onSave(val);
    };

    modal.style.display = 'flex';
    setTimeout(function() { input.focus(); }, 100);
}

// -- Auto-save wiring --

function _igenAttachAutoSave() {
    var fields = [
        'igen-provider', 'igen-model', 'igen-enabled', 'igen-cloud-enabled',
        'igen-hf-provider', 'igen-routing-override', 'horde-nsfw', 'horde-worker-blacklist',
        'igen-aspect-ratio', 'igen-width', 'igen-height', 'igen-seed',
        'igen-sampler', 'igen-scheduler', 'igen-guidance', 'igen-steps',
        'igen-use-neg-prompt', 'igen-neg-prompt',
        'igen-auto-enrich', 'igen-enrich-keywords',
        'igen-style', 'igen-nologo', 'igen-show-metadata', 'igen-optimize-flux',
        'igen-vae', 'igen-loras'
    ];
    fields.forEach(function(id) {
        var el = document.getElementById(id);
        if (!el) return;
        var evt = (el.type === 'checkbox' || el.tagName === 'SELECT') ? 'change' : 'input';
        el.addEventListener(evt, _igenDebounceSave);
    });
}

// -- Hook into Hecos global saveConfig --
function _igenHookGlobalSave() {
    if (typeof window.saveConfig !== 'function') return;
    var _orig = window.saveConfig;
    window.saveConfig = async function(silent) {
        await _orig.call(this, silent);
        await window.saveIgenConfig(true);
    };
}

// -- Bootstrap --

var _igenInitDone = false;

var _IGEN_REQUIRED_FNS = [
    'loadIgenPresets', 'applyIgenConfig', 'onProviderChanged',
    'saveIgenConfig', 'collectIgenConfig', 'checkIgenPresetUI'
];

function _igenAllModulesReady() {
    return _IGEN_REQUIRED_FNS.every(function(fn) { return typeof window[fn] === 'function'; });
}

function _waitForIgenReady(callback) {
    var MAX_WAIT = 15000;
    var POLL_MS  = 100;
    var elapsed  = 0;

    var check = function() {
        var domReady = !!document.getElementById('igen-provider');
        var fnsReady = _igenAllModulesReady();

        if (domReady && fnsReady) {
            callback();
            return;
        }
        elapsed += POLL_MS;
        if (elapsed >= MAX_WAIT) {
            var missing = _IGEN_REQUIRED_FNS.filter(function(fn) { return typeof window[fn] !== 'function'; });
            console.error('[ImageGen] Timeout waiting for modules. Missing:', missing, 'DOM:', domReady);
            return;
        }
        setTimeout(check, POLL_MS);
    };
    check();
}

var initImageGenPanel = async function() {
    if (_igenInitDone) return;
    _igenInitDone = true;

    console.log('[ImageGen] All modules loaded - initializing...');
    try {
        var res  = await fetch('/hecos/api/plugins/image_gen/config');
        var data = await res.json();
        var cfg  = data.image_gen || {};

        await window.loadIgenPresets(cfg.active_preset);
        
        var provSel = document.getElementById('igen-provider');
        if (provSel && cfg.provider) provSel.setAttribute('data-initial-val', cfg.provider);
        var modelSel = document.getElementById('igen-model');
        if (modelSel && cfg.model) modelSel.setAttribute('data-initial-val', cfg.model);
        
        _igenLoadingConfig = true;  // Guard: prevent auto-save during initial load
        await window.onProviderChanged(false);
        window.applyIgenConfig(cfg);
        _igenLoadingConfig = false;
        
        _igenAttachAutoSave();
        _igenHookGlobalSave();

        console.log('[ImageGen] Panel ready.');
    } catch (e) {
        console.error('[ImageGen] Bootstrap error:', e);
    }
};

_waitForIgenReady(initImageGenPanel);

document.addEventListener('visibilitychange', function() {
    if (document.visibilityState === 'visible' && _igenInitDone) {
        var provSel  = document.getElementById('igen-provider');
        var modelSel = document.getElementById('igen-model');
        if (provSel && modelSel && modelSel.options.length === 0) {
            console.log('[ImageGen] Tab visible with empty models - auto-refreshing...');
            window.onProviderChanged(false, 0);
        }
    }
});

window._igenDebounceSave = _igenDebounceSave;
window._igenAlert        = _igenAlert;
window._igenConfirm      = _igenConfirm;
window._igenPrompt       = _igenPrompt;
