/**
 * Quick Config HUD - Main Logic
 * Populates options, handles selections and saves.
 */

window._qcState = {
    sysOptions: null,
    currentConfig: null,
    audioConfig: null,
    richModels: null
};

window._qcInitAndShow = async function() {
    const overlay = document.getElementById('qc-hud-overlay');
    if (overlay) overlay.classList.remove('qc-hud-hidden');
    
    // Reset sync status
    const statusEl = document.getElementById('qc-sync-status');
    if (statusEl) statusEl.classList.remove('visible');

    // Fetch options, current config, audio config, and rich models in parallel
    try {
        const [optRes, cfgRes, audRes, richRes] = await Promise.all([
            fetch('/hecos/options'),
            fetch('/hecos/config'),
            fetch('/api/audio/config'),
            fetch('/api/chat/options')
        ]);
        
        if (optRes.ok) window._qcState.sysOptions = await optRes.json();
        if (cfgRes.ok) window._qcState.currentConfig = await cfgRes.json();
        if (audRes.ok) {
            const audJson = await audRes.json();
            window._qcState.audioConfig = audJson.config || {};
        }
        if (richRes.ok) {
            const richJson = await richRes.json();
            window._qcState.richModels = richJson.models || [];
        }
        
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
    let activeType = cfg.backend?.type || 'ollama';
    
    if (activeType === 'hybrid') {
        activeType = cfg.backend?.active_model_source || 'cloud';
    }
    
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

    // TTS Engine
    const audCfg = window._qcState.audioConfig || {};
    const ttsEngineEl = document.getElementById('qc-tts-engine');
    if (ttsEngineEl) {
        ttsEngineEl.value = audCfg.active_engine || 'piper';
        
        let activeVoice = null;
        if (audCfg.active_engine === 'piper') {
            activeVoice = audCfg.onnx_model ? audCfg.onnx_model.replace('.onnx', '').split(/[\\/]/).pop() : null;
        } else if (audCfg.active_engine === 'kokoro') {
            activeVoice = audCfg.kokoro?.voice;
        } else if (audCfg.active_engine === 'xtts2') {
            activeVoice = audCfg.xtts?.speaker;
        }
        
        window.qcTTSChanged(activeVoice); // populate voices
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
        options = [cfg?.backend?.kobold?.model || 'Kobold Model'];
        activeModel = cfg?.backend?.kobold?.model || '';
    } else if (backendType === 'llama_cpp') {
        options = sysOpts.llamacpp_models || [];
        activeModel = cfg?.backend?.llama_cpp?.model || '';
    }
    
    let items = options;
    if (options && typeof options === 'object' && !Array.isArray(options)) {
        items = Object.values(options);
    }
    
    const richModels = window._qcState.richModels || [];
    
    items.forEach(m => {
        const opt = document.createElement('option');
        opt.value = m;
        
        let textContent = m;
        let tooltipText = m;
        
        // Find matching rich model — local models match by provider, cloud by type
        const richModel = richModels.find(rm => {
            if (backendType === 'cloud') return rm.type === 'cloud' && rm.id === m;
            return rm.provider === backendType && rm.id === m;
        });
        
        if (richModel) {
            let prefix = richModel.type === 'cloud' ? '☁️ ' : '🖥️ ';
            let suffix = '';
            let sizeTag = '';
            
            if (richModel.parameter_size || richModel.size_bytes) {
                sizeTag = ' [';
                let parts = [];
                if (richModel.parameter_size) {
                    let p = richModel.parameter_size;
                    if (richModel.quantization_level) p += ' ' + richModel.quantization_level;
                    parts.push(p);
                }
                if (richModel.size_bytes) {
                    let gb = (richModel.size_bytes / (1024*1024*1024)).toFixed(1);
                    parts.push(gb + 'GB');
                }
                sizeTag += parts.join(' | ') + ']';
            }
            
            tooltipText = richModel.name + sizeTag;
            
            if (richModel.capabilities && richModel.capabilities.length > 0) {
                const iconMap = { 'tools': '⚙️', 'vision': '👁️', 'thinking': '💭' };
                const descMap = { 'tools': 'Tools/Function Calling', 'vision': 'Vision/Multimodal', 'thinking': 'Thinking/Reasoning' };
                
                const icons = richModel.capabilities.map(c => iconMap[c]).filter(Boolean).join('');
                if (icons) suffix = ' ' + icons;
                
                const descs = richModel.capabilities.map(c => descMap[c]).filter(Boolean).join(', ');
                if (descs) tooltipText += '\nCapabilities: ' + descs;
            }
            
            textContent = prefix + richModel.name + sizeTag + suffix;
        }
        
        opt.textContent = textContent;
        opt.title = tooltipText;
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

window.qcTTSChanged = async function(selectedVoice = null) {
    const engine = document.getElementById('qc-tts-engine').value;
    const voiceEl = document.getElementById('qc-tts-voice');
    if (!voiceEl) return;
    
    voiceEl.innerHTML = '';
    
    try {
        const res = await fetch(`/api/audio/voices?engine=${engine}`);
        if (res.ok) {
            const voices = await res.json();
            const voiceList = Array.isArray(voices) ? voices : (voices[engine] || Object.keys(voices));
            
            // if it's an object of objects (like Piper json), we need keys
            const iter = Array.isArray(voiceList) ? voiceList : Object.keys(voiceList);
            
            iter.forEach(v => {
                const opt = document.createElement('option');
                opt.value = v;
                
                let text = v;
                if (!Array.isArray(voices)) {
                    if (voices[engine] && typeof voices[engine] === 'object' && !Array.isArray(voices[engine])) {
                        text = voices[engine][v];
                    } else if (voices[v] && typeof voices[v] === 'string') {
                        text = voices[v];
                    }
                }
                
                opt.textContent = text;
                voiceEl.appendChild(opt);
            });
            if (selectedVoice) {
                voiceEl.value = selectedVoice;
            }
        }
    } catch(e) {
        console.error("Failed to fetch TTS voices", e);
    }
    window.qcSaveConfig();
};

window.qcSaveConfig = function() {
    const bType = document.getElementById('qc-backend-type').value;
    const modelRaw = document.getElementById('qc-model').value;
    const ttsEngine = document.getElementById('qc-tts-engine')?.value;
    const ttsVoice = document.getElementById('qc-tts-voice')?.value;
    
    const wasHybrid = window._qcState.currentConfig?.backend?.type === 'hybrid';
    
    // 1. Update System Config
    const payload = {
        backend: { type: wasHybrid ? 'hybrid' : bType },
        ai: { 
            active_personality: document.getElementById('qc-persona').value,
            tts_engine: ttsEngine,
            tts_voice: ttsVoice
        }
    };
    
    if (wasHybrid) {
        payload.backend.active_model_source = bType;
        if (bType === 'cloud') payload.backend.cloud = { model: modelRaw };
        else if (bType === 'ollama') payload.backend.ollama = { model: modelRaw };
        else if (bType === 'kobold') payload.backend.kobold = { model: modelRaw };
        else if (bType === 'llama_cpp') payload.backend.llama_cpp = { model: modelRaw };
    } else {
        if (bType === 'ollama') payload.backend.ollama = { model: modelRaw };
        else if (bType === 'cloud') payload.backend.cloud = { model: modelRaw };
        else if (bType === 'kobold') payload.backend.kobold = { model: modelRaw };
        else if (bType === 'llama_cpp') payload.backend.llama_cpp = { model: modelRaw };
    }
    
    if (window.qcSaveConfigAPI) {
        window.qcSaveConfigAPI(payload);
    }
    
    // 2. Update Audio Config globally
    if (ttsEngine && ttsVoice && window._qcState.audioConfig) {
        const audPayload = { active_engine: ttsEngine };
        const baseAud = window._qcState.audioConfig;
        
        if (ttsEngine === 'piper') {
            // retain path prefix if any in base config, else just filename
            const prefix = baseAud.piper_path ? baseAud.piper_path.replace('piper.exe', '') : '';
            audPayload.onnx_model = prefix + ttsVoice + '.onnx';
        } else if (ttsEngine === 'kokoro') {
            audPayload.kokoro = Object.assign({}, baseAud.kokoro || {}, { voice: ttsVoice });
        } else if (ttsEngine === 'xtts2') {
            audPayload.xtts = Object.assign({}, baseAud.xtts || {}, { speaker: ttsVoice });
        }
        
        fetch('/api/audio/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(audPayload)
        }).then(async r => {
            if(r.ok) {
                const updated = await r.json();
                if(updated.config) window._qcState.audioConfig = updated.config;
            }
        }).catch(e => console.error("Failed to sync audio config:", e));
    }
};
