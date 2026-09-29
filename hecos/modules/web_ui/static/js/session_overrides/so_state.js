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
        const res = await fetch(`/api/chat/session/config?session_id=${sessionId}`);
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
            const soulRes = await fetch(`/api/souls/${activeSoulId}`);
            const soulData = await soulRes.json();
            if (soulData.ok) {
                window.soApplySoulToUI(soulData.soul);
            }
        }
        
        window.soState.isDirty = false;
        document.getElementById('so-save-inline-btn').style.display = 'none';
        
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


