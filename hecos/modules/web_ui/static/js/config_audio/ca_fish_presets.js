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

// ── Timbre Studio: Browser Microphone Recording & Deletion ──────────────────

let _fishRecordStream = null;
let _fishMediaRecorder = null;
let _fishAudioChunks = [];
let _fishRecordTimer = null;
let _fishRecordStartTime = 0;
let _fishRecordedBlob = null;

window.openFishRecordTimbreModal = function() {
    const modal = document.getElementById('modal-fish-record-timbre');
    if (!modal) return;
    modal.style.display = 'flex';
    document.getElementById('fish-rec-name').value = '';
    document.getElementById('fish-rec-transcript').value = '';
    document.getElementById('fish-rec-timer').textContent = '00:00';
    document.getElementById('fish-rec-audio').style.display = 'none';
    document.getElementById('fish-rec-save-btn').disabled = true;
    const btn = document.getElementById('fish-rec-btn');
    btn.innerHTML = '<i class="fas fa-circle" style="color:var(--danger, #ff4d4f);"></i> Start Recording';
    btn.className = 'btn btn-secondary';
};

window.closeFishRecordTimbreModal = function() {
    const modal = document.getElementById('modal-fish-record-timbre');
    if (modal) modal.style.display = 'none';
    if (_fishMediaRecorder && _fishMediaRecorder.state === 'recording') {
        _fishMediaRecorder.stop();
    }
    if (_fishRecordStream) {
        _fishRecordStream.getTracks().forEach(t => t.stop());
        _fishRecordStream = null;
    }
    if (_fishRecordTimer) {
        clearInterval(_fishRecordTimer);
        _fishRecordTimer = null;
    }
};

window.toggleFishTimbreRecording = async function() {
    const btn = document.getElementById('fish-rec-btn');
    const timerEl = document.getElementById('fish-rec-timer');

    if (_fishMediaRecorder && _fishMediaRecorder.state === 'recording') {
        // Stop recording
        _fishMediaRecorder.stop();
        if (_fishRecordTimer) clearInterval(_fishRecordTimer);
        btn.innerHTML = '<i class="fas fa-redo"></i> Record Again';
        btn.className = 'btn btn-secondary';
        return;
    }

    // Start recording
    try {
        _fishRecordStream = await navigator.mediaDevices.getUserMedia({ audio: true });
        _fishAudioChunks = [];
        _fishRecordedBlob = null;

        const mimeType = MediaRecorder.isTypeSupported('audio/webm') ? 'audio/webm' : '';
        _fishMediaRecorder = mimeType ? new MediaRecorder(_fishRecordStream, { mimeType }) : new MediaRecorder(_fishRecordStream);

        _fishMediaRecorder.ondataavailable = e => {
            if (e.data.size > 0) _fishAudioChunks.push(e.data);
        };

        _fishMediaRecorder.onstop = async () => {
            const rawBlob = new Blob(_fishAudioChunks, { type: _fishMediaRecorder.mimeType || 'audio/webm' });
            
            // Convert to clean standard 16-bit WAV using browser OfflineAudioContext
            try {
                const arrayBuffer = await rawBlob.arrayBuffer();
                const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
                const decodedBuffer = await audioCtx.decodeAudioData(arrayBuffer);
                
                if (typeof window._audioBufferToWav === 'function') {
                    _fishRecordedBlob = await window._audioBufferToWav(decodedBuffer);
                } else {
                    _fishRecordedBlob = rawBlob;
                }
            } catch (err) {
                console.warn('[FishTimbre] Fallback to raw blob:', err);
                _fishRecordedBlob = rawBlob;
            }

            const audioEl = document.getElementById('fish-rec-audio');
            if (audioEl && _fishRecordedBlob) {
                audioEl.src = URL.createObjectURL(_fishRecordedBlob);
                audioEl.style.display = 'block';
            }
            const saveBtn = document.getElementById('fish-rec-save-btn');
            if (saveBtn) saveBtn.disabled = false;
        };

        _fishMediaRecorder.start();
        _fishRecordStartTime = Date.now();
        btn.innerHTML = '<i class="fas fa-stop"></i> Stop Recording';
        btn.className = 'btn btn-danger';

        _fishRecordTimer = setInterval(() => {
            const elapsed = Math.floor((Date.now() - _fishRecordStartTime) / 1000);
            const m = String(Math.floor(elapsed / 60)).padStart(2, '0');
            const s = String(elapsed % 60).padStart(2, '0');
            if (timerEl) timerEl.textContent = `${m}:${s}`;
        }, 200);

    } catch (e) {
        if (window.showToast) window.showToast("Microphone access denied: " + e.message, "error");
        else alert("Microphone access denied: " + e.message);
    }
};

