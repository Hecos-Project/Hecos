/**
 * ca_kokoro_presets.js
 * ─────────────────────────────────────────────────────────────────────────────
 * Frontend module for Kokoro Configuration Presets (global voice persona profiles).
 * Complements ca_kokoro_inference.js (inference hyper-parameters).
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
        if (!cfg.kokoro_presets) cfg.kokoro_presets = {};
        return cfg.kokoro_presets;
    }

    // ── Save Current Settings as New Configuration Preset ───────────────────
    window.saveKokoroPreset = function () {
        const presets = _getConfigPresets();
        const defName = window.getNextCustomPresetName ? window.getNextCustomPresetName(presets, 'custom') : 'custom_1';
        const promptFn = window.hecosPrompt || prompt;

        promptFn("Kokoro Configuration Preset Name:", function (name) {
            if (!name || !name.trim()) return;
            name = name.trim();
            const cfg = _getAudioConfig();

            const voice = (document.getElementById('v-kokoro-voice')?.value || 'af_heart').trim();
            const blendVoice = (document.getElementById('v-kokoro-blend-voice')?.value || '').trim();
            const langCode = (document.getElementById('v-kokoro-lang')?.value || 'auto').trim();
            const infPreset = (document.getElementById('v-kokoro-inference-preset')?.value || '').trim();

            presets[name] = {
                voice: voice,
                blend_voice: blendVoice,
                lang_code: langCode,
                inference_preset: infPreset,
                speed: parseFloat(document.getElementById('v-kokoro-speed')?.value || 0.95),
                alpha: parseFloat(document.getElementById('v-kokoro-alpha')?.value || 1.0),
                beta: parseFloat(document.getElementById('v-kokoro-beta')?.value || 1.0),
                sentence_silence: parseFloat(document.getElementById('v-kokoro-silence')?.value || 0.15),
                volume: parseFloat(document.getElementById('v-kokoro-volume')?.value || 1.0),
                normalize: document.getElementById('v-kokoro-normalize')?.checked ?? true,
                model_path: (document.getElementById('v-kokoro-model')?.value || '').trim()
            };

            if (!cfg.kokoro) cfg.kokoro = {};
            cfg.kokoro.current_preset = name;
            cfg.kokoro.current_inference_preset = infPreset;

            const sel = document.getElementById('v-kokoro-preset');
            if (sel) {
                let opt = Array.from(sel.options).find(o => o.value === name);
                if (!opt) {
                    opt = document.createElement('option');
                    opt.value = name;
                    opt.textContent = name;
                    sel.appendChild(opt);
                }
                sel.value = name;
            }

            if (typeof window.saveAudioConfig === 'function') {
                window.saveAudioConfig().then(() => {
                    if (typeof window.populateAudioUI === 'function') window.populateAudioUI();
                    const s = document.getElementById('v-kokoro-preset');
                    if (s) s.value = name;
                    if (window.showToast) window.showToast(`Preset '${name}' saved successfully!`, 'success');
                });
            }
        }, defName);
    };

    // ── Update Currently Selected Configuration Preset ───────────────────────
    window.updateKokoroPreset = function () {
        const sel = document.getElementById('v-kokoro-preset');
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

                const voice = (document.getElementById('v-kokoro-voice')?.value || 'af_heart').trim();
                const blendVoice = (document.getElementById('v-kokoro-blend-voice')?.value || '').trim();
                const langCode = (document.getElementById('v-kokoro-lang')?.value || 'auto').trim();
                const infPreset = (document.getElementById('v-kokoro-inference-preset')?.value || '').trim();

                presets[customName] = {
                    voice: voice,
                    blend_voice: blendVoice,
                    lang_code: langCode,
                    inference_preset: infPreset,
                    speed: parseFloat(document.getElementById('v-kokoro-speed')?.value || 0.95),
                    alpha: parseFloat(document.getElementById('v-kokoro-alpha')?.value || 1.0),
                    beta: parseFloat(document.getElementById('v-kokoro-beta')?.value || 1.0),
                    sentence_silence: parseFloat(document.getElementById('v-kokoro-silence')?.value || 0.15),
                    volume: parseFloat(document.getElementById('v-kokoro-volume')?.value || 1.0),
                    normalize: document.getElementById('v-kokoro-normalize')?.checked ?? true,
                    model_path: (document.getElementById('v-kokoro-model')?.value || '').trim()
                };

                if (!cfg.kokoro) cfg.kokoro = {};
                cfg.kokoro.current_preset = customName;
                cfg.kokoro.current_inference_preset = infPreset;

                if (typeof window.saveAudioConfig === 'function') {
                    window.saveAudioConfig().then(() => {
                        if (typeof window.populateAudioUI === 'function') window.populateAudioUI();
                        if (sel) sel.value = customName;
                        if (window.showToast) window.showToast(`Saved as new custom preset '${customName}'!`, 'success');
                    });
                }
            }, defName);
            return;
        }

        const cfg = _getAudioConfig();
        const voice = (document.getElementById('v-kokoro-voice')?.value || 'af_heart').trim();
        const blendVoice = (document.getElementById('v-kokoro-blend-voice')?.value || '').trim();
        const langCode = (document.getElementById('v-kokoro-lang')?.value || 'auto').trim();
        const infPreset = (document.getElementById('v-kokoro-inference-preset')?.value || '').trim();

        presets[name] = {
            voice: voice,
            blend_voice: blendVoice,
            lang_code: langCode,
            inference_preset: infPreset,
            speed: parseFloat(document.getElementById('v-kokoro-speed')?.value || 0.95),
            alpha: parseFloat(document.getElementById('v-kokoro-alpha')?.value || 1.0),
            beta: parseFloat(document.getElementById('v-kokoro-beta')?.value || 1.0),
            sentence_silence: parseFloat(document.getElementById('v-kokoro-silence')?.value || 0.15),
            volume: parseFloat(document.getElementById('v-kokoro-volume')?.value || 1.0),
            normalize: document.getElementById('v-kokoro-normalize')?.checked ?? true,
            model_path: (document.getElementById('v-kokoro-model')?.value || '').trim()
        };

        if (!cfg.kokoro) cfg.kokoro = {};
        cfg.kokoro.current_preset = name;
        cfg.kokoro.current_inference_preset = infPreset;

        if (typeof window.saveAudioConfig === 'function') {
            window.saveAudioConfig().then(() => {
                if (window.showToast) window.showToast(`Preset '${name}' updated!`, 'success');
            });
        }
    };

    // ── Rename Selected Configuration Preset ────────────────────────────────
    window.renameKokoroPreset = function () {
        const sel = document.getElementById('v-kokoro-preset');
        const oldName = sel ? sel.value : '';
        if (!oldName || oldName === 'default' || oldName === 'Default') {
            if (window.showToast) window.showToast("Cannot rename the default preset.", "warning");
            else alert("Cannot rename the default preset.");
            return;
        }

        const presets = _getConfigPresets();
        const promptFn = window.hecosPrompt || prompt;

        promptFn(`Rename Kokoro Preset '${oldName}' to:`, function (newName) {
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
            if (cfg.kokoro && cfg.kokoro.current_preset === oldName) {
                cfg.kokoro.current_preset = newName;
            }

            if (typeof window.saveAudioConfig === 'function') {
                window.saveAudioConfig().then(() => {
                    if (typeof window.populateAudioUI === 'function') window.populateAudioUI();
                    if (sel) sel.value = newName;
                    if (window.showToast) window.showToast(`Preset renamed to '${newName}'!`, 'success');
                });
            }
        }, oldName);
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
            setVal('v-kokoro-speed', 0.95);
            setVal('v-kokoro-alpha', 1.0);
            setVal('v-kokoro-beta', 1.0);
            setVal('v-kokoro-silence', 0.15);
            setVal('v-kokoro-volume', 1.0);
            const normCheck = document.getElementById('v-kokoro-normalize');
            if (normCheck) normCheck.checked = true;

            const pSel = document.getElementById('v-kokoro-preset');
            if (pSel) pSel.value = 'default';
            const infSel = document.getElementById('v-kokoro-inference-preset');
            if (infSel) infSel.value = '';

            if (typeof window.syncKokoroBlendVoiceOptions === 'function') window.syncKokoroBlendVoiceOptions();
            if (typeof window.onKokoroBlendVoiceChange === 'function') window.onKokoroBlendVoiceChange();

            const cfg = _getAudioConfig();
            if (cfg.kokoro) {
                cfg.kokoro.current_preset = 'default';
                cfg.kokoro.current_inference_preset = '';
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
        const sel = document.getElementById('v-kokoro-preset');
        const name = sel ? sel.value : '';
        if (!name || name === 'default' || name === 'Default') {
            if (window.showToast) window.showToast("Cannot delete the default preset.", "error");
            else alert("Cannot delete the default preset.");
            return;
        }

        const confirmFn = window.hecosConfirm || confirm;
        confirmFn(`Are you sure you want to delete the preset '${name}'?`, function () {
            const cfg = _getAudioConfig();
            if (cfg.kokoro_presets && cfg.kokoro_presets[name]) {
                delete cfg.kokoro_presets[name];
                cfg._allow_empty_presets = true;
                if (!cfg.kokoro) cfg.kokoro = {};
                cfg.kokoro.current_preset = 'default';
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
        const cfg = _getAudioConfig();
        if (!name || name === 'default' || !cfg.kokoro_presets || !cfg.kokoro_presets[name]) {
            if (name === 'default' && cfg.kokoro) {
                cfg.kokoro.current_preset = 'default';
                if (typeof window.saveAudioConfig === 'function') window.saveAudioConfig();
            }
            return;
        }

        const p = cfg.kokoro_presets[name];
        const setValAndRange = (id, val) => {
            if (val === undefined || isNaN(val)) return;
            const input = document.getElementById(id);
            const range = document.getElementById(id + '-range');
            if (input) input.value = val;
            if (range) range.value = val;
        };

        if (p.voice && document.getElementById('v-kokoro-voice')) {
            const vSel = document.getElementById('v-kokoro-voice');
            let hasOpt = Array.from(vSel.options).some(o => o.value === p.voice);
            if (!hasOpt) {
                const opt = document.createElement('option');
                opt.value = p.voice;
                opt.textContent = `🎭 ${p.voice} (Custom Cloned)`;
                vSel.appendChild(opt);
            }
            vSel.value = p.voice;
        }
        if (p.lang_code && document.getElementById('v-kokoro-lang')) {
            document.getElementById('v-kokoro-lang').value = p.lang_code;
        }
        if (p.blend_voice !== undefined && document.getElementById('v-kokoro-blend-voice')) {
            const bSel = document.getElementById('v-kokoro-blend-voice');
            if (p.blend_voice) {
                let hasOpt = Array.from(bSel.options).some(o => o.value === p.blend_voice);
                if (!hasOpt) {
                    const opt = document.createElement('option');
                    opt.value = p.blend_voice;
                    opt.textContent = `🎭 ${p.blend_voice} (Custom Cloned)`;
                    bSel.appendChild(opt);
                }
            }
            bSel.value = p.blend_voice;
        }
        if (p.model_path !== undefined && document.getElementById('v-kokoro-model')) {
            document.getElementById('v-kokoro-model').value = p.model_path;
        }

        setValAndRange('v-kokoro-speed', p.speed ?? 0.95);
        setValAndRange('v-kokoro-alpha', p.alpha ?? 1.0);
        setValAndRange('v-kokoro-beta', p.beta ?? 1.0);
        setValAndRange('v-kokoro-silence', p.sentence_silence ?? 0.15);
        setValAndRange('v-kokoro-volume', p.volume ?? 1.0);
        if (p.normalize !== undefined && document.getElementById('v-kokoro-normalize')) {
            document.getElementById('v-kokoro-normalize').checked = p.normalize;
        }

        const infPreset = p.inference_preset || '';
        const infSel = document.getElementById('v-kokoro-inference-preset');
        if (infSel) infSel.value = infPreset;

        if (typeof window.syncKokoroBlendVoiceOptions === 'function') window.syncKokoroBlendVoiceOptions();
        if (typeof window.onKokoroBlendVoiceChange === 'function') window.onKokoroBlendVoiceChange();
        if (typeof window.loadKokoroInstalledClones === 'function') window.loadKokoroInstalledClones();

        if (!cfg.kokoro) cfg.kokoro = {};
        cfg.kokoro.current_preset = name;
        cfg.kokoro.current_inference_preset = infPreset;

        if (typeof window.saveAudioConfig === 'function') {
            window.saveAudioConfig().then(() => {
                if (window.showToast) window.showToast(`Loaded preset '${name}'`, 'info');
            });
        }
    };

})();
