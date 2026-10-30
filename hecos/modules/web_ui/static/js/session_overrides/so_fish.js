/* ⚡ SESSION OVERRIDES: so_fish.js */

window.soSaveNewFishInferencePreset = function() {
    window.hecosPrompt("Enter the name for the new Fish Speech Inference Preset:", async function(name) {
        if (!name || !name.trim()) return;
        name = name.trim();
        
        const getNum = (id) => { const v = document.getElementById(id).value; return v ? parseFloat(v) : null; };
        const p = {
            temperature: getNum('so-fish-temp'),
            top_p: getNum('so-fish-topp'),
            repetition_penalty: getNum('so-fish-reppen'),
            chunk_length: getNum('so-fish-chunk-length') || 200,
            max_new_tokens: getNum('so-fish-max-tokens') || 1024
        };
        
        if (!window.soState.fishSpeechInferencePresets) window.soState.fishSpeechInferencePresets = {};
        window.soState.fishSpeechInferencePresets[name] = p;
        
        try {
            const res = await fetch('/api/audio/config', {
                method: 'POST',
                headers: {'Content-Type':'application/json'},
                body: JSON.stringify({ fish_speech_inference_presets: window.soState.fishSpeechInferencePresets })
            });
            if (res.ok) {
                await window.soLoadData();
                const sel = document.getElementById('so-fish-inference-preset-select');
                if (sel) sel.value = name;
                if (window.showToast) window.showToast(`Fish Speech Inference Preset '${name}' saved!`, "success");
            }
        } catch(e) {}
    });
};

window.soOverwriteFishInferencePreset = function() {
    const name = document.getElementById('so-fish-inference-preset-select')?.value;
    if (!name) {
        if (window.showToast) window.showToast("No Fish Speech Inference Preset selected for overwrite.", "error");
        return;
    }
    
    window.hecosConfirm(`Do you really want to overwrite the Fish Speech Inference Preset "${name}"?`, async function() {
        const getNum = (id) => { const v = document.getElementById(id).value; return v ? parseFloat(v) : null; };
        const p = {
            temperature: getNum('so-fish-temp'),
            top_p: getNum('so-fish-topp'),
            repetition_penalty: getNum('so-fish-reppen'),
            chunk_length: getNum('so-fish-chunk-length') || 200,
            max_new_tokens: getNum('so-fish-max-tokens') || 1024
        };
        
        if (!window.soState.fishSpeechInferencePresets) window.soState.fishSpeechInferencePresets = {};
        window.soState.fishSpeechInferencePresets[name] = p;
        
        try {
            const res = await fetch('/api/audio/config', {
                method: 'POST',
                headers: {'Content-Type':'application/json'},
                body: JSON.stringify({ fish_speech_inference_presets: window.soState.fishSpeechInferencePresets })
            });
            if (res.ok) {
                await window.soLoadData();
                const sel = document.getElementById('so-fish-inference-preset-select');
                if (sel) sel.value = name;
                if (window.showToast) window.showToast(`Fish Speech Inference Preset '${name}' updated!`, "success");
            }
        } catch(e) {}
    });
};

window.soDeleteFishInferencePreset = function() {
    const name = document.getElementById('so-fish-inference-preset-select')?.value;
    if (!name) {
        if (window.showToast) window.showToast("No Fish Speech Inference Preset selected to delete.", "error");
        return;
    }
    
    window.hecosConfirm(`Are you sure you want to delete the Fish Speech Inference Preset "${name}"?`, async function() {
        if (window.soState.fishSpeechInferencePresets) {
            delete window.soState.fishSpeechInferencePresets[name];
        }
        
        try {
            const res = await fetch('/api/audio/config', {
                method: 'POST',
                headers: {'Content-Type':'application/json'},
                body: JSON.stringify({ fish_speech_inference_presets: window.soState.fishSpeechInferencePresets })
            });
            if (res.ok) {
                await window.soLoadData();
                const sel = document.getElementById('so-fish-inference-preset-select');
                if (sel) sel.value = "";
                if (window.showToast) window.showToast(`Fish Speech Inference Preset '${name}' deleted.`, "info");
            }
        } catch(e) {}
    });
};
