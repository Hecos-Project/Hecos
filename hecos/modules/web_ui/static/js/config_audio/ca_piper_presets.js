/**
 * ca_piper_presets.js
 * ─────────────────────────────────────────────────────────────────────────────
 * Frontend module for Piper Configuration Presets & Inference Parameters Presets.
 * Follows Hecos architectural standards with full preset lifecycle:
 * New, Update (with default overwrite protection), Rename, Reset, Delete.
 * ─────────────────────────────────────────────────────────────────────────────
 */

(function () {
    'use strict';

    // ── Built-in Fallback Inference Presets ────────────────────────────────────
    const DEFAULT_PIPER_INFERENCE_PRESETS = {
        "Standard & Balanced": { speed: 1.0, sentence_silence: 0.2, noise_scale: 0.67, noise_w: 0.8, volume: 1.0 },
        "Expressive & Dynamic": { speed: 1.05, sentence_silence: 0.25, noise_scale: 1.2, noise_w: 1.2, volume: 1.0 },
        "Fast & Direct": { speed: 1.35, sentence_silence: 0.05, noise_scale: 0.6, noise_w: 0.7, volume: 1.0 },
        "Stable & Monotone": { speed: 1.0, sentence_silence: 0.15, noise_scale: 0.0, noise_w: 0.0, volume: 1.0 },
        "Creative & Wild": { speed: 1.15, sentence_silence: 0.35, noise_scale: 1.6, noise_w: 1.5, volume: 1.0 }
    };
    const BUILTIN_INFERENCE_KEYS = Object.keys(DEFAULT_PIPER_INFERENCE_PRESETS);

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
        if (!cfg.piper_inference_presets || Object.keys(cfg.piper_inference_presets).length === 0) {
            cfg.piper_inference_presets = JSON.parse(JSON.stringify(DEFAULT_PIPER_INFERENCE_PRESETS));
        }
        return cfg.piper_inference_presets;
    }

    function _getConfigPresets() {
        const cfg = _getAudioConfig();
        if (!cfg.piper_presets) cfg.piper_presets = {};
        return cfg.piper_presets;
    }

    function _getFloat(id, def) {
        const el = document.getElementById(id);
        return (el && el.value !== '' && !isNaN(parseFloat(el.value))) ? parseFloat(el.value) : def;
    }

    function _getInt(id, def) {
        const el = document.getElementById(id);
        return (el && el.value !== '' && !isNaN(parseInt(el.value))) ? parseInt(el.value) : def;
    }

    function _setValAndRange(id, val) {
        if (val === undefined || isNaN(val)) return;
        const input = document.getElementById(id);
        const range = document.getElementById(id + '-range');
        if (input) input.value = val;
        if (range) range.value = val;
    }

    // ══════════════════════════════════════════════════════════════════════════
    // 1. PIPER CONFIGURATION PRESETS (Global Voice Profile)
    // ══════════════════════════════════════════════════════════════════════════

    window.populatePiperPresets = function () {
        const sel = document.getElementById('v-piper-preset');
        if (!sel) return;

        const presets = _getConfigPresets();
        const cfg = _getAudioConfig();
        const current = cfg.piper_current_preset || 'default';

        sel.innerHTML = '<option value="default">Default</option>';
        for (const pName in presets) {
            const opt = document.createElement('option');
            opt.value = pName;
            opt.textContent = pName;
            if (pName === current) opt.selected = true;
            sel.appendChild(opt);
        }
        if (current === 'default') sel.value = 'default';
        else sel.value = current;
    };

    window.savePiperPreset = function () {
        const presets = _getConfigPresets();
        const defName = window.getNextCustomPresetName ? window.getNextCustomPresetName(presets, 'custom') : 'custom_1';
        const promptFn = window.hecosPrompt || prompt;

        promptFn("Piper Configuration Preset Name:", function (name) {
            if (!name || !name.trim()) return;
            name = name.trim();
            const cfg = _getAudioConfig();

            const onnxModel = (document.getElementById('v-onnx-model')?.value || '').trim();
            const infPreset = (document.getElementById('v-piper-inference-preset')?.value || '').trim();

            presets[name] = {
                onnx_model: onnxModel,
                inference_preset: infPreset,
                speed: _getFloat('v-speed', 1.0),
                sentence_silence: _getFloat('v-silence', 0.2),
                noise_scale: _getFloat('v-noise', 0.67),
                noise_w: _getFloat('v-noisew', 0.8),
                volume: _getFloat('v-volume', 1.0),
                piper_timeout: _getInt('v-timeout', 180),
                piper_autostart: document.getElementById('v-piper-autostart')?.checked ?? true
            };

            cfg.piper_current_preset = name;

            if (typeof window.saveAudioConfig === 'function') {
                window.saveAudioConfig().then(() => {
                    window.populatePiperPresets();
                    const s = document.getElementById('v-piper-preset');
                    if (s) s.value = name;
                    if (window.showToast) window.showToast(`Piper Preset '${name}' saved successfully!`, 'success');
                });
            }
        }, defName);
    };

    window.updatePiperPreset = function () {
        const sel = document.getElementById('v-piper-preset');
        const name = sel ? sel.value : 'default';
        const presets = _getConfigPresets();

        // Protect built-in default
        if (!name || name === 'default' || name === 'Default') {
            const defName = window.getNextCustomPresetName ? window.getNextCustomPresetName(presets, 'custom') : 'custom_1';
            const promptFn = window.hecosPrompt || prompt;
            promptFn("The default preset cannot be overwritten.\nEnter a name to save as a new custom preset:", function (customName) {
                if (!customName || !customName.trim()) return;
                customName = customName.trim();
                const cfg = _getAudioConfig();
                const onnxModel = (document.getElementById('v-onnx-model')?.value || '').trim();
                const infPreset = (document.getElementById('v-piper-inference-preset')?.value || '').trim();

                presets[customName] = {
                    onnx_model: onnxModel,
                    inference_preset: infPreset,
                    speed: _getFloat('v-speed', 1.0),
                    sentence_silence: _getFloat('v-silence', 0.2),
                    noise_scale: _getFloat('v-noise', 0.67),
                    noise_w: _getFloat('v-noisew', 0.8),
                    volume: _getFloat('v-volume', 1.0),
                    piper_timeout: _getInt('v-timeout', 180),
                    piper_autostart: document.getElementById('v-piper-autostart')?.checked ?? true
                };

                cfg.piper_current_preset = customName;

                if (typeof window.saveAudioConfig === 'function') {
                    window.saveAudioConfig().then(() => {
                        window.populatePiperPresets();
                        if (sel) sel.value = customName;
                        if (window.showToast) window.showToast(`Saved as new custom preset '${customName}'!`, 'success');
                    });
                }
            }, defName);
            return;
        }

        const cfg = _getAudioConfig();
        const onnxModel = (document.getElementById('v-onnx-model')?.value || '').trim();
        const infPreset = (document.getElementById('v-piper-inference-preset')?.value || '').trim();

        presets[name] = {
            onnx_model: onnxModel,
            inference_preset: infPreset,
            speed: _getFloat('v-speed', 1.0),
            sentence_silence: _getFloat('v-silence', 0.2),
            noise_scale: _getFloat('v-noise', 0.67),
            noise_w: _getFloat('v-noisew', 0.8),
            volume: _getFloat('v-volume', 1.0),
            piper_timeout: _getInt('v-timeout', 180),
            piper_autostart: document.getElementById('v-piper-autostart')?.checked ?? true
        };

        cfg.piper_current_preset = name;

        if (typeof window.saveAudioConfig === 'function') {
            window.saveAudioConfig().then(() => {
                if (window.showToast) window.showToast(`Piper Preset '${name}' updated!`, 'success');
            });
        }
    };

    window.renamePiperPreset = function () {
        const sel = document.getElementById('v-piper-preset');
        const oldName = sel ? sel.value : '';
        if (!oldName || oldName === 'default' || oldName === 'Default') {
            if (window.showToast) window.showToast("Cannot rename the default preset.", "warning");
            else alert("Cannot rename the default preset.");
            return;
        }

        const presets = _getConfigPresets();
        const promptFn = window.hecosPrompt || prompt;

        promptFn(`Rename Piper Preset '${oldName}' to:`, function (newName) {
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
            if (cfg.piper_current_preset === oldName) {
                cfg.piper_current_preset = newName;
            }

            if (typeof window.saveAudioConfig === 'function') {
                window.saveAudioConfig().then(() => {
                    window.populatePiperPresets();
                    if (sel) sel.value = newName;
                    if (window.showToast) window.showToast(`Preset renamed to '${newName}'!`, 'success');
                });
            }
        }, oldName);
    };

    window.resetPiperConfig = function () {
        const confirmFn = window.hecosConfirm || confirm;
        confirmFn("Reset all Piper parameters to their default values?", function () {
            _setValAndRange('v-speed', 1.0);
            _setValAndRange('v-silence', 0.2);
            _setValAndRange('v-noise', 0.67);
            _setValAndRange('v-noisew', 0.8);
            _setValAndRange('v-volume', 1.0);
            _setValAndRange('v-timeout', 180);

            const infSel = document.getElementById('v-piper-inference-preset');
            if (infSel) infSel.value = '';
            const pSel = document.getElementById('v-piper-preset');
            if (pSel) pSel.value = 'default';

            const cfg = _getAudioConfig();
            cfg.piper_current_preset = 'default';
            cfg.piper_current_inference_preset = '';

            if (typeof window.saveAudioConfig === 'function') {
                window.saveAudioConfig().then(() => {
                    if (window.showToast) window.showToast("Piper configuration reset to defaults.", "info");
                });
            }
        });
    };

    window.deletePiperPreset = function () {
        const sel = document.getElementById('v-piper-preset');
        const name = sel ? sel.value : '';
        if (!name || name === 'default' || name === 'Default') {
            if (window.showToast) window.showToast("Cannot delete the default preset.", "error");
            else alert("Cannot delete the default preset.");
            return;
        }

        const confirmFn = window.hecosConfirm || confirm;
        confirmFn(`Are you sure you want to delete the preset '${name}'?`, function () {
            const presets = _getConfigPresets();
            if (presets[name]) {
                delete presets[name];
                const cfg = _getAudioConfig();
                cfg.piper_current_preset = 'default';
                if (typeof window.saveAudioConfig === 'function') {
                    window.saveAudioConfig().then(() => {
                        window.populatePiperPresets();
                        if (window.showToast) window.showToast(`Preset '${name}' deleted.`, "info");
                    });
                }
            }
        });
    };

    window.loadPiperPreset = function () {
        const sel = document.getElementById('v-piper-preset');
        const name = sel ? sel.value : 'default';
        const presets = _getConfigPresets();
        const cfg = _getAudioConfig();

        if (name === 'default' || !presets[name]) {
            cfg.piper_current_preset = 'default';
            if (typeof window.saveAudioConfig === 'function') window.saveAudioConfig();
            return;
        }

        const p = presets[name];
        if (p.onnx_model && document.getElementById('v-onnx-model')) {
            const mSel = document.getElementById('v-onnx-model');
            const bare = p.onnx_model.split('\\').pop().split('/').pop();
            mSel.value = bare;
        }
        _setValAndRange('v-speed', p.speed ?? 1.0);
        _setValAndRange('v-silence', p.sentence_silence ?? 0.2);
        _setValAndRange('v-noise', p.noise_scale ?? 0.67);
        _setValAndRange('v-noisew', p.noise_w ?? 0.8);
        _setValAndRange('v-volume', p.volume ?? 1.0);
        _setValAndRange('v-timeout', p.piper_timeout ?? 180);

        if (p.piper_autostart !== undefined && document.getElementById('v-piper-autostart')) {
            document.getElementById('v-piper-autostart').checked = p.piper_autostart;
        }

        const infPreset = p.inference_preset || '';
        const infSel = document.getElementById('v-piper-inference-preset');
        if (infSel) infSel.value = infPreset;

        cfg.piper_current_preset = name;
        cfg.piper_current_inference_preset = infPreset;

        if (typeof window.saveAudioConfig === 'function') {
            window.saveAudioConfig().then(() => {
                if (window.showToast) window.showToast(`Loaded Piper Preset '${name}'`, 'info');
            });
        }
    };

    // ══════════════════════════════════════════════════════════════════════════
    // 2. PIPER INFERENCE PARAMETERS PRESETS
    // ══════════════════════════════════════════════════════════════════════════

    window.populatePiperInferencePresets = function () {
        const sel = document.getElementById('v-piper-inference-preset');
        if (!sel) return;

        const presets = _getInferencePresets();
        const cfg = _getAudioConfig();
        const current = cfg.piper_current_inference_preset || '';

        sel.innerHTML = '<option value="">-- No Preset Selected --</option>';
        for (const pName in presets) {
            const opt = document.createElement('option');
            opt.value = pName;
            opt.textContent = pName;
            if (pName === current) opt.selected = true;
            sel.appendChild(opt);
        }
    };

    window.savePiperInferencePreset = function () {
        const presets = _getInferencePresets();
        const defName = window.getNextCustomPresetName ? window.getNextCustomPresetName(presets, 'custom') : 'custom_1';
        const promptFn = window.hecosPrompt || prompt;

        promptFn("Piper Inference Preset Name:", function (name) {
            if (!name || !name.trim()) return;
            name = name.trim();

            presets[name] = {
                speed: _getFloat('v-speed', 1.0),
                sentence_silence: _getFloat('v-silence', 0.2),
                noise_scale: _getFloat('v-noise', 0.67),
                noise_w: _getFloat('v-noisew', 0.8),
                volume: _getFloat('v-volume', 1.0)
            };

            const cfg = _getAudioConfig();
            cfg.piper_current_inference_preset = name;

            if (typeof window.saveAudioConfig === 'function') {
                window.saveAudioConfig().then(() => {
                    window.populatePiperInferencePresets();
                    const sel = document.getElementById('v-piper-inference-preset');
                    if (sel) sel.value = name;
                    if (window.showToast) window.showToast(`Piper Inference Preset '${name}' saved!`, 'success');
                });
            }
        }, defName);
    };

    window.updatePiperInferencePreset = function () {
        const sel = document.getElementById('v-piper-inference-preset');
        const name = sel ? sel.value : '';
        if (!name) {
            if (window.showToast) window.showToast('Please select an Inference Preset to update.', 'error');
            else alert('Please select an Inference Preset to update.');
            return;
        }

        const presets = _getInferencePresets();
        const isDefault = window.isDefaultPresetName ? window.isDefaultPresetName(name, BUILTIN_INFERENCE_KEYS) : BUILTIN_INFERENCE_KEYS.includes(name);

        if (isDefault) {
            const defName = window.getNextCustomPresetName ? window.getNextCustomPresetName(presets, 'custom') : 'custom_1';
            const promptFn = window.hecosPrompt || prompt;
            promptFn(`The default preset '${name}' cannot be overwritten.\nEnter a name to save as a new custom preset:`, function (customName) {
                if (!customName || !customName.trim()) return;
                customName = customName.trim();

                presets[customName] = {
                    speed: _getFloat('v-speed', 1.0),
                    sentence_silence: _getFloat('v-silence', 0.2),
                    noise_scale: _getFloat('v-noise', 0.67),
                    noise_w: _getFloat('v-noisew', 0.8),
                    volume: _getFloat('v-volume', 1.0)
                };

                const cfg = _getAudioConfig();
                cfg.piper_current_inference_preset = customName;

                if (typeof window.saveAudioConfig === 'function') {
                    window.saveAudioConfig().then(() => {
                        window.populatePiperInferencePresets();
                        if (sel) sel.value = customName;
                        if (window.showToast) window.showToast(`Saved as new custom preset '${customName}'!`, 'success');
                    });
                }
            }, defName);
            return;
        }

        presets[name] = {
            speed: _getFloat('v-speed', 1.0),
            sentence_silence: _getFloat('v-silence', 0.2),
            noise_scale: _getFloat('v-noise', 0.67),
            noise_w: _getFloat('v-noisew', 0.8),
            volume: _getFloat('v-volume', 1.0)
        };

        const cfg = _getAudioConfig();
        cfg.piper_current_inference_preset = name;

        if (typeof window.saveAudioConfig === 'function') {
            window.saveAudioConfig().then(() => {
                if (window.showToast) window.showToast(`Piper Inference Preset '${name}' updated!`, 'success');
            });
        }
    };

    window.renamePiperInferencePreset = function () {
        const sel = document.getElementById('v-piper-inference-preset');
        const oldName = sel ? sel.value : '';
        if (!oldName) {
            if (window.showToast) window.showToast('No preset selected.', 'error');
            return;
        }

        const isDefault = window.isDefaultPresetName ? window.isDefaultPresetName(oldName, BUILTIN_INFERENCE_KEYS) : BUILTIN_INFERENCE_KEYS.includes(oldName);
        if (isDefault) {
            if (window.showToast) window.showToast("Cannot rename a built-in default preset. Create a New preset first.", "warning");
            else alert("Cannot rename a built-in default preset. Create a New preset first.");
            return;
        }

        const presets = _getInferencePresets();
        const promptFn = window.hecosPrompt || prompt;

        promptFn(`Rename Piper Inference Preset '${oldName}' to:`, function (newName) {
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
            if (cfg.piper_current_inference_preset === oldName) {
                cfg.piper_current_inference_preset = newName;
            }
            // Update reference in configuration presets if present
            if (cfg.piper_presets) {
                for (const k in cfg.piper_presets) {
                    if (cfg.piper_presets[k].inference_preset === oldName) {
                        cfg.piper_presets[k].inference_preset = newName;
                    }
                }
            }

            if (typeof window.saveAudioConfig === 'function') {
                window.saveAudioConfig().then(() => {
                    window.populatePiperInferencePresets();
                    if (sel) sel.value = newName;
                    if (window.showToast) window.showToast(`Preset renamed to '${newName}'!`, 'success');
                });
            }
        }, oldName);
    };

    window.resetPiperInferencePreset = function () {
        const sel = document.getElementById('v-piper-inference-preset');
        const name = sel ? sel.value : '';
        const presets = _getInferencePresets();

        if (name && presets[name]) {
            const p = presets[name];
            _setValAndRange('v-speed', p.speed ?? 1.0);
            _setValAndRange('v-silence', p.sentence_silence ?? 0.2);
            _setValAndRange('v-noise', p.noise_scale ?? 0.67);
            _setValAndRange('v-noisew', p.noise_w ?? 0.8);
            _setValAndRange('v-volume', p.volume ?? 1.0);
            if (window.showToast) window.showToast(`Inference parameters reloaded from '${name}'.`, 'info');
        } else {
            _setValAndRange('v-speed', 1.0);
            _setValAndRange('v-silence', 0.2);
            _setValAndRange('v-noise', 0.67);
            _setValAndRange('v-noisew', 0.8);
            _setValAndRange('v-volume', 1.0);
            if (sel) sel.value = '';
            if (window.showToast) window.showToast("Inference parameters reset to standard defaults.", "info");
        }
    };

    window.deletePiperInferencePreset = function () {
        const sel = document.getElementById('v-piper-inference-preset');
        const name = sel ? sel.value : '';
        if (!name) {
            if (window.showToast) window.showToast('No preset selected.', 'error');
            else alert('No preset selected.');
            return;
        }

        const isDefault = window.isDefaultPresetName ? window.isDefaultPresetName(name, BUILTIN_INFERENCE_KEYS) : BUILTIN_INFERENCE_KEYS.includes(name);
        if (isDefault) {
            if (window.showToast) window.showToast("Cannot delete a built-in default preset.", "error");
            else alert("Cannot delete a built-in default preset.");
            return;
        }

        const confirmFn = window.hecosConfirm || confirm;
        confirmFn(`Do you want to delete the Inference Preset '${name}'?`, function () {
            const presets = _getInferencePresets();
            if (presets[name]) {
                delete presets[name];
                const cfg = _getAudioConfig();
                if (cfg.piper_current_inference_preset === name) {
                    cfg.piper_current_inference_preset = '';
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

    window.loadPiperInferencePreset = function () {
        const sel = document.getElementById('v-piper-inference-preset');
        const name = sel ? sel.value : '';
        if (!name) {
            const cfg = _getAudioConfig();
            cfg.piper_current_inference_preset = '';
            return;
        }

        const presets = _getInferencePresets();
        const p = presets[name];
        if (!p) return;

        _setValAndRange('v-speed', p.speed);
        _setValAndRange('v-silence', p.sentence_silence);
        _setValAndRange('v-noise', p.noise_scale);
        _setValAndRange('v-noisew', p.noise_w);
        _setValAndRange('v-volume', p.volume);

        const cfg = _getAudioConfig();
        cfg.piper_current_inference_preset = name;

        if (window.showToast) window.showToast(`Loaded preset '${name}'`, 'info');
    };

    // Auto-populate when DOM is ready
    document.addEventListener('DOMContentLoaded', () => {
        setTimeout(() => {
            if (typeof window.populatePiperPresets === 'function') window.populatePiperPresets();
            if (typeof window.populatePiperInferencePresets === 'function') window.populatePiperInferencePresets();
        }, 100);
    });

})();
