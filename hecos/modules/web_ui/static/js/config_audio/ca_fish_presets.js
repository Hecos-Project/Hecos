/**
 * Hecos WebUI - Fish Speech Presets & Voice Studio Logic
 * Handles saving, updating, loading and deleting Fish Speech configuration presets,
 * inference presets, expressiveness tags, scenario loading, and custom timbre recording/management.
 */

// ── Configuration Presets ───────────────────────────────────────────────────

window.saveFishPreset = function() {
    window.hecosPrompt("Fish Speech Preset Name (e.g. 'German Narrator', 'Soft Character'):", function(name) {
        if (!name || !name.trim()) return;
        name = name.trim();
        if (!audioConfig.fish_speech_presets) audioConfig.fish_speech_presets = {};

        const speakerWav = (document.getElementById('v-fish-speaker-wav')?.value || '').trim();
        const refId = (document.getElementById('v-fish-reference-id')?.value || '').trim();
        const refText = (document.getElementById('v-fish-reference-text')?.value || '').trim();
        const infPreset = (document.getElementById('v-fish-inference-preset')?.value || '').trim();

        audioConfig.fish_speech_presets[name] = {
            reference_audio: speakerWav,
            reference_id: refId,
            reference_text: refText,
            inference_preset: infPreset,
            temperature: parseFloat(document.getElementById('v-fish-temperature')?.value || 0.7),
            top_p: parseFloat(document.getElementById('v-fish-topp')?.value || 0.7),
            repetition_penalty: parseFloat(document.getElementById('v-fish-repetition')?.value || 1.2),
            chunk_length: parseInt(document.getElementById('v-fish-chunk-length')?.value || 200),
            max_new_tokens: parseInt(document.getElementById('v-fish-max-tokens')?.value || 1024),
            seed: parseInt(document.getElementById('v-fish-seed')?.value || 0),
            normalize: document.getElementById('v-fish-normalize')?.checked ?? true,
            use_memory_cache: document.getElementById('v-fish-memory-cache')?.checked ?? true,
            chunk_sentences: document.getElementById('v-fish-chunk')?.checked ?? true,
            volume: parseFloat(document.getElementById('v-fish-volume')?.value || 1.0)
        };

        if (!audioConfig.fish_speech) audioConfig.fish_speech = {};
        audioConfig.fish_speech.current_preset = name;
        audioConfig.fish_speech.current_inference_preset = infPreset;

        saveAudioConfig().then(() => {
            populateAudioUI();
            if (window.showToast) window.showToast(`Preset '${name}' saved successfully!`, "success");
        });
    });
};

window.updateFishPreset = function() {
    const name = document.getElementById('v-fish-preset')?.value;
    if (!name || name === 'default') {
        if (window.showToast) window.showToast("Select a custom preset to update first, or create a New one.", "error");
        return;
    }

    if (!audioConfig.fish_speech_presets) audioConfig.fish_speech_presets = {};

    const speakerWav = (document.getElementById('v-fish-speaker-wav')?.value || '').trim();
    const refId = (document.getElementById('v-fish-reference-id')?.value || '').trim();
    const refText = (document.getElementById('v-fish-reference-text')?.value || '').trim();
    const infPreset = (document.getElementById('v-fish-inference-preset')?.value || '').trim();

    audioConfig.fish_speech_presets[name] = {
        reference_audio: speakerWav,
        reference_id: refId,
        reference_text: refText,
        inference_preset: infPreset,
        temperature: parseFloat(document.getElementById('v-fish-temperature')?.value || 0.7),
        top_p: parseFloat(document.getElementById('v-fish-topp')?.value || 0.7),
        repetition_penalty: parseFloat(document.getElementById('v-fish-repetition')?.value || 1.2),
        chunk_length: parseInt(document.getElementById('v-fish-chunk-length')?.value || 200),
        max_new_tokens: parseInt(document.getElementById('v-fish-max-tokens')?.value || 1024),
        seed: parseInt(document.getElementById('v-fish-seed')?.value || 0),
        normalize: document.getElementById('v-fish-normalize')?.checked ?? true,
        use_memory_cache: document.getElementById('v-fish-memory-cache')?.checked ?? true,
        chunk_sentences: document.getElementById('v-fish-chunk')?.checked ?? true,
        volume: parseFloat(document.getElementById('v-fish-volume')?.value || 1.0)
    };

    if (!audioConfig.fish_speech) audioConfig.fish_speech = {};
    audioConfig.fish_speech.current_preset = name;
    audioConfig.fish_speech.current_inference_preset = infPreset;

    saveAudioConfig().then(() => {
        if (window.showToast) window.showToast(`Preset '${name}' updated!`, "success");
    });
};