window.saveFishRecordedTimbre = async function() {
    if (!_fishRecordedBlob) {
        if (window.showToast) window.showToast("No audio recorded.", "error");
        return;
    }

    const nameInput = document.getElementById('fish-rec-name');
    const txtInput = document.getElementById('fish-rec-transcript');
    const name = (nameInput?.value || '').trim();
    const transcript = (txtInput?.value || '').trim();

    if (!name) {
        if (window.showToast) window.showToast("Please enter a name for this timbre.", "warning");
        if (nameInput) nameInput.focus();
        return;
    }

    const fd = new FormData();
    fd.append('file', _fishRecordedBlob, `${name}.wav`);
    fd.append('name', name);
    fd.append('transcript', transcript);

    try {
        if (window.showToast) window.showToast("Saving custom timbre to library...", "info");
        const r = await fetch('/api/audio/voice-clones/save-recorded', {
            method: 'POST',
            body: fd
        });
        const res = await r.json();

        if (res.ok) {
            if (window.showToast) window.showToast(`Timbre '${res.name}' created and saved!`, "success");
            window.closeFishRecordTimbreModal();

            if (typeof loadFishVoiceCloneList === 'function') await loadFishVoiceCloneList();
            if (typeof loadVoiceCloneList === 'function') await loadVoiceCloneList();

            // Auto-select the newly created timbre
            const sel = document.getElementById('v-fish-clone-select');
            const inp = document.getElementById('v-fish-speaker-wav');
            const refTxt = document.getElementById('v-fish-reference-text');

            if (sel && res.path) {
                sel.value = res.path;
                if (inp) inp.value = res.path;
                if (refTxt && res.transcript) refTxt.value = res.transcript;
                if (typeof saveAudioConfig === 'function') saveAudioConfig();
            }
        } else {
            if (window.showToast) window.showToast("Failed to save timbre: " + (res.error || "Unknown"), "error");
        }
    } catch (e) {
        if (window.showToast) window.showToast("Error saving timbre: " + e.message, "error");
    }
};

window.deleteFishVoiceClone = async function() {
    const sel = document.getElementById('v-fish-clone-select');
    const current = (document.getElementById('v-fish-speaker-wav')?.value || sel?.value || '').trim();

    if (!current) {
        if (window.showToast) window.showToast("Select a custom voice clone from the library to delete.", "warning");
        return;
    }

    const baseName = current.split('\\').pop().split('/').pop();
    window.hecosConfirm(`Are you sure you want to delete the voice timbre '${baseName}'? This will remove the WAV and transcript from disk.`, async function() {
        try {
            const r = await fetch('/api/audio/voice-clones/delete', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ filename: current })
            });
            const res = await r.json();
            if (res.ok) {
                if (window.showToast) window.showToast(`Timbre '${baseName}' deleted.`, "info");
                if (document.getElementById('v-fish-speaker-wav')) document.getElementById('v-fish-speaker-wav').value = '';
                if (document.getElementById('v-fish-reference-text')) document.getElementById('v-fish-reference-text').value = '';
                if (typeof loadFishVoiceCloneList === 'function') await loadFishVoiceCloneList();
                if (typeof loadVoiceCloneList === 'function') await loadVoiceCloneList();
                if (typeof saveAudioConfig === 'function') saveAudioConfig();
            } else {
                if (window.showToast) window.showToast("Error deleting: " + res.error, "error");
            }
        } catch (e) {
            if (window.showToast) window.showToast("Delete failed: " + e.message, "error");
        }
    });
};

// ── Local Fish Speech Server Management (Status, Start, Stop, Restart) ─────

