/* ⚡ SOUL FORGE: gp_state.js — Unified State & Session/Global Loader */

window.sfState = {
    souls: [],
    inferencePresets: {},
    globalDefaultSoulId: null,
    activeSoulId: null,
    sessionHasDraft: false,
    isDirty: false,
    baselineState: null,
    lastLabResponse: ""
};

// Backwards-compatible alias for any external callers checking window.soState
window.soState = window.sfState;

window.sfGetActiveSessionId = function() {
    return window.chatHistoryState?.activeSessionId || localStorage.getItem('hecos_active_session_id') || null;
};

window.hecosConfirm = function(msg, onYes, onNo) {
    const modal = document.getElementById('hecos-confirm-modal');
    const textEl = document.getElementById('hecos-confirm-modal-text');
    const yesBtn = document.getElementById('hecos-confirm-modal-yes');
    const noBtn = document.getElementById('hecos-confirm-modal-no');
    
    if (modal && textEl && yesBtn) {
        textEl.textContent = msg;
        modal.style.display = 'flex';
        
        yesBtn.onclick = function() {
            modal.style.display = 'none';
            if (onYes) onYes();
        };
        
        if (noBtn) {
            noBtn.onclick = function() {
                modal.style.display = 'none';
                if (onNo) onNo();
            };
        }
    } else {
        if (confirm(msg)) {
            if (onYes) onYes();
        } else {
            if (onNo) onNo();
        }
    }
};

window.hecosPrompt = function(msg, onSave) {
    const modal = document.getElementById('hecos-prompt-modal');
    const textEl = document.getElementById('hecos-prompt-modal-text');
    const inputEl = document.getElementById('hecos-prompt-modal-input');
    const yesBtn = document.getElementById('hecos-prompt-modal-yes');
    
    if (modal && textEl && inputEl && yesBtn) {
        textEl.textContent = msg;
        inputEl.value = '';
        modal.style.display = 'flex';
        inputEl.focus();
        
        const finish = function() {
            const val = inputEl.value.trim();
            if (!val) return;
            modal.style.display = 'none';
            onSave(val);
        };
        
        yesBtn.onclick = finish;
        inputEl.onkeydown = function(e) {
            if (e.key === 'Enter') finish();
        };
    } else {
        const val = prompt(msg);
        if (val && val.trim() !== '') onSave(val.trim());
    }
};

