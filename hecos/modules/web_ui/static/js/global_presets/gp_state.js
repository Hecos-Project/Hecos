/* ⚡ SOUL FORGE: gp_state.js */

/* ⚡ SOUL FORGE: Global Presets JS Logic */

window.sfState = {
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
        }
        
        window.sfState.isDirty = false;
        const btn = document.getElementById('sf-save-inline-btn');
        if (btn) btn.style.display = 'none';
        
    } catch(e) {}
};

window.sfActivateSoul = async function(soulId) {
    if (!soulId) return;
    
    try {
        const res = await fetch('/api/souls/activate', {
            method: 'POST',
            headers: {'Content-Type':'application/json'},
            body: JSON.stringify({ soul_id: soulId, session_id: 'global' })
        });
        
        if (res.ok) {
            document.getElementById('sf-status-msg').textContent = "Global Preset activated as system default.";
            setTimeout(() => document.getElementById('sf-status-msg').textContent = "", 3000);
            
            // Reload the UI state to match the newly activated global
            await window.sfLoadGlobalState();
        }
    } catch(e) {}
};



// Auto-load sidebar preset label on page load
document.addEventListener('DOMContentLoaded', () => {
    if (window.sfLoadGlobalState) window.sfLoadGlobalState();
});
