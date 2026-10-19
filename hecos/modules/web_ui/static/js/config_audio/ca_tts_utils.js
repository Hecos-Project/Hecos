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
    const prefix = engine === 'xtts2' ? 'v-xtts' : (engine === 'kokoro' ? 'v-kokoro' : (engine === 'fish_speech' ? 'v-fish' : 'v'));
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
        const reqPayload = { text: text, mode: mode, engine: engine };
        if (engine === 'fish_speech') {
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
        } else if (engine === 'kokoro') {
            reqPayload.voice = {
                tts_voice: document.getElementById('v-kokoro-voice')?.value || 'af_heart',
                speed: parseFloat(document.getElementById('v-kokoro-speed')?.value || 1.0),
                sentence_silence: parseFloat(document.getElementById('v-kokoro-silence')?.value || 0.0),
                volume: parseFloat(document.getElementById('v-kokoro-volume')?.value || 1.0),
                normalize: document.getElementById('v-kokoro-normalize')?.checked ?? true,
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
    const prefix = engine === 'xtts2' ? 'v-xtts' : (engine === 'kokoro' ? 'v-kokoro' : (engine === 'fish_speech' ? 'v-fish' : 'v'));
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

// ── Kokoro Neural Model Management & Folder Browsing ─────────────────────────
async function loadKokoroModelList() {
    const select = document.getElementById('v-kokoro-model-select');
    const hiddenInput = document.getElementById('v-kokoro-model');
    if (!select) return;

    try {
        const res = await fetch('/api/audio/kokoro/models');
        if (!res.ok) return;
        const data = await res.json();
        if (!data.ok || !Array.isArray(data.models)) return;

        const currentVal = hiddenInput ? (hiddenInput.value || '').trim() : '';
        select.innerHTML = '';

        let foundMatch = false;
        data.models.forEach(m => {
            const opt = document.createElement('option');
            opt.value = m.id;
            opt.textContent = m.name;
            opt.dataset.path = m.path;
            opt.dataset.type = m.type;
            if (m.id === currentVal) {
                opt.selected = true;
                foundMatch = true;
            }
            select.appendChild(opt);
        });

        if (currentVal && !foundMatch) {
            const opt = document.createElement('option');
            opt.value = currentVal;
            opt.textContent = `Custom: ${currentVal.split('\\').pop().split('/').pop()}`;
            opt.dataset.path = currentVal;
            opt.dataset.type = 'custom';
            opt.selected = true;
            select.appendChild(opt);
        }

        updateKokoroModelUI();
    } catch (e) {
        console.warn("Failed to load Kokoro model list:", e);
    }
}

function updateKokoroModelUI() {
    const select = document.getElementById('v-kokoro-model-select');
    const hiddenInput = document.getElementById('v-kokoro-model');
    const pathDisplay = document.getElementById('v-kokoro-model-path-display');
    const badge = document.getElementById('v-kokoro-model-badge');
    if (!select) return;

    const val = select.value || '';
    if (hiddenInput) hiddenInput.value = val;

    if (!val) {
        if (pathDisplay) pathDisplay.innerHTML = '📁 Active Path: <code>Default integrated local model</code>';
        if (badge) {
            badge.textContent = 'Kokoro-82M v1.0';
            badge.className = 'badge-pill badge-accent';
        }
    } else {
        if (pathDisplay) pathDisplay.innerHTML = `📁 Active Path: <code>${val}</code>`;
        if (badge) {
            badge.textContent = 'Custom Model';
            badge.className = 'badge-pill badge-ok';
        }
    }
}

function onKokoroModelSelectChange() {
    updateKokoroModelUI();
}

function setKokoroModelPath(path) {
    const select = document.getElementById('v-kokoro-model-select');
    const hiddenInput = document.getElementById('v-kokoro-model');
    if (hiddenInput) hiddenInput.value = path || '';

    let found = false;
    if (select) {
        for (let i = 0; i < select.options.length; i++) {
            if (select.options[i].value === path) {
                select.selectedIndex = i;
                found = true;
                break;
            }
        }
        if (!found && path) {
            const opt = document.createElement('option');
            opt.value = path;
            opt.textContent = `Custom: ${path.split('\\').pop().split('/').pop()}`;
            opt.selected = true;
            select.appendChild(opt);
        }
    }
    updateKokoroModelUI();
}

async function browseKokoroModelPath() {
    const currentVal = document.getElementById('v-kokoro-model')?.value || '';
    const initialPath = currentVal || 'C:\\Hecos\\hecos\\models\\kokoro';
    if (typeof HecosFilePicker !== 'undefined') {
        HecosFilePicker.open({
            title: 'Select Kokoro Model Weights (.pth) or Model Folder',
            initialPath: initialPath,
            onSelect: (path) => {
                if (path) {
                    setKokoroModelPath(path);
                    if (window.showToast) window.showToast('Selected model: ' + path.split('\\').pop(), 'info');
                }
            }
        });
    } else {
        const customPath = prompt("Enter full path to Kokoro model (.pth) or directory:", initialPath);
        if (customPath !== null) {
            setKokoroModelPath(customPath.trim());
        }
    }
}

async function openKokoroModelsFolder() {
    try {
        const res = await fetch('/api/audio/kokoro/open-folder', { method: 'POST' });
        const data = await res.json();
        if (data.ok) {
            if (window.showToast) window.showToast("Opened Kokoro models folder in File Explorer!", "info");
        } else {
            if (window.showToast) window.showToast("Error opening folder: " + data.error, "error");
        }
    } catch (e) {
        if (window.showToast) window.showToast("Error opening folder: " + e.message, "error");
    }
}

function copyKokoroModelsPath() {
    const p = "C:\\Hecos\\hecos\\models\\kokoro";
    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(p).then(() => {
            if (window.showToast) window.showToast("Copied path to clipboard: " + p, "success");
        }).catch(() => {
            prompt("Kokoro models directory path:", p);
        });
    } else {
        prompt("Kokoro models directory path:", p);
    }
}

// ── Audio History Helpers ──────────────────────────────────────────────────────
async function installTTSEngine(engine) {
    const statusEl = document.getElementById(`${engine}-install-status`);
    const taskId = `tts_engine_${engine}`;

    if (statusEl && window.HecosProgress) {
        statusEl.innerHTML = '';
        window.HecosProgress.attach(statusEl, {
            taskId: taskId,
            title: `Installazione ${engine.toUpperCase()}`,
            variant: 'inline',
            showCancel: true,
            onDone: () => {
                const badge = document.getElementById(`${engine}-status-badge`);
                if (badge) badge.textContent = '✅ Available';
            }
        });
    } else if (statusEl) {
        statusEl.textContent = '⏳ Installazione in corso...';
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
            } catch(e) { console.warn("Failed to fetch Kokoro voices", e); }
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
            } catch(e) { console.warn("Failed to fetch XTTS voices", e); }
        }

        // Dynamically populate voices for Fish Speech
        if (typeof window.loadFishVoiceCloneList === 'function') {
            await window.loadFishVoiceCloneList();
        }

        // Dynamically populate models for Kokoro
        if (typeof loadKokoroModelList === 'function') {
            await loadKokoroModelList();
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

        // Fish Speech badge
        const fishBadge = document.getElementById('fish_speech-status-badge');
        if (fishBadge) {
            if (d.fish_speech_ready) {
                fishBadge.textContent = '✅ Server Ready & Connected';
                fishBadge.style.color = 'var(--green, #2ecc71)';
            } else if (d.fish_speech) {
                fishBadge.textContent = '⏳ Client ready (Server offline on port 8080 / Enter Cloud Key)';
                fishBadge.style.color = 'var(--yellow, #f1c40f)';
            } else {
                fishBadge.textContent = '⚠️ Not installed';
                fishBadge.style.color = 'var(--yellow, #f1c40f)';
            }
        }

        // XTTS and Kokoro download their voices automatically or they are built-in.
        // No per-voice download indicators are needed here.
    } catch(e) {}
}

