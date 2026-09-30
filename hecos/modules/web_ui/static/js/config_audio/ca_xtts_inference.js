window.saveXTTSInferencePreset = function() {
    window.hecosPrompt("Inference Preset Name (e.g., 'Fast', 'Expressive'):", function(name) {
        if (!audioConfig.xtts_inference_presets) audioConfig.xtts_inference_presets = {};
        
        audioConfig.xtts_inference_presets[name] = {
            speed: parseFloat(document.getElementById('v-xtts-speed')?.value || 1.0),
            temperature: parseFloat(document.getElementById('v-xtts-temperature')?.value || 0.75),
            repetition_penalty: parseFloat(document.getElementById('v-xtts-repetition_penalty')?.value || 5.0),
            top_k: parseInt(document.getElementById('v-xtts-topk')?.value || 50),
            top_p: parseFloat(document.getElementById('v-xtts-topp')?.value || 0.85),
            length_penalty: parseFloat(document.getElementById('v-xtts-length-penalty')?.value || 1.0)
        };
        
        saveAudioConfig().then(() => {
            populateAudioUI();
            if (document.getElementById('v-xtts-inference-preset')) {
                document.getElementById('v-xtts-inference-preset').value = name;
            }
            if (window.showToast) window.showToast("Inference Preset saved!", "success");
        });
    });
};

window.updateXTTSInferencePreset = function() {
    const name = document.getElementById('v-xtts-inference-preset')?.value;
    if (!name) {
        if (window.showToast) window.showToast("Select an Inference Preset first.", "error");
        return;
    }
    
    if (!audioConfig.xtts_inference_presets) audioConfig.xtts_inference_presets = {};
    
    audioConfig.xtts_inference_presets[name] = {
        speed: parseFloat(document.getElementById('v-xtts-speed')?.value || 1.0),
        temperature: parseFloat(document.getElementById('v-xtts-temperature')?.value || 0.75),
        repetition_penalty: parseFloat(document.getElementById('v-xtts-repetition_penalty')?.value || 5.0),
        top_k: parseInt(document.getElementById('v-xtts-topk')?.value || 50),
        top_p: parseFloat(document.getElementById('v-xtts-topp')?.value || 0.85),
        length_penalty: parseFloat(document.getElementById('v-xtts-length-penalty')?.value || 1.0)
    };
    
    saveAudioConfig().then(() => {
        if (window.showToast) window.showToast("Inference Preset updated!", "success");
    });
};

window.deleteXTTSInferencePreset = function() {
    const name = document.getElementById('v-xtts-inference-preset')?.value;
    if (!name) {
        if (window.showToast) window.showToast("No preset selected.", "error");
        return;
    }
    
    window.hecosConfirm(`Do you want to delete the Inference Preset '${name}'?`, function() {
        if (audioConfig.xtts_inference_presets && audioConfig.xtts_inference_presets[name]) {
            delete audioConfig.xtts_inference_presets[name];
            saveAudioConfig().then(() => {
                populateAudioUI();
                if (window.showToast) window.showToast("Preset deleted.", "info");
            });
        }
    });
};

window.loadXTTSInferencePreset = function() {
    const name = document.getElementById('v-xtts-inference-preset')?.value;
    if (!name || !audioConfig.xtts_inference_presets || !audioConfig.xtts_inference_presets[name]) return;
    
    const p = audioConfig.xtts_inference_presets[name];
    if (document.getElementById('v-xtts-speed')) document.getElementById('v-xtts-speed').value = p.speed || 1.0;
    if (document.getElementById('v-xtts-temperature')) document.getElementById('v-xtts-temperature').value = p.temperature || 0.75;
    if (document.getElementById('v-xtts-repetition_penalty')) document.getElementById('v-xtts-repetition_penalty').value = p.repetition_penalty || 5.0;
    if (document.getElementById('v-xtts-topk')) document.getElementById('v-xtts-topk').value = p.top_k || 50;
    if (document.getElementById('v-xtts-topp')) document.getElementById('v-xtts-topp').value = p.top_p || 0.85;
    if (document.getElementById('v-xtts-length-penalty')) document.getElementById('v-xtts-length-penalty').value = p.length_penalty || 1.0;
    
    document.getElementById('v-xtts-speed')?.dispatchEvent(new Event('input'));
    document.getElementById('v-xtts-temperature')?.dispatchEvent(new Event('input'));
    document.getElementById('v-xtts-repetition_penalty')?.dispatchEvent(new Event('input'));
    document.getElementById('v-xtts-topk')?.dispatchEvent(new Event('input'));
    document.getElementById('v-xtts-topp')?.dispatchEvent(new Event('input'));
    document.getElementById('v-xtts-length-penalty')?.dispatchEvent(new Event('input'));
};