window.resetFishConfig = function() {
    window.hecosConfirm("Reset all Fish Speech parameters to default values?", function() {
        const presetSelect = document.getElementById('v-fish-preset');
        if (presetSelect) presetSelect.value = 'default';
        loadFishPreset();
    });
};

window.loadFishPreset = function() {
    const name = document.getElementById('v-fish-preset')?.value;
    if (!name) return;

    if (name === 'default' || !audioConfig.fish_speech_presets || !audioConfig.fish_speech_presets[name]) {
        if (name === 'default') {
            if (document.getElementById('v-fish-speaker-wav')) document.getElementById('v-fish-speaker-wav').value = '';
            if (document.getElementById('v-fish-reference-id')) document.getElementById('v-fish-reference-id').value = '';
            if (document.getElementById('v-fish-clone-select')) document.getElementById('v-fish-clone-select').value = '';
            if (document.getElementById('v-fish-reference-text')) document.getElementById('v-fish-reference-text').value = '';
            if (document.getElementById('v-fish-inference-preset')) document.getElementById('v-fish-inference-preset').value = '';
            if (document.getElementById('v-fish-temperature')) document.getElementById('v-fish-temperature').value = 0.7;
            if (document.getElementById('v-fish-temperature-range')) document.getElementById('v-fish-temperature-range').value = 0.7;
            if (document.getElementById('v-fish-topp')) document.getElementById('v-fish-topp').value = 0.7;
            if (document.getElementById('v-fish-topp-range')) document.getElementById('v-fish-topp-range').value = 0.7;
            if (document.getElementById('v-fish-repetition')) document.getElementById('v-fish-repetition').value = 1.2;
            if (document.getElementById('v-fish-repetition-range')) document.getElementById('v-fish-repetition-range').value = 1.2;
            if (document.getElementById('v-fish-chunk-length')) document.getElementById('v-fish-chunk-length').value = 200;
            if (document.getElementById('v-fish-chunk-length-range')) document.getElementById('v-fish-chunk-length-range').value = 200;
            if (document.getElementById('v-fish-max-tokens')) document.getElementById('v-fish-max-tokens').value = 1024;
            if (document.getElementById('v-fish-max-tokens-range')) document.getElementById('v-fish-max-tokens-range').value = 1024;
            if (document.getElementById('v-fish-seed')) document.getElementById('v-fish-seed').value = 0;
            if (document.getElementById('v-fish-normalize')) document.getElementById('v-fish-normalize').checked = true;
            if (document.getElementById('v-fish-memory-cache')) document.getElementById('v-fish-memory-cache').checked = true;
            if (document.getElementById('v-fish-chunk')) document.getElementById('v-fish-chunk').checked = true;
            if (document.getElementById('v-fish-volume')) document.getElementById('v-fish-volume').value = 1.0;
            if (document.getElementById('v-fish-volume-range')) document.getElementById('v-fish-volume-range').value = 1.0;

            if (!audioConfig.fish_speech) audioConfig.fish_speech = {};
            audioConfig.fish_speech.current_preset = 'default';
            audioConfig.fish_speech.current_inference_preset = '';
            audioConfig.fish_speech.reference_audio = '';
            audioConfig.fish_speech.reference_id = '';
            audioConfig.fish_speech.reference_text = '';
            saveAudioConfig();
        }
        return;
    }

    const p = audioConfig.fish_speech_presets[name];
    const speakerWav = p.reference_audio || '';
    if (document.getElementById('v-fish-speaker-wav')) document.getElementById('v-fish-speaker-wav').value = speakerWav;
    if (document.getElementById('v-fish-reference-id')) document.getElementById('v-fish-reference-id').value = p.reference_id || '';
    if (document.getElementById('v-fish-reference-text')) document.getElementById('v-fish-reference-text').value = p.reference_text || '';

    if (document.getElementById('v-fish-temperature')) document.getElementById('v-fish-temperature').value = p.temperature ?? 0.7;
    if (document.getElementById('v-fish-temperature-range')) document.getElementById('v-fish-temperature-range').value = p.temperature ?? 0.7;
    if (document.getElementById('v-fish-topp')) document.getElementById('v-fish-topp').value = p.top_p ?? 0.7;
    if (document.getElementById('v-fish-topp-range')) document.getElementById('v-fish-topp-range').value = p.top_p ?? 0.7;
    if (document.getElementById('v-fish-repetition')) document.getElementById('v-fish-repetition').value = p.repetition_penalty ?? 1.2;
    if (document.getElementById('v-fish-repetition-range')) document.getElementById('v-fish-repetition-range').value = p.repetition_penalty ?? 1.2;
    if (document.getElementById('v-fish-chunk-length')) document.getElementById('v-fish-chunk-length').value = p.chunk_length ?? 200;
    if (document.getElementById('v-fish-chunk-length-range')) document.getElementById('v-fish-chunk-length-range').value = p.chunk_length ?? 200;
    if (document.getElementById('v-fish-max-tokens')) document.getElementById('v-fish-max-tokens').value = p.max_new_tokens ?? 1024;
    if (document.getElementById('v-fish-max-tokens-range')) document.getElementById('v-fish-max-tokens-range').value = p.max_new_tokens ?? 1024;
    if (document.getElementById('v-fish-seed')) document.getElementById('v-fish-seed').value = p.seed ?? 0;
    if (document.getElementById('v-fish-normalize')) document.getElementById('v-fish-normalize').checked = p.normalize ?? true;
    if (document.getElementById('v-fish-memory-cache')) document.getElementById('v-fish-memory-cache').checked = p.use_memory_cache ?? true;
    if (document.getElementById('v-fish-chunk')) document.getElementById('v-fish-chunk').checked = p.chunk_sentences ?? true;
    if (p.volume !== undefined) {
        if (document.getElementById('v-fish-volume')) document.getElementById('v-fish-volume').value = p.volume;
        if (document.getElementById('v-fish-volume-range')) document.getElementById('v-fish-volume-range').value = p.volume;
    }

    // Resolve associated inference preset
    let matchedInf = p.inference_preset || '';
    if (document.getElementById('v-fish-inference-preset')) {
        document.getElementById('v-fish-inference-preset').value = matchedInf;
    }

    // Match clone select dropdown if available
    const cloneSel = document.getElementById('v-fish-clone-select');
    if (cloneSel) {
        let matched = '';
        for (let i = 0; i < cloneSel.options.length; i++) {
            const val = cloneSel.options[i].value;
            if (val && (val === speakerWav || speakerWav.endsWith(val) || val.endsWith(speakerWav))) {
                matched = val;
                break;
            }
        }
        cloneSel.value = matched;
    }

    if (!audioConfig.fish_speech) audioConfig.fish_speech = {};
    audioConfig.fish_speech.current_preset = name;
    audioConfig.fish_speech.current_inference_preset = matchedInf;
    audioConfig.fish_speech.reference_audio = speakerWav;
    audioConfig.fish_speech.reference_id = p.reference_id || '';
    audioConfig.fish_speech.reference_text = p.reference_text || '';
    audioConfig.fish_speech.temperature = p.temperature ?? 0.7;
    audioConfig.fish_speech.top_p = p.top_p ?? 0.7;
    audioConfig.fish_speech.repetition_penalty = p.repetition_penalty ?? 1.2;
    audioConfig.fish_speech.chunk_length = p.chunk_length ?? 200;
    audioConfig.fish_speech.max_new_tokens = p.max_new_tokens ?? 1024;
    audioConfig.fish_speech.seed = p.seed ?? 0;
    audioConfig.fish_speech.normalize = p.normalize ?? true;
    audioConfig.fish_speech.use_memory_cache = p.use_memory_cache ?? true;
    audioConfig.fish_speech.chunk_sentences = p.chunk_sentences ?? true;

    saveAudioConfig();
};

