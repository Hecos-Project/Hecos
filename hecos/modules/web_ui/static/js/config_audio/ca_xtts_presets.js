/**
 * ca_xtts_presets.js
 * ─────────────────────────────────────────────────────────────────────────────
 * Frontend module for XTTS Configuration Presets (global voice persona profiles).
 * Complements ca_xtts_inference.js (inference hyper-parameters).
 * Follows Hecos architectural standards with full preset lifecycle:
 * New, Update (with default overwrite protection), Rename, Reset, Delete.
 * ─────────────────────────────────────────────────────────────────────────────
 */

(function () {
    'use strict';

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
        if (!cfg.xtts_presets) cfg.xtts_presets = {};
        return cfg.xtts_presets;
    }

    // ── Save Current Settings as New Configuration Preset ───────────────────
    window.saveXTTSPreset = function () {
        const presets = _getConfigPresets();
        const defName = window.getNextCustomPresetName ? window.getNextCustomPresetName(presets, 'custom') : 'custom_1';
        const promptFn = window.hecosPrompt || prompt;

        promptFn("XTTS Configuration Preset Name:", function (name) {
            if (!name || !name.trim()) return;
            name = name.trim();
            const cfg = _getAudioConfig();

            const infPreset = (document.getElementById('v-xtts-inference-preset')?.value || '').trim();

            presets[name] = {
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
                length_penalty: parseFloat(document.getElementById('v-xtts-length-penalty')?.value || 1.0),
                inference_preset: infPreset
            };

            if (!cfg.xtts) cfg.xtts = {};
            cfg.xtts.current_preset = name;

            saveAudioConfig().then(() => {
                populateAudioUI();
                const sel = document.getElementById('v-xtts-preset');
                if (sel) sel.value = name;
                if (window.showToast) window.showToast(`Preset '${name}' saved successfully!`, "success");
            });
        }, defName);
    };

    // ── Update Currently Selected Configuration Preset ───────────────────────
    window.updateXTTSPreset = function () {
        const sel = document.getElementById('v-xtts-preset');
        const name = sel ? sel.value : 'default';
        const presets = _getConfigPresets();

        // Protect default preset from overwrite
        if (!name || name === 'default' || name === 'Default') {
            const defName = window.getNextCustomPresetName ? window.getNextCustomPresetName(presets, 'custom') : 'custom_1';
            const promptFn = window.hecosPrompt || prompt;
            promptFn("The default preset cannot be overwritten.\nEnter a name to save as a new custom preset:", function (customName) {
                if (!customName || !customName.trim()) return;
                customName = customName.trim();
                const cfg = _getAudioConfig();
                const infPreset = (document.getElementById('v-xtts-inference-preset')?.value || '').trim();

                presets[customName] = {
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
                    length_penalty: parseFloat(document.getElementById('v-xtts-length-penalty')?.value || 1.0),
                    inference_preset: infPreset
                };

                if (!cfg.xtts) cfg.xtts = {};
                cfg.xtts.current_preset = customName;

                saveAudioConfig().then(() => {
                    populateAudioUI();
                    if (sel) sel.value = customName;
                    if (window.showToast) window.showToast(`Saved as new custom preset '${customName}'!`, "success");
                });
            }, defName);
            return;
        }

        const cfg = _getAudioConfig();
        const infPreset = (document.getElementById('v-xtts-inference-preset')?.value || '').trim();

        presets[name] = {
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
            length_penalty: parseFloat(document.getElementById('v-xtts-length-penalty')?.value || 1.0),
            inference_preset: infPreset
        };

        if (!cfg.xtts) cfg.xtts = {};
        cfg.xtts.current_preset = name;

        saveAudioConfig().then(() => {
            if (window.showToast) window.showToast(`Preset '${name}' updated!`, "success");
        });
    };

    // ── Rename Selected Configuration Preset ────────────────────────────────
    window.renameXTTSPreset = function () {
        const sel = document.getElementById('v-xtts-preset');
        const oldName = sel ? sel.value : '';
        if (!oldName || oldName === 'default' || oldName === 'Default') {
            if (window.showToast) window.showToast("Cannot rename the default preset.", "warning");
            else alert("Cannot rename the default preset.");
            return;
        }

        const presets = _getConfigPresets();
        const promptFn = window.hecosPrompt || prompt;

        promptFn(`Rename XTTS Preset '${oldName}' to:`, function (newName) {
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
            if (cfg.xtts && cfg.xtts.current_preset === oldName) {
                cfg.xtts.current_preset = newName;
            }

            saveAudioConfig().then(() => {
                populateAudioUI();
                if (sel) sel.value = newName;
                if (window.showToast) window.showToast(`Preset renamed to '${newName}'!`, "success");
            });
        }, oldName);
    };

    // ── Reset to Defaults ───────────────────────────────────────────────────
    window.resetXTTSConfig = function () {
        window.hecosConfirm("Reset all XTTS parameters to their default values?", function () {
            const presetSelect = document.getElementById('v-xtts-preset');
            if (presetSelect) presetSelect.value = 'default';
            window.loadXTTSPreset();
        });
    };

    // ── Load Selected Configuration Preset ───────────────────────────────────
    window.loadXTTSPreset = function () {
        const name = document.getElementById('v-xtts-preset')?.value;
        const cfg = _getAudioConfig();
        if (!name) {
            if (document.getElementById('v-xtts-speaker-wav')) document.getElementById('v-xtts-speaker-wav').value = '';
            if (document.getElementById('v-xtts-clone-select')) document.getElementById('v-xtts-clone-select').value = '';
            return;
        }

        if (name === 'default' || !cfg.xtts_presets || !cfg.xtts_presets[name]) {
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

                if (!cfg.xtts) cfg.xtts = {};
                cfg.xtts.current_preset = 'default';
                saveAudioConfig();
            }
            return;
        }

        const p = cfg.xtts_presets[name];
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

        let matchedInf = p.inference_preset || '';
        if (!matchedInf && cfg.xtts_inference_presets) {
            for (const [k, inf] of Object.entries(cfg.xtts_inference_presets)) {
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

        if (!cfg.xtts) cfg.xtts = {};
        cfg.xtts.current_preset = name;
        saveAudioConfig();
    };

    // ── Delete Selected Preset ───────────────────────────────────────────────
    window.deleteXTTSPreset = function () {
        const name = document.getElementById('v-xtts-preset')?.value;
        if (!name || name === 'default' || name === 'Default') {
            if (window.showToast) window.showToast("Cannot delete the default preset.", "error");
            return;
        }

        window.hecosConfirm(`Are you sure you want to delete the preset '${name}'?`, function () {
            const cfg = _getAudioConfig();
            if (cfg.xtts_presets && cfg.xtts_presets[name]) {
                delete cfg.xtts_presets[name];
                if (!cfg.xtts) cfg.xtts = {};
                cfg.xtts.current_preset = 'default';
                saveAudioConfig().then(() => {
                    populateAudioUI();
                    if (window.showToast) window.showToast("Preset deleted.", "info");
                });
            }
        });
    };

})();
