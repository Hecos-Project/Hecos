/**
 * ca_xtts_inference.js
 * ─────────────────────────────────────────────────────────────────────────────
 * Frontend module for XTTS Inference Parameters & Presets management.
 * Follows Hecos architectural standards with full preset lifecycle:
 * New, Update (with default overwrite protection), Rename, Reset, Delete.
 * ─────────────────────────────────────────────────────────────────────────────
 */

(function () {
    'use strict';

    const BUILTIN_XTTS_INFERENCE_KEYS = [
        "Fast & Direct", "Expressive & Dynamic", "Slow & Clear",
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

    function _getInferencePresets() {
        const cfg = _getAudioConfig();
        if (!cfg.xtts_inference_presets) cfg.xtts_inference_presets = {};
        return cfg.xtts_inference_presets;
    }

    // ── Save Current Parameters as New Inference Preset ───────────────────────
    window.saveXTTSInferencePreset = function () {
        const presets = _getInferencePresets();
        const defName = window.getNextCustomPresetName ? window.getNextCustomPresetName(presets, 'custom') : 'custom_1';
        const promptFn = window.hecosPrompt || prompt;

        promptFn("XTTS Inference Preset Name:", function (name) {
            if (!name || !name.trim()) return;
            name = name.trim();

            presets[name] = {
                speed: parseFloat(document.getElementById('v-xtts-speed')?.value || 1.0),
                temperature: parseFloat(document.getElementById('v-xtts-temperature')?.value || 0.75),
                repetition_penalty: parseFloat(document.getElementById('v-xtts-repetition_penalty')?.value || 5.0),
                top_k: parseInt(document.getElementById('v-xtts-topk')?.value || 50),
                top_p: parseFloat(document.getElementById('v-xtts-topp')?.value || 0.85),
                length_penalty: parseFloat(document.getElementById('v-xtts-length-penalty')?.value || 1.0)
            };

            saveAudioConfig().then(() => {
                populateAudioUI();
                const sel = document.getElementById('v-xtts-inference-preset');
                if (sel) sel.value = name;
                if (window.showToast) window.showToast(`Inference Preset '${name}' saved!`, "success");
            });
        }, defName);
    };

    // ── Update Currently Selected Inference Preset ───────────────────────────
    window.updateXTTSInferencePreset = function () {
        const sel = document.getElementById('v-xtts-inference-preset');
        const name = sel ? sel.value : '';
        if (!name) {
            if (window.showToast) window.showToast("Select an Inference Preset first.", "error");
            return;
        }

        const presets = _getInferencePresets();
        const isDefault = window.isDefaultPresetName ? window.isDefaultPresetName(name, BUILTIN_XTTS_INFERENCE_KEYS) : BUILTIN_XTTS_INFERENCE_KEYS.includes(name);

        if (isDefault) {
            const defName = window.getNextCustomPresetName ? window.getNextCustomPresetName(presets, 'custom') : 'custom_1';
            const promptFn = window.hecosPrompt || prompt;
            promptFn(`The default preset '${name}' cannot be overwritten.\nEnter a name to save as a new custom preset:`, function (customName) {
                if (!customName || !customName.trim()) return;
                customName = customName.trim();

                presets[customName] = {
                    speed: parseFloat(document.getElementById('v-xtts-speed')?.value || 1.0),
                    temperature: parseFloat(document.getElementById('v-xtts-temperature')?.value || 0.75),
                    repetition_penalty: parseFloat(document.getElementById('v-xtts-repetition_penalty')?.value || 5.0),
                    top_k: parseInt(document.getElementById('v-xtts-topk')?.value || 50),
                    top_p: parseFloat(document.getElementById('v-xtts-topp')?.value || 0.85),
                    length_penalty: parseFloat(document.getElementById('v-xtts-length-penalty')?.value || 1.0)
                };

                saveAudioConfig().then(() => {
                    populateAudioUI();
                    if (sel) sel.value = customName;
                    if (window.showToast) window.showToast(`Saved as new custom preset '${customName}'!`, "success");
                });
            }, defName);
            return;
        }

        presets[name] = {
            speed: parseFloat(document.getElementById('v-xtts-speed')?.value || 1.0),
            temperature: parseFloat(document.getElementById('v-xtts-temperature')?.value || 0.75),
            repetition_penalty: parseFloat(document.getElementById('v-xtts-repetition_penalty')?.value || 5.0),
            top_k: parseInt(document.getElementById('v-xtts-topk')?.value || 50),
            top_p: parseFloat(document.getElementById('v-xtts-topp')?.value || 0.85),
            length_penalty: parseFloat(document.getElementById('v-xtts-length-penalty')?.value || 1.0)
        };

        saveAudioConfig().then(() => {
            if (window.showToast) window.showToast(`Inference Preset '${name}' updated!`, "success");
        });
    };

    // ── Rename Selected Inference Preset ─────────────────────────────────────
    window.renameXTTSInferencePreset = function () {
        const sel = document.getElementById('v-xtts-inference-preset');
        const oldName = sel ? sel.value : '';
        if (!oldName) {
            if (window.showToast) window.showToast("No preset selected.", "error");
            return;
        }

        const isDefault = window.isDefaultPresetName ? window.isDefaultPresetName(oldName, BUILTIN_XTTS_INFERENCE_KEYS) : BUILTIN_XTTS_INFERENCE_KEYS.includes(oldName);
        if (isDefault) {
            if (window.showToast) window.showToast("Cannot rename a built-in default preset. Create a New preset first.", "warning");
            else alert("Cannot rename a built-in default preset. Create a New preset first.");
            return;
        }

        const presets = _getInferencePresets();
        const promptFn = window.hecosPrompt || prompt;

        promptFn(`Rename XTTS Inference Preset '${oldName}' to:`, function (newName) {
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
            if (cfg.xtts_presets) {
                for (const k in cfg.xtts_presets) {
                    if (cfg.xtts_presets[k].inference_preset === oldName) {
                        cfg.xtts_presets[k].inference_preset = newName;
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

    // ── Reset Inference Parameters to Defaults ──────────────────────────────
    window.resetXTTSInferencePreset = function () {
        const sel = document.getElementById('v-xtts-inference-preset');
        const name = sel ? sel.value : '';
        const presets = _getInferencePresets();

        if (name && presets[name]) {
            const p = presets[name];
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

            if (window.showToast) window.showToast(`Inference parameters reloaded from '${name}'.`, 'info');
        } else {
            if (document.getElementById('v-xtts-speed')) document.getElementById('v-xtts-speed').value = 1.0;
            if (document.getElementById('v-xtts-temperature')) document.getElementById('v-xtts-temperature').value = 0.75;
            if (document.getElementById('v-xtts-repetition_penalty')) document.getElementById('v-xtts-repetition_penalty').value = 5.0;
            if (document.getElementById('v-xtts-topk')) document.getElementById('v-xtts-topk').value = 50;
            if (document.getElementById('v-xtts-topp')) document.getElementById('v-xtts-topp').value = 0.85;
            if (document.getElementById('v-xtts-length-penalty')) document.getElementById('v-xtts-length-penalty').value = 1.0;

            document.getElementById('v-xtts-speed')?.dispatchEvent(new Event('input'));
            document.getElementById('v-xtts-temperature')?.dispatchEvent(new Event('input'));
            document.getElementById('v-xtts-repetition_penalty')?.dispatchEvent(new Event('input'));
            document.getElementById('v-xtts-topk')?.dispatchEvent(new Event('input'));
            document.getElementById('v-xtts-topp')?.dispatchEvent(new Event('input'));
            document.getElementById('v-xtts-length-penalty')?.dispatchEvent(new Event('input'));

            if (sel) sel.value = '';
            if (window.showToast) window.showToast("Inference parameters reset to standard defaults.", "info");
        }
    };

    // ── Delete Selected Inference Preset ─────────────────────────────────────
    window.deleteXTTSInferencePreset = function () {
        const sel = document.getElementById('v-xtts-inference-preset');
        const name = sel ? sel.value : '';
        if (!name) {
            if (window.showToast) window.showToast("No preset selected.", "error");
            return;
        }

        const isDefault = window.isDefaultPresetName ? window.isDefaultPresetName(name, BUILTIN_XTTS_INFERENCE_KEYS) : BUILTIN_XTTS_INFERENCE_KEYS.includes(name);
        if (isDefault) {
            if (window.showToast) window.showToast("Cannot delete a built-in default preset.", "error");
            else alert("Cannot delete a built-in default preset.");
            return;
        }

        window.hecosConfirm(`Do you want to delete the Inference Preset '${name}'?`, function () {
            const presets = _getInferencePresets();
            if (presets[name]) {
                delete presets[name];
                saveAudioConfig().then(() => {
                    populateAudioUI();
                    if (window.showToast) window.showToast(`Preset '${name}' deleted.`, "info");
                });
            }
        });
    };

    // ── Load Preset Values into Sliders & Inputs ─────────────────────────────
    window.loadXTTSInferencePreset = function () {
        const sel = document.getElementById('v-xtts-inference-preset');
        const name = sel ? sel.value : '';
        const presets = _getInferencePresets();
        if (!name || !presets[name]) return;

        const p = presets[name];
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

})();