window.deleteFishPreset = function() {
    const name = document.getElementById('v-fish-preset')?.value;
    if (!name || name === 'default') {
        if (window.showToast) window.showToast("Cannot delete the default preset.", "error");
        return;
    }

    window.hecosConfirm(`Are you sure you want to delete the preset '${name}'?`, function() {
        if (audioConfig.fish_speech_presets && audioConfig.fish_speech_presets[name]) {
            delete audioConfig.fish_speech_presets[name];
            if (!audioConfig.fish_speech) audioConfig.fish_speech = {};
            audioConfig.fish_speech.current_preset = 'default';
            saveAudioConfig().then(() => {
                populateAudioUI();
                if (window.showToast) window.showToast("Preset deleted.", "info");
            });
        }
    });
};

// ── Companion Transcript ────────────────────────────────────────────────────

window.saveFishVoiceTranscript = async function() {
    const wav = (document.getElementById('v-fish-speaker-wav')?.value || '').trim();
    const txt = (document.getElementById('v-fish-reference-text')?.value || '').trim();
    if (!wav) {
        if (window.showToast) window.showToast("Please select or specify a reference voice WAV first.", "warning");
        return;
    }

    try {
        if (window.showToast) window.showToast("Saving companion transcript...", "info");
        const r = await fetch('/api/audio/voice-clones/transcript', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ filename: wav, transcript: txt })
        });
        const res = await r.json();
        if (res.ok) {
            if (window.showToast) window.showToast("Transcript saved (.txt companion file)!", "success");
            if (typeof loadFishVoiceCloneList === 'function') await loadFishVoiceCloneList();
        } else {
            if (window.showToast) window.showToast("Error saving transcript: " + (res.error || "Unknown error"), "error");
        }
    } catch (e) {
        if (window.showToast) window.showToast("Failed to save transcript: " + e.message, "error");
    }
};

