/* ⚡ SOUL FORGE: gp_ui.js */

window.sfTogglePanel = function(force, mode = 'global') {
    const panel = document.getElementById('soul-forge-panel');
    const overlay = document.getElementById('soul-forge-overlay');
    const isOpen = panel.classList.contains('open');
    
    const shouldOpen = force !== undefined ? force : !isOpen;
    
    if (shouldOpen) {
        try {
            const audio = new Audio('/assets/sounds/beep-6.mp3');
            audio.volume = 1.0; // Fixed at system volume
            audio.play().catch(e => console.log('Audio play prevented:', e));
        } catch(e) {}

        // Update Title and Description based on mode
        const titleEl = document.getElementById('sf-panel-title');
        const descEl = document.getElementById('sf-panel-desc');
        
        if (mode === 'chat') {
            if (titleEl) titleEl.textContent = 'Chat Overrides';
            if (descEl) descEl.innerHTML = 'These are the <b>Chat Overrides</b>. Changes here do not overwrite the Global Defaults unless you explicitly choose to overwrite them.';
        } else {
            if (titleEl) titleEl.textContent = 'Global Defaults';
            if (descEl) descEl.innerHTML = "These are the system's <b>Global Defaults</b>. Settings saved here are automatically applied as the foundation for every new chat and are independent of Chat Overrides.";
        }
        
        // We will dynamically fetch the system config and update the fallbacks to show the actual fallback values.
        window.sfUpdateFallbackLabels();
        
        panel.classList.add('open');
        overlay.style.display = 'block';
        window.sfLoadData();
    } else {
        panel.classList.remove('open');
        overlay.style.display = 'none';
        if (window.sfState.isDirty) {
            window.sfSaveInlineToSession();
        }
    }
};

window.sfUpdateFallbackLabels = async function() {
    try {
        const [cfgRes, audRes] = await Promise.all([
            fetch('/hecos/config'),
            fetch('/api/audio/config')
        ]);
        
        let bType = 'unknown';
        let bModel = 'unknown';
        let pName = 'unknown';
        
        if (cfgRes.ok) {
            const cfg = await cfgRes.json();
            pName = cfg.ai?.active_personality || 'unknown';
            
            bType = cfg.backend?.type || 'ollama';
            if (bType === 'hybrid') {
                bType = cfg.backend?.active_model_source || 'cloud';
            }
            if (cfg.backend) {
                if (bType === 'ollama') bModel = cfg.backend.ollama?.model || 'unknown';
                else if (bType === 'cloud') bModel = cfg.backend.cloud?.model || 'unknown';
                else if (bType === 'kobold') bModel = cfg.backend.kobold?.model || 'unknown';
                else if (bType === 'llama_cpp') bModel = cfg.backend.llama_cpp?.model || 'unknown';
            }
        }
        
        let tEngine = 'unknown';
        let tVoice = 'unknown';
        if (audRes.ok) {
            const audRaw = await audRes.json();
            const aud = audRaw.config || {};
            tEngine = aud.active_engine || 'piper';
            if (tEngine === 'piper') {
                tVoice = aud.onnx_model ? aud.onnx_model.replace('.onnx', '').split(/[\\/]/).pop() : 'unknown';
            } else if (tEngine === 'kokoro') {
                tVoice = aud.kokoro?.voice || 'unknown';
            } else if (tEngine === 'xtts2') {
                tVoice = aud.xtts?.speaker || 'unknown';
            }
        }
        
        window.sfSystemFallbacks = {
            persona: pName,
            backend: bType,
            model: bModel,
            tts_engine: tEngine,
            tts_voice: tVoice
        };
        
    } catch (e) {
        console.error("Failed to fetch system fallbacks for Global Defaults UI", e);
    }
};

window.sfDirty = function() {
    if (window.sfUpdateCloneState) window.sfUpdateCloneState();
    window.sfState.isDirty = true;
    
    const topBtn = document.getElementById('sf-top-save-btn');
    if (topBtn) {
        if (window.sfState.activeSoulId) {
            topBtn.innerHTML = '<i class="fas fa-save"></i> Update';
            topBtn.style.backgroundColor = 'var(--accent1, #00d2ff)';
            topBtn.style.color = '#000';
            topBtn.onclick = window.sfSaveInlineToActive;
        }
    }
    
    // Toggle XTTS settings visibility
    const ttsEngine = document.getElementById('sf-tts-engine-select').value;
    document.getElementById('sf-xtts-controls').style.display = (ttsEngine === 'xtts2') ? 'block' : 'none';
};


window.sfUpdateSliderVal = function(el, spanId) {
    document.getElementById(spanId).textContent = el.value;
};