window.sfBuildBaseVirtualSoul = function(cfg) {
    cfg = cfg || window.HecosSystemConfig || {};
    let btype = cfg.backend?.type || 'ollama';
    if (btype === 'hybrid') {
        btype = cfg.backend?.active_model_source || 'cloud';
    }
    const bdict = cfg.backend?.[btype] || {};
    
    let ttsEngine = cfg.ai?.tts_engine;
    if (!ttsEngine && cfg.audio) ttsEngine = cfg.audio.active_engine;
    if (!ttsEngine && window.sfSystemFallbacks?.tts_engine && window.sfSystemFallbacks.tts_engine !== 'unknown') {
        ttsEngine = window.sfSystemFallbacks.tts_engine;
    }
    if (!cfg.audio && window.sfState?.audioConfig) {
        cfg = Object.assign({}, cfg, { audio: window.sfState.audioConfig });
    }
    let resolvedVoice = cfg.ai?.tts_voice || "";
    if (!resolvedVoice && ttsEngine === 'kokoro') resolvedVoice = cfg.audio?.kokoro?.voice || "";
    if (!resolvedVoice && ttsEngine === 'xtts2') resolvedVoice = cfg.audio?.xtts?.speaker || "";
    if (!resolvedVoice) resolvedVoice = window.sfSystemFallbacks?.tts_voice || "";

    const rawKokoroPreset = cfg.ai?.kokoro_preset || (cfg.audio?.kokoro?.current_preset !== 'default' ? cfg.audio?.kokoro?.current_preset : "") || "";
    const validKokoroPreset = (rawKokoroPreset && (!window.sfState?.kokoroPresets || window.sfState.kokoroPresets[rawKokoroPreset])) ? rawKokoroPreset : "";

    return {
        persona: {
            soul_file: cfg.ai?.active_personality || window.sfSystemFallbacks?.persona || "",
            use_global_direct_instructions: cfg.ai?.use_global_direct_instructions !== false,
            use_global_safety_instructions: cfg.ai?.use_global_safety_instructions !== false,
            custom_instructions: cfg.ai?.custom_instructions || "",
            user_notes: cfg.ai?.user_notes || "",
            send_notes_to_ai: cfg.ai?.send_notes_to_ai === true
        },
        model: {
            backend_type: btype,
            model_name: bdict.model || window.sfSystemFallbacks?.model || ""
        },
        payload: {
            send_tools: cfg.payload_control?.send_tools !== false,
            send_personality: cfg.payload_control?.send_personality !== false,
            send_memory: cfg.payload_control?.send_memory !== false,
            include_thinking_in_history: cfg.payload_control?.include_thinking_in_history === true,
            enable_thinking: cfg.payload_control?.enable_thinking !== false
        },
        voice: {
            tts_engine: ttsEngine || "piper",
            tts_voice: resolvedVoice,
            xtts_preset: cfg.ai?.xtts_preset || (cfg.audio?.xtts?.current_preset !== 'default' ? cfg.audio?.xtts?.current_preset : "") || "",
            xtts_inference_preset: cfg.audio?.xtts?.current_inference_preset || "",
            xtts_speaker_wav: cfg.audio?.xtts?.speaker_wav || "",
            xtts_temperature: cfg.audio?.xtts?.temperature ?? 0.75,
            xtts_speed: cfg.audio?.xtts?.speed ?? 1.0,
            xtts_top_k: cfg.audio?.xtts?.top_k ?? 50,
            xtts_repetition_penalty: cfg.audio?.xtts?.repetition_penalty ?? 5.0,
            xtts_top_p: cfg.audio?.xtts?.top_p ?? 0.85,
            xtts_length_penalty: cfg.audio?.xtts?.length_penalty ?? 1.0,
            fish_preset: cfg.ai?.fish_preset || (cfg.audio?.fish_speech?.current_preset !== 'default' ? cfg.audio?.fish_speech?.current_preset : "") || "",
            fish_inference_preset: cfg.audio?.fish_speech?.current_inference_preset || "",
            fish_reference_audio: cfg.audio?.fish_speech?.reference_audio || "",
            fish_reference_text: cfg.audio?.fish_speech?.reference_text || "",
            fish_temperature: cfg.audio?.fish_speech?.temperature ?? 0.7,
            fish_top_p: cfg.audio?.fish_speech?.top_p ?? 0.7,
            fish_repetition_penalty: cfg.audio?.fish_speech?.repetition_penalty ?? 1.2,
            fish_chunk_length: cfg.audio?.fish_speech?.chunk_length ?? 200,
            fish_max_new_tokens: cfg.audio?.fish_speech?.max_new_tokens ?? 1024,
            kokoro_preset: validKokoroPreset,
            kokoro_inference_preset: cfg.audio?.kokoro?.current_inference_preset || "",
            kokoro_voice: cfg.audio?.kokoro?.voice || "",
            kokoro_blend_voice: cfg.audio?.kokoro?.blend_voice || "",
            kokoro_speed: cfg.audio?.kokoro?.speed ?? 1.0,
            kokoro_alpha: cfg.audio?.kokoro?.alpha ?? 1.0,
            kokoro_beta: cfg.audio?.kokoro?.beta ?? 1.0,
            kokoro_silence: cfg.audio?.kokoro?.sentence_silence ?? 0.0,
            kokoro_volume: cfg.audio?.kokoro?.volume ?? 1.0
        },
        inference: {
            preset_name: "",
            temperature: bdict.temperature ?? 0.7,
            top_p: bdict.top_p ?? 0.9,
            repeat_penalty: bdict.repeat_penalty ?? 1.1,
            num_predict: bdict.num_predict ?? 1024,
            num_ctx: bdict.num_ctx || bdict.n_ctx || null,
            n_gpu_layers: (bdict.num_gpu !== undefined ? bdict.num_gpu : bdict.n_gpu_layers) ?? null
        }
    };
};

