/**
 * ca_tts_utils.js
 * ─────────────────────────────────────────────────────────────────────────────
 * TTS Engine Utilities: Piper Diagnostics & Dynamic Engine Status Monitoring.
 * Testing and Kokoro Model management have been split into ca_tts_testing.js
 * and ca_kokoro_models.js for modular architectural compliance (<200 lines).
 * ─────────────────────────────────────────────────────────────────────────────
 */

(function () {
    'use strict';

    // ── Auto-detect Piper path (calls the diagnostic fix-paths API) ────────────────
    async function autoFixPiperPath() {
        const sts = document.getElementById('v-test-status');
        if (sts) sts.textContent = window.t ? window.t('webui_conf_voice_detecting') : 'Auto-detecting Piper...';

        try {
            const r = await fetch('/api/system/diagnostic/fix-paths', { method: 'POST' });
            const data = await r.json();
            if (data.ok) {
                if (sts) sts.textContent = 'Path found! Reloading...';
                setTimeout(() => window.location.reload(), 800);
            } else {
                if (sts) sts.textContent = '❌ ' + (data.error || 'Detection failed.');
            }
        } catch (e) {
            if (sts) sts.textContent = '❌ Request failed.';
        }
    }

    // ── Browse for piper.exe via web-native explorer ─────────────────────────────
    async function browsePiperPath() {
        const currentPath = document.getElementById('v-piper')?.value || 'C:\\Hecos\\bin\\piper';
        if (typeof HecosFilePicker !== 'undefined') {
            HecosFilePicker.open({
                title: window.t ? window.t('webui_conf_voice_select_piper') : 'Select Piper Executable',
                initialPath: currentPath,
                onSelect: (path) => {
                    const inp = document.getElementById('v-piper');
                    if (inp) inp.value = path;
                    const sts = document.getElementById('v-test-status');
                    if (sts) sts.textContent = '✅ Path selected: ' + path.split('\\').pop();
                    if (typeof syncPluginStateToMemory === 'function') syncPluginStateToMemory('VOICE');
                }
            });
        }
    }

    // ── Engine Installation with Unified Progress Bar ────────────────────────────
    async function installTTSEngine(engine) {
        const statusEl = document.getElementById(`${engine}-install-status`);
        const taskId = `tts_engine_${engine}`;

        if (statusEl && window.HecosProgress) {
            statusEl.innerHTML = '';
            window.HecosProgress.attach(statusEl, {
                taskId: taskId,
                title: `Install ${engine.toUpperCase()}`,
                variant: 'inline',
                showCancel: true,
                onDone: () => {
                    const badge = document.getElementById(`${engine}-status-badge`);
                    if (badge) badge.textContent = '✅ Available';
                }
            });
        } else if (statusEl) {
            statusEl.textContent = '⏳ Installing engine...';
        }

        try {
            const r = await fetch('/api/audio/install-engine', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ engine, async: true })
            });
            const d = await r.json();
            if (!d.ok && statusEl) {
                statusEl.textContent = '❌ ' + (d.error || 'Installation failed.');
            }
        } catch (e) {
            if (statusEl) statusEl.textContent = '❌ Request failed: ' + e.message;
        }
    }

    // ── TTS Engine Availability Check & Dynamic Voice Population ──────────────────
    async function checkTTSEngineStatus() {
        try {
            // 1. Dynamically populate voices for Kokoro and XTTSv2
            const kokoroVoiceSel = document.getElementById('v-kokoro-voice');
            const xttsSpeakerSel = document.getElementById('v-xtts-speaker');
            const v = typeof audioConfig !== 'undefined' ? (audioConfig || {}) : {};
            const selKokoro = (v.kokoro && v.kokoro.voice) ? v.kokoro.voice : 'af_heart';
            const selXtts = (v.xtts && v.xtts.speaker) ? v.xtts.speaker : 'Claribel Dervla';

            if (kokoroVoiceSel) {
                try {
                    const res = await fetch(`/api/audio/voices?engine=kokoro`);
                    if (res.ok) {
                        const voices = await res.json();
                        const voiceMap = (!Array.isArray(voices) && voices.kokoro) ? voices.kokoro : voices;
                        const keys = Array.isArray(voiceMap) ? voiceMap : Object.keys(voiceMap);
                        if (keys.length > 0) {
                            kokoroVoiceSel.innerHTML = '';
                            keys.forEach(k => {
                                const opt = document.createElement('option');
                                opt.value = k;
                                opt.textContent = (!Array.isArray(voiceMap) && voiceMap[k]) ? voiceMap[k] : k;
                                kokoroVoiceSel.appendChild(opt);
                            });
                            if (selKokoro) kokoroVoiceSel.value = selKokoro;
                        }
                    }
                } catch (e) { console.warn("Failed to fetch Kokoro voices", e); }
            }

            if (xttsSpeakerSel) {
                try {
                    const res = await fetch(`/api/audio/voices?engine=xtts2`);
                    if (res.ok) {
                        const voices = await res.json();
                        const voiceMap = (!Array.isArray(voices) && voices.xtts2) ? voices.xtts2 : voices;
                        const keys = Array.isArray(voiceMap) ? voiceMap : Object.keys(voiceMap);
                        if (keys.length > 0) {
                            xttsSpeakerSel.innerHTML = '';
                            keys.forEach(k => {
                                const opt = document.createElement('option');
                                opt.value = k;
                                opt.textContent = (!Array.isArray(voiceMap) && voiceMap[k]) ? voiceMap[k] : k;
                                xttsSpeakerSel.appendChild(opt);
                            });
                            if (selXtts) xttsSpeakerSel.value = selXtts;
                        }
                    }
                } catch (e) { console.warn("Failed to fetch XTTS voices", e); }
            }

            // Dynamically populate voices for Fish Speech
            if (typeof window.loadFishVoiceCloneList === 'function') {
                await window.loadFishVoiceCloneList();
            }

            // Dynamically populate models for Kokoro
            if (typeof window.loadKokoroModelList === 'function') {
                await window.loadKokoroModelList();
            }

            // 2. Fetch status and update badges
            const r = await fetch('/api/audio/tts-status');
            const d = await r.json();
            if (!d.ok) return;

            // Kokoro badge
            const kokoroBadge = document.getElementById('kokoro-status-badge');
            if (kokoroBadge) {
                kokoroBadge.textContent = d.kokoro ? '✅ Installed' : '⚠️ Not installed';
                kokoroBadge.style.color = d.kokoro ? 'var(--green, #2ecc71)' : 'var(--yellow, #f1c40f)';
            }

            // XTTSv2 badge
            const xttsBadge = document.getElementById('xtts2-status-badge');
            if (xttsBadge) {
                if (d.xtts2) {
                    xttsBadge.textContent = '✅ Installed & Ready (All voices built-in)';
                    xttsBadge.style.color = 'var(--green, #2ecc71)';
                } else if (d.xtts2_lib) {
                    xttsBadge.textContent = '⏳ Library installed — model will download on first use (~1.8 GB)';
                    xttsBadge.style.color = 'var(--yellow, #f1c40f)';
                } else {
                    xttsBadge.textContent = '⚠️ Not installed';
                    xttsBadge.style.color = 'var(--yellow, #f1c40f)';
                }
            }

            // Fish Speech badge
            const fishBadge = document.getElementById('fish_speech-status-badge');
            if (fishBadge) {
                if (d.fish_speech_ready) {
                    fishBadge.textContent = '✅ Server Ready & Connected';
                    fishBadge.style.color = 'var(--green, #2ecc71)';
                } else if (d.fish_speech) {
                    fishBadge.textContent = '⏳ Client ready (Server offline on port 8080)';
                    fishBadge.style.color = 'var(--yellow, #f1c40f)';
                } else {
                    fishBadge.textContent = '⚠️ Not installed';
                    fishBadge.style.color = 'var(--yellow, #f1c40f)';
                }
            }
        } catch (e) {}
    }

    // Global exports
    window.autoFixPiperPath     = autoFixPiperPath;
    window.browsePiperPath      = browsePiperPath;
    window.installTTSEngine     = installTTSEngine;
    window.checkTTSEngineStatus = checkTTSEngineStatus;

})();