// ── Inference Presets ───────────────────────────────────────────────────────

window.saveFishInferencePreset = function() {
    window.hecosPrompt("Fish Speech Inference Preset Name (e.g. 'Fast & Direct', 'Creative & Wild'):", function(name) {
        if (!name || !name.trim()) return;
        name = name.trim();
        if (!audioConfig.fish_speech_inference_presets) audioConfig.fish_speech_inference_presets = {};

        audioConfig.fish_speech_inference_presets[name] = {
            temperature: parseFloat(document.getElementById('v-fish-temperature')?.value || 0.7),
            top_p: parseFloat(document.getElementById('v-fish-topp')?.value || 0.7),
            repetition_penalty: parseFloat(document.getElementById('v-fish-repetition')?.value || 1.2),
            chunk_length: parseInt(document.getElementById('v-fish-chunk-length')?.value || 200),
            max_new_tokens: parseInt(document.getElementById('v-fish-max-tokens')?.value || 1024),
            seed: parseInt(document.getElementById('v-fish-seed')?.value || 0),
            normalize: document.getElementById('v-fish-normalize')?.checked ?? true,
            use_memory_cache: document.getElementById('v-fish-memory-cache')?.checked ?? true
        };

        saveAudioConfig().then(() => {
            populateAudioUI();
            if (document.getElementById('v-fish-inference-preset')) {
                document.getElementById('v-fish-inference-preset').value = name;
            }
            if (window.showToast) window.showToast(`Inference Preset '${name}' saved!`, "success");
        });
    });
};

window.updateFishInferencePreset = function() {
    const name = document.getElementById('v-fish-inference-preset')?.value;
    if (!name) {
        if (window.showToast) window.showToast("Select an Inference Preset first.", "error");
        return;
    }

    if (!audioConfig.fish_speech_inference_presets) audioConfig.fish_speech_inference_presets = {};

    audioConfig.fish_speech_inference_presets[name] = {
        temperature: parseFloat(document.getElementById('v-fish-temperature')?.value || 0.7),
        top_p: parseFloat(document.getElementById('v-fish-topp')?.value || 0.7),
        repetition_penalty: parseFloat(document.getElementById('v-fish-repetition')?.value || 1.2),
        chunk_length: parseInt(document.getElementById('v-fish-chunk-length')?.value || 200),
        max_new_tokens: parseInt(document.getElementById('v-fish-max-tokens')?.value || 1024),
        seed: parseInt(document.getElementById('v-fish-seed')?.value || 0),
        normalize: document.getElementById('v-fish-normalize')?.checked ?? true,
        use_memory_cache: document.getElementById('v-fish-memory-cache')?.checked ?? true
    };

    saveAudioConfig().then(() => {
        if (window.showToast) window.showToast(`Inference Preset '${name}' updated!`, "success");
    });
};

window.deleteFishInferencePreset = function() {
    const name = document.getElementById('v-fish-inference-preset')?.value;
    if (!name) {
        if (window.showToast) window.showToast("No preset selected.", "error");
        return;
    }

    window.hecosConfirm(`Do you want to delete the Inference Preset '${name}'?`, function() {
        if (audioConfig.fish_speech_inference_presets && audioConfig.fish_speech_inference_presets[name]) {
            delete audioConfig.fish_speech_inference_presets[name];
            saveAudioConfig().then(() => {
                populateAudioUI();
                if (window.showToast) window.showToast(`Preset '${name}' deleted.`, "info");
            });
        }
    });
};

