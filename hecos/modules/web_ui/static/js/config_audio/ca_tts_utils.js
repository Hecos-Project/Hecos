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
    const prefix = engine === 'xtts2' ? 'v-xtts' : (engine === 'kokoro' ? 'v-kokoro' : 'v');
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
        const r = await fetch('/api/audio/test', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: text, mode: mode, engine: engine })
        });
        const data = await r.json();
        if (!data.ok) {
            _clearTestUI(prefix);
            if (sts) sts.textContent = '❌ ' + (data.error || 'Unknown error.');
            if (stopBtn) stopBtn.style.display = 'none';
            return;
        }

        // both web and console modes now poll progress via SSE


        // web mode — poll progress via SSE then play when done
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
                        }, 8000); // Give it some time to play before hiding stop
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
    const prefix = engine === 'xtts2' ? 'v-xtts' : (engine === 'kokoro' ? 'v-kokoro' : 'v');
    _clearTestUI(prefix);
    try { await fetch('/api/audio/stop', { method: 'POST' }); } catch (e) {}
    
    const stopBtn = document.getElementById(prefix + '-test-stop');
    if (stopBtn) stopBtn.style.display = 'none';
    const sts = document.getElementById(prefix + '-test-status');
    if (sts) sts.textContent = 'Stopped.';
}

// Key Listener: ESC stops any playing test audio
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') stopVoice();
});

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

// ── Browse for piper.exe via NEW web-native explorer ─────────────────────────
async function browsePiperPath() {
    const currentPath = document.getElementById('v-piper').value || 'C:\\Hecos\\bin\\piper';
    HecosFilePicker.open({
        title: window.t('webui_conf_voice_select_piper'),
        initialPath: currentPath,
        onSelect: (path) => {
            document.getElementById('v-piper').value = path;
            const sts = document.getElementById('v-test-status');
            if (sts) sts.textContent = '✅ Path selected: ' + path.split('\\').pop();
            // Trigger auto-save sync if needed
            if (typeof syncPluginStateToMemory === 'function') syncPluginStateToMemory('VOICE');
        }
    });
}

// ── Audio History Helpers ──────────────────────────────────────────────────────
async function installTTSEngine(engine) {
    const statusEl = document.getElementById(`${engine}-install-status`);
    if (statusEl) statusEl.textContent = '⏳ Installazione in corso...';
    try {
        const r = await fetch('/api/audio/install-engine', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ engine })
        });
        const d = await r.json();
        if (d.ok) {
            if (statusEl) statusEl.textContent = '✅ Installed successfully!';
            const badge = document.getElementById(`${engine}-status-badge`);
            if (badge) badge.textContent = '✅ Available';
        } else {
            if (statusEl) statusEl.textContent = '❌ ' + (d.error || 'Installation failed.');
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
                    const list = Array.isArray(voices) ? voices : (voices.kokoro || Object.keys(voices));
                    const iter = Array.isArray(list) ? list : Object.keys(list);
                    if (iter.length > 0) {
                        kokoroVoiceSel.innerHTML = '';
                        iter.forEach(voice => {
                            const opt = document.createElement('option');
                            opt.value = voice;
                            let text = voice;
                            if (!Array.isArray(list) && typeof list[voice] === 'string') text = list[voice];
                            opt.textContent = text;
                            kokoroVoiceSel.appendChild(opt);
                        });
                        kokoroVoiceSel.value = selKokoro;
                    }
                }
            } catch(e) { console.warn("Failed to fetch Kokoro voices"); }
        }
        
        if (xttsSpeakerSel) {
            try {
                const res = await fetch(`/api/audio/voices?engine=xtts2`);
                if (res.ok) {
                    const voices = await res.json();
                    const list = Array.isArray(voices) ? voices : (voices.xtts2 || Object.keys(voices));
                    const iter = Array.isArray(list) ? list : Object.keys(list);
                    if (iter.length > 0) {
                        xttsSpeakerSel.innerHTML = '';
                        iter.forEach(voice => {
                            const opt = document.createElement('option');
                            opt.value = voice;
                            let text = voice;
                            if (!Array.isArray(list) && typeof list[voice] === 'string') text = list[voice];
                            opt.textContent = text;
                            xttsSpeakerSel.appendChild(opt);
                        });
                        xttsSpeakerSel.value = selXtts;
                    }
                }
            } catch(e) { console.warn("Failed to fetch XTTS voices"); }
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

        // XTTSv2 badge — show ✅ if library is installed, even if model not yet downloaded
        const xttsBadge = document.getElementById('xtts2-status-badge');
        if (xttsBadge) {
            if (d.xtts2) {
                xttsBadge.textContent = '✅ Installed & Ready (All voices are built-in)';
                xttsBadge.style.color = 'var(--green, #2ecc71)';
            } else if (d.xtts2_lib) {
                xttsBadge.textContent = '⏳ Library installed — model will download on first use (~1.8 GB)';
                xttsBadge.style.color = 'var(--yellow, #f1c40f)';
            } else {
                xttsBadge.textContent = '⚠️ Not installed';
                xttsBadge.style.color = 'var(--yellow, #f1c40f)';
            }
        }

        // XTTS and Kokoro download their voices automatically or they are built-in.
        // No per-voice download indicators are needed here.
    } catch(e) {}
}

// Exports for Global Scope
window.testVoice             = testVoice;
window.stopVoice             = stopVoice;
window.autoFixPiperPath      = autoFixPiperPath;
window.browsePiperPath       = browsePiperPath;
window.installTTSEngine      = installTTSEngine;
window.checkTTSEngineStatus  = checkTTSEngineStatus;
// saveAudioConfig is a lazy wrapper: resolves saveConfig at call-time, not at load-time
// (saveConfig lives in config_core_persistence.js which may load after this file)