window.checkFishServerStatus = async function(interactive = false) {
    const badge = document.getElementById('fish-server-status-pill');
    const desc = document.getElementById('fish-server-desc');
    const startBtn = document.getElementById('btn-fish-server-start');
    const stopBtn = document.getElementById('btn-fish-server-stop');
    const restartBtn = document.getElementById('btn-fish-server-restart');

    try {
        const res = await fetch('/api/audio/fish/server-status');
        const data = await res.json();
        if (!data.ok) throw new Error(data.error || 'Failed to fetch status');

        if (data.status === 'online') {
            if (badge) {
                badge.className = 'badge-pill badge-ok';
                badge.style.background = '';
                badge.style.color = '';
                badge.innerHTML = '🟢 Server Online (CUDA S2-Pro Ready)';
            }
            if (desc) desc.textContent = `Running on ${data.host}:${data.port} · Model: ${data.model_name}`;
            if (startBtn) startBtn.style.display = 'none';
            if (stopBtn) stopBtn.style.display = 'inline-flex';
            if (restartBtn) restartBtn.style.display = 'inline-flex';
            if (interactive && window.showToast) window.showToast("Fish Speech server is healthy and responding!", "success");
        } else if (data.status === 'starting') {
            if (badge) {
                badge.className = 'badge-pill';
                badge.style.background = 'rgba(234, 179, 8, 0.2)';
                badge.style.color = '#eab308';
                badge.innerHTML = '🟡 Initializing Model on GPU...';
            }
            if (desc) desc.textContent = `Port ${data.port} active. Loading weights...`;
            if (startBtn) startBtn.style.display = 'none';
            if (stopBtn) stopBtn.style.display = 'inline-flex';
            if (restartBtn) restartBtn.style.display = 'inline-flex';
            if (interactive && window.showToast) window.showToast("Server is starting, please wait a few seconds...", "info");
        } else {
            if (badge) {
                badge.className = 'badge-pill';
                badge.style.background = 'rgba(239, 68, 68, 0.2)';
                badge.style.color = '#ef4444';
                badge.innerHTML = '🔴 Server Offline (VRAM Free)';
            }
            if (desc) desc.textContent = `Daemon stopped. Click 'Start Server' to load S2-Pro into VRAM.`;
            if (startBtn) startBtn.style.display = 'inline-flex';
            if (stopBtn) stopBtn.style.display = 'none';
            if (restartBtn) restartBtn.style.display = 'none';
            if (interactive && window.showToast) window.showToast("Fish Speech server is offline.", "warning");
        }
    } catch (e) {
        if (badge) {
            badge.className = 'badge-pill';
            badge.style.background = 'rgba(239, 68, 68, 0.2)';
            badge.style.color = '#ef4444';
            badge.innerHTML = '⚠️ Unreachable';
        }
        if (desc) desc.textContent = e.message;
        if (interactive && window.showToast) window.showToast("Cannot connect to server status endpoint: " + e.message, "error");
    }
};

window.fishServerAction = async function(action) {
    const restartBtn = document.getElementById('btn-fish-server-restart');
    const startBtn = document.getElementById('btn-fish-server-start');
    const stopBtn = document.getElementById('btn-fish-server-stop');
    const badge = document.getElementById('fish-server-status-pill');

    const actionLabels = {
        restart: "Restarting Fish Speech server (reloading PyTorch model into VRAM)...",
        start: "Starting Fish Speech server on port 8080...",
        stop: "Stopping Fish Speech server and freeing GPU VRAM..."
    };

    if (badge) {
        badge.className = 'badge-pill';
        badge.style.background = 'rgba(234, 179, 8, 0.2)';
        badge.style.color = '#eab308';
        badge.innerHTML = `⏳ ${action.toUpperCase()} in progress...`;
    }

    if (window.showToast) window.showToast(actionLabels[action] || `Executing ${action}...`, "info");

    if (restartBtn) restartBtn.disabled = true;
    if (startBtn) startBtn.disabled = true;
    if (stopBtn) stopBtn.disabled = true;

    try {
        const res = await fetch('/api/audio/fish/server-action', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: action })
        });
        const data = await res.json();
        if (data.ok) {
            if (window.showToast) window.showToast(data.message || `Action ${action} completed successfully!`, "success");
        } else {
            if (window.showToast) window.showToast("Server action failed: " + (data.error || data.message), "error");
        }
    } catch (e) {
        if (window.showToast) window.showToast("Request error: " + e.message, "error");
    } finally {
        if (restartBtn) restartBtn.disabled = false;
        if (startBtn) startBtn.disabled = false;
        if (stopBtn) stopBtn.disabled = false;
        await window.checkFishServerStatus();
    }
};

