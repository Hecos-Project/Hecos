window.saveXTTSPreset = function() {
    window.hecosPrompt("Preset name (e.g. 'Fast voice', 'Cloned voice'):", function(name) {
        if (!audioConfig.xtts_presets) audioConfig.xtts_presets = {};
        
        audioConfig.xtts_presets[name] = {
            speed: parseFloat(document.getElementById('v-xtts-speed')?.value || 1.0),
            language: document.getElementById('v-xtts-lang')?.value || 'it',
            speaker: document.getElementById('v-xtts-speaker')?.value || 'Claribel Dervla',
            gpu_acceleration: document.getElementById('v-xtts-gpu')?.value || 'auto',
            chunk_sentences: document.getElementById('v-xtts-chunk')?.checked ?? true,
            speaker_wav: document.getElementById('v-xtts-speaker-wav')?.value || '',
            temperature: parseFloat(document.getElementById('v-xtts-temperature')?.value || 0.75),
            repetition_penalty: parseFloat(document.getElementById('v-xtts-repetition_penalty')?.value || 5.0)
        };
        
        if (!audioConfig.xtts) audioConfig.xtts = {};
        audioConfig.xtts.current_preset = name;
        
        saveAudioConfig().then(() => {
            populateAudioUI();
            if (window.showToast) window.showToast("Preset saved successfully!", "success");
        });
    });
};

window.updateXTTSPreset = function() {
    const name = document.getElementById('v-xtts-preset')?.value;
    if (!name || name === 'default') {
        if (window.showToast) window.showToast("Select a custom preset to update first.", "error");
        return;
    }
    
    if (!audioConfig.xtts_presets) audioConfig.xtts_presets = {};
    
    audioConfig.xtts_presets[name] = {
        speed: parseFloat(document.getElementById('v-xtts-speed')?.value || 1.0),
        language: document.getElementById('v-xtts-lang')?.value || 'it',
        speaker: document.getElementById('v-xtts-speaker')?.value || 'Claribel Dervla',
        gpu_acceleration: document.getElementById('v-xtts-gpu')?.value || 'auto',
        chunk_sentences: document.getElementById('v-xtts-chunk')?.checked ?? true,
        speaker_wav: document.getElementById('v-xtts-speaker-wav')?.value || '',
        temperature: parseFloat(document.getElementById('v-xtts-temperature')?.value || 0.75),
        repetition_penalty: parseFloat(document.getElementById('v-xtts-repetition_penalty')?.value || 5.0),
        top_k: parseInt(document.getElementById('v-xtts-topk')?.value || 50),
        top_p: parseFloat(document.getElementById('v-xtts-topp')?.value || 0.85),
        length_penalty: parseFloat(document.getElementById('v-xtts-length-penalty')?.value || 1.0)
    };
    
    if (!audioConfig.xtts) audioConfig.xtts = {};
    audioConfig.xtts.current_preset = name;
    
    saveAudioConfig().then(() => {
        if (window.showToast) window.showToast("Preset configuration updated!", "success");
    });
};

window.resetXTTSConfig = function() {
    window.hecosConfirm("Reset all XTTS parameters to their default values?", function() {
        const presetSelect = document.getElementById('v-xtts-preset');
        if (presetSelect) presetSelect.value = 'default';
        loadXTTSPreset();
    });
};