window.sfPopulateDropdowns = function(optData) {
    const soulSel = document.getElementById('sf-active-soul-select');
    const quickSel = document.getElementById('sf-quick-preset-select');
    
    soulSel.innerHTML = '<option value="">-- No active global preset --</option>';
    if (quickSel) quickSel.innerHTML = '<option value="">⚡ Preset...</option>';
    
    window.sfState.souls.forEach(s => {
        const opt = document.createElement('option');
        opt.value = s.meta.id;
        opt.textContent = `${s.meta.icon} ${s.meta.name}`;
        soulSel.appendChild(opt);
        
        if (quickSel) {
            const qOpt = document.createElement('option');
            qOpt.value = s.meta.id;
            qOpt.textContent = `⚡ ${s.meta.name}`;
            quickSel.appendChild(qOpt);
        }
    });
    
    const infSel = document.getElementById('sf-inference-preset-select');
    infSel.innerHTML = '<option value="">-- No preset selected --</option>';
    Object.keys(window.sfState.inferencePresets).forEach(k => {
        const opt = document.createElement('option');
        opt.value = k;
        opt.textContent = k;
        infSel.appendChild(opt);
    });
    
    const xttsSel = document.getElementById('sf-xtts-preset-select');
    if (xttsSel) {
        xttsSel.innerHTML = '<option value="">-- No XTTS Preset --</option>';
        Object.keys(window.sfState.xttsPresets || {}).forEach(k => {
            const opt = document.createElement('option');
            opt.value = k;
            opt.textContent = k;
            xttsSel.appendChild(opt);
        });
    }
    
    const xttsInfSel = document.getElementById('sf-xtts-inference-preset-select');
    if (xttsInfSel) {
        xttsInfSel.innerHTML = '<option value="">-- No Inference Preset --</option>';
        Object.keys(window.sfState.xttsInferencePresets || {}).forEach(k => {
            const opt = document.createElement('option');
            opt.value = k;
            opt.textContent = k;
            xttsInfSel.appendChild(opt);
        });
    }
    
    if (optData && optData.ok) {
        const pSel = document.getElementById('sf-persona-select');
        pSel.innerHTML = '';
        optData.personas.forEach(p => {
            const opt = document.createElement('option');
            opt.value = p;
            opt.textContent = p.replace('.yaml', '');
            pSel.appendChild(opt);
        });
        
        window.sfState.allModels = optData.models;
        window.sfUpdateModelsDropdown();
    }
};


window.sfUpdateModelsDropdown = function() {
    const bType = document.getElementById('sf-backend-select').value;
    const mSel = document.getElementById('sf-model-select');
    mSel.innerHTML = '';
    
    if (!window.sfState.allModels) return;
    
    const filtered = window.sfState.allModels.filter(m => {
        if (!bType) return true;
        if (bType === 'cloud' && m.type === 'cloud') return true;
        if (bType === 'ollama' && m.type === 'local' && !m.id.includes('.gguf')) return true;
        if (bType === 'llama_cpp' && m.id.includes('.gguf')) return true;
        return false;
    });
    
    filtered.forEach(m => {
        const opt = document.createElement('option');
        opt.value = m.id;
        
        let prefix = (m.type === 'cloud') ? '☁️ ' : (m.type === 'local' ? '🖥️ ' : '');
        let suffix = '';
        let sizeTag = '';
        if (m.details && (m.details.parameter_size || m.size)) {
            let parts = [];
            if (m.details.parameter_size) parts.push(m.details.parameter_size);
            if (m.size) parts.push((m.size/1024/1024/1024).toFixed(1) + 'GB');
            sizeTag += ' [' + parts.join(' | ') + ']';
        }
        let tooltipText = m.name + sizeTag;
        
        if (m.capabilities && m.capabilities.length > 0) {
            const iconMap = { 'tools': '⚙️', 'vision': '👁️', 'thinking': '💭' };
            const descMap = { 'tools': 'Tools/Function Calling', 'vision': 'Vision/Multimodal', 'thinking': 'Thinking/Reasoning' };
            
            const icons = m.capabilities.map(c => iconMap[c]).filter(Boolean).join('');
            if (icons) suffix = ' ' + icons;
            
            const descs = m.capabilities.map(c => descMap[c]).filter(Boolean).join(', ');
            if (descs) tooltipText += '\nCapabilities: ' + descs;
        }
        
        opt.textContent = prefix + m.name + sizeTag + suffix;
        opt.title = tooltipText;
        mSel.appendChild(opt);
    });
};