window.sfLoadData = async function() {
    try {
        const [soulsRes, infRes, chatOptRes, audioConfRes] = await Promise.all([
            fetch('/api/souls', { cache: 'no-store' }),
            fetch('/api/souls/presets/inference', { cache: 'no-store' }),
            fetch('/api/chat/options', { cache: 'no-store' }), 
            fetch('/api/audio/config', { cache: 'no-store' })
        ]);
        
        const soulsData = await soulsRes.json();
        const infData = await infRes.json();
        const optData = await chatOptRes.json();
        const audioConfData = await audioConfRes.json();
        
        if (soulsData.ok) window.sfState.souls = soulsData.souls;
        if (infData.ok) window.sfState.inferencePresets = infData.presets;
        if (audioConfData.ok) {
            window.sfState.audioConfig = audioConfData.config || {};
            window.sfState.xttsPresets = audioConfData.config.xtts_presets || {};
            window.sfState.xttsInferencePresets = audioConfData.config.xtts_inference_presets || {};
            window.sfState.fishSpeechPresets = audioConfData.config.fish_speech_presets || {};
            window.sfState.fishSpeechInferencePresets = audioConfData.config.fish_speech_inference_presets || {};
            window.sfState.kokoroPresets = audioConfData.config.kokoro_presets || {};
            window.sfState.kokoroInferencePresets = audioConfData.config.kokoro_inference_presets || {};
        }
        
        window.sfPopulateDropdowns(optData);
        await window.sfLoadGlobalState();
        await window.sfLoadActiveSessionState();
        
    } catch(e) { console.error("GlobalPresets Load Error", e); }
};

window.soLoadData = window.sfLoadData;

window.sfLoadGlobalState = async function() {
    try {
        const res = await fetch(`/hecos/config`, { cache: 'no-store' });
        const cfg = await res.json();
        if (window.sfState.audioConfig) {
            cfg.audio = window.sfState.audioConfig;
        }
        window.HecosSystemConfig = cfg;
        
        let globalSoulId = null;
        if (cfg.ai && cfg.ai.active_global_preset) {
            globalSoulId = cfg.ai.active_global_preset;
        }
        window.sfState.globalDefaultSoulId = globalSoulId;

        let globalSoul = null;
        if (globalSoulId) {
            const soulObj = window.sfState.souls.find(s => s.meta.id === globalSoulId);
            if (soulObj) {
                globalSoul = soulObj;
            } else {
                const soulRes = await fetch(`/api/souls/${globalSoulId}`, { cache: 'no-store' });
                const soulData = await soulRes.json();
                if (soulData.ok) globalSoul = soulData.soul;
            }
        }
        if (!globalSoul) {
            globalSoul = window.sfBuildBaseVirtualSoul(cfg);
        }
        window.sfState.globalDefaultSoul = globalSoul;

        if (window.sfUpdateTooltip) {
            window.sfUpdateTooltip(globalSoul, globalSoulId);
        }
    } catch(e) { console.error("sfLoadGlobalState error", e); }
};

