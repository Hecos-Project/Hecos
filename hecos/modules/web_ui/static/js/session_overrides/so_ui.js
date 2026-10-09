/* ⚡ SOUL FORGE: gp_ui.js */

window.soTogglePanel = function(force, mode = 'global') {
    const panel = document.getElementById('session-overrides-panel');
    const overlay = document.getElementById('session-overrides-overlay');
    const isOpen = panel.classList.contains('open');
    
    const shouldOpen = force !== undefined ? force : !isOpen;
    
    if (shouldOpen) {
        try {
            const audio = new Audio('/assets/sounds/beep-6.mp3');
            audio.volume = 1.0; // Fixed at system volume
            audio.play().catch(e => console.log('Audio play prevented:', e));
        } catch(e) {}

        // Update Title and Description based on mode
        const titleEl = document.getElementById('so-panel-title');
        const descEl = document.getElementById('so-panel-desc');
        
        if (mode === 'chat') {
            if (titleEl) titleEl.textContent = 'Chat Overrides';
            if (descEl) descEl.innerHTML = 'These are the <b>Chat Overrides</b>. Changes here do not overwrite the Chat Overrides unless you explicitly choose to overwrite them.';
        } else {
            if (titleEl) titleEl.textContent = 'Chat Overrides';
            if (descEl) descEl.innerHTML = "These are the system's <b>Chat Overrides</b>. Settings saved here are automatically applied as the foundation for every new chat and are independent of Chat Overrides.";
        }
        
        // We will dynamically fetch the system config and update the fallbacks to show the actual fallback values.
        window.soUpdateFallbackLabels();
        
        panel.classList.add('open');
        overlay.style.display = 'block';
        window.soLoadData();
    } else {
        panel.classList.remove('open');
        overlay.style.display = 'none';
        if (window.soState.isDirty) {
            if (window.soState.activeSoulId) {
                window.hecosConfirm("You have unsaved changes. Do you want to update the active Global Preset?\n\n(Click 'Confirm' to update the Global Preset, or 'Cancel' to keep changes only for this session)", function() {
                    window.soSaveGlobalInlineToActive();
                }, function() {
                    window.soSaveInlineToActive();
                });
            } else {
                window.soSaveInlineToActive();
            }
        }
    }
};

window.soUpdateFallbackLabels = async function() {
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
        
        window.soSystemFallbacks = {
            persona: pName,
            backend: bType,
            model: bModel,
            tts_engine: tEngine,
            tts_voice: tVoice
        };
        
    } catch (e) {
        console.error("Failed to fetch system fallbacks for Chat Overrides UI", e);
    }
};

window.soDirty = function() {
    if (window.soUpdateCloneState) window.soUpdateCloneState();
    window.soState.isDirty = true;
    
    const topBtn = document.getElementById('so-top-save-global-btn');
    if (topBtn) {
        if (window.soState.activeSoulId) {
            topBtn.innerHTML = '<i class="fas fa-save"></i>';
            topBtn.style.backgroundColor = 'var(--accent1, #00d2ff)';
            topBtn.style.color = '#000';
            topBtn.onclick = window.soSaveGlobalInlineToActive;
        }
    }
    
    // Toggle XTTS settings visibility
    const ttsEngine = document.getElementById('so-tts-engine-select').value;
    document.getElementById('so-xtts-controls').style.display = (ttsEngine === 'xtts2') ? 'block' : 'none';
    
    // Visually update the topbar in the background so the user gets instant feedback
    const pSel = document.getElementById('chat-persona-select');
    const pVal = document.getElementById('so-persona-select')?.value || "";
    if (pSel) pSel.value = pVal;

    const mSel = document.getElementById('chat-model-select');
    const mVal = document.getElementById('so-model-select')?.value || "";
    if (mSel) mSel.value = mVal;

    const tEngSel = document.getElementById('chat-tts-engine-select');
    const tEngVal = document.getElementById('so-tts-engine-select')?.value || "";
    let engineChanged = false;
    if (tEngSel && tEngSel.value !== tEngVal) {
        tEngSel.value = tEngVal;
        engineChanged = true;
    }

    const tVoiceSel = document.getElementById('chat-tts-voice-select');
    let tVoiceVal = document.getElementById('so-tts-voice-select')?.value || "";
    const soXttsWav = document.getElementById('so-xtts-speaker-wav')?.value;
    if (soXttsWav) {
        tVoiceVal = 'custom';
    }
    
    let voiceMissing = false;
    if (tVoiceSel && !engineChanged) {
        tVoiceSel.value = tVoiceVal;
        if (tVoiceVal && tVoiceSel.value !== tVoiceVal) {
            voiceMissing = true;
        }
    }

    if (engineChanged || voiceMissing) {
        if (window.updateSessionTTSVoices) {
            window.updateSessionTTSVoices(tVoiceVal);
        }
    }
    
    if (window.updateSessionDropdownTitles) window.updateSessionDropdownTitles();
    
    // Visually update the avatar and persona name instantly and flip the card if it changed
    if (window._lastSoPersonaVal !== pVal) {
        window._lastSoPersonaVal = pVal;
        if (pVal) {
            window.HecosPersonaName = pVal.replace('.yaml', '').replace(/_/g, ' ');
            fetch(`/api/persona/avatar?persona=${encodeURIComponent(pVal)}`)
                .then(r => r.json())
                .then(d => { 
                    if (d.ok && d.avatar_path) window.HecosAvatar = d.avatar_path; 
                    if (window.HecosWelcome && window.HecosWelcome.show) window.HecosWelcome.show(true);
                })
                .catch(()=>{
                    if (window.HecosWelcome && window.HecosWelcome.show) window.HecosWelcome.show(true);
                });
        } else {
            window.HecosPersonaName = window._globalPersonaName || 'Hecos';
            if (window._globalAvatar) window.HecosAvatar = window._globalAvatar;
            if (window.HecosWelcome && window.HecosWelcome.show) window.HecosWelcome.show(true);
        }
    }
};


