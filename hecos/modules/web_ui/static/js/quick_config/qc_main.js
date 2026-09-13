/**
 * Quick Config HUD - Main Logic
 * Populates options, handles selections and saves.
 */

window._qcState = {
    sysOptions: null,
    currentConfig: null
};

window._qcInitAndShow = async function() {
    const overlay = document.getElementById('qc-hud-overlay');
    if (overlay) overlay.classList.remove('qc-hud-hidden');
    
    // Reset sync status
    const statusEl = document.getElementById('qc-sync-status');
    if (statusEl) statusEl.classList.remove('visible');

    // Fetch options and current config in parallel
    try {
        const [optRes, cfgRes] = await Promise.all([
            fetch('/hecos/options'),
            fetch('/hecos/config')
        ]);
        
        if (optRes.ok) window._qcState.sysOptions = await optRes.json();
        if (cfgRes.ok) window._qcState.currentConfig = await cfgRes.json();
        
        _qcPopulateUI();
    } catch(e) {
        console.error("Failed to fetch data for QC HUD:", e);
    }
};

function _qcPopulateUI() {
    const sysOpts = window._qcState.sysOptions || {};
    const cfg = window._qcState.currentConfig || {};
    
    // Backend Type
    const bTypeEl = document.getElementById('qc-backend-type');
    const activeType = cfg.backend?.type || 'ollama';
    if (bTypeEl) bTypeEl.value = activeType;
    
    _qcUpdateModelSelect(activeType, cfg);
    
    // Persona
    const personaEl = document.getElementById('qc-persona');
    if (personaEl) {
        personaEl.innerHTML = '';
        (sysOpts.personalities || []).forEach(p => {
            const opt = document.createElement('option');
            opt.value = p;
            opt.textContent = p;
            personaEl.appendChild(opt);
        });
        personaEl.value = cfg.ai?.active_personality || '';
    }
}

function _qcUpdateModelSelect(backendType, cfg) {
    const sysOpts = window._qcState.sysOptions || {};
    const modelEl = document.getElementById('qc-model');
    if (!modelEl) return;
    
    modelEl.innerHTML = '';
    let options = [];
    let activeModel = '';
    
    if (backendType === 'ollama') {
        options = sysOpts.ollama_models || [];
        activeModel = cfg?.backend?.ollama?.model || '';
    } else if (backendType === 'cloud') {
        options = sysOpts.all_cloud || [];
        activeModel = cfg?.backend?.cloud?.model || '';
    } else if (backendType === 'kobold') {
        // Kobold doesn't usually list options this way, but we'll try or allow text input
        // For simplicity, we just add the active one
        options = [cfg?.backend?.kobold?.model || 'Kobold Model'];
        activeModel = cfg?.backend?.kobold?.model || '';
    }
    
    options.forEach(m => {
        const opt = document.createElement('option');
        opt.value = m;
        opt.textContent = m;
        modelEl.appendChild(opt);
    });
    
    if (activeModel) {
        modelEl.value = activeModel;
    }
}

window.qcBackendChanged = function() {
    const type = document.getElementById('qc-backend-type').value;
    _qcUpdateModelSelect(type, window._qcState.currentConfig);
    window.qcSaveConfig();
};

window.qcSaveConfig = function() {
    const payload = {
        backend: {
            type: document.getElementById('qc-backend-type').value
        },
        ai: {
            active_personality: document.getElementById('qc-persona').value
        }
    };
    
    const bType = payload.backend.type;
    const modelValue = document.getElementById('qc-model').value;
    
    if (bType === 'ollama') {
        payload.backend.ollama = { model: modelValue };
    } else if (bType === 'cloud') {
        payload.backend.cloud = { model: modelValue };
    } else if (bType === 'kobold') {
        payload.backend.kobold = { model: modelValue };
    }
    
    if (window.qcSaveConfigAPI) {
        window.qcSaveConfigAPI(payload);
    }
};