window.sfUpdateVoicesDropdown = async function() {
    const engine = document.getElementById('sf-tts-engine-select').value;
    const vSel = document.getElementById('sf-tts-voice-select');
    vSel.innerHTML = '';
    if (!engine) return;
    
    try {
        const res = await fetch(`/api/audio/voices?engine=${engine}`);
        if (res.ok) {
            const voices = await res.json();
            const list = Array.isArray(voices) ? voices : (voices[engine] || Object.keys(voices));
            list.forEach(v => {
                const opt = document.createElement('option');
                opt.value = v;
                opt.textContent = v;
                vSel.appendChild(opt);
            });
        }
    } catch(e) {}
};


window.sfApplySoulToUI = async function(soul) {
    if (!soul) return;
    
    const fallbacks = window.sfSystemFallbacks || {};
    
    // Persona
    document.getElementById('sf-persona-select').value = soul.persona?.soul_file || fallbacks.persona || "";
    
    // Model
    document.getElementById('sf-backend-select').value = soul.model?.backend_type || fallbacks.backend || "ollama";
    window.sfUpdateModelsDropdown();
    document.getElementById('sf-model-select').value = soul.model?.model_name || fallbacks.model || "";
    
    // Voice
    document.getElementById('sf-tts-engine-select').value = soul.voice?.tts_engine || fallbacks.tts_engine || "piper";
    await window.sfUpdateVoicesDropdown();
    document.getElementById('sf-tts-voice-select').value = soul.voice?.tts_voice || fallbacks.tts_voice || "";
    
    // Inference
    document.getElementById('sf-inference-preset-select').value = soul.inference?.preset_name || "";
    
    const setVal = (id, val) => {
        if (val !== undefined && val !== null) {
            const el = document.getElementById(id);
            if (el) { el.value = val; window.sfUpdateSliderVal(el, id.replace('sf-', 'sf-val-')); }
        }
    };
    
    setVal('sf-temp', soul.inference?.temperature);
    setVal('sf-topp', soul.inference?.top_p);
    setVal('sf-reppen', soul.inference?.repeat_penalty);
    setVal('sf-predict', soul.inference?.num_predict);
    
    document.getElementById('sf-xtts-preset-select').value = soul.voice?.xtts_preset || "";
    
    const xttsInfSel = document.getElementById('sf-xtts-inference-preset-select');
    if (xttsInfSel) {
        xttsInfSel.value = soul.voice?.xtts_inference_preset || "";
    }
    
    document.getElementById('sf-xtts-speaker-wav').value = soul.voice?.xtts_speaker_wav || "";
    setVal('sf-xtts-temp', soul.voice?.xtts_temperature);
    setVal('sf-xtts-speed', soul.voice?.xtts_speed);
    setVal('sf-xtts-topk', soul.voice?.xtts_top_k);
    setVal('sf-xtts-reppen', soul.voice?.xtts_repetition_penalty);
    setVal('sf-xtts-topp', soul.voice?.xtts_top_p);
    setVal('sf-xtts-length-penalty', soul.voice?.xtts_length_penalty);
    
    window.sfUpdateCloneState();
    window.sfDirty();
    if (window.sfUpdateCloneState) window.sfUpdateCloneState();
    window.sfState.isDirty = false; // reset dirty flag as we just loaded
    
    const topBtn = document.getElementById('sf-top-save-btn');
    if (topBtn) {
        topBtn.innerHTML = '<i class="fas fa-save"></i> Save';
        topBtn.style.backgroundColor = '';
        topBtn.style.color = '';
        topBtn.onclick = window.sfOverwriteSoul;
    }
    
    const sbGD = document.getElementById('sb-global-defaults');
    if (sbGD) {
        sbGD.textContent = window.sfState.activeSoulId || 'Custom';
    }
};


window.sfCollectUIState = function() {
    const getVal = (id) => { const v = document.getElementById(id).value; return v === "" ? null : v; };
    const getNum = (id) => { const v = document.getElementById(id).value; return v ? parseFloat(v) : null; };
    
    return {
        persona: { soul_file: getVal('sf-persona-select') },
        model: { backend_type: getVal('sf-backend-select'), model_name: getVal('sf-model-select') },
        inference: {
            preset_name: getVal('sf-inference-preset-select'),
            temperature: getNum('sf-temp'),
            top_p: getNum('sf-topp'),
            repeat_penalty: getNum('sf-reppen'),
            num_predict: parseInt(getNum('sf-predict'))
        },
        voice: {
            tts_engine: getVal('sf-tts-engine-select'),
            tts_voice: getVal('sf-tts-voice-select'),
            xtts_preset: getVal('sf-xtts-preset-select'),
            xtts_inference_preset: getVal('sf-xtts-inference-preset-select'),
            xtts_speaker_wav: getVal('sf-xtts-speaker-wav'),
            xtts_temperature: getNum('sf-xtts-temp'),
            xtts_speed: getNum('sf-xtts-speed'),
            xtts_top_k: parseInt(getNum('sf-xtts-topk')),
            xtts_repetition_penalty: getNum('sf-xtts-reppen'),
            xtts_top_p: getNum('sf-xtts-topp'),
            xtts_length_penalty: getNum('sf-xtts-length-penalty')
        }
    };
};