// Purge TTS disk cache
async function clearTTSCache() {
    try {
        const res = await fetch('/api/audio/cache/clear', { method: 'POST' });
        const data = await res.json();
        if (data.ok) {
            if (window.showToast) {
                window.showToast(`TTS Cache cleared (${data.deleted_count} files removed).`, 'info');
            } else {
                alert(`TTS Cache cleared (${data.deleted_count} files removed).`);
            }
        } else {
            if (window.showToast) window.showToast('Failed to clear TTS cache: ' + data.error, 'error');
        }
    } catch(e) {
        if (window.showToast) window.showToast('Error clearing cache: ' + e.message, 'error');
    }
}

// Exports for Global Scope
window.testVoice             = testVoice;
window.stopVoice             = stopVoice;
window.clearTTSCache         = clearTTSCache;
window.autoFixPiperPath      = autoFixPiperPath;
window.browsePiperPath       = browsePiperPath;
window.installTTSEngine      = installTTSEngine;
window.checkTTSEngineStatus  = checkTTSEngineStatus;
window.loadKokoroModelList      = loadKokoroModelList;
window.updateKokoroModelUI      = updateKokoroModelUI;
window.onKokoroModelSelectChange = onKokoroModelSelectChange;
window.browseKokoroModelPath    = browseKokoroModelPath;
window.openKokoroModelsFolder   = openKokoroModelsFolder;
window.copyKokoroModelsPath     = copyKokoroModelsPath;
// saveAudioConfig is a lazy wrapper: resolves saveConfig at call-time, not at load-time
// (saveConfig lives in config_core_persistence.js which may load after this file)