window.sfLoadActiveSessionState = async function() {
    const sessionId = window.sfGetActiveSessionId();
    if (!window.HecosSystemConfig) {
        await window.sfLoadGlobalState();
    }

    let sessionCfg = null;
    if (sessionId) {
        try {
            const res = await fetch(`/api/chat/session/config?session_id=${encodeURIComponent(sessionId)}`, { cache: 'no-store' });
            const data = await res.json();
            if (data.ok && data.config && Object.keys(data.config).length > 0) {
                sessionCfg = data.config;
            }
        } catch(e) {}
    }

    // Determine active preset for this chat session:
    // If session has an explicit active_global_preset, use it; otherwise inherit globalDefaultSoulId
    let effectiveSoulId = window.sfState.globalDefaultSoulId || null;
    if (sessionCfg && sessionCfg.active_global_preset !== undefined) {
        effectiveSoulId = sessionCfg.active_global_preset || null;
    }

    window.sfState.activeSoulId = effectiveSoulId;

    const sel = document.getElementById('sf-active-soul-select');
    if (sel) sel.value = effectiveSoulId || "";

    // Load the clean base Soul for this session (either the preset or the system base config)
    let baseSoul = null;
    if (effectiveSoulId) {
        baseSoul = window.sfState.souls.find(s => s.meta.id === effectiveSoulId) || null;
        if (!baseSoul) {
            try {
                const soulRes = await fetch(`/api/souls/${effectiveSoulId}`, { cache: 'no-store' });
                const soulData = await soulRes.json();
                if (soulData.ok) baseSoul = soulData.soul;
            } catch(e) {}
        }
    }
    if (!baseSoul) {
        baseSoul = window.sfBuildBaseVirtualSoul(window.HecosSystemConfig);
    }

    // Apply clean base soul to UI first
    await window.sfApplySoulToUI(baseSoul);

    // Save clean baseline snapshot of UI state (before per-chat draft tweaks)
    window.sfState.baselineState = JSON.parse(JSON.stringify(window.sfCollectUIState()));

    // Now overlay any per-session overrides / draft on top of the UI
    if (sessionCfg) {
        await window.sfApplySessionOverridesToUI(sessionCfg);
    }

    window.sfRefreshUIVisibilityAndSummaries();
    if (window.sfSyncActivePersonaAvatar) window.sfSyncActivePersonaAvatar();
};

window.soLoadActiveSessionState = window.sfLoadActiveSessionState;

window.sfSelectSessionSoul = async function(soulId) {
    const sessionId = window.sfGetActiveSessionId();
    if (!sessionId) {
        return window.sfActivateSoul(soulId);
    }

    try {
        const res = await fetch('/api/souls/activate', {
            method: 'POST',
            headers: {'Content-Type':'application/json'},
            body: JSON.stringify({ soul_id: soulId || "", session_id: sessionId })
        });
        
        if (res.ok) {
            const msgEl = document.getElementById('sf-status-msg');
            if (msgEl) {
                msgEl.textContent = soulId ? "Preset applied to this chat." : "Chat reset to system defaults.";
                setTimeout(() => { if (msgEl) msgEl.textContent = ""; }, 3000);
            }
            await window.sfLoadActiveSessionState();
            if (window.HecosWelcome && window.HecosWelcome.show) window.HecosWelcome.show();
        }
    } catch(e) { console.error("sfSelectSessionSoul error", e); }
};

window.soActivateSoul = window.sfSelectSessionSoul;

window.sfActivateSoul = async function(soulId, extraSoulPayload = null) {
    if (soulId === undefined || soulId === null) soulId = "";
    
    try {
        const bodyObj = { soul_id: soulId, session_id: 'global' };
        if (extraSoulPayload) bodyObj.soul = extraSoulPayload;

        const res = await fetch('/api/souls/activate', {
            method: 'POST',
            headers: {'Content-Type':'application/json'},
            body: JSON.stringify(bodyObj)
        });
        
        if (res.ok) {
            const msgEl = document.getElementById('sf-status-msg');
            if (msgEl) {
                msgEl.textContent = soulId
                    ? "⭐ Preset set as Global Default."
                    : "⭐ Base Configuration saved as Global Default.";
                setTimeout(() => { if (msgEl) msgEl.textContent = ""; }, 3500);
            }
            
            await window.sfUpdateFallbackLabels();
            await window.sfLoadGlobalState();
            
            // Also align the current chat session with the new default
            const sessionId = window.sfGetActiveSessionId();
            if (sessionId) {
                await fetch('/api/souls/activate', {
                    method: 'POST',
                    headers: {'Content-Type':'application/json'},
                    body: JSON.stringify({ soul_id: soulId, session_id: sessionId })
                });
            }
            await window.sfLoadActiveSessionState();
        }
    } catch(e) { console.error("sfActivateSoul error", e); }
};

document.addEventListener('DOMContentLoaded', async () => {
    if (window.sfUpdateFallbackLabels) await window.sfUpdateFallbackLabels();
    if (window.sfLoadData) {
        await window.sfLoadData();
    }
});
