/* ⚡ SOUL FORGE: gp_fish.js */

window.sfSaveNewFishInferencePreset = function() {
    window.hecosPrompt("Enter the name for the new Fish Speech Inference Preset:", async function(name) {
        if (!name || !name.trim()) return;
        name = name.trim();
        
        const getNum = (id) => { const v = document.getElementById(id).value; return v ? parseFloat(v) : null; };
        const p = {
            temperature: getNum('sf-fish-temp'),
            top_p: getNum('sf-fish-topp'),
            repetition_penalty: getNum('sf-fish-reppen'),
            chunk_length: getNum('sf-fish-chunk-length') || 200,
            max_new_tokens: getNum('sf-fish-max-tokens') || 1024
        };
        
        if (!window.sfState.fishSpeechInferencePresets) window.sfState.fishSpeechInferencePresets = {};
        window.sfState.fishSpeechInferencePresets[name] = p;
        
        try {
            const res = await fetch('/api/audio/config', {
                method: 'POST',
                headers: {'Content-Type':'application/json'},
                body: JSON.stringify({ fish_speech_inference_presets: window.sfState.fishSpeechInferencePresets })
            });
            if (res.ok) {
                await window.sfLoadData();
                const sel = document.getElementById('sf-fish-inference-preset-select');
                if (sel) sel.value = name;
                if (window.showToast) window.showToast(`Fish Speech Inference Preset '${name}' saved!`, "success");
            }
        } catch(e) {}
    });
};

window.sfOverwriteFishInferencePreset = function() {
    const name = document.getElementById('sf-fish-inference-preset-select')?.value;
    if (!name) {
        if (window.showToast) window.showToast("No Fish Speech Inference Preset selected for overwrite.", "error");
        return;
    }
    
    window.hecosConfirm(`Do you really want to overwrite the Fish Speech Inference Preset "${name}"?`, async function() {
        const getNum = (id) => { const v = document.getElementById(id).value; return v ? parseFloat(v) : null; };
        const p = {
            temperature: getNum('sf-fish-temp'),
            top_p: getNum('sf-fish-topp'),
            repetition_penalty: getNum('sf-fish-reppen'),
            chunk_length: getNum('sf-fish-chunk-length') || 200,
            max_new_tokens: getNum('sf-fish-max-tokens') || 1024
        };
        
        if (!window.sfState.fishSpeechInferencePresets) window.sfState.fishSpeechInferencePresets = {};
        window.sfState.fishSpeechInferencePresets[name] = p;
        
        try {
            const res = await fetch('/api/audio/config', {
                method: 'POST',
                headers: {'Content-Type':'application/json'},
                body: JSON.stringify({ fish_speech_inference_presets: window.sfState.fishSpeechInferencePresets })
            });
            if (res.ok) {
                await window.sfLoadData();
                const sel = document.getElementById('sf-fish-inference-preset-select');
                if (sel) sel.value = name;
                if (window.showToast) window.showToast(`Fish Speech Inference Preset '${name}' updated!`, "success");
            }
        } catch(e) {}
    });
};

window.sfDeleteFishInferencePreset = function() {
    const name = document.getElementById('sf-fish-inference-preset-select')?.value;
    if (!name) {
        if (window.showToast) window.showToast("No Fish Speech Inference Preset selected to delete.", "error");
        return;
    }
    
    window.hecosConfirm(`Are you sure you want to delete the Fish Speech Inference Preset "${name}"?`, async function() {
        if (window.sfState.fishSpeechInferencePresets) {
            delete window.sfState.fishSpeechInferencePresets[name];
        }
        
        try {
            const res = await fetch('/api/audio/config', {
                method: 'POST',
                headers: {'Content-Type':'application/json'},
                body: JSON.stringify({ fish_speech_inference_presets: window.sfState.fishSpeechInferencePresets })
            });
            if (res.ok) {
                await window.sfLoadData();
                const sel = document.getElementById('sf-fish-inference-preset-select');
                if (sel) sel.value = "";
                if (window.showToast) window.showToast(`Fish Speech Inference Preset '${name}' deleted.`, "info");
            }
        } catch(e) {}
    });
};