window.loadFishInferencePreset = function() {
    const name = document.getElementById('v-fish-inference-preset')?.value;
    if (!name || !audioConfig.fish_speech_inference_presets || !audioConfig.fish_speech_inference_presets[name]) return;

    const p = audioConfig.fish_speech_inference_presets[name];
    if (document.getElementById('v-fish-temperature')) document.getElementById('v-fish-temperature').value = p.temperature ?? 0.7;
    if (document.getElementById('v-fish-temperature-range')) document.getElementById('v-fish-temperature-range').value = p.temperature ?? 0.7;
    if (document.getElementById('v-fish-topp')) document.getElementById('v-fish-topp').value = p.top_p ?? 0.7;
    if (document.getElementById('v-fish-topp-range')) document.getElementById('v-fish-topp-range').value = p.top_p ?? 0.7;
    if (document.getElementById('v-fish-repetition')) document.getElementById('v-fish-repetition').value = p.repetition_penalty ?? 1.2;
    if (document.getElementById('v-fish-repetition-range')) document.getElementById('v-fish-repetition-range').value = p.repetition_penalty ?? 1.2;
    if (document.getElementById('v-fish-chunk-length')) document.getElementById('v-fish-chunk-length').value = p.chunk_length ?? 200;
    if (document.getElementById('v-fish-chunk-length-range')) document.getElementById('v-fish-chunk-length-range').value = p.chunk_length ?? 200;
    if (document.getElementById('v-fish-max-tokens')) document.getElementById('v-fish-max-tokens').value = p.max_new_tokens ?? 1024;
    if (document.getElementById('v-fish-max-tokens-range')) document.getElementById('v-fish-max-tokens-range').value = p.max_new_tokens ?? 1024;
    if (document.getElementById('v-fish-seed')) document.getElementById('v-fish-seed').value = p.seed ?? 0;
    if (document.getElementById('v-fish-normalize')) document.getElementById('v-fish-normalize').checked = p.normalize ?? true;
    if (document.getElementById('v-fish-memory-cache')) document.getElementById('v-fish-memory-cache').checked = p.use_memory_cache ?? true;
    if (p.volume !== undefined) {
        if (document.getElementById('v-fish-volume')) document.getElementById('v-fish-volume').value = p.volume;
        if (document.getElementById('v-fish-volume-range')) document.getElementById('v-fish-volume-range').value = p.volume;
    }

    document.getElementById('v-fish-temperature')?.dispatchEvent(new Event('input'));
    document.getElementById('v-fish-topp')?.dispatchEvent(new Event('input'));
    document.getElementById('v-fish-repetition')?.dispatchEvent(new Event('input'));
    document.getElementById('v-fish-chunk-length')?.dispatchEvent(new Event('input'));
    document.getElementById('v-fish-max-tokens')?.dispatchEvent(new Event('input'));
};

// ── Expressive Emotion Tags & Test Scenarios ────────────────────────────────

window.insertFishEmotionTag = function(tag) {
    const input = document.getElementById('v-fish-test-text');
    if (!input) return;

    const tagStr = `[${tag}] `;
    const start = input.selectionStart ?? input.value.length;
    const end = input.selectionEnd ?? input.value.length;
    const val = input.value;

    input.value = val.substring(0, start) + tagStr + val.substring(end);
    input.focus();
    input.selectionStart = input.selectionEnd = start + tagStr.length;

    if (window.showToast) {
        window.showToast(`Expressive directive [${tag}] inserted!`, "info");
    }
};

window.insertFishProsodyMark = function(mark) {
    const input = document.getElementById('v-fish-test-text');
    if (!input) return;

    const str = `${mark} `;
    const start = input.selectionStart ?? input.value.length;
    const end = input.selectionEnd ?? input.value.length;
    const val = input.value;

    input.value = val.substring(0, start) + str + val.substring(end);
    input.focus();
    input.selectionStart = input.selectionEnd = start + str.length;
};

window.loadFishTestScenario = function(key) {
    const input = document.getElementById('v-fish-test-text');
    if (!input || !key) return;

    const scenarios = {
        laugh: "[laughing] You won't believe what happened today... haha, I was about to cause an absolute disaster! I still can't believe it!",
        whisper: "[whisper] Come closer, don't let anyone overhear us... I just discovered the core system secrets. Shh, stay quiet...",
        excited: "[excited] This is incredible news! Absolutely fantastic, I can't wait to share all of this progress with you!",
        dramatic: "[dramatic] Complete silence suddenly fell over the room... Every single decision made right now will change our future forever.",
        calm: "[calm] All Hecos neural modules are operating smoothly and reliably. The voice synthesis pipeline responds with high fidelity.",
        surprised: "[surprised] Are you serious?! I can't believe it! I never expected we could achieve this kind of quality so quickly!"
    };

    if (scenarios[key]) {
        input.value = scenarios[key];
        if (window.showToast) window.showToast("Test scenario loaded with S2-Pro expressive tag!", "info");
    }
};


// Note: Timbre Recording & Voice Clone Management moved to ca_fish_recorder.js
// Note: Server Lifecycle & Model Management moved to ca_fish_server.js

