/**
 * ca_kokoro_inference.js
 * ─────────────────────────────────────────────────────────────────────────────
 * Frontend module for Kokoro Inference Parameters, Voice Blending (StyleTTS 2),
 * and Inference Presets management.
 * ─────────────────────────────────────────────────────────────────────────────
 */

(function () {
    'use strict';

    // ── Quick Speed Preset Setter ─────────────────────────────────────────────
    window.setKokoroSpeedPreset = function (speed) {
        const val = parseFloat(speed) || 1.0;
        const spInput = document.getElementById('v-kokoro-speed');
        const spRange = document.getElementById('v-kokoro-speed-range');
        if (spInput) spInput.value = val.toFixed(2).replace(/\.?0+$/, '');
        if (spRange) spRange.value = val;
    };

    // ── Handle Blend Voice Selection Change ───────────────────────────────────
    window.onKokoroBlendVoiceChange = function () {
        const blendSel = document.getElementById('v-kokoro-blend-voice');
        const badge = document.getElementById('kokoro-blend-badge');
        const alphaLabel = document.getElementById('kokoro-alpha-label');
        const betaLabel = document.getElementById('kokoro-beta-label');
        const val = blendSel ? blendSel.value.trim() : '';

        if (badge) {
            if (val) {
                badge.textContent = 'Dual-Voice Blending Active';
                badge.style.background = 'rgba(46, 204, 113, 0.15)';
                badge.style.color = 'var(--green, #2ecc71)';
                badge.style.borderColor = 'rgba(46, 204, 113, 0.3)';
            } else {
                badge.textContent = 'Single Voice Mode';
                badge.style.background = 'rgba(0, 180, 216, 0.15)';
                badge.style.color = 'var(--accent, #00b4d8)';
                badge.style.borderColor = 'rgba(0, 180, 216, 0.3)';
            }
        }

        const alphaInput = document.getElementById('v-kokoro-alpha');
        const betaInput = document.getElementById('v-kokoro-beta');
        if (alphaLabel && alphaInput) alphaLabel.textContent = parseFloat(alphaInput.value || 1.0).toFixed(2);
        if (betaLabel && betaInput) betaLabel.textContent = parseFloat(betaInput.value || 1.0).toFixed(2);
    };

    // ── Populate Blend Voice Dropdown from Primary Voice Options ─────────────
    window.syncKokoroBlendVoiceOptions = function () {
        const primarySel = document.getElementById('v-kokoro-voice');
        const blendSel = document.getElementById('v-kokoro-blend-voice');
        if (!primarySel || !blendSel) return;

        const currentVal = blendSel.value;
        blendSel.innerHTML = '<option value="">-- None (Single Voice Mode) --</option>';

        for (let i = 0; i < primarySel.options.length; i++) {
            const opt = primarySel.options[i];
            if (!opt.value) continue;
            const newOpt = document.createElement('option');
            newOpt.value = opt.value;
            newOpt.textContent = opt.textContent;
            blendSel.appendChild(newOpt);
        }

        if (currentVal) blendSel.value = currentVal;
        window.onKokoroBlendVoiceChange();
    };

    // ── Save Current Parameters as New Inference Preset ───────────────────────
    window.saveKokoroInferencePreset = function () {
        const promptFn = window.hecosPrompt || prompt;
        promptFn("Kokoro Inference Preset Name (e.g. 'Fast & Direct', 'Expressive Dynamic'):", function (name) {
            if (!name || !name.trim()) return;
            name = name.trim();
            if (!window.audioConfig) window.audioConfig = {};
            if (!window.audioConfig.kokoro_inference_presets) window.audioConfig.kokoro_inference_presets = {};

            window.audioConfig.kokoro_inference_presets[name] = {
                speed: parseFloat(document.getElementById('v-kokoro-speed')?.value || 1.0),
                sentence_silence: parseFloat(document.getElementById('v-kokoro-silence')?.value || 0.0),
                lang_code: document.getElementById('v-kokoro-lang')?.value || 'auto',
                blend_voice: document.getElementById('v-kokoro-blend-voice')?.value || '',
                alpha: parseFloat(document.getElementById('v-kokoro-alpha')?.value || 1.0),
                beta: parseFloat(document.getElementById('v-kokoro-beta')?.value || 1.0),
                volume: parseFloat(document.getElementById('v-kokoro-volume')?.value || 1.0),
                normalize: document.getElementById('v-kokoro-normalize')?.checked ?? true
            };

            if (typeof window.saveAudioConfig === 'function') {
                window.saveAudioConfig().then(() => {
                    if (typeof window.populateAudioUI === 'function') window.populateAudioUI();
                    const sel = document.getElementById('v-kokoro-inference-preset');
                    if (sel) sel.value = name;
                    if (window.showToast) window.showToast(`Inference Preset '${name}' saved!`, 'success');
                });
            }
        });
    };

    // ── Update Currently Selected Inference Preset ───────────────────────────
    window.updateKokoroInferencePreset = function () {
        const sel = document.getElementById('v-kokoro-inference-preset');
        const name = sel ? sel.value : '';
        if (!name) {
            if (window.showToast) window.showToast('Please select an Inference Preset to update.', 'error');
            else alert('Please select an Inference Preset to update.');
            return;
        }

        if (!window.audioConfig) window.audioConfig = {};
        if (!window.audioConfig.kokoro_inference_presets) window.audioConfig.kokoro_inference_presets = {};

        window.audioConfig.kokoro_inference_presets[name] = {
            speed: parseFloat(document.getElementById('v-kokoro-speed')?.value || 1.0),
            sentence_silence: parseFloat(document.getElementById('v-kokoro-silence')?.value || 0.0),
            lang_code: document.getElementById('v-kokoro-lang')?.value || 'auto',
            blend_voice: document.getElementById('v-kokoro-blend-voice')?.value || '',
            alpha: parseFloat(document.getElementById('v-kokoro-alpha')?.value || 1.0),
            beta: parseFloat(document.getElementById('v-kokoro-beta')?.value || 1.0),
            volume: parseFloat(document.getElementById('v-kokoro-volume')?.value || 1.0),
            normalize: document.getElementById('v-kokoro-normalize')?.checked ?? true
        };

        if (typeof window.saveAudioConfig === 'function') {
            window.saveAudioConfig().then(() => {
                if (window.showToast) window.showToast(`Inference Preset '${name}' updated!`, 'success');
            });
        }
    };

    // ── Delete Selected Inference Preset ─────────────────────────────────────
    window.deleteKokoroInferencePreset = function () {
        const sel = document.getElementById('v-kokoro-inference-preset');
        const name = sel ? sel.value : '';
        if (!name) {
            if (window.showToast) window.showToast('No preset selected.', 'error');
            else alert('No preset selected.');
            return;
        }

        const confirmFn = window.hecosConfirm || confirm;
        confirmFn(`Do you want to delete the Inference Preset '${name}'?`, function () {
            if (window.audioConfig?.kokoro_inference_presets && window.audioConfig.kokoro_inference_presets[name]) {
                delete window.audioConfig.kokoro_inference_presets[name];
                if (typeof window.saveAudioConfig === 'function') {
                    window.saveAudioConfig().then(() => {
                        if (typeof window.populateAudioUI === 'function') window.populateAudioUI();
                        if (window.showToast) window.showToast(`Preset '${name}' deleted.`, 'info');
                    });
                }
            }
        });
    };

    // ── Load Preset Values into Form Sliders and Inputs ───────────────────────
    window.loadKokoroInferencePreset = function () {
        const sel = document.getElementById('v-kokoro-inference-preset');
        const name = sel ? sel.value : '';
        if (!name || !window.audioConfig?.kokoro_inference_presets || !window.audioConfig.kokoro_inference_presets[name]) return;

        const p = window.audioConfig.kokoro_inference_presets[name];

        // Speed
        if (p.speed !== undefined) {
            if (document.getElementById('v-kokoro-speed')) document.getElementById('v-kokoro-speed').value = p.speed;
            if (document.getElementById('v-kokoro-speed-range')) document.getElementById('v-kokoro-speed-range').value = p.speed;
        }
        // Sentence Silence
        if (p.sentence_silence !== undefined) {
            if (document.getElementById('v-kokoro-silence')) document.getElementById('v-kokoro-silence').value = p.sentence_silence;
            if (document.getElementById('v-kokoro-silence-range')) document.getElementById('v-kokoro-silence-range').value = p.sentence_silence;
        }
        // Language Code
        if (p.lang_code !== undefined && document.getElementById('v-kokoro-lang')) {
            document.getElementById('v-kokoro-lang').value = p.lang_code;
        }
        // Blend Voice
        if (p.blend_voice !== undefined && document.getElementById('v-kokoro-blend-voice')) {
            document.getElementById('v-kokoro-blend-voice').value = p.blend_voice;
        }
        // Alpha (Timbre)
        if (p.alpha !== undefined) {
            if (document.getElementById('v-kokoro-alpha')) document.getElementById('v-kokoro-alpha').value = p.alpha;
            if (document.getElementById('v-kokoro-alpha-range')) document.getElementById('v-kokoro-alpha-range').value = p.alpha;
            if (document.getElementById('kokoro-alpha-label')) document.getElementById('kokoro-alpha-label').textContent = parseFloat(p.alpha).toFixed(2);
        }
        // Beta (Prosody)
        if (p.beta !== undefined) {
            if (document.getElementById('v-kokoro-beta')) document.getElementById('v-kokoro-beta').value = p.beta;
            if (document.getElementById('v-kokoro-beta-range')) document.getElementById('v-kokoro-beta-range').value = p.beta;
            if (document.getElementById('kokoro-beta-label')) document.getElementById('kokoro-beta-label').textContent = parseFloat(p.beta).toFixed(2);
        }
        // Volume
        if (p.volume !== undefined) {
            if (document.getElementById('v-kokoro-volume')) document.getElementById('v-kokoro-volume').value = p.volume;
            if (document.getElementById('v-kokoro-volume-range')) document.getElementById('v-kokoro-volume-range').value = p.volume;
        }
        // Normalize
        if (p.normalize !== undefined && document.getElementById('v-kokoro-normalize')) {
            document.getElementById('v-kokoro-normalize').checked = p.normalize;
        }

        window.onKokoroBlendVoiceChange();
    };

    // Auto-sync options on page ready
    document.addEventListener('DOMContentLoaded', function () {
        setTimeout(window.syncKokoroBlendVoiceOptions, 500);
    });
})();
