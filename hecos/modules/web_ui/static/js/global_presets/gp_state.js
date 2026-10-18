/* ⚡ SOUL FORGE: gp_state.js */

/* ⚡ SOUL FORGE: Global Presets JS Logic */

window.sfState = {
    souls: [],
    inferencePresets: {},
    activeSoulId: null,
    isDirty: false
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
            window.sfState.xttsPresets = audioConfData.config.xtts_presets || {};
            window.sfState.xttsInferencePresets = audioConfData.config.xtts_inference_presets || {};
            window.sfState.fishSpeechPresets = audioConfData.config.fish_speech_presets || {};
            window.sfState.fishSpeechInferencePresets = audioConfData.config.fish_speech_inference_presets || {};
        }
        
        // Populate select lists
        window.sfPopulateDropdowns(optData);
        
        await window.sfLoadGlobalState();
        
    } catch(e) { console.error("GlobalPresets Load Error", e); }
};


window.sfLoadGlobalState = async function() {
    try {
        const res = await fetch(`/hecos/config`, { cache: 'no-store' });
        const cfg = await res.json();
        window.HecosSystemConfig = cfg;
        
        let activeSoulId = null;
        if (cfg.ai && cfg.ai.active_global_preset) {
            activeSoulId = cfg.ai.active_global_preset;
        }
        
        window.sfState.activeSoulId = activeSoulId;
        const sel = document.getElementById('sf-active-soul-select');
        if (sel) sel.value = activeSoulId || "";
        const quickSel = document.getElementById('sf-quick-preset-select');
        if (quickSel) quickSel.value = activeSoulId || "";
        
        if (activeSoulId) {
            const soulRes = await fetch(`/api/souls/${activeSoulId}`, { cache: 'no-store' });
            const soulData = await soulRes.json();
            if (soulData.ok) {
                window.sfApplySoulToUI(soulData.soul);
            }
        } else {
            // Build virtual soul from cfg when no preset is active
            const btype = cfg.backend?.type || 'ollama';
            const bdict = cfg.backend?.[btype] || {};
            
            // TTS engine might be in cfg.audio or cfg.ai, check both
            let ttsEngine = cfg.ai?.tts_engine;
            if (!ttsEngine && cfg.audio) ttsEngine = cfg.audio.active_engine;
            
            const virtualSoul = {
                persona: {
                    soul_file: cfg.ai?.active_personality,
                    use_global_direct_instructions: cfg.ai?.use_global_direct_instructions,
                    use_global_safety_instructions: cfg.ai?.use_global_safety_instructions,
                    custom_instructions: cfg.ai?.custom_instructions,
                    user_notes: cfg.ai?.user_notes,
                    send_notes_to_ai: cfg.ai?.send_notes_to_ai
                },
                model: {
                    backend_type: btype,
                    model_name: bdict.model
                },
                voice: {
                    tts_engine: ttsEngine,
                    tts_voice: cfg.ai?.tts_voice,
                    xtts_preset: cfg.ai?.xtts_preset || (cfg.audio?.xtts?.current_preset !== 'default' ? cfg.audio?.xtts?.current_preset : "") || "",
                    xtts_inference_preset: cfg.audio?.xtts?.current_inference_preset || "",
                    xtts_speaker_wav: cfg.audio?.xtts?.speaker_wav || "",
                    xtts_temperature: cfg.audio?.xtts?.temperature,
                    xtts_speed: cfg.audio?.xtts?.speed,
                    xtts_top_k: cfg.audio?.xtts?.top_k,
                    xtts_repetition_penalty: cfg.audio?.xtts?.repetition_penalty,
                    xtts_top_p: cfg.audio?.xtts?.top_p,
                    xtts_length_penalty: cfg.audio?.xtts?.length_penalty,
                    fish_preset: cfg.ai?.fish_preset || (cfg.audio?.fish_speech?.current_preset !== 'default' ? cfg.audio?.fish_speech?.current_preset : "") || "",
                    fish_inference_preset: cfg.audio?.fish_speech?.current_inference_preset || "",
                    fish_reference_audio: cfg.audio?.fish_speech?.reference_audio || "",
                    fish_reference_text: cfg.audio?.fish_speech?.reference_text || "",
                    fish_temperature: cfg.audio?.fish_speech?.temperature,
                    fish_top_p: cfg.audio?.fish_speech?.top_p,
                    fish_repetition_penalty: cfg.audio?.fish_speech?.repetition_penalty,
                    fish_chunk_length: cfg.audio?.fish_speech?.chunk_length,
                    fish_max_new_tokens: cfg.audio?.fish_speech?.max_new_tokens
                },
                inference: {
                    temperature: bdict.temperature,
                    top_p: bdict.top_p,
                    repeat_penalty: bdict.repeat_penalty,
                    num_predict: bdict.num_predict,
                    num_ctx: bdict.num_ctx || bdict.n_ctx,
                    n_gpu_layers: bdict.num_gpu || bdict.n_gpu_layers
                }
            };
            window.sfApplySoulToUI(virtualSoul);
        }
        
        window.sfState.isDirty = false;
        const btn = document.getElementById('sf-save-inline-btn');
        if (btn) btn.style.display = 'none';
        
    } catch(e) {}
};

window.sfActivateSoul = async function(soulId) {
    if (soulId === undefined || soulId === null) return;
    
    try {
        const res = await fetch('/api/souls/activate', {
            method: 'POST',
            headers: {'Content-Type':'application/json'},
            body: JSON.stringify({ soul_id: soulId, session_id: 'global' })
        });
        
        if (res.ok) {
            document.getElementById('sf-status-msg').textContent = soulId ? "Global Preset activated as system default." : "Global Preset cleared.";
            setTimeout(() => document.getElementById('sf-status-msg').textContent = "", 3000);
            
            // Reload the UI state to match the newly activated global
            await window.sfLoadGlobalState();
            
            // Also refresh the Chat Session topbar because the default fallbacks have changed!
            if (window.chatHistoryState && window.chatHistoryState.activeSessionId) {
                if (window.soActivateSoul) {
                    // Explicitly bind the current chat session to the newly activated global preset
                    // so that it immediately reflects the changes and clears stale overrides.
                    await window.soActivateSoul(soulId);
                } else if (window.loadSessionConfig) {
                    await window.loadSessionConfig(window.chatHistoryState.activeSessionId);
                }
            }
            
            // If the Chat Overrides panel is currently open, sync it to reflect the new system fallbacks
            const panel = document.getElementById('session-overrides-panel');
            if (panel && panel.classList.contains('open') && window.soLoadActiveSessionState) {
                window.soLoadActiveSessionState();
            }
        }
    } catch(e) {}
};



// Auto-load sidebar preset label on page load.
// sfUpdateFallbackLabels MUST run first so that window.sfSystemFallbacks is populated
// before sfLoadGlobalState → sfApplySoulToUI → sfDirty uses it to resolve the persona name.
document.addEventListener('DOMContentLoaded', async () => {
    if (window.sfUpdateFallbackLabels) await window.sfUpdateFallbackLabels();
    if (window.sfLoadGlobalState) window.sfLoadGlobalState();
});
