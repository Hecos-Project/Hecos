/* ⚡ SOUL FORGE: gp_state.js */

/* ⚡ SOUL FORGE: Global Presets JS Logic */

window.soState = {
    souls: [],
    inferencePresets: {},
    activeSoulId: null,
    isDirty: false
};

// Custom Hecos Modals for Chat UI
window.hecosConfirm = function(msg, onYes) {
    const modal = document.getElementById('hecos-confirm-modal');
    const textEl = document.getElementById('hecos-confirm-modal-text');
    const yesBtn = document.getElementById('hecos-confirm-modal-yes');
    
    if (modal && textEl && yesBtn) {
        textEl.textContent = msg;
        modal.style.display = 'flex';
        yesBtn.onclick = function() {
            modal.style.display = 'none';
            onYes();
        };
    } else {
        if (confirm(msg)) onYes();
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

window.soLoadData = async function() {
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
        
        if (soulsData.ok) window.soState.souls = soulsData.souls;
        if (infData.ok) window.soState.inferencePresets = infData.presets;
        if (audioConfData.ok) {
            window.soState.xttsPresets = audioConfData.config.xtts_presets || {};
            window.soState.xttsInferencePresets = audioConfData.config.xtts_inference_presets || {};
        }
        
        // Populate select lists
        window.soPopulateDropdowns(optData);
        
        // Get active soul from session_config_db
        await window.soLoadActiveSessionState();
        
    } catch(e) { console.error("GlobalPresets Load Error", e); }
};


window.soLoadActiveSessionState = async function() {
    const sessionId = window.chatHistoryState?.activeSessionId;
    if (!sessionId) return;
    
    try {
        // Read directly from session_config endpoint
        const res = await fetch(`/api/chat/session/config?session_id=${sessionId}`, { cache: 'no-store' });
        const data = await res.json();
        
        let activeSoulId = null;
        if (data.ok && data.config) {
            activeSoulId = data.config.active_global_preset || null;
        }
        
        window.soState.activeSoulId = activeSoulId;
        document.getElementById('so-active-soul-select').value = activeSoulId || "";
        const quickSel = document.getElementById('so-quick-preset-select');
        if (quickSel) quickSel.value = activeSoulId || "";
        
        if (activeSoulId) {
            // Load the full soul profile data into the UI
            const soulRes = await fetch(`/api/souls/${activeSoulId}`, { cache: 'no-store' });
            const soulData = await soulRes.json();
            if (soulData.ok) {
                await window.soApplySoulToUI(soulData.soul);
            }
        } else {
            await window.soApplySoulToUI(null);
        }
        
        // Apply individual overrides from session config
        if (data.ok && data.config) {
            const cfg = data.config;
            if (cfg.ai?.active_personality) document.getElementById('so-persona-select').value = cfg.ai.active_personality;
            if (cfg.backend?.type) {
                document.getElementById('so-backend-select').value = cfg.backend.type;
                window.soUpdateModelsDropdown();
                const bType = cfg.backend.type;
                if (cfg.backend[bType]?.model) {
                    document.getElementById('so-model-select').value = cfg.backend[bType].model;
                }
            }
            if (cfg.ai?.tts_engine) {
                document.getElementById('so-tts-engine-select').value = cfg.ai.tts_engine;
                await window.soUpdateVoicesDropdown();
            }
            if (cfg.ai?.tts_voice) {
                document.getElementById('so-tts-voice-select').value = cfg.ai.tts_voice;
            }
            
            if (cfg.inference?.preset_name) document.getElementById('so-inference-preset-select').value = cfg.inference.preset_name;
            const setVal = (id, val) => {
                if (val !== undefined && val !== null) {
                    const el = document.getElementById(id);
                    if (el) { el.value = val; window.soUpdateSliderVal(el, id.replace('so-', 'so-val-')); }
                }
            };
            if (cfg.inference) {
                setVal('so-temp', cfg.inference.temperature);
                setVal('so-topp', cfg.inference.top_p);
                setVal('so-reppen', cfg.inference.repeat_penalty);
                setVal('so-predict', cfg.inference.num_predict);
            }
            if (cfg.voice?.xtts_preset) document.getElementById('so-xtts-preset-select').value = cfg.voice.xtts_preset;
            if (cfg.voice?.xtts_inference_preset) document.getElementById('so-xtts-inference-preset-select').value = cfg.voice.xtts_inference_preset;
            if (cfg.voice?.xtts_speaker_wav) document.getElementById('so-xtts-speaker-wav').value = cfg.voice.xtts_speaker_wav;
            if (cfg.voice) {
                setVal('so-xtts-temp', cfg.voice.xtts_temperature);
                setVal('so-xtts-speed', cfg.voice.xtts_speed);
                setVal('so-xtts-topk', cfg.voice.xtts_top_k);
                setVal('so-xtts-reppen', cfg.voice.xtts_repetition_penalty);
                setVal('so-xtts-topp', cfg.voice.xtts_top_p);
                setVal('so-xtts-length-penalty', cfg.voice.xtts_length_penalty);
            }
        }
        
        window.soState.isDirty = false;
        const inlineBtn = document.getElementById('so-save-inline-btn');
        if (inlineBtn) inlineBtn.style.display = 'none';
        
    } catch(e) {}
};


window.soActivateSoul = async function(soulId) {
    const sessionId = window.chatHistoryState?.activeSessionId;
    if (!sessionId || !soulId) return;
    
    try {
        const res = await fetch('/api/souls/activate', {
            method: 'POST',
            headers: {'Content-Type':'application/json'},
            body: JSON.stringify({ soul_id: soulId, session_id: sessionId })
        });
        
        if (res.ok) {
            document.getElementById('so-status-msg').textContent = "Global Preset activated.";
            setTimeout(() => document.getElementById('so-status-msg').textContent = "", 3000);
            
            // Reload the topbar UI dropdowns so they reflect the new active persona/model
            if (window.loadSessionConfig) {
                await window.loadSessionConfig(sessionId);
            }
            
            await window.soLoadActiveSessionState();
        }
    } catch(e) {}
};

// Auto-load data on page load so the topbar dropdowns are populated
document.addEventListener('DOMContentLoaded', () => {
    if (window.soLoadData) window.soLoadData();
});