// ── Model Selection & Explorer Integration ───────────────────────────────────

let _fishModelsCache = null;

window.loadFishModelList = async function() {
    const select = document.getElementById('v-fish-model-checkpoint');
    if (!select) return;

    try {
        const res = await fetch('/api/audio/fish/models');
        const data = await res.json();
        if (!data.ok) return;

        _fishModelsCache = data;
        const currentActive = data.active_checkpoint || 's2-pro';

        select.innerHTML = '';
        data.installed_models.forEach(m => {
            const opt = document.createElement('option');
            opt.value = m.id;
            opt.textContent = `${m.name} (${m.size_mb} MB)${m.active ? ' — [Active]' : ''}`;
            opt.style.background = 'var(--bg3)';
            opt.style.color = 'var(--text)';
            if (m.id === currentActive) opt.selected = true;
            select.appendChild(opt);
        });

        window.updateFishModelInfoDisplay(currentActive);
    } catch(e) {
        console.warn("[FishSpeech] Could not load models list:", e);
    }
};

window.updateFishModelInfoDisplay = function(modelId) {
    if (!_fishModelsCache || !_fishModelsCache.installed_models) return;
    const model = _fishModelsCache.installed_models.find(m => m.id === modelId);
    const pathDisplay = document.getElementById('v-fish-model-path-display');
    const descDisplay = document.getElementById('v-fish-model-desc-display');
    const familyPill = document.getElementById('v-fish-model-family-pill');

    if (model) {
        if (pathDisplay) pathDisplay.innerHTML = `📁 Path: <code>checkpoints/${model.id}</code> (~${model.size_mb} MB)`;
        if (descDisplay) descDisplay.textContent = model.description;
        if (familyPill) familyPill.textContent = model.id === 's2-pro' ? 'Dual-AR S2-Pro' : 'Dual-AR 1.5';
    }
};

window.onFishModelSelectChange = function() {
    const val = document.getElementById('v-fish-model-checkpoint')?.value;
    if (val) window.updateFishModelInfoDisplay(val);
};

window.applyFishModelSelection = async function() {
    const select = document.getElementById('v-fish-model-checkpoint');
    const btn = document.getElementById('btn-fish-apply-model');
    if (!select || !btn) return;

    const val = select.value;
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Switching Model...';

    if (window.showToast) window.showToast(`Loading checkpoint '${val}' into Fish Speech daemon...`, "info");

    try {
        const res = await fetch('/api/audio/fish/select-model', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ checkpoint: val })
        });
        const data = await res.json();
        if (data.ok) {
            if (window.showToast) window.showToast(`Active model switched to '${val}'!`, "success");
            await window.loadFishModelList();
            await window.checkFishServerStatus();
        } else {
            if (window.showToast) window.showToast("Failed to switch model: " + data.error, "error");
        }
    } catch (e) {
        if (window.showToast) window.showToast("Error switching model: " + e.message, "error");
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-check"></i> Apply & Reload Model';
    }
};

window.openFishCheckpointsFolder = async function() {
    try {
        const res = await fetch('/api/audio/fish/open-folder', { method: 'POST' });
        const data = await res.json();
        if (data.ok) {
            if (window.showToast) window.showToast("Opened checkpoints folder in Explorer!", "info");
        } else {
            if (window.showToast) window.showToast("Error opening folder: " + data.error, "error");
        }
    } catch (e) {
        if (window.showToast) window.showToast("Error opening folder: " + e.message, "error");
    }
};

window.copyFishCheckpointsPath = function() {
    const p = "C:\\Hecos\\hecos\\engines\\fish_speech\\checkpoints";
    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(p).then(() => {
            if (window.showToast) window.showToast("Copied path to clipboard: " + p, "success");
        }).catch(() => {
            prompt("Checkpoints directory path:", p);
        });
    } else {
        prompt("Checkpoints directory path:", p);
    }
};

// Check server status & load models on initial DOM load if card is present
document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('card-fish_speech')) {
        window.checkFishServerStatus();
        window.loadFishModelList();
    }
});
