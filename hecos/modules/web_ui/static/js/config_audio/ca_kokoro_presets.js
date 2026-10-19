/**
 * ca_kokoro_presets.js
 * ─────────────────────────────────────────────────────────────────────────────
 * Frontend module for Kokoro Configuration Presets (global voice persona profiles).
 * Complements ca_kokoro_inference.js (inference hyper-parameters).
 * Modularized to adhere to Hecos architectural standards (<200 lines).
 * ─────────────────────────────────────────────────────────────────────────────
 */

(function () {
    'use strict';

    // ── Save Current Settings as New Configuration Preset ───────────────────
    window.saveKokoroPreset = function () {
        const promptFn = window.hecosPrompt || prompt;
        promptFn("Kokoro Preset Name (e.g. 'Alice Italian', 'Heart Fast Narrator'):", function (name) {
            if (!name || !name.trim()) return;
            name = name.trim();
            if (!window.audioConfig) window.audioConfig = {};
            if (!window.audioConfig.kokoro_presets) window.audioConfig.kokoro_presets = {};

            const voice = (document.getElementById('v-kokoro-voice')?.value || 'af_heart').trim();
            const blendVoice = (document.getElementById('v-kokoro-blend-voice')?.value || '').trim();
            const langCode = (document.getElementById('v-kokoro-lang')?.value || 'auto').trim();
            const infPreset = (document.getElementById('v-kokoro-inference-preset')?.value || '').trim();

            window.audioConfig.kokoro_presets[name] = {
                voice: voice,
                blend_voice: blendVoice,
                lang_code: langCode,
                inference_preset: infPreset,
                speed: parseFloat(document.getElementById('v-kokoro-speed')?.value || 1.0),
                alpha: parseFloat(document.getElementById('v-kokoro-alpha')?.value || 1.0),
                beta: parseFloat(document.getElementById('v-kokoro-beta')?.value || 1.0),
                sentence_silence: parseFloat(document.getElementById('v-kokoro-silence')?.value || 0.0),
                volume: parseFloat(document.getElementById('v-kokoro-volume')?.value || 1.0),
                normalize: document.getElementById('v-kokoro-normalize')?.checked ?? true,
                model_path: (document.getElementById('v-kokoro-model')?.value || '').trim()
            };

            if (!window.audioConfig.kokoro) window.audioConfig.kokoro = {};
            window.audioConfig.kokoro.current_preset = name;
            window.audioConfig.kokoro.current_inference_preset = infPreset;

            if (typeof window.saveAudioConfig === 'function') {
                window.saveAudioConfig().then(() => {
                    if (typeof window.populateAudioUI === 'function') window.populateAudioUI();
                    const sel = document.getElementById('v-kokoro-preset');
                    if (sel) sel.value = name;
                    if (window.showToast) window.showToast(`Preset '${name}' saved successfully!`, 'success');
                });
            }
        });
    };

    // ── Update Currently Selected Configuration Preset ───────────────────────
    window.updateKokoroPreset = function () {
        const name = document.getElementById('v-kokoro-preset')?.value;
        if (!name || name === 'default') {
            if (window.showToast) window.showToast("Select a custom preset to update first, or create a New one.", "error");
            else alert("Select a custom preset to update first, or create a New one.");
            return;
        }

        if (!window.audioConfig) window.audioConfig = {};
        if (!window.audioConfig.kokoro_presets) window.audioConfig.kokoro_presets = {};

        const voice = (document.getElementById('v-kokoro-voice')?.value || 'af_heart').trim();
        const blendVoice = (document.getElementById('v-kokoro-blend-voice')?.value || '').trim();
        const langCode = (document.getElementById('v-kokoro-lang')?.value || 'auto').trim();
        const infPreset = (document.getElementById('v-kokoro-inference-preset')?.value || '').trim();

        window.audioConfig.kokoro_presets[name] = {
            voice: voice,
            blend_voice: blendVoice,
            lang_code: langCode,
            inference_preset: infPreset,
            speed: parseFloat(document.getElementById('v-kokoro-speed')?.value || 1.0),
            alpha: parseFloat(document.getElementById('v-kokoro-alpha')?.value || 1.0),
            beta: parseFloat(document.getElementById('v-kokoro-beta')?.value || 1.0),
            sentence_silence: parseFloat(document.getElementById('v-kokoro-silence')?.value || 0.0),
            volume: parseFloat(document.getElementById('v-kokoro-volume')?.value || 1.0),
            normalize: document.getElementById('v-kokoro-normalize')?.checked ?? true,
            model_path: (document.getElementById('v-kokoro-model')?.value || '').trim()
        };

        if (!window.audioConfig.kokoro) window.audioConfig.kokoro = {};
        window.audioConfig.kokoro.current_preset = name;
        window.audioConfig.kokoro.current_inference_preset = infPreset;

        if (typeof window.saveAudioConfig === 'function') {
            window.saveAudioConfig().then(() => {
                if (window.showToast) window.showToast(`Preset '${name}' updated!`, 'success');
            });
        }
    };

    // ── Reset to Defaults ───────────────────────────────────────────────────
    window.resetKokoroConfig = function () {
        const confirmFn = window.hecosConfirm || confirm;
        confirmFn("Reset all Kokoro parameters to their default values?", function () {
            const setVal = (id, val) => {
                const el = document.getElementById(id);
                if (el) el.value = val;
                const rng = document.getElementById(id + '-range');
                if (rng) rng.value = val;
            };

            setVal('v-kokoro-voice', 'af_heart');
            setVal('v-kokoro-blend-voice', '');
            setVal('v-kokoro-lang', 'auto');
            setVal('v-kokoro-speed', 1.0);
            setVal('v-kokoro-alpha', 1.0);
            setVal('v-kokoro-beta', 1.0);
            setVal('v-kokoro-silence', 0.0);
            setVal('v-kokoro-volume', 1.0);
            const normCheck = document.getElementById('v-kokoro-normalize');
            if (normCheck) normCheck.checked = true;

            const pSel = document.getElementById('v-kokoro-preset');
            if (pSel) pSel.value = 'default';
            const infSel = document.getElementById('v-kokoro-inference-preset');
            if (infSel) infSel.value = '';

            if (typeof window.syncKokoroBlendVoiceOptions === 'function') window.syncKokoroBlendVoiceOptions();
            if (typeof window.onKokoroBlendVoiceChange === 'function') window.onKokoroBlendVoiceChange();

            if (window.audioConfig?.kokoro) {
                window.audioConfig.kokoro.current_preset = 'default';
                window.audioConfig.kokoro.current_inference_preset = '';
            }

            if (typeof window.saveAudioConfig === 'function') {
                window.saveAudioConfig().then(() => {
                    if (window.showToast) window.showToast("Kokoro configuration reset to defaults.", "info");
                });
            }
        });
    };

    // ── Delete Selected Preset ───────────────────────────────────────────────
    window.deleteKokoroPreset = function () {
        const name = document.getElementById('v-kokoro-preset')?.value;
        if (!name || name === 'default') {
            if (window.showToast) window.showToast("Cannot delete the default preset.", "error");
            else alert("Cannot delete the default preset.");
            return;
        }

        const confirmFn = window.hecosConfirm || confirm;
        confirmFn(`Are you sure you want to delete the preset '${name}'?`, function () {
            if (window.audioConfig?.kokoro_presets && window.audioConfig.kokoro_presets[name]) {
                delete window.audioConfig.kokoro_presets[name];
                if (!window.audioConfig.kokoro) window.audioConfig.kokoro = {};
                window.audioConfig.kokoro.current_preset = 'default';
                if (typeof window.saveAudioConfig === 'function') {
                    window.saveAudioConfig().then(() => {
                        if (typeof window.populateAudioUI === 'function') window.populateAudioUI();
                        if (window.showToast) window.showToast("Preset deleted.", "info");
                    });
                }
            }
        });
    };

    // ── Load Selected Configuration Preset ───────────────────────────────────
    window.loadKokoroPreset = function () {
        const name = document.getElementById('v-kokoro-preset')?.value;
        if (!name || name === 'default' || !window.audioConfig?.kokoro_presets || !window.audioConfig.kokoro_presets[name]) {
            if (name === 'default' && window.audioConfig?.kokoro) {
                window.audioConfig.kokoro.current_preset = 'default';
                if (typeof window.saveAudioConfig === 'function') window.saveAudioConfig();
            }
            return;
        }

        const p = window.audioConfig.kokoro_presets[name];
        const setValAndRange = (id, val) => {
            if (val === undefined || isNaN(val)) return;
            const input = document.getElementById(id);
            const range = document.getElementById(id + '-range');
            if (input) input.value = val;
            if (range) range.value = val;
        };

        if (p.voice && document.getElementById('v-kokoro-voice')) {
            document.getElementById('v-kokoro-voice').value = p.voice;
        }
        if (p.lang_code && document.getElementById('v-kokoro-lang')) {
            document.getElementById('v-kokoro-lang').value = p.lang_code;
        }
        if (p.blend_voice !== undefined && document.getElementById('v-kokoro-blend-voice')) {
            document.getElementById('v-kokoro-blend-voice').value = p.blend_voice;
        }
        if (p.model_path !== undefined && document.getElementById('v-kokoro-model')) {
            document.getElementById('v-kokoro-model').value = p.model_path;
        }

        setValAndRange('v-kokoro-speed', p.speed ?? 1.0);
        setValAndRange('v-kokoro-alpha', p.alpha ?? 1.0);
        setValAndRange('v-kokoro-beta', p.beta ?? 1.0);
        setValAndRange('v-kokoro-silence', p.sentence_silence ?? 0.0);
        setValAndRange('v-kokoro-volume', p.volume ?? 1.0);
        if (p.normalize !== undefined && document.getElementById('v-kokoro-normalize')) {
            document.getElementById('v-kokoro-normalize').checked = p.normalize;
        }

        // Match associated inference preset
        const infPreset = p.inference_preset || '';
        const infSel = document.getElementById('v-kokoro-inference-preset');
        if (infSel) infSel.value = infPreset;

        if (typeof window.syncKokoroBlendVoiceOptions === 'function') window.syncKokoroBlendVoiceOptions();
        if (typeof window.onKokoroBlendVoiceChange === 'function') window.onKokoroBlendVoiceChange();

        if (!window.audioConfig.kokoro) window.audioConfig.kokoro = {};
        window.audioConfig.kokoro.current_preset = name;
        window.audioConfig.kokoro.current_inference_preset = infPreset;

        if (typeof window.saveAudioConfig === 'function') {
            window.saveAudioConfig().then(() => {
                if (window.showToast) window.showToast(`Loaded preset '${name}'`, 'info');
            });
        }
    };

})();