window.sfApplyInferencePreset = function(presetName) {
    if (!presetName || !window.sfState.inferencePresets[presetName]) return;
    const p = window.sfState.inferencePresets[presetName];
    
    const setVal = (id, val) => {
        if (val !== undefined && val !== null) {
            const el = document.getElementById(id);
            if (el) { el.value = val; window.sfUpdateSliderVal(el, id.replace('sf-', 'sf-val-')); }
        }
    };
    
    setVal('sf-temp', p.temperature);
    setVal('sf-topp', p.top_p);
    setVal('sf-reppen', p.repeat_penalty);
    setVal('sf-predict', p.num_predict);
    
    window.sfDirty();
};


window.sfApplyXttsPreset = function(presetName) {
    if (!presetName || !window.sfState.xttsPresets[presetName]) {
        document.getElementById('sf-xtts-speaker-wav').value = "";
        window.sfDirty();
        return;
    }
    const p = window.sfState.xttsPresets[presetName];
    
    const setVal = (id, val) => {
        if (val !== undefined && val !== null) {
            const el = document.getElementById(id);
            if (el) { el.value = val; window.sfUpdateSliderVal(el, id.replace('sf-', 'sf-val-')); }
        }
    };
    
    setVal('sf-xtts-temp', p.temperature);
    setVal('sf-xtts-speed', p.speed);
    setVal('sf-xtts-topk', p.top_k);
    setVal('sf-xtts-reppen', p.repetition_penalty);
    setVal('sf-xtts-topp', p.top_p);
    
    if (p.speaker !== undefined && p.speaker !== null) {
        document.getElementById('sf-tts-voice-select').value = p.speaker;
    }
    
    document.getElementById('sf-xtts-speaker-wav').value = p.speaker_wav || "";

    // Try to match sliders with an inference preset to update the dropdown
    let matchedInf = "";
    if (window.sfState.xttsInferencePresets) {
        for (const [k, inf] of Object.entries(window.sfState.xttsInferencePresets)) {
            if (
                (!p.temperature || Math.abs(inf.temperature - p.temperature) < 0.01) &&
                (!p.speed || Math.abs(inf.speed - p.speed) < 0.01) &&
                (!p.top_k || inf.top_k === p.top_k) &&
                (!p.repetition_penalty || Math.abs(inf.repetition_penalty - p.repetition_penalty) < 0.01)
            ) {
                matchedInf = k;
                break;
            }
        }
    }
    const xttsInfSel = document.getElementById('sf-xtts-inference-preset-select');
    if (xttsInfSel) {
        xttsInfSel.value = matchedInf;
    }
    
    window.sfDirty();
};


window.sfApplyXttsInferencePreset = function(presetName) {
    if (!presetName || !window.sfState.xttsInferencePresets[presetName]) return;
    const p = window.sfState.xttsInferencePresets[presetName];
    
    const setVal = (id, val) => {
        if (val !== undefined && val !== null) {
            const el = document.getElementById(id);
            if (el) { el.value = val; window.sfUpdateSliderVal(el, id.replace('sf-', 'sf-val-')); }
        }
    };
    
    setVal('sf-xtts-temp', p.temperature);
    setVal('sf-xtts-speed', p.speed);
    setVal('sf-xtts-topk', p.top_k);
    setVal('sf-xtts-reppen', p.repetition_penalty);
    setVal('sf-xtts-topp', p.top_p);
    setVal('sf-xtts-length-penalty', p.length_penalty);
    
    window.sfDirty();
};


window.sfUpdateCloneState = function() {
    const wavInput = document.getElementById('sf-xtts-speaker-wav');
    const voiceSelect = document.getElementById('sf-tts-voice-select');
    if (wavInput && voiceSelect) {
        if (wavInput.value.trim() !== '') {
            voiceSelect.disabled = true;
            voiceSelect.title = "Using Voice Clone (.wav)";
        } else {
            voiceSelect.disabled = false;
            voiceSelect.title = "";
        }
    }
};
