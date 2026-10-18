/**
 * Hecos WebUI - Audio Configuration Logic
 * Handles STT/TTS settings, device scanning and testing.
 */

function populateAudioUI() {
    const v = audioConfig || {};
    setVal('v-piper', v.piper_path || '');
    const curOnnx = (v.onnx_model || '').split('\\').pop().split('/').pop();
    populateSelect('v-onnx-model', sysOptions.piper_voices || [], curOnnx, true);
    setVal('v-speed', v.speed ?? 1.2);
    setVal('v-noise', v.noise_scale ?? 0.817);
    setVal('v-noisew', v.noise_w ?? 0.9);
    setVal('v-silence', v.sentence_silence ?? 0.1);
    setVal('v-timeout', v.piper_timeout ?? 180);
    setVal('v-tts-history-max', v.tts_history_max_files ?? 100);
    setVal('v-active-engine', v.active_engine ?? 'piper');
    // Kokoro
    setVal('v-kokoro-speed', (v.kokoro && v.kokoro.speed) ? v.kokoro.speed : 1.0);
    setVal('v-kokoro-voice', (v.kokoro && v.kokoro.voice) ? v.kokoro.voice : 'af_heart');
    setVal('v-kokoro-silence', (v.kokoro && v.kokoro.sentence_silence) ? v.kokoro.sentence_silence : 0.0);
    setVal('v-kokoro-model', (v.kokoro && v.kokoro.model_path) ? v.kokoro.model_path : '');
    // XTTS
    setVal('v-xtts-speed', (v.xtts && v.xtts.speed) ? v.xtts.speed : 1.0);
    setVal('v-xtts-lang', (v.xtts && v.xtts.language) ? v.xtts.language : 'it');
    setVal('v-xtts-speaker', (v.xtts && v.xtts.speaker) ? v.xtts.speaker : 'Claribel Dervla');
    setVal('v-xtts-gpu', (v.xtts && v.xtts.gpu_acceleration) ? v.xtts.gpu_acceleration : 'auto');
    setCheck('v-xtts-chunk', (v.xtts && v.xtts.chunk_sentences !== undefined) ? v.xtts.chunk_sentences : true);
    setVal('v-xtts-speaker-wav', (v.xtts && v.xtts.speaker_wav) ? v.xtts.speaker_wav : '');
    setVal('v-xtts-temperature', (v.xtts && v.xtts.temperature !== undefined) ? v.xtts.temperature : 0.75);
    setVal('v-xtts-repetition_penalty', (v.xtts && v.xtts.repetition_penalty !== undefined) ? v.xtts.repetition_penalty : 5.0);
    setVal('v-xtts-topk', (v.xtts && v.xtts.top_k !== undefined) ? v.xtts.top_k : 50);
    setVal('v-xtts-topp', (v.xtts && v.xtts.top_p !== undefined) ? v.xtts.top_p : 0.85);
    setVal('v-xtts-length-penalty', (v.xtts && v.xtts.length_penalty !== undefined) ? v.xtts.length_penalty : 1.0);
    
    // Fish Speech
    setVal('v-fish-api-url', (v.fish_speech && v.fish_speech.api_url) ? v.fish_speech.api_url : 'http://127.0.0.1:8080/v1/tts');
    setVal('v-fish-api-key', (v.fish_speech && v.fish_speech.api_key) ? v.fish_speech.api_key : '');
    setVal('v-fish-speaker-wav', (v.fish_speech && v.fish_speech.reference_audio) ? v.fish_speech.reference_audio : '');
    setVal('v-fish-reference-id', (v.fish_speech && v.fish_speech.reference_id) ? v.fish_speech.reference_id : '');
    setVal('v-fish-reference-text', (v.fish_speech && v.fish_speech.reference_text) ? v.fish_speech.reference_text : '');
    setVal('v-fish-temperature', (v.fish_speech && v.fish_speech.temperature !== undefined) ? v.fish_speech.temperature : 0.7);
    setVal('v-fish-temperature-range', (v.fish_speech && v.fish_speech.temperature !== undefined) ? v.fish_speech.temperature : 0.7);
    setVal('v-fish-topp', (v.fish_speech && v.fish_speech.top_p !== undefined) ? v.fish_speech.top_p : 0.7);
    setVal('v-fish-topp-range', (v.fish_speech && v.fish_speech.top_p !== undefined) ? v.fish_speech.top_p : 0.7);
    setVal('v-fish-repetition', (v.fish_speech && v.fish_speech.repetition_penalty !== undefined) ? v.fish_speech.repetition_penalty : 1.2);
    setVal('v-fish-repetition-range', (v.fish_speech && v.fish_speech.repetition_penalty !== undefined) ? v.fish_speech.repetition_penalty : 1.2);
    setVal('v-fish-chunk-length', (v.fish_speech && v.fish_speech.chunk_length !== undefined) ? v.fish_speech.chunk_length : 200);
    setVal('v-fish-chunk-length-range', (v.fish_speech && v.fish_speech.chunk_length !== undefined) ? v.fish_speech.chunk_length : 200);
    setVal('v-fish-max-tokens', (v.fish_speech && v.fish_speech.max_new_tokens !== undefined) ? v.fish_speech.max_new_tokens : 1024);
    setVal('v-fish-max-tokens-range', (v.fish_speech && v.fish_speech.max_new_tokens !== undefined) ? v.fish_speech.max_new_tokens : 1024);
    setVal('v-fish-seed', (v.fish_speech && v.fish_speech.seed !== undefined) ? v.fish_speech.seed : 0);
    setCheck('v-fish-normalize', (v.fish_speech && v.fish_speech.normalize !== undefined) ? v.fish_speech.normalize : true);
    setCheck('v-fish-memory-cache', (v.fish_speech && v.fish_speech.use_memory_cache !== undefined) ? v.fish_speech.use_memory_cache : true);
    setCheck('v-fish-chunk', (v.fish_speech && v.fish_speech.chunk_sentences !== undefined) ? v.fish_speech.chunk_sentences : true);
    setVal('v-fish-volume', (v.fish_speech && v.fish_speech.volume !== undefined) ? v.fish_speech.volume : 1.0);
    setVal('v-fish-volume-range', (v.fish_speech && v.fish_speech.volume !== undefined) ? v.fish_speech.volume : 1.0);
    
    // Update value displays
    const spVal = document.getElementById('v-xtts-speed-val'); if(spVal) spVal.textContent = getV('v-xtts-speed');
    const tpVal = document.getElementById('v-xtts-temperature-val'); if(tpVal) tpVal.textContent = getV('v-xtts-temperature');
    const rpVal = document.getElementById('v-xtts-repetition-val'); if(rpVal) rpVal.textContent = getV('v-xtts-repetition_penalty');
    const tkVal = document.getElementById('v-xtts-topk-val'); if(tkVal) tkVal.textContent = getV('v-xtts-topk');
    const tppVal = document.getElementById('v-xtts-topp-val'); if(tppVal) tppVal.textContent = getV('v-xtts-topp');
    const lpVal = document.getElementById('v-xtts-length-penalty-val'); if(lpVal) lpVal.textContent = getV('v-xtts-length-penalty');
    
    // Populate XTTS Presets
    const presetSel = document.getElementById('v-xtts-preset');
    if (presetSel) {
        presetSel.innerHTML = '<option value="default">Default (Built-in)</option>';
        if (v.xtts_presets) {
            for (const pName in v.xtts_presets) {
                const opt = document.createElement('option');
                opt.value = pName;
                opt.textContent = pName;
                presetSel.appendChild(opt);
            }
        }
        if (v.xtts && v.xtts.current_preset && v.xtts_presets && v.xtts_presets[v.xtts.current_preset]) {
            presetSel.value = v.xtts.current_preset;
        } else {
            presetSel.value = 'default';
        }
    }

    // Populate XTTS Inference Presets
    const infPresetSel = document.getElementById('v-xtts-inference-preset');
    if (infPresetSel) {
        infPresetSel.innerHTML = '<option value="">-- Nessun Preset --</option>';
        if (v.xtts_inference_presets) {
            for (const pName in v.xtts_inference_presets) {
                const opt = document.createElement('option');
                opt.value = pName;
                opt.textContent = pName;
                infPresetSel.appendChild(opt);
            }
        }
    }

    // Populate Fish Speech Presets
    const fishPresetSel = document.getElementById('v-fish-preset');
    if (fishPresetSel) {
        fishPresetSel.innerHTML = '<option value="default">Default (Base / Zero-Shot)</option>';
        if (v.fish_speech_presets) {
            for (const pName in v.fish_speech_presets) {
                const opt = document.createElement('option');
                opt.value = pName;
                opt.textContent = pName;
                fishPresetSel.appendChild(opt);
            }
        }
        if (v.fish_speech && v.fish_speech.current_preset && v.fish_speech_presets && v.fish_speech_presets[v.fish_speech.current_preset]) {
            fishPresetSel.value = v.fish_speech.current_preset;
        } else {
            fishPresetSel.value = 'default';
        }
    }

    // Populate Fish Speech Inference Presets
    const fishInfPresetSel = document.getElementById('v-fish-inference-preset');
    if (fishInfPresetSel) {
        fishInfPresetSel.innerHTML = '<option value="">-- No Preset Selected --</option>';
        if (v.fish_speech_inference_presets) {
            for (const pName in v.fish_speech_inference_presets) {
                const opt = document.createElement('option');
                opt.value = pName;
                opt.textContent = pName;
                fishInfPresetSel.appendChild(opt);
            }
        }
        if (v.fish_speech && v.fish_speech.current_inference_preset && v.fish_speech_inference_presets && v.fish_speech_inference_presets[v.fish_speech.current_inference_preset]) {
            fishInfPresetSel.value = v.fish_speech.current_inference_preset;
        }
    }

    refreshAudioHistoryCount();
    checkTTSEngineStatus();
    if (typeof loadVoiceCloneList === 'function') loadVoiceCloneList();
    if (typeof loadFishVoiceCloneList === 'function') loadFishVoiceCloneList();
    // Activate the tab matching the current engine
    const activeEngine = (v.active_engine || 'piper');
    if (typeof switchAudioEngineTab === 'function') switchAudioEngineTab(activeEngine, false);


    const a = audioConfig || {};
    setVal('a-threshold', a.energy_threshold ?? 450);
    setVal('a-timeout', a.silence_timeout ?? 5);
    setVal('a-limit', a.phrase_limit ?? 15);

    setCheck('sys-mic-status', (audioConfig || {}).listening_status ?? false);
    setCheck('sys-voice-status', (audioConfig || {}).voice_status ?? false);

    if (audioDevices) {
        const inSel = document.getElementById('audio-input-device');
        const outSel = document.getElementById('audio-output-device');
        if (inSel) {
            inSel.innerHTML = '';
            (audioDevices.input_devices || []).forEach(d => {
                const opt = document.createElement('option');
                opt.value = d.index;
                opt.textContent = `${d.index}: ${d.name}`;
                if (d.index === audioDevices.selected_input_index) opt.selected = true;
                inSel.appendChild(opt);
            });
        }
        if (outSel) {
            outSel.innerHTML = '';
            (audioDevices.output_devices || []).forEach(d => {
                const opt = document.createElement('option');
                opt.value = d.index;
                opt.textContent = `${d.index}: ${d.name}`;
                if (d.index === audioDevices.selected_output_index) opt.selected = true;
                outSel.appendChild(opt);
            });
        }
    }
    
    if (typeof window.onVoiceClonePathInput === 'function') {
        window.onVoiceClonePathInput();
    }
    if (typeof window.onFishVoiceClonePathInput === 'function') {
        window.onFishVoiceClonePathInput();
    }
    if (typeof window.checkFishServerStatus === 'function') {
        window.checkFishServerStatus();
    }
}