window.soUpdateSliderVal = function(el, spanId) {
    document.getElementById(spanId).textContent = el.value;
};


window.soPopulateDropdowns = function(optData) {
    const soulSel = document.getElementById('so-active-soul-select');
    const quickSel = document.getElementById('so-quick-preset-select');
    
    soulSel.innerHTML = '<option value="">-- No active global preset --</option>';
    if (quickSel) quickSel.innerHTML = '<option value="">⚡ Preset...</option>';
    
    window.soState.souls.forEach(s => {
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
    
    const infSel = document.getElementById('so-inference-preset-select');
    infSel.innerHTML = '<option value="">-- No preset selected --</option>';
    Object.keys(window.soState.inferencePresets).forEach(k => {
        const opt = document.createElement('option');
        opt.value = k;
        opt.textContent = k;
        infSel.appendChild(opt);
    });
    
    const xttsSel = document.getElementById('so-xtts-preset-select');
    if (xttsSel) {
        xttsSel.innerHTML = '<option value="">-- No XTTS Preset --</option>';
        Object.keys(window.soState.xttsPresets || {}).forEach(k => {
            const opt = document.createElement('option');
            opt.value = k;
            opt.textContent = k;
            xttsSel.appendChild(opt);
        });
    }
    
    const xttsInfSel = document.getElementById('so-xtts-inference-preset-select');
    if (xttsInfSel) {
        xttsInfSel.innerHTML = '<option value="">-- No Inference Preset --</option>';
        Object.keys(window.soState.xttsInferencePresets || {}).forEach(k => {
            const opt = document.createElement('option');
            opt.value = k;
            opt.textContent = k;
            xttsInfSel.appendChild(opt);
        });
    }
    
    if (optData && optData.ok) {
        const pSel = document.getElementById('so-persona-select');
        pSel.innerHTML = '';
        optData.personas.forEach(p => {
            const opt = document.createElement('option');
            opt.value = p;
            opt.textContent = p.replace('.yaml', '');
            pSel.appendChild(opt);
        });
        
        window.soState.allModels = optData.models;
        window.soUpdateModelsDropdown();
    }
};


window.soUpdateModelsDropdown = function() {
    const bType = document.getElementById('so-backend-select').value;
    const mSel = document.getElementById('so-model-select');
    mSel.innerHTML = '';
    
    if (!window.soState.allModels) return;
    
    const filtered = window.soState.allModels.filter(m => {
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
        if (m.parameter_size || m.size_bytes) {
            sizeTag = ' [';
            let parts = [];
            if (m.parameter_size) {
                let p = m.parameter_size;
                if (m.quantization_level) p += ' ' + m.quantization_level;
                parts.push(p);
            }
            if (m.size_bytes) {
                let gb = (m.size_bytes / (1024*1024*1024)).toFixed(1);
                parts.push(gb + 'GB');
            }
            sizeTag += parts.join(' | ') + ']';
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


window.soUpdateVoicesDropdown = async function() {
    const engine = document.getElementById('so-tts-engine-select').value;
    const vSel = document.getElementById('so-tts-voice-select');
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


window.soApplySoulToUI = async function(soul) {
    const fallbacks = window.soSystemFallbacks || {};
    
    if (!soul) {
        document.getElementById('so-persona-select').value = "";
        
        const dirChk = document.getElementById('so-use-global-direct');
        if (dirChk) dirChk.checked = true;
        
        const safeChk = document.getElementById('so-use-global-safety');
        if (safeChk) safeChk.checked = true;
        
        const custInst = document.getElementById('so-custom-instructions');
        if (custInst) custInst.value = "";

        document.getElementById('so-backend-select').value = "";
        window.soUpdateModelsDropdown();
        document.getElementById('so-model-select').value = "";
        document.getElementById('so-tts-engine-select').value = "";
        await window.soUpdateVoicesDropdown();
        document.getElementById('so-tts-voice-select').value = "";
        document.getElementById('so-inference-preset-select').value = "";
        
        const quickSel = document.getElementById('so-quick-preset-select');
        if (quickSel) quickSel.value = "";
        
        const resetVal = (id, defVal) => {
            const el = document.getElementById(id);
            if (el) { el.value = defVal; window.soUpdateSliderVal(el, id.replace('so-', 'so-val-')); }
        };
        
        resetVal('so-temp', 0.7);
        resetVal('so-topp', 0.9);
        resetVal('so-reppen', 1.1);
        resetVal('so-predict', 1024);
        
        document.getElementById('so-xtts-preset-select').value = "";
        const xttsInfSel = document.getElementById('so-xtts-inference-preset-select');
        if (xttsInfSel) xttsInfSel.value = "";
        
        document.getElementById('so-xtts-speaker-wav').value = "";
        resetVal('so-xtts-temp', 0.75);
        resetVal('so-xtts-speed', 1.0);
        resetVal('so-xtts-topk', 50);
        resetVal('so-xtts-reppen', 5.0);
        resetVal('so-xtts-topp', 0.85);
        resetVal('so-xtts-length-penalty', 1.0);
        
        window.soDirty();
        if (window.soUpdateCloneState) window.soUpdateCloneState();
        window.soState.isDirty = false;
        
        // Restore system default persona/avatar when override is cleared
        if (window._globalPersonaName) window.HecosPersonaName = window._globalPersonaName;
        if (window._globalAvatar) window.HecosAvatar = window._globalAvatar;
        
        const topBtn = document.getElementById('so-top-save-global-btn');
        if (topBtn) {
            topBtn.innerHTML = '<i class="fas fa-save"></i>';
            topBtn.style.backgroundColor = '';
            topBtn.style.color = '';
            topBtn.onclick = window.soOverwriteGlobalPreset;
        }
        return;
    }
    
    
    // Persona
    document.getElementById('so-persona-select').value = soul.persona?.soul_file || fallbacks.persona || "";
    
    document.getElementById('so-use-global-direct').checked = soul.persona?.use_global_direct_instructions !== false;
    document.getElementById('so-use-global-safety').checked = soul.persona?.use_global_safety_instructions !== false;
    document.getElementById('so-custom-instructions').value = soul.persona?.custom_instructions || "";
    document.getElementById('so-user-notes').value = soul.persona?.user_notes || "";
    document.getElementById('so-send-notes-ai').checked = soul.persona?.send_notes_to_ai === true;
    
    // Model
    document.getElementById('so-backend-select').value = soul.model?.backend_type || fallbacks.backend || "ollama";
    window.soUpdateModelsDropdown();
    document.getElementById('so-model-select').value = soul.model?.model_name || fallbacks.model || "";
    
    // Voice
    document.getElementById('so-tts-engine-select').value = soul.voice?.tts_engine || fallbacks.tts_engine || "piper";
    await window.soUpdateVoicesDropdown();
    document.getElementById('so-tts-voice-select').value = soul.voice?.tts_voice || fallbacks.tts_voice || "";
    
    // Inference
    document.getElementById('so-inference-preset-select').value = soul.inference?.preset_name || "";
    
    const setVal = (id, val) => {
        if (val !== undefined && val !== null) {
            const el = document.getElementById(id);
            if (el) { el.value = val; window.soUpdateSliderVal(el, id.replace('so-', 'so-val-')); }
        }
    };
    
    setVal('so-temp', soul.inference?.temperature);
    setVal('so-topp', soul.inference?.top_p);
    setVal('so-reppen', soul.inference?.repeat_penalty);
    setVal('so-predict', soul.inference?.num_predict);

    const ctxEl = document.getElementById('so-ctx');
    if (ctxEl) {
        ctxEl.value = (soul.inference?.num_ctx !== undefined && soul.inference?.num_ctx !== null) ? soul.inference.num_ctx : 0;
        ctxEl.dispatchEvent(new Event('input'));
    }
    
    const gpuEl = document.getElementById('so-gpu');
    if (gpuEl) {
        gpuEl.value = (soul.inference?.n_gpu_layers !== undefined && soul.inference?.n_gpu_layers !== null) ? soul.inference.n_gpu_layers : -2;
        gpuEl.dispatchEvent(new Event('input'));
    }
    
    document.getElementById('so-xtts-preset-select').value = soul.voice?.xtts_preset || "";
    
    const xttsInfSel = document.getElementById('so-xtts-inference-preset-select');
    if (xttsInfSel) {
        xttsInfSel.value = soul.voice?.xtts_inference_preset || "";
    }
    
    document.getElementById('so-xtts-speaker-wav').value = soul.voice?.xtts_speaker_wav || "";
    setVal('so-xtts-temp', soul.voice?.xtts_temperature);
    setVal('so-xtts-speed', soul.voice?.xtts_speed);
    setVal('so-xtts-topk', soul.voice?.xtts_top_k);
    setVal('so-xtts-reppen', soul.voice?.xtts_repetition_penalty);
    setVal('so-xtts-topp', soul.voice?.xtts_top_p);
    setVal('so-xtts-length-penalty', soul.voice?.xtts_length_penalty);
    
    window.soDirty();
    if (window.soUpdateCloneState) window.soUpdateCloneState();
    window.soState.isDirty = false; // reset dirty flag as we just loaded
    
    // ── Immediately update the chat avatar & persona name globals ─────
    // This ensures addBubble() shows the correct soul from the first instant,
    // instead of flashing the system default until the AI response arrives.
    const soulPersona = soul.persona?.soul_file;
    if (soulPersona) {
        window.HecosPersonaName = soulPersona;
        // Async-fetch the avatar so it's ready before the user sends a message
        fetch(`/api/persona/avatar?persona=${encodeURIComponent(soulPersona)}`)
            .then(r => r.json())
            .then(d => {
                if (d.ok && d.avatar_path) {
                    window.HecosAvatar = d.avatar_path;
                    window.HecosAvatarType = d.avatar_type || 'image';
                }
            })
            .catch(() => {});
    }
    
    const topBtn = document.getElementById('so-top-save-global-btn');
    if (topBtn) {
        topBtn.innerHTML = '<i class="fas fa-save"></i>';
        topBtn.style.backgroundColor = '';
        topBtn.style.color = '';
        topBtn.onclick = window.soOverwriteGlobalPreset;
    }
};


window.soCollectUIState = function() {
    const getVal = (id) => { const v = document.getElementById(id).value; return v === "" ? null : v; };
    const getNum = (id) => { const v = document.getElementById(id).value; return v ? parseFloat(v) : null; };
    const getCheck = (id) => document.getElementById(id).checked;
    
    return {
        active_global_preset: window.soState ? window.soState.activeSoulId : null,
        persona: { 
            soul_file: getVal('so-persona-select'),
            use_global_direct_instructions: getCheck('so-use-global-direct'),
            use_global_safety_instructions: getCheck('so-use-global-safety'),
            custom_instructions: getVal('so-custom-instructions'),
            user_notes: getVal('so-user-notes'),
            send_notes_to_ai: getCheck('so-send-notes-ai')
        },
        model: { backend_type: getVal('so-backend-select'), model_name: getVal('so-model-select') },
        inference: {
            preset_name: getVal('so-inference-preset-select'),
            temperature: getNum('so-temp'),
            top_p: getNum('so-topp'),
            repeat_penalty: getNum('so-reppen'),
            num_predict: parseInt(getNum('so-predict')),
            num_ctx: getNum('so-ctx') === 0 ? null : parseInt(getNum('so-ctx')),
            n_gpu_layers: getNum('so-gpu') === -2 ? null : parseInt(getNum('so-gpu'))
        },
        voice: {
            tts_engine: getVal('so-tts-engine-select'),
            tts_voice: getVal('so-tts-voice-select'),
            xtts_preset: getVal('so-xtts-preset-select'),
            xtts_inference_preset: getVal('so-xtts-inference-preset-select'),
            xtts_speaker_wav: getVal('so-xtts-speaker-wav'),
            xtts_temperature: getNum('so-xtts-temp'),
            xtts_speed: getNum('so-xtts-speed'),
            xtts_top_k: parseInt(getNum('so-xtts-topk')),
            xtts_repetition_penalty: getNum('so-xtts-reppen'),
            xtts_top_p: getNum('so-xtts-topp'),
            xtts_length_penalty: getNum('so-xtts-length-penalty')
        }
    };
};


window.soApplyInferencePreset = function(presetName) {
    if (!presetName || !window.soState.inferencePresets[presetName]) return;
    const p = window.soState.inferencePresets[presetName];
    
    const setVal = (id, val) => {
        if (val !== undefined && val !== null) {
            const el = document.getElementById(id);
            if (el) { el.value = val; window.soUpdateSliderVal(el, id.replace('so-', 'so-val-')); }
        }
    };
    
    setVal('so-temp', p.temperature);
    setVal('so-topp', p.top_p);
    setVal('so-reppen', p.repeat_penalty);
    setVal('so-predict', p.num_predict);
    
    window.soDirty();
};


window.soApplyXttsPreset = function(presetName) {
    if (!presetName || !window.soState.xttsPresets[presetName]) {
        document.getElementById('so-xtts-speaker-wav').value = "";
        window.soDirty();
        return;
    }
    const p = window.soState.xttsPresets[presetName];
    
    const setVal = (id, val) => {
        if (val !== undefined && val !== null) {
            const el = document.getElementById(id);
            if (el) { el.value = val; window.soUpdateSliderVal(el, id.replace('so-', 'so-val-')); }
        }
    };
    
    setVal('so-xtts-temp', p.temperature);
    setVal('so-xtts-speed', p.speed);
    setVal('so-xtts-topk', p.top_k);
    setVal('so-xtts-reppen', p.repetition_penalty);
    setVal('so-xtts-topp', p.top_p);
    
    if (p.speaker !== undefined && p.speaker !== null) {
        document.getElementById('so-tts-voice-select').value = p.speaker;
    }
    
    document.getElementById('so-xtts-speaker-wav').value = p.speaker_wav || "";

    // Try to match sliders with an inference preset to update the dropdown
    let matchedInf = "";
    if (window.soState.xttsInferencePresets) {
        for (const [k, inf] of Object.entries(window.soState.xttsInferencePresets)) {
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
    const xttsInfSel = document.getElementById('so-xtts-inference-preset-select');
    if (xttsInfSel) {
        xttsInfSel.value = matchedInf;
    }
    
    window.soDirty();
};


window.soApplyXttsInferencePreset = function(presetName) {
    if (!presetName || !window.soState.xttsInferencePresets[presetName]) return;
    const p = window.soState.xttsInferencePresets[presetName];
    
    const setVal = (id, val) => {
        if (val !== undefined && val !== null) {
            const el = document.getElementById(id);
            if (el) { el.value = val; window.soUpdateSliderVal(el, id.replace('so-', 'so-val-')); }
        }
    };
    
    setVal('so-xtts-temp', p.temperature);
    setVal('so-xtts-speed', p.speed);
    setVal('so-xtts-topk', p.top_k);
    setVal('so-xtts-reppen', p.repetition_penalty);
    setVal('so-xtts-topp', p.top_p);
    setVal('so-xtts-length-penalty', p.length_penalty);
    
    window.soDirty();
};




window.soUpdateCloneState = function() {
    const wavInput = document.getElementById('so-xtts-speaker-wav');
    const voiceSelect = document.getElementById('so-tts-voice-select');
    if (wavInput && voiceSelect) {
        if (wavInput.value.trim() !== '') {
            voiceSelect.disabled = true;
            voiceSelect.title = "Using Voice Clone (.wav)";
            // Add a temporary option so it shows the clone text
            let cloneOpt = Array.from(voiceSelect.options).find(o => o.value === "CLONE");
            if (!cloneOpt) {
                cloneOpt = document.createElement('option');
                cloneOpt.value = "CLONE";
                cloneOpt.textContent = "-- Voice Clone Active --";
                voiceSelect.appendChild(cloneOpt);
            }
            voiceSelect.value = "CLONE";
        } else {
            voiceSelect.disabled = false;
            voiceSelect.title = "";
            const cloneOpt = Array.from(voiceSelect.options).find(o => o.value === "CLONE");
            if (cloneOpt) {
                cloneOpt.remove();
            }
        }
    }
};
