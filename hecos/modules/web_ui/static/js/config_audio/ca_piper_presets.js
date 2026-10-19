/**
 * ca_piper_presets.js
 * ─────────────────────────────────────────────────────────────────────────────
 * Frontend module for Piper Inference Parameters Presets & Volume Management.
 * Modularized to adhere to Hecos architectural standards (<200 lines).
 * ─────────────────────────────────────────────────────────────────────────────
 */

(function () {
    'use strict';

    // ── Built-in Fallback Presets ─────────────────────────────────────────────
    const DEFAULT_PIPER_INFERENCE_PRESETS = {
        "Standard & Balanced": { speed: 1.0, sentence_silence: 0.2, noise_scale: 0.67, noise_w: 0.8, volume: 1.0 },
        "Expressive & Dynamic": { speed: 1.05, sentence_silence: 0.25, noise_scale: 1.2, noise_w: 1.2, volume: 1.0 },
        "Fast & Direct": { speed: 1.35, sentence_silence: 0.05, noise_scale: 0.6, noise_w: 0.7, volume: 1.0 },
        "Stable & Monotone": { speed: 1.0, sentence_silence: 0.15, noise_scale: 0.0, noise_w: 0.0, volume: 1.0 },
        "Creative & Wild": { speed: 1.15, sentence_silence: 0.35, noise_scale: 1.6, noise_w: 1.5, volume: 1.0 }
    };

    function _getPresets() {
        if (!window.audioConfig) window.audioConfig = {};
        if (!window.audioConfig.piper_inference_presets || Object.keys(window.audioConfig.piper_inference_presets).length === 0) {
            window.audioConfig.piper_inference_presets = JSON.parse(JSON.stringify(DEFAULT_PIPER_INFERENCE_PRESETS));
        }
        return window.audioConfig.piper_inference_presets;
    }

    // ── Populate Piper Inference Presets Dropdown ─────────────────────────────
    window.populatePiperInferencePresets = function () {
        const sel = document.getElementById('v-piper-inference-preset');
        if (!sel) return;

        const presets = _getPresets();
        const current = window.audioConfig.piper_current_inference_preset || '';
        
        sel.innerHTML = '<option value="">-- No Preset Selected --</option>';
        for (const pName in presets) {
            const opt = document.createElement('option');
            opt.value = pName;
            opt.textContent = pName;
            if (pName === current) opt.selected = true;
            sel.appendChild(opt);
        }
    };

    // ── Save Current Parameters as New Preset ────────────────────────────────
    window.savePiperInferencePreset = function () {
        const promptFn = window.hecosPrompt || prompt;
        promptFn("Piper Inference Preset Name (e.g. 'Fast & Direct', 'Creative & Wild'):", function (name) {
            if (!name || !name.trim()) return;
            name = name.trim();
            const presets = _getPresets();

            const getF = (id, def) => {
                const el = document.getElementById(id);
                return (el && el.value !== '' && !isNaN(parseFloat(el.value))) ? parseFloat(el.value) : def;
            };

            presets[name] = {
                speed: getF('v-speed', 1.0),
                sentence_silence: getF('v-silence', 0.2),
                noise_scale: getF('v-noise', 0.67),
                noise_w: getF('v-noisew', 0.8),
                volume: getF('v-volume', 1.0)
            };

            window.audioConfig.piper_current_inference_preset = name;

            if (typeof window.saveAudioConfig === 'function') {
                window.saveAudioConfig().then(() => {
                    window.populatePiperInferencePresets();
                    const sel = document.getElementById('v-piper-inference-preset');
                    if (sel) sel.value = name;
                    if (window.showToast) window.showToast(`Piper Preset '${name}' saved!`, 'success');
                });
            }
        });
    };

    // ── Update Currently Selected Preset ─────────────────────────────────────
    window.updatePiperInferencePreset = function () {
        const sel = document.getElementById('v-piper-inference-preset');
        const name = sel ? sel.value : '';
        if (!name) {
            if (window.showToast) window.showToast('Please select an Inference Preset to update.', 'error');
            else alert('Please select an Inference Preset to update.');
            return;
        }

        const presets = _getPresets();
        const getF = (id, def) => {
            const el = document.getElementById(id);
            return (el && el.value !== '' && !isNaN(parseFloat(el.value))) ? parseFloat(el.value) : def;
        };

        presets[name] = {
            speed: getF('v-speed', 1.0),
            sentence_silence: getF('v-silence', 0.2),
            noise_scale: getF('v-noise', 0.67),
            noise_w: getF('v-noisew', 0.8),
            volume: getF('v-volume', 1.0)
        };

        window.audioConfig.piper_current_inference_preset = name;

        if (typeof window.saveAudioConfig === 'function') {
            window.saveAudioConfig().then(() => {
                if (window.showToast) window.showToast(`Piper Preset '${name}' updated!`, 'success');
            });
        }
    };

    // ── Delete Selected Preset ───────────────────────────────────────────────
    window.deletePiperInferencePreset = function () {
        const sel = document.getElementById('v-piper-inference-preset');
        const name = sel ? sel.value : '';
        if (!name) {
            if (window.showToast) window.showToast('No preset selected.', 'error');
            else alert('No preset selected.');
            return;
        }

        const confirmFn = window.hecosConfirm || confirm;
        confirmFn(`Do you want to delete the Inference Preset '${name}'?`, function () {
            const presets = _getPresets();
            if (presets[name]) {
                delete presets[name];
                if (window.audioConfig.piper_current_inference_preset === name) {
                    window.audioConfig.piper_current_inference_preset = '';
                }
                if (typeof window.saveAudioConfig === 'function') {
                    window.saveAudioConfig().then(() => {
                        window.populatePiperInferencePresets();
                        if (window.showToast) window.showToast(`Preset '${name}' deleted.`, 'info');
                    });
                }
            }
        });
    };

    // ── Load Preset Values into Sliders & Inputs ─────────────────────────────
    window.loadPiperInferencePreset = function () {
        const sel = document.getElementById('v-piper-inference-preset');
        const name = sel ? sel.value : '';
        if (!name) {
            if (window.audioConfig) window.audioConfig.piper_current_inference_preset = '';
            return;
        }

        const presets = _getPresets();
        const p = presets[name];
        if (!p) return;

        const setValAndRange = (id, val) => {
            if (val === undefined || isNaN(val)) return;
            const input = document.getElementById(id);
            const range = document.getElementById(id + '-range');
            if (input) input.value = val;
            if (range) range.value = val;
        };

        if (p.speed !== undefined) setValAndRange('v-speed', p.speed);
        if (p.sentence_silence !== undefined) setValAndRange('v-silence', p.sentence_silence);
        if (p.noise_scale !== undefined) setValAndRange('v-noise', p.noise_scale);
        if (p.noise_w !== undefined) setValAndRange('v-noisew', p.noise_w);
        if (p.volume !== undefined) setValAndRange('v-volume', p.volume);

        if (window.audioConfig) window.audioConfig.piper_current_inference_preset = name;

        if (window.showToast) window.showToast(`Loaded preset '${name}'`, 'info');
    };

    // Auto-populate when DOM is ready
    document.addEventListener('DOMContentLoaded', () => {
        setTimeout(window.populatePiperInferencePresets, 100);
    });

})();