// ── Engine Tab Switcher ──────────────────────────────────────────────────────

window.switchAudioEngineTab = function(engine, saveEngine = true) {
    const engines = ['piper', 'kokoro', 'xtts2', 'fish_speech'];

    // Show/hide engine cards
    engines.forEach(e => {
        const card = document.getElementById(`card-${e}`);
        if (card) card.style.display = (e === engine) ? '' : 'none';
    });

    // Style tab buttons: active = var(--bg3), inactive = transparent
    engines.forEach(e => {
        const btn = document.getElementById(`btn-tab-${e}`);
        if (!btn) return;
        if (e === engine) {
            btn.style.background = 'var(--bg3)';
            btn.style.color = 'var(--accent)';
            btn.style.borderBottom = '2px solid var(--accent)';
            btn.style.marginBottom = '-1px';
        } else {
            btn.style.background = 'transparent';
            btn.style.color = 'var(--muted)';
            btn.style.borderBottom = 'none';
            btn.style.marginBottom = '0';
        }
    });

    if (engine === 'fish_speech') {
        if (typeof window.checkFishServerStatus === 'function') window.checkFishServerStatus();
        if (typeof window.loadFishModelList === 'function') window.loadFishModelList();
    }
};


function buildAudioPayload() {
    const v = (typeof audioConfig !== 'undefined' ? audioConfig : {}) || {};
    const pdir = (window.sysOptions || {}).piper_dir || 'C:\\piper';
    const el = document.getElementById('v-onnx-model');
    const sel = el ? el.value : (v.onnx_model || 'it_IT-paola-medium.onnx');
    const modelFile = (sel && sel.trim() && sel !== 'null') ? sel : 'it_IT-paola-medium.onnx';
    
    return {
        active_engine:    getV('v-active-engine', v.active_engine || 'piper'),
        kokoro:           { 
            speed: parseFloat(getV('v-kokoro-speed', v.kokoro?.speed ?? 1.0)),
            voice: getV('v-kokoro-voice', v.kokoro?.voice || 'af_heart'),
            sentence_silence: parseFloat(getV('v-kokoro-silence', v.kokoro?.sentence_silence ?? 0.0)),
            model_path: getV('v-kokoro-model', v.kokoro?.model_path || '')
        },
        xtts:             { 
            speed: parseFloat(getV('v-xtts-speed', v.xtts?.speed ?? 1.0)), 
            language: getV('v-xtts-lang', v.xtts?.language || 'it'),
            speaker: getV('v-xtts-speaker', v.xtts?.speaker || 'Claribel Dervla'),
            gpu_acceleration: getV('v-xtts-gpu', v.xtts?.gpu_acceleration || 'auto'),
            chunk_sentences: getC('v-xtts-chunk', v.xtts?.chunk_sentences ?? true),
            speaker_wav: getV('v-xtts-speaker-wav', v.xtts?.speaker_wav || ''),
            temperature: parseFloat(getV('v-xtts-temperature', v.xtts?.temperature ?? 0.75)),
            repetition_penalty: parseFloat(getV('v-xtts-repetition_penalty', v.xtts?.repetition_penalty ?? 5.0)),
            top_k: parseInt(getV('v-xtts-topk', v.xtts?.top_k ?? 50)),
            top_p: parseFloat(getV('v-xtts-topp', v.xtts?.top_p ?? 0.85)),
            length_penalty: parseFloat(getV('v-xtts-length-penalty', v.xtts?.length_penalty ?? 1.0)),
            current_preset: getV('v-xtts-preset', 'default')
        },
        fish_speech:      {
            api_url:            getV('v-fish-api-url', v.fish_speech?.api_url || 'http://127.0.0.1:8080/v1/tts'),
            api_key:            getV('v-fish-api-key', v.fish_speech?.api_key || ''),
            reference_id:       getV('v-fish-reference-id', v.fish_speech?.reference_id || ''),
            reference_audio:    getV('v-fish-speaker-wav', v.fish_speech?.reference_audio || ''),
            reference_text:     getV('v-fish-reference-text', v.fish_speech?.reference_text || ''),
            temperature:        parseFloat(getV('v-fish-temperature', v.fish_speech?.temperature ?? 0.7)),
            top_p:              parseFloat(getV('v-fish-topp', v.fish_speech?.top_p ?? 0.7)),
            repetition_penalty: parseFloat(getV('v-fish-repetition', v.fish_speech?.repetition_penalty ?? 1.2)),
            chunk_length:       parseInt(getV('v-fish-chunk-length', v.fish_speech?.chunk_length ?? 200)),
            max_new_tokens:     parseInt(getV('v-fish-max-tokens', v.fish_speech?.max_new_tokens ?? 1024)),
            seed:               parseInt(getV('v-fish-seed', v.fish_speech?.seed ?? 0)),
            normalize:          getC('v-fish-normalize', v.fish_speech?.normalize ?? true),
            use_memory_cache:   getC('v-fish-memory-cache', v.fish_speech?.use_memory_cache ?? true),
            chunk_sentences:    getC('v-fish-chunk', v.fish_speech?.chunk_sentences ?? true),
            volume:             parseFloat(getV('v-fish-volume', v.fish_speech?.volume ?? 1.0)),
            current_preset:     getV('v-fish-preset', 'default'),
            current_inference_preset: getV('v-fish-inference-preset', '')
        },
        xtts_presets:                  v.xtts_presets || {},
        xtts_inference_presets:        v.xtts_inference_presets || {},
        fish_speech_presets:           v.fish_speech_presets || {},
        fish_speech_inference_presets: v.fish_speech_inference_presets || {},
        listening_status: getC('sys-mic-status', v.listening_status ?? false),
        voice_status:     getC('sys-voice-status', v.voice_status ?? false),
        piper_path:       getV('v-piper', v.piper_path || ''),
        onnx_model:       (modelFile.includes('\\') || modelFile.includes('/')) ? modelFile : pdir + '\\' + modelFile,
        speed:            parseFloat(getV('v-speed', v.speed)) || 1.0,
        noise_scale:      parseFloat(getV('v-noise', v.noise_scale)) || 0.8,
        noise_w:          parseFloat(getV('v-noisew', v.noise_w)) || 1.0,
        sentence_silence: parseFloat(getV('v-silence', v.sentence_silence)) || 0.2,
        piper_timeout:    parseInt(getV('v-timeout', v.piper_timeout)) || 180,
        tts_history_max_files: parseInt(getV('v-tts-history-max', v.tts_history_max_files)) || 100,
        energy_threshold: parseInt(getV('a-threshold', v.energy_threshold)) || 450,
        silence_timeout:  parseInt(getV('a-timeout', v.silence_timeout)) || 5,
        phrase_limit:     parseInt(getV('a-limit', v.phrase_limit)) || 15
    };
}

let currentTestAudio = null;
let currentTestTimer = null;
let testStartTime = 0;

window.populateAudioUI       = populateAudioUI;
window.buildAudioPayload     = buildAudioPayload;
window.saveAudioConfig = function() {
    if (typeof window.saveConfig === 'function') return window.saveConfig(true);
    console.warn('[AudioConfig] saveConfig not yet available');
    return Promise.resolve();
};

