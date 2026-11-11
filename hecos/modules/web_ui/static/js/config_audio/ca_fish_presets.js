/**
 * Hecos WebUI - Fish Speech Presets & Voice Studio Logic
 * Handles saving, updating, loading and deleting Fish Speech configuration presets,
 * inference presets, expressiveness tags, and scenario loading.
 * Follows Hecos architectural standards with full preset lifecycle:
 * New, Update (with default overwrite protection), Rename, Reset, Delete.
 */

(function () {
    'use strict';

    const BUILTIN_FISH_INFERENCE_KEYS = [
        "Standard & Balanced", "Expressive & Dynamic", "Fast & Direct",
        "Creative & Wild", "Stable & Monotone"
    ];

    function _getAudioConfig() {
        const cfg = (window.audioConfig && typeof window.audioConfig === 'object')
            ? window.audioConfig
            : ((typeof audioConfig !== 'undefined' && audioConfig) ? audioConfig : {});
        window.audioConfig = cfg;
        if (typeof audioConfig !== 'undefined') {
            try { audioConfig = cfg; } catch (_) {}
        }
        return cfg;
    }

    function _getConfigPresets() {
        const cfg = _getAudioConfig();
        if (!cfg.fish_speech_presets) cfg.fish_speech_presets = {};
        return cfg.fish_speech_presets;
    }

    function _getInferencePresets() {
        const cfg = _getAudioConfig();
        if (!cfg.fish_speech_inference_presets) cfg.fish_speech_inference_presets = {};
        return cfg.fish_speech_inference_presets;
    }

    // ══════════════════════════════════════════════════════════════════════════
    // 1. CONFIGURATION PRESETS
    // ══════════════════════════════════════════════════════════════════════════

    window.saveFishPreset = function() {
        const presets = _getConfigPresets();
        const defName = window.getNextCustomPresetName ? window.getNextCustomPresetName(presets, 'custom') : 'custom_1';
        const promptFn = window.hecosPrompt || prompt;

        promptFn("Fish Speech Configuration Preset Name:", function(name) {
            if (!name || !name.trim()) return;
            name = name.trim();
            const cfg = _getAudioConfig();

            const speakerWav = (document.getElementById('v-fish-speaker-wav')?.value || '').trim();
            const refId = (document.getElementById('v-fish-reference-id')?.value || '').trim();
            const refText = (document.getElementById('v-fish-reference-text')?.value || '').trim();
            const infPreset = (document.getElementById('v-fish-inference-preset')?.value || '').trim();

            presets[name] = {
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

            if (!cfg.fish_speech) cfg.fish_speech = {};
            cfg.fish_speech.current_preset = name;
            cfg.fish_speech.current_inference_preset = infPreset;

            saveAudioConfig().then(() => {
                populateAudioUI();
                const sel = document.getElementById('v-fish-preset');
                if (sel) sel.value = name;
                if (window.showToast) window.showToast(`Preset '${name}' saved successfully!`, "success");
            });
        }, defName);
    };

    window.updateFishPreset = function() {
        const sel = document.getElementById('v-fish-preset');
        const name = sel ? sel.value : 'default';
        const presets = _getConfigPresets();

        // Protect default preset from overwrite
        if (!name || name === 'default' || name === 'Default') {
            const defName = window.getNextCustomPresetName ? window.getNextCustomPresetName(presets, 'custom') : 'custom_1';
            const promptFn = window.hecosPrompt || prompt;
            promptFn("The default preset cannot be overwritten.\nEnter a name to save as a new custom preset:", function(customName) {
                if (!customName || !customName.trim()) return;
                customName = customName.trim();
                const cfg = _getAudioConfig();

                const speakerWav = (document.getElementById('v-fish-speaker-wav')?.value || '').trim();
                const refId = (document.getElementById('v-fish-reference-id')?.value || '').trim();
                const refText = (document.getElementById('v-fish-reference-text')?.value || '').trim();
                const infPreset = (document.getElementById('v-fish-inference-preset')?.value || '').trim();

                presets[customName] = {
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

                if (!cfg.fish_speech) cfg.fish_speech = {};
                cfg.fish_speech.current_preset = customName;
                cfg.fish_speech.current_inference_preset = infPreset;

                saveAudioConfig().then(() => {
                    populateAudioUI();
                    if (sel) sel.value = customName;
                    if (window.showToast) window.showToast(`Saved as new custom preset '${customName}'!`, "success");
                });
            }, defName);
            return;
        }

        const cfg = _getAudioConfig();
        const speakerWav = (document.getElementById('v-fish-speaker-wav')?.value || '').trim();
        const refId = (document.getElementById('v-fish-reference-id')?.value || '').trim();
        const refText = (document.getElementById('v-fish-reference-text')?.value || '').trim();
        const infPreset = (document.getElementById('v-fish-inference-preset')?.value || '').trim();

        presets[name] = {
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

        if (!cfg.fish_speech) cfg.fish_speech = {};
        cfg.fish_speech.current_preset = name;
        cfg.fish_speech.current_inference_preset = infPreset;

        saveAudioConfig().then(() => {
            if (window.showToast) window.showToast(`Preset '${name}' updated!`, "success");
        });
    };

    window.renameFishPreset = function() {
        const sel = document.getElementById('v-fish-preset');
        const oldName = sel ? sel.value : '';
        if (!oldName || oldName === 'default' || oldName === 'Default') {
            if (window.showToast) window.showToast("Cannot rename the default preset.", "warning");
            else alert("Cannot rename the default preset.");
            return;
        }

        const presets = _getConfigPresets();
        const promptFn = window.hecosPrompt || prompt;

        promptFn(`Rename Fish Speech Preset '${oldName}' to:`, function(newName) {
            if (!newName || !newName.trim() || newName.trim() === oldName) return;
            newName = newName.trim();
            if (presets[newName] && newName !== oldName) {
                if (window.showToast) window.showToast(`A preset named '${newName}' already exists.`, "error");
                else alert(`A preset named '${newName}' already exists.`);
                return;
            }

            presets[newName] = presets[oldName];
            delete presets[oldName];

            const cfg = _getAudioConfig();
            if (cfg.fish_speech && cfg.fish_speech.current_preset === oldName) {
                cfg.fish_speech.current_preset = newName;
            }

            saveAudioConfig().then(() => {
                populateAudioUI();
                if (sel) sel.value = newName;
                if (window.showToast) window.showToast(`Preset renamed to '${newName}'!`, "success");
            });
        }, oldName);
    };

    window.resetFishConfig = function() {
        window.hecosConfirm("Reset all Fish Speech parameters to default values?", function() {
            const presetSelect = document.getElementById('v-fish-preset');
            if (presetSelect) presetSelect.value = 'default';
            window.loadFishPreset();
        });
    };

    window.loadFishPreset = function() {
        const name = document.getElementById('v-fish-preset')?.value;
        const cfg = _getAudioConfig();
        if (!name) return;

        if (name === 'default' || !cfg.fish_speech_presets || !cfg.fish_speech_presets[name]) {
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

                if (!cfg.fish_speech) cfg.fish_speech = {};
                cfg.fish_speech.current_preset = 'default';
                cfg.fish_speech.current_inference_preset = '';
                cfg.fish_speech.reference_audio = '';
                cfg.fish_speech.reference_id = '';
                cfg.fish_speech.reference_text = '';
                saveAudioConfig();
            }
            return;
        }

        const p = cfg.fish_speech_presets[name];
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

        let matchedInf = p.inference_preset || '';
        if (document.getElementById('v-fish-inference-preset')) {
            document.getElementById('v-fish-inference-preset').value = matchedInf;
        }

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

        if (!cfg.fish_speech) cfg.fish_speech = {};
        cfg.fish_speech.current_preset = name;
        cfg.fish_speech.current_inference_preset = matchedInf;
        cfg.fish_speech.reference_audio = speakerWav;
        cfg.fish_speech.reference_id = p.reference_id || '';
        cfg.fish_speech.reference_text = p.reference_text || '';
        cfg.fish_speech.temperature = p.temperature ?? 0.7;
        cfg.fish_speech.top_p = p.top_p ?? 0.7;
        cfg.fish_speech.repetition_penalty = p.repetition_penalty ?? 1.2;
        cfg.fish_speech.chunk_length = p.chunk_length ?? 200;
        cfg.fish_speech.max_new_tokens = p.max_new_tokens ?? 1024;
        cfg.fish_speech.seed = p.seed ?? 0;
        cfg.fish_speech.normalize = p.normalize ?? true;
        cfg.fish_speech.use_memory_cache = p.use_memory_cache ?? true;
        cfg.fish_speech.chunk_sentences = p.chunk_sentences ?? true;

        saveAudioConfig();
    };

    window.deleteFishPreset = function() {
        const name = document.getElementById('v-fish-preset')?.value;
        if (!name || name === 'default' || name === 'Default') {
            if (window.showToast) window.showToast("Cannot delete the default preset.", "error");
            return;
        }

        window.hecosConfirm(`Are you sure you want to delete the preset '${name}'?`, function() {
            const cfg = _getAudioConfig();
            if (cfg.fish_speech_presets && cfg.fish_speech_presets[name]) {
                delete cfg.fish_speech_presets[name];
                if (!cfg.fish_speech) cfg.fish_speech = {};
                cfg.fish_speech.current_preset = 'default';
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

    // ══════════════════════════════════════════════════════════════════════════
    // 2. INFERENCE PRESETS
    // ══════════════════════════════════════════════════════════════════════════

    window.saveFishInferencePreset = function() {
        const presets = _getInferencePresets();
        const defName = window.getNextCustomPresetName ? window.getNextCustomPresetName(presets, 'custom') : 'custom_1';
        const promptFn = window.hecosPrompt || prompt;

        promptFn("Fish Speech Inference Preset Name:", function(name) {
            if (!name || !name.trim()) return;
            name = name.trim();

            presets[name] = {
                temperature: parseFloat(document.getElementById('v-fish-temperature')?.value || 0.7),
                top_p: parseFloat(document.getElementById('v-fish-topp')?.value || 0.7),
                repetition_penalty: parseFloat(document.getElementById('v-fish-repetition')?.value || 1.2),
                chunk_length: parseInt(document.getElementById('v-fish-chunk-length')?.value || 200),
                max_new_tokens: parseInt(document.getElementById('v-fish-max-tokens')?.value || 1024),
                seed: parseInt(document.getElementById('v-fish-seed')?.value || 0),
                normalize: document.getElementById('v-fish-normalize')?.checked ?? true,
                use_memory_cache: document.getElementById('v-fish-memory-cache')?.checked ?? true,
                volume: parseFloat(document.getElementById('v-fish-volume')?.value || 1.0)
            };

            const cfg = _getAudioConfig();
            if (!cfg.fish_speech) cfg.fish_speech = {};
            cfg.fish_speech.current_inference_preset = name;

            saveAudioConfig().then(() => {
                populateAudioUI();
                const sel = document.getElementById('v-fish-inference-preset');
                if (sel) sel.value = name;
                if (window.showToast) window.showToast(`Inference Preset '${name}' saved!`, "success");
            });
        }, defName);
    };

    window.updateFishInferencePreset = function() {
        const sel = document.getElementById('v-fish-inference-preset');
        const name = sel ? sel.value : '';
        if (!name) {
            if (window.showToast) window.showToast("Select an Inference Preset first.", "error");
            return;
        }

        const presets = _getInferencePresets();
        const isDefault = window.isDefaultPresetName ? window.isDefaultPresetName(name, BUILTIN_FISH_INFERENCE_KEYS) : BUILTIN_FISH_INFERENCE_KEYS.includes(name);

        if (isDefault) {
            const defName = window.getNextCustomPresetName ? window.getNextCustomPresetName(presets, 'custom') : 'custom_1';
            const promptFn = window.hecosPrompt || prompt;
            promptFn(`The default preset '${name}' cannot be overwritten.\nEnter a name to save as a new custom preset:`, function(customName) {
                if (!customName || !customName.trim()) return;
                customName = customName.trim();

                presets[customName] = {
                    temperature: parseFloat(document.getElementById('v-fish-temperature')?.value || 0.7),
                    top_p: parseFloat(document.getElementById('v-fish-topp')?.value || 0.7),
                    repetition_penalty: parseFloat(document.getElementById('v-fish-repetition')?.value || 1.2),
                    chunk_length: parseInt(document.getElementById('v-fish-chunk-length')?.value || 200),
                    max_new_tokens: parseInt(document.getElementById('v-fish-max-tokens')?.value || 1024),
                    seed: parseInt(document.getElementById('v-fish-seed')?.value || 0),
                    normalize: document.getElementById('v-fish-normalize')?.checked ?? true,
                    use_memory_cache: document.getElementById('v-fish-memory-cache')?.checked ?? true,
                    volume: parseFloat(document.getElementById('v-fish-volume')?.value || 1.0)
                };

                const cfg = _getAudioConfig();
                if (!cfg.fish_speech) cfg.fish_speech = {};
                cfg.fish_speech.current_inference_preset = customName;

                saveAudioConfig().then(() => {
                    populateAudioUI();
                    if (sel) sel.value = customName;
                    if (window.showToast) window.showToast(`Saved as new custom preset '${customName}'!`, "success");
                });
            }, defName);
            return;
        }

        presets[name] = {
            temperature: parseFloat(document.getElementById('v-fish-temperature')?.value || 0.7),
            top_p: parseFloat(document.getElementById('v-fish-topp')?.value || 0.7),
            repetition_penalty: parseFloat(document.getElementById('v-fish-repetition')?.value || 1.2),
            chunk_length: parseInt(document.getElementById('v-fish-chunk-length')?.value || 200),
            max_new_tokens: parseInt(document.getElementById('v-fish-max-tokens')?.value || 1024),
            seed: parseInt(document.getElementById('v-fish-seed')?.value || 0),
            normalize: document.getElementById('v-fish-normalize')?.checked ?? true,
            use_memory_cache: document.getElementById('v-fish-memory-cache')?.checked ?? true,
            volume: parseFloat(document.getElementById('v-fish-volume')?.value || 1.0)
        };

        const cfg = _getAudioConfig();
        if (!cfg.fish_speech) cfg.fish_speech = {};
        cfg.fish_speech.current_inference_preset = name;

        saveAudioConfig().then(() => {
            if (window.showToast) window.showToast(`Inference Preset '${name}' updated!`, "success");
        });
    };

    window.renameFishInferencePreset = function() {
        const sel = document.getElementById('v-fish-inference-preset');
        const oldName = sel ? sel.value : '';
        if (!oldName) {
            if (window.showToast) window.showToast("No preset selected.", "error");
            return;
        }

        const isDefault = window.isDefaultPresetName ? window.isDefaultPresetName(oldName, BUILTIN_FISH_INFERENCE_KEYS) : BUILTIN_FISH_INFERENCE_KEYS.includes(oldName);
        if (isDefault) {
            if (window.showToast) window.showToast("Cannot rename a built-in default preset. Create a New preset first.", "warning");
            else alert("Cannot rename a built-in default preset. Create a New preset first.");
            return;
        }

        const presets = _getInferencePresets();
        const promptFn = window.hecosPrompt || prompt;

        promptFn(`Rename Fish Speech Inference Preset '${oldName}' to:`, function(newName) {
            if (!newName || !newName.trim() || newName.trim() === oldName) return;
            newName = newName.trim();
            if (presets[newName] && newName !== oldName) {
                if (window.showToast) window.showToast(`A preset named '${newName}' already exists.`, "error");
                else alert(`A preset named '${newName}' already exists.`);
                return;
            }

            presets[newName] = presets[oldName];
            delete presets[oldName];

            const cfg = _getAudioConfig();
            if (cfg.fish_speech && cfg.fish_speech.current_inference_preset === oldName) {
                cfg.fish_speech.current_inference_preset = newName;
            }
            if (cfg.fish_speech_presets) {
                for (const k in cfg.fish_speech_presets) {
                    if (cfg.fish_speech_presets[k].inference_preset === oldName) {
                        cfg.fish_speech_presets[k].inference_preset = newName;
                    }
                }
            }

            saveAudioConfig().then(() => {
                populateAudioUI();
                if (sel) sel.value = newName;
                if (window.showToast) window.showToast(`Preset renamed to '${newName}'!`, "success");
            });
        }, oldName);
    };

    window.resetFishInferencePreset = function() {
        const sel = document.getElementById('v-fish-inference-preset');
        const name = sel ? sel.value : '';
        const presets = _getInferencePresets();

        if (name && presets[name]) {
            const p = presets[name];
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

            if (window.showToast) window.showToast(`Inference parameters reloaded from '${name}'.`, 'info');
        } else {
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
            if (document.getElementById('v-fish-volume')) document.getElementById('v-fish-volume').value = 1.0;
            if (document.getElementById('v-fish-volume-range')) document.getElementById('v-fish-volume-range').value = 1.0;

            document.getElementById('v-fish-temperature')?.dispatchEvent(new Event('input'));
            document.getElementById('v-fish-topp')?.dispatchEvent(new Event('input'));
            document.getElementById('v-fish-repetition')?.dispatchEvent(new Event('input'));
            document.getElementById('v-fish-chunk-length')?.dispatchEvent(new Event('input'));
            document.getElementById('v-fish-max-tokens')?.dispatchEvent(new Event('input'));

            if (sel) sel.value = '';
            if (window.showToast) window.showToast("Inference parameters reset to standard defaults.", "info");
        }
    };

    window.deleteFishInferencePreset = function() {
        const sel = document.getElementById('v-fish-inference-preset');
        const name = sel ? sel.value : '';
        if (!name) {
            if (window.showToast) window.showToast("No preset selected.", "error");
            return;
        }

        const isDefault = window.isDefaultPresetName ? window.isDefaultPresetName(name, BUILTIN_FISH_INFERENCE_KEYS) : BUILTIN_FISH_INFERENCE_KEYS.includes(name);
        if (isDefault) {
            if (window.showToast) window.showToast("Cannot delete a built-in default preset.", "error");
            else alert("Cannot delete a built-in default preset.");
            return;
        }

        window.hecosConfirm(`Do you want to delete the Inference Preset '${name}'?`, function() {
            const presets = _getInferencePresets();
            if (presets[name]) {
                delete presets[name];
                const cfg = _getAudioConfig();
                if (cfg.fish_speech && cfg.fish_speech.current_inference_preset === name) {
                    cfg.fish_speech.current_inference_preset = '';
                }
                saveAudioConfig().then(() => {
                    populateAudioUI();
                    if (window.showToast) window.showToast(`Preset '${name}' deleted.`, "info");
                });
            }
        });
    };

    window.loadFishInferencePreset = function() {
        const sel = document.getElementById('v-fish-inference-preset');
        const name = sel ? sel.value : '';
        const presets = _getInferencePresets();
        if (!name || !presets[name]) return;

        const p = presets[name];
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

})();
