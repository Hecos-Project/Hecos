/**
 * ca_tts_testing.js
 * ─────────────────────────────────────────────────────────────────────────────
 * TTS Voice Testing, Real-Time Audio Playback & Progress Polling.
 * Modularized from ca_tts_utils.js to adhere to Hecos architectural standards (<200 lines).
 * ─────────────────────────────────────────────────────────────────────────────
 */

(function () {
    'use strict';

    let currentTestAudio = null;
    let currentTestTimer = null;
    let testStartTime = 0;

    function _clearTestUI(prefix) {
        if (currentTestTimer) { clearInterval(currentTestTimer); currentTestTimer = null; }
        const pbarCont = document.getElementById(prefix + '-progress-container');
        const pbar = document.getElementById(prefix + '-progress-bar');
        const ptext = document.getElementById(prefix + '-progress-text');
        if (pbar) pbar.style.width = '100%';
        setTimeout(() => {
            if (pbarCont) pbarCont.style.display = 'none';
            if (ptext) ptext.style.display = 'none';
        }, 1000);
    }

    async function testVoice(mode, engine = null) {
        const activeEng = engine || (window.currentAudioEngine || 'piper');
        const prefix = activeEng === 'xtts2' ? 'v-xtts' : (activeEng === 'kokoro' ? 'v-kokoro' : (activeEng === 'fish_speech' ? 'v-fish' : 'v'));
        const vTextEl = document.getElementById(prefix + '-test-text');
        const text = (vTextEl ? vTextEl.value : '') || 'Hecos test, everything is working correctly.';
        const sts = document.getElementById(prefix + '-test-status');
        const stopBtn = document.getElementById(prefix + '-test-stop');
        const timerEl = document.getElementById(prefix + '-timer');
        const pbarCont = document.getElementById(prefix + '-progress-container');
        const pbar = document.getElementById(prefix + '-progress-bar');
        const ptext = document.getElementById(prefix + '-progress-text');

        if (sts) sts.textContent = mode === 'web' ? 'Generating audio...' : 'Playing on server...';
        if (stopBtn) stopBtn.style.display = 'inline-block';

        // Reset Console UI
        if (timerEl) { timerEl.style.display = 'inline'; timerEl.textContent = '0.0s'; }
        if (pbarCont) pbarCont.style.display = 'block';
        if (pbar) pbar.style.width = '0%';
        if (ptext) { ptext.style.display = 'block'; ptext.textContent = '0%'; }

        if (currentTestTimer) clearInterval(currentTestTimer);
        testStartTime = Date.now();
        currentTestTimer = setInterval(() => {
            if (timerEl) timerEl.textContent = ((Date.now() - testStartTime) / 1000).toFixed(1) + 's';
        }, 100);

        try {
            const reqPayload = { text: text, mode: mode, engine: activeEng, bypass_cache: true };
            if (activeEng === 'fish_speech') {
                const fishWav = (document.getElementById('v-fish-speaker-wav')?.value || document.getElementById('v-fish-clone-select')?.value || '').trim();
                reqPayload.voice = {
                    fish_reference_audio: fishWav,
                    tts_voice: fishWav,
                    fish_reference_id: document.getElementById('v-fish-reference-id')?.value || '',
                    fish_reference_text: document.getElementById('v-fish-reference-text')?.value || '',
                    fish_temperature: parseFloat(document.getElementById('v-fish-temperature')?.value || 0.7),
                    fish_top_p: parseFloat(document.getElementById('v-fish-topp')?.value || 0.7),
                    fish_repetition_penalty: parseFloat(document.getElementById('v-fish-repetition')?.value || 1.2),
                    fish_chunk_length: parseInt(document.getElementById('v-fish-chunk-length')?.value || 200),
                    fish_max_new_tokens: parseInt(document.getElementById('v-fish-max-tokens')?.value || 1024),
                    fish_seed: parseInt(document.getElementById('v-fish-seed')?.value || 0),
                    fish_normalize: document.getElementById('v-fish-normalize')?.checked ?? true,
                    fish_use_memory_cache: document.getElementById('v-fish-memory-cache')?.checked ?? true,
                    fish_chunk_sentences: document.getElementById('v-fish-chunk')?.checked ?? false,
                    fish_volume: parseFloat(document.getElementById('v-fish-volume')?.value || 1.0),
                };
            } else if (activeEng === 'kokoro') {
                reqPayload.voice = {
                    tts_voice: document.getElementById('v-kokoro-voice')?.value || 'af_heart',
                    kokoro_voice: document.getElementById('v-kokoro-voice')?.value || 'af_heart',
                    speed: parseFloat(document.getElementById('v-kokoro-speed')?.value || 1.0),
                    lang_code: document.getElementById('v-kokoro-lang')?.value || 'auto',
                    blend_voice: document.getElementById('v-kokoro-blend-voice')?.value || '',
                    alpha: parseFloat(document.getElementById('v-kokoro-alpha')?.value || 1.0),
                    beta: parseFloat(document.getElementById('v-kokoro-beta')?.value || 1.0),
                    sentence_silence: parseFloat(document.getElementById('v-kokoro-silence')?.value || 0.0),
                    volume: parseFloat(document.getElementById('v-kokoro-volume')?.value || 1.0),
                    normalize: document.getElementById('v-kokoro-normalize')?.checked ?? true,
                };
            } else if (activeEng === 'xtts2' || activeEng === 'xtts') {
                const xttsWav = (document.getElementById('v-xtts-speaker-wav')?.value || document.getElementById('v-xtts-clone-select')?.value || '').trim();
                reqPayload.voice = {
                    tts_engine: 'xtts2',
                    tts_voice: xttsWav,
                    speaker_wav: xttsWav,
                    temperature: parseFloat(document.getElementById('v-xtts-temperature')?.value || 0.75),
                    speed: parseFloat(document.getElementById('v-xtts-speed')?.value || 1.0),
                    repetition_penalty: parseFloat(document.getElementById('v-xtts-repetition-penalty')?.value || 5.0),
                    top_p: parseFloat(document.getElementById('v-xtts-topp')?.value || 0.85),
                    length_penalty: parseFloat(document.getElementById('v-xtts-length-penalty')?.value || 1.0),
                    chunk_sentences: document.getElementById('v-xtts-chunk')?.checked ?? false,
                };
            } else if (activeEng === 'piper') {
                const onnxVal = (document.getElementById('v-onnx-model')?.value || '').trim();
                const getVal = (id, def) => {
                    const el = document.getElementById(id);
                    if (!el || el.value === '' || isNaN(parseFloat(el.value))) return def;
                    return parseFloat(el.value);
                };
                reqPayload.voice = {
                    tts_engine: 'piper',
                    tts_voice: onnxVal,
                    onnx_model: onnxVal,
                    piper_path: (document.getElementById('v-piper')?.value || '').trim(),
                    speed: getVal('v-speed', 1.0),
                    noise_scale: getVal('v-noise', 0.667),
                    noise_w: getVal('v-noisew', 0.8),
                    sentence_silence: getVal('v-silence', 0.2),
                    volume: getVal('v-volume', 1.0),
                    piper_timeout: parseInt(document.getElementById('v-timeout')?.value || 180)
                };
            }
            const r = await fetch('/api/audio/test', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(reqPayload)
            });
            const data = await r.json();
            if (!data.ok) {
                _clearTestUI(prefix);
                if (sts) sts.textContent = '❌ ' + (data.error || 'Unknown error.');
                if (stopBtn) stopBtn.style.display = 'none';
                return;
            }

            if (!data.job_id) {
                _clearTestUI(prefix);
                if (sts) sts.textContent = '❌ No job_id returned.';
                if (stopBtn) stopBtn.style.display = 'none';
                return;
            }

            if (sts) sts.textContent = 'Generating... ⏳';
            const es = new EventSource(`/api/audio/test/progress/${data.job_id}`);
            es.onmessage = (evt) => {
                try {
                    const prog = JSON.parse(evt.data);
                    if (prog.status === 'done' && prog.audio_id) {
                        es.close();
                        _clearTestUI(prefix);

                        if (mode === 'console') {
                            if (sts) sts.textContent = 'Playing on server speakers...';
                            setTimeout(() => {
                                if (sts) sts.textContent = 'Completed.';
                                if (stopBtn) stopBtn.style.display = 'none';
                            }, 8000);
                        } else {
                            const audioUrl = `/api/audio?id=${encodeURIComponent(prog.audio_id)}&t=${Date.now()}`;
                            if (currentTestAudio) currentTestAudio.pause();
                            currentTestAudio = new Audio(audioUrl);
                            currentTestAudio.play().catch(err => {
                                if (sts) sts.textContent = '❌ Playback error: ' + err.message;
                            });
                            if (sts) sts.textContent = 'Playing...';
                            currentTestAudio.onended = () => {
                                if (sts) sts.textContent = 'Completed.';
                                if (stopBtn) stopBtn.style.display = 'none';
                                currentTestAudio = null;
                            };
                        }
                    } else if (prog.status === 'error') {
                        es.close();
                        _clearTestUI(prefix);
                        if (sts) sts.textContent = '❌ ' + (prog.error || 'Generation failed.');
                        if (stopBtn) stopBtn.style.display = 'none';
                    } else if (prog.status === 'not_found') {
                        es.close();
                        _clearTestUI(prefix);
                        if (sts) sts.textContent = '❌ Job not found.';
                        if (stopBtn) stopBtn.style.display = 'none';
                    } else if (prog.total > 0) {
                        const pct = Math.round((prog.current / prog.total) * 100);
                        if (sts) sts.textContent = `Generating... ${pct}%`;
                        if (pbar) pbar.style.width = pct + '%';
                        if (ptext) ptext.textContent = pct + '%';
                    }
                } catch (e) {
                    es.close();
                    _clearTestUI(prefix);
                    if (sts) sts.textContent = '❌ SSE parse error.';
                    if (stopBtn) stopBtn.style.display = 'none';
                }
            };
            es.onerror = () => {
                es.close();
                _clearTestUI(prefix);
                if (sts && sts.textContent.includes('Generating')) {
                    if (sts) sts.textContent = '❌ Connection lost during generation.';
                    if (stopBtn) stopBtn.style.display = 'none';
                }
            };

        } catch (e) {
            _clearTestUI(prefix);
            if (sts) sts.textContent = '❌ Request failed: ' + e.message;
            if (stopBtn) stopBtn.style.display = 'none';
        }
    }

    async function stopVoice(engine = null) {
        if (currentTestAudio) {
            currentTestAudio.pause();
            currentTestAudio.src = '';
            currentTestAudio = null;
        }
        const activeEng = engine || (window.currentAudioEngine || 'piper');
        const prefix = activeEng === 'xtts2' ? 'v-xtts' : (activeEng === 'kokoro' ? 'v-kokoro' : (activeEng === 'fish_speech' ? 'v-fish' : 'v'));
        _clearTestUI(prefix);
        try { await fetch('/api/audio/stop', { method: 'POST' }); } catch (e) {}

        const stopBtn = document.getElementById(prefix + '-test-stop');
        if (stopBtn) stopBtn.style.display = 'none';
        const sts = document.getElementById(prefix + '-test-status');
        if (sts) sts.textContent = 'Stopped.';
    }

    async function clearTTSCache() {
        const btn = document.getElementById('btn-clear-tts-cache');
        if (btn) btn.disabled = true;
        try {
            const r = await fetch('/api/audio/cache/clear', { method: 'POST' });
            const data = await r.json();
            if (data.ok) {
                if (window.showToast) window.showToast("TTS Cache cleared successfully!", "success");
            } else {
                if (window.showToast) window.showToast("Failed to clear cache: " + data.error, "error");
            }
        } catch (e) {
            if (window.showToast) window.showToast("Cache clear request failed: " + e.message, "error");
        } finally {
            if (btn) btn.disabled = false;
        }
    }

    // Key Listener: ESC stops any playing test audio
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') stopVoice();
    });

    window.testVoice = testVoice;
    window.stopVoice = stopVoice;
    window.clearTTSCache = clearTTSCache;
    window._clearTestUI = _clearTestUI;

})();