window.loadXTTSPreset = function() {
    const name = document.getElementById('v-xtts-preset')?.value;
    if (!name) {
        if (document.getElementById('v-xtts-speaker-wav')) document.getElementById('v-xtts-speaker-wav').value = '';
        if (document.getElementById('v-xtts-clone-select')) document.getElementById('v-xtts-clone-select').value = '';
        return;
    }

    if (name === 'default' || !audioConfig.xtts_presets || !audioConfig.xtts_presets[name]) {
        if (name === 'default') {
            if (document.getElementById('v-xtts-speed')) document.getElementById('v-xtts-speed').value = 1.0;
            if (document.getElementById('v-xtts-temperature')) document.getElementById('v-xtts-temperature').value = 0.75;
            if (document.getElementById('v-xtts-repetition_penalty')) document.getElementById('v-xtts-repetition_penalty').value = 5.0;
            if (document.getElementById('v-xtts-topk')) document.getElementById('v-xtts-topk').value = 50;
            if (document.getElementById('v-xtts-topp')) document.getElementById('v-xtts-topp').value = 0.85;
            if (document.getElementById('v-xtts-length-penalty')) document.getElementById('v-xtts-length-penalty').value = 1.0;
            if (document.getElementById('v-xtts-speaker')) document.getElementById('v-xtts-speaker').value = 'Claribel Dervla';
            if (document.getElementById('v-xtts-speaker-wav')) document.getElementById('v-xtts-speaker-wav').value = '';
            if (document.getElementById('v-xtts-clone-select')) document.getElementById('v-xtts-clone-select').value = '';
            if (document.getElementById('v-xtts-inference-preset')) document.getElementById('v-xtts-inference-preset').value = '';
            
            document.getElementById('v-xtts-speed')?.dispatchEvent(new Event('input'));
            document.getElementById('v-xtts-temperature')?.dispatchEvent(new Event('input'));
            document.getElementById('v-xtts-repetition_penalty')?.dispatchEvent(new Event('input'));
            document.getElementById('v-xtts-topk')?.dispatchEvent(new Event('input'));
            document.getElementById('v-xtts-topp')?.dispatchEvent(new Event('input'));
            document.getElementById('v-xtts-length-penalty')?.dispatchEvent(new Event('input'));
            
            audioConfig.xtts.current_preset = 'default';
            saveAudioConfig();
        }
        return;
    }
    
    const p = audioConfig.xtts_presets[name];
    if (document.getElementById('v-xtts-speed')) document.getElementById('v-xtts-speed').value = p.speed || 1.0;
    if (document.getElementById('v-xtts-lang')) document.getElementById('v-xtts-lang').value = p.language || 'it';
    if (document.getElementById('v-xtts-speaker')) document.getElementById('v-xtts-speaker').value = p.speaker || 'Claribel Dervla';
    if (document.getElementById('v-xtts-gpu')) document.getElementById('v-xtts-gpu').value = p.gpu_acceleration || 'auto';
    if (document.getElementById('v-xtts-chunk')) document.getElementById('v-xtts-chunk').checked = p.chunk_sentences ?? true;
    
    const speakerWav = p.speaker_wav || '';
    if (document.getElementById('v-xtts-speaker-wav')) document.getElementById('v-xtts-speaker-wav').value = speakerWav;
    if (document.getElementById('v-xtts-clone-select')) {
        const cloneSel = document.getElementById('v-xtts-clone-select');
        let matchedClone = '';
        for (let i = 0; i < cloneSel.options.length; i++) {
            if (cloneSel.options[i].value === speakerWav) {
                matchedClone = speakerWav;
                break;
            }
        }
        cloneSel.value = matchedClone;
    }

    if (document.getElementById('v-xtts-temperature')) document.getElementById('v-xtts-temperature').value = p.temperature || 0.75;
    if (document.getElementById('v-xtts-repetition_penalty')) document.getElementById('v-xtts-repetition_penalty').value = p.repetition_penalty || 5.0;
    if (document.getElementById('v-xtts-topk')) document.getElementById('v-xtts-topk').value = p.top_k || 50;
    if (document.getElementById('v-xtts-topp')) document.getElementById('v-xtts-topp').value = p.top_p || 0.85;
    if (document.getElementById('v-xtts-length-penalty')) document.getElementById('v-xtts-length-penalty').value = p.length_penalty || 1.0;
    
    let matchedInf = "";
    if (audioConfig.xtts_inference_presets) {
        for (const [k, inf] of Object.entries(audioConfig.xtts_inference_presets)) {
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
    if (document.getElementById('v-xtts-inference-preset')) {
        document.getElementById('v-xtts-inference-preset').value = matchedInf;
    }

    document.getElementById('v-xtts-speed')?.dispatchEvent(new Event('input'));
    document.getElementById('v-xtts-temperature')?.dispatchEvent(new Event('input'));
    document.getElementById('v-xtts-repetition_penalty')?.dispatchEvent(new Event('input'));
    document.getElementById('v-xtts-topk')?.dispatchEvent(new Event('input'));
    document.getElementById('v-xtts-topp')?.dispatchEvent(new Event('input'));
    document.getElementById('v-xtts-length-penalty')?.dispatchEvent(new Event('input'));
    
    audioConfig.xtts.current_preset = name;
    saveAudioConfig();
};

window.deleteXTTSPreset = function() {
    const name = document.getElementById('v-xtts-preset').value;
    if (name === 'default') {
        if (window.showToast) window.showToast("Cannot delete the default preset.", "error");
        return;
    }
    
    window.hecosConfirm(`Are you sure you want to delete the preset '${name}'?`, function() {
        if (audioConfig.xtts_presets && audioConfig.xtts_presets[name]) {
            delete audioConfig.xtts_presets[name];
            audioConfig.xtts.current_preset = 'default';
            saveAudioConfig().then(() => {
                populateAudioUI();
                if (window.showToast) window.showToast("Preset deleted.", "info");
            });
        }
    });
};

