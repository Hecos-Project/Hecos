/**
 * Hecos WebUI - Audio Configuration Logic
 * Handles STT/TTS settings, device scanning and testing.
 */

function populateAudioUI() {
    const v = audioConfig || {};
    setVal('v-piper', v.piper_path || '');
    const curOnnx = (v.onnx_model || '').split('\\').pop().split('/').pop();
    populateSelect('v-onnx-model', sysOptions.piper_voices || [], curOnnx, true);
    setVal('v-speed', v.speed ?? 1.2);
    setVal('v-noise', v.noise_scale ?? 0.817);
    setVal('v-noisew', v.noise_w ?? 0.9);
    setVal('v-silence', v.sentence_silence ?? 0.1);
    setVal('v-timeout', v.piper_timeout ?? 180);
    setVal('v-tts-history-max', v.tts_history_max_files ?? 100);
    setVal('v-active-engine', v.active_engine ?? 'piper');
    // Kokoro
    setVal('v-kokoro-speed', (v.kokoro && v.kokoro.speed) ? v.kokoro.speed : 1.0);
    setVal('v-kokoro-voice', (v.kokoro && v.kokoro.voice) ? v.kokoro.voice : 'af_heart');
    setVal('v-kokoro-silence', (v.kokoro && v.kokoro.sentence_silence) ? v.kokoro.sentence_silence : 0.0);
    setVal('v-kokoro-model', (v.kokoro && v.kokoro.model_path) ? v.kokoro.model_path : '');
    // XTTS
    setVal('v-xtts-speed', (v.xtts && v.xtts.speed) ? v.xtts.speed : 1.0);
    setVal('v-xtts-lang', (v.xtts && v.xtts.language) ? v.xtts.language : 'it');
    setVal('v-xtts-speaker', (v.xtts && v.xtts.speaker) ? v.xtts.speaker : 'Claribel Dervla');
    setVal('v-xtts-gpu', (v.xtts && v.xtts.gpu_acceleration) ? v.xtts.gpu_acceleration : 'auto');
    setCheck('v-xtts-chunk', (v.xtts && v.xtts.chunk_sentences !== undefined) ? v.xtts.chunk_sentences : true);
    setVal('v-xtts-speaker-wav', (v.xtts && v.xtts.speaker_wav) ? v.xtts.speaker_wav : '');
    setVal('v-xtts-temperature', (v.xtts && v.xtts.temperature !== undefined) ? v.xtts.temperature : 0.75);
    setVal('v-xtts-repetition_penalty', (v.xtts && v.xtts.repetition_penalty !== undefined) ? v.xtts.repetition_penalty : 5.0);
    setVal('v-xtts-topk', (v.xtts && v.xtts.top_k !== undefined) ? v.xtts.top_k : 50);
    setVal('v-xtts-topp', (v.xtts && v.xtts.top_p !== undefined) ? v.xtts.top_p : 0.85);
    setVal('v-xtts-length-penalty', (v.xtts && v.xtts.length_penalty !== undefined) ? v.xtts.length_penalty : 1.0);
    
    // Update value displays
    const spVal = document.getElementById('v-xtts-speed-val'); if(spVal) spVal.textContent = getV('v-xtts-speed');
    const tpVal = document.getElementById('v-xtts-temperature-val'); if(tpVal) tpVal.textContent = getV('v-xtts-temperature');
    const rpVal = document.getElementById('v-xtts-repetition-val'); if(rpVal) rpVal.textContent = getV('v-xtts-repetition_penalty');
    const tkVal = document.getElementById('v-xtts-topk-val'); if(tkVal) tkVal.textContent = getV('v-xtts-topk');
    const tppVal = document.getElementById('v-xtts-topp-val'); if(tppVal) tppVal.textContent = getV('v-xtts-topp');
    const lpVal = document.getElementById('v-xtts-length-penalty-val'); if(lpVal) lpVal.textContent = getV('v-xtts-length-penalty');
    
    // Populate XTTS Presets
    const presetSel = document.getElementById('v-xtts-preset');
    if (presetSel) {
        presetSel.innerHTML = '<option value="default">Default (Built-in)</option>';
        if (v.xtts_presets) {
            for (const pName in v.xtts_presets) {
                const opt = document.createElement('option');
                opt.value = pName;
                opt.textContent = pName;
                presetSel.appendChild(opt);
            }
        }
        if (v.xtts && v.xtts.current_preset && v.xtts_presets && v.xtts_presets[v.xtts.current_preset]) {
            presetSel.value = v.xtts.current_preset;
        } else {
            presetSel.value = 'default';
        }
    }

    refreshAudioHistoryCount();
    checkTTSEngineStatus();
    if (typeof loadVoiceCloneList === 'function') loadVoiceCloneList();
    // Activate the tab matching the current engine
    const activeEngine = (v.active_engine || 'piper');
    if (typeof switchAudioEngineTab === 'function') switchAudioEngineTab(activeEngine, false);


    const a = audioConfig || {};
    setVal('a-threshold', a.energy_threshold ?? 450);
    setVal('a-timeout', a.silence_timeout ?? 5);
    setVal('a-limit', a.phrase_limit ?? 15);

    setCheck('sys-mic-status', (audioConfig || {}).listening_status ?? false);
    setCheck('sys-voice-status', (audioConfig || {}).voice_status ?? false);

    if (audioDevices) {
        const inSel = document.getElementById('audio-input-device');
        const outSel = document.getElementById('audio-output-device');
        if (inSel) {
            inSel.innerHTML = '';
            (audioDevices.input_devices || []).forEach(d => {
                const opt = document.createElement('option');
                opt.value = d.index;
                opt.textContent = `${d.index}: ${d.name}`;
                if (d.index === audioDevices.selected_input_index) opt.selected = true;
                inSel.appendChild(opt);
            });
        }
        if (outSel) {
            outSel.innerHTML = '';
            (audioDevices.output_devices || []).forEach(d => {
                const opt = document.createElement('option');
                opt.value = d.index;
                opt.textContent = `${d.index}: ${d.name}`;
                if (d.index === audioDevices.selected_output_index) opt.selected = true;
                outSel.appendChild(opt);
            });
        }
    }
}

// ── Engine Tab Switcher ──────────────────────────────────────────────────────

window.switchAudioEngineTab = function(engine, saveEngine = true) {
    const engines = ['piper', 'kokoro', 'xtts2'];

    // Show/hide engine cards
    engines.forEach(e => {
        const card = document.getElementById(`card-${e}`);
        if (card) card.style.display = (e === engine) ? '' : 'none';
    });

    // Style tab buttons: active = var(--bg3), inactive = transparent
    engines.forEach(e => {
        const btn = document.getElementById(`btn-tab-${e}`);
        if (!btn) return;
        if (e === engine) {
            btn.style.background = 'var(--bg3)';
            btn.style.color = 'var(--accent)';
            btn.style.borderBottom = '2px solid var(--accent)';
            btn.style.marginBottom = '-1px';
        } else {
            btn.style.background = 'transparent';
            btn.style.color = 'var(--muted)';
            btn.style.borderBottom = 'none';
            btn.style.marginBottom = '0';
        }
    });

    // removed active engine syncing
};


function buildAudioPayload() {
    const v = (typeof audioConfig !== 'undefined' ? audioConfig : {}) || {};
    const pdir = (window.sysOptions || {}).piper_dir || 'C:\\piper';
    const el = document.getElementById('v-onnx-model');
    const sel = el ? el.value : (v.onnx_model || 'it_IT-paola-medium.onnx');
    const modelFile = (sel && sel.trim() && sel !== 'null') ? sel : 'it_IT-paola-medium.onnx';
    
    return {
        active_engine:    getV('v-active-engine', v.active_engine || 'piper'),
        kokoro:           { 
            speed: parseFloat(getV('v-kokoro-speed', v.kokoro?.speed ?? 1.0)),
            voice: getV('v-kokoro-voice', v.kokoro?.voice || 'af_heart'),
            sentence_silence: parseFloat(getV('v-kokoro-silence', v.kokoro?.sentence_silence ?? 0.0)),
            model_path: getV('v-kokoro-model', v.kokoro?.model_path || '')
        },
        xtts:             { 
            speed: parseFloat(getV('v-xtts-speed', v.xtts?.speed ?? 1.0)), 
            language: getV('v-xtts-lang', v.xtts?.language || 'it'),
            speaker: getV('v-xtts-speaker', v.xtts?.speaker || 'Claribel Dervla'),
            gpu_acceleration: getV('v-xtts-gpu', v.xtts?.gpu_acceleration || 'auto'),
            chunk_sentences: getC('v-xtts-chunk', v.xtts?.chunk_sentences ?? true),
            speaker_wav: getV('v-xtts-speaker-wav', v.xtts?.speaker_wav || ''),
            temperature: parseFloat(getV('v-xtts-temperature', v.xtts?.temperature ?? 0.75)),
            repetition_penalty: parseFloat(getV('v-xtts-repetition_penalty', v.xtts?.repetition_penalty ?? 5.0)),
            top_k: parseInt(getV('v-xtts-topk', v.xtts?.top_k ?? 50)),
            top_p: parseFloat(getV('v-xtts-topp', v.xtts?.top_p ?? 0.85)),
            length_penalty: parseFloat(getV('v-xtts-length-penalty', v.xtts?.length_penalty ?? 1.0)),
            current_preset: getV('v-xtts-preset', 'default')
        },
        xtts_presets:     v.xtts_presets || {},
        listening_status: getC('sys-mic-status', v.listening_status ?? false),
        voice_status:     getC('sys-voice-status', v.voice_status ?? false),
        piper_path:       getV('v-piper', v.piper_path || ''),
        onnx_model:       (modelFile.includes('\\') || modelFile.includes('/')) ? modelFile : pdir + '\\' + modelFile,
        speed:            parseFloat(getV('v-speed', v.speed)) || 1.0,
        noise_scale:      parseFloat(getV('v-noise', v.noise_scale)) || 0.8,
        noise_w:          parseFloat(getV('v-noisew', v.noise_w)) || 1.0,
        sentence_silence: parseFloat(getV('v-silence', v.sentence_silence)) || 0.2,
        piper_timeout:    parseInt(getV('v-timeout', v.piper_timeout)) || 180,
        tts_history_max_files: parseInt(getV('v-tts-history-max', v.tts_history_max_files)) || 100,
        energy_threshold: parseInt(getV('a-threshold', v.energy_threshold)) || 450,
        silence_timeout:  parseInt(getV('a-timeout', v.silence_timeout)) || 5,
        phrase_limit:     parseInt(getV('a-limit', v.phrase_limit)) || 15
    };
}

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
async function refreshAudioHistoryCount() {
    const lbl = document.getElementById('v-history-count');
    if (lbl) lbl.textContent = 'Loading...';
    try {
        const r = await fetch('/api/audio/history/info');
        const d = await r.json();
        if (d.ok) {
            const max = parseInt(document.getElementById('v-tts-history-max')?.value || 100);
            if (lbl) lbl.textContent = `📂 ${d.count} files present (${d.size_mb} MB) — limit: ${max}`;
        } else {
            if (lbl) lbl.textContent = '❌ Error loading.';
        }
    } catch (e) {
        if (lbl) lbl.textContent = '❌ Request failed.';
    }
}

async function clearAudioHistory() {
    if (!confirm('Delete all audio files from history?')) return;
    const lbl = document.getElementById('v-history-count');
    try {
        const r = await fetch('/api/audio/history/clear', { method: 'POST' });
        const d = await r.json();
        if (d.ok) {
            if (lbl) lbl.textContent = `✅ History cleared (${d.deleted} files deleted).`;
        } else {
            if (lbl) lbl.textContent = '❌ ' + (d.error || 'Unknown error.');
        }
    } catch (e) {
        if (lbl) lbl.textContent = '❌ Request failed.';
    }
}

// ── On-Demand TTS Engine Installer ───────────────────────────────────────────
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
window.populateAudioUI       = populateAudioUI;
window.buildAudioPayload     = buildAudioPayload;
window.testVoice             = testVoice;
window.stopVoice             = stopVoice;
window.autoFixPiperPath      = autoFixPiperPath;
window.browsePiperPath       = browsePiperPath;
window.refreshAudioHistoryCount = refreshAudioHistoryCount;
window.clearAudioHistory     = clearAudioHistory;
window.installTTSEngine      = installTTSEngine;
window.checkTTSEngineStatus  = checkTTSEngineStatus;
// saveAudioConfig is a lazy wrapper: resolves saveConfig at call-time, not at load-time
// (saveConfig lives in config_core_persistence.js which may load after this file)
window.saveAudioConfig = function() {
    if (typeof window.saveConfig === 'function') return window.saveConfig(true);
    console.warn('[AudioConfig] saveConfig not yet available');
    return Promise.resolve();
};

window.pickXTTSVoiceWav = function() {
    fetch('/api/system/explorer/pick-native', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            title: "Select Voice Clone WAV",
            filetypes: [["WAV Audio", "*.wav"], ["All Files", "*.*"]]
        })
    })
    .then(r => r.json())
    .then(data => {
        if (data.ok && data.path) {
            const input = document.getElementById('v-xtts-speaker-wav');
            if (input) {
                input.value = data.path;
                // Reset dropdown to show it's a custom path
                const sel = document.getElementById('v-xtts-clone-select');
                if (sel) sel.value = '';
                saveAudioConfig();
            }
        }
    })
    .catch(err => console.error("Native pick error:", err));
};

// ── Voice Clone Library ──────────────────────────────────────────────────────

window.loadVoiceCloneList = async function() {
    try {
        const r = await fetch('/api/audio/voice-clones');
        const data = await r.json();
        if (!data.ok) return;
        const sel = document.getElementById('v-xtts-clone-select');
        if (!sel) return;
        const currentPath = document.getElementById('v-xtts-speaker-wav')?.value || '';
        sel.innerHTML = '<option value="">— None (use Default Speaker) —</option>';
        for (const f of data.files) {
            const opt = document.createElement('option');
            opt.value = f.path;
            opt.textContent = f.name;
            if (f.path === currentPath) opt.selected = true;
            sel.appendChild(opt);
        }
        // If no library option matched but there's a path typed, leave dropdown at "None"
    } catch(e) {
        console.error('[AudioConfig] loadVoiceCloneList error:', e);
    }
};

window.onVoiceCloneSelect = function() {
    const sel = document.getElementById('v-xtts-clone-select');
    const input = document.getElementById('v-xtts-speaker-wav');
    if (!sel || !input) return;
    input.value = sel.value; // '' for None, path for a file
    saveAudioConfig();
};

window.onVoiceClonePathInput = function() {
    // If user types manually, deselect dropdown so it stays in sync
    const input = document.getElementById('v-xtts-speaker-wav');
    const sel = document.getElementById('v-xtts-clone-select');
    if (!sel || !input) return;
    const typed = input.value.trim();
    // Try to find a matching option
    const matched = Array.from(sel.options).find(o => o.value === typed);
    sel.value = matched ? matched.value : '';
};

window.uploadVoiceClone = async function(fileInput) {
    if (!fileInput.files.length) return;
    const file = fileInput.files[0];
    if (!file.name.toLowerCase().endsWith('.wav')) {
        if (window.showToast) window.showToast('Only WAV files are accepted.', 'error');
        return;
    }
    const fd = new FormData();
    fd.append('file', file);
    try {
        if (window.showToast) window.showToast('Uploading...', 'info');
        const r = await fetch('/api/audio/voice-clones/upload', { method: 'POST', body: fd });
        const data = await r.json();
        if (data.ok) {
            await loadVoiceCloneList();
            // Auto-select the just-uploaded file
            const sel = document.getElementById('v-xtts-clone-select');
            const input = document.getElementById('v-xtts-speaker-wav');
            if (sel && data.path) {
                sel.value = data.path;
                if (input) input.value = data.path;
                saveAudioConfig();
            }
            if (window.showToast) window.showToast(`Uploaded: ${data.filename}`, 'success');
        } else {
            if (window.showToast) window.showToast('Upload failed: ' + data.error, 'error');
        }
    } catch(e) {
        if (window.showToast) window.showToast('Upload error: ' + e.message, 'error');
    }
    fileInput.value = ''; // reset so same file can be re-uploaded
};



// ── Custom Modals for Audio Panel ───────────────────────────────────────────
window.hecosPrompt = function(msg, onSave) {
    var modalId = 'audio-custom-prompt-modal';
    var modal = document.getElementById(modalId);
    if (!modal) {
        modal = document.createElement('div');
        modal.id = modalId;
        modal.style.cssText = 'position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.6); display:flex; align-items:center; justify-content:center; z-index:9999;';
        modal.innerHTML = '<div style="background:var(--bg2); border:1px solid var(--border); padding:24px; border-radius:12px; max-width:400px; width:90%; box-shadow:0 10px 30px rgba(0,0,0,0.5);">' +
            '<h3 style="margin-top:0; color:var(--text);"><i class="fas fa-keyboard" style="margin-right:8px; color:var(--accent);"></i> Input Required</h3>' +
            '<p id="' + modalId + '-text" style="margin:20px 0; color:var(--text); font-size:1.05em;"></p>' +
            '<input type="text" id="' + modalId + '-input" class="config-input" style="width:100%; margin-bottom:20px; border:1px solid var(--border); background:var(--bg3); color:var(--text); padding:8px 12px; border-radius:6px;">' +
            '<div style="display:flex; justify-content:flex-end; gap:10px;">' +
            '<button class="btn" id="' + modalId + '-cancel" style="border:1px solid var(--border); background:var(--bg3); color:var(--text); padding:8px 16px; border-radius:6px; cursor:pointer;">Cancel</button>' +
            '<button class="btn" style="background:var(--accent); color:white; border:none; padding:8px 16px; border-radius:6px; cursor:pointer;" id="' + modalId + '-save">Save</button>' +
            '</div></div>';
        document.body.appendChild(modal);
    }
    document.getElementById(modalId + '-text').textContent = msg;
    var input = document.getElementById(modalId + '-input');
    input.value = '';

    var cleanup = function() { modal.style.display = 'none'; };

    document.getElementById(modalId + '-cancel').onclick = cleanup;
    document.getElementById(modalId + '-save').onclick = function() {
        cleanup();
        var val = input.value.trim();
        if (val) onSave(val);
    };

    modal.style.display = 'flex';
    setTimeout(function() { input.focus(); }, 100);
};

window.hecosConfirm = function(msg, onYes) {
    if (window.hpmShowConfirm) {
        window.hpmShowConfirm(msg, 'Confirm', onYes);
    } else {
        var modalId = 'audio-custom-confirm-modal';
        var modal = document.getElementById(modalId);
        if (!modal) {
            modal = document.createElement('div');
            modal.id = modalId;
            modal.style.cssText = 'position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.6); display:flex; align-items:center; justify-content:center; z-index:9999;';
            modal.innerHTML = '<div style="background:var(--bg2); border:1px solid var(--border); padding:24px; border-radius:12px; max-width:400px; width:90%; box-shadow:0 10px 30px rgba(0,0,0,0.5);">' +
                '<h3 style="margin-top:0; color:var(--text);"><i class="fas fa-question-circle" style="margin-right:8px; color:var(--accent);"></i> Confirmation</h3>' +
                '<p id="' + modalId + '-text" style="margin:20px 0; color:var(--text); font-size:1.05em;"></p>' +
                '<div style="display:flex; justify-content:flex-end; gap:10px;">' +
                '<button class="btn" id="' + modalId + '-cancel" style="border:1px solid var(--border); background:var(--bg3); color:var(--text); padding:8px 16px; border-radius:6px; cursor:pointer;">Cancel</button>' +
                '<button class="btn" style="background:var(--accent); color:white; border:none; padding:8px 16px; border-radius:6px; cursor:pointer;" id="' + modalId + '-yes">Confirm</button>' +
                '</div></div>';
            document.body.appendChild(modal);
        }
        document.getElementById(modalId + '-text').textContent = msg;

        var cleanup = function() { modal.style.display = 'none'; };

        document.getElementById(modalId + '-cancel').onclick = cleanup;
        document.getElementById(modalId + '-yes').onclick = function() {
            cleanup();
            onYes();
        };

        modal.style.display = 'flex';
    }
};

// ── XTTS Presets Logic ───────────────────────────────────────────────────────

window.saveXTTSPreset = function() {
    window.hecosPrompt("Preset name (e.g. 'Fast voice', 'Cloned voice'):", function(name) {
        if (!audioConfig.xtts_presets) audioConfig.xtts_presets = {};
        
        audioConfig.xtts_presets[name] = {
            speed: parseFloat(document.getElementById('v-xtts-speed')?.value || 1.0),
            language: document.getElementById('v-xtts-lang')?.value || 'it',
            speaker: document.getElementById('v-xtts-speaker')?.value || 'Claribel Dervla',
            gpu_acceleration: document.getElementById('v-xtts-gpu')?.value || 'auto',
            chunk_sentences: document.getElementById('v-xtts-chunk')?.checked ?? true,
            speaker_wav: document.getElementById('v-xtts-speaker-wav')?.value || '',
            temperature: parseFloat(document.getElementById('v-xtts-temperature')?.value || 0.75),
            repetition_penalty: parseFloat(document.getElementById('v-xtts-repetition_penalty')?.value || 5.0)
        };
        
        if (!audioConfig.xtts) audioConfig.xtts = {};
        audioConfig.xtts.current_preset = name;
        
        saveAudioConfig().then(() => {
            populateAudioUI();
            if (window.showToast) window.showToast("Preset saved successfully!", "success");
        });
    });
};

window.updateXTTSPreset = function() {
    const name = document.getElementById('v-xtts-preset')?.value;
    if (!name || name === 'default') {
        if (window.showToast) window.showToast("Select a custom preset to update first.", "error");
        return;
    }
    
    if (!audioConfig.xtts_presets) audioConfig.xtts_presets = {};
    
    audioConfig.xtts_presets[name] = {
        speed: parseFloat(document.getElementById('v-xtts-speed')?.value || 1.0),
        language: document.getElementById('v-xtts-lang')?.value || 'it',
        speaker: document.getElementById('v-xtts-speaker')?.value || 'Claribel Dervla',
        gpu_acceleration: document.getElementById('v-xtts-gpu')?.value || 'auto',
        chunk_sentences: document.getElementById('v-xtts-chunk')?.checked ?? true,
        speaker_wav: document.getElementById('v-xtts-speaker-wav')?.value || '',
        temperature: parseFloat(document.getElementById('v-xtts-temperature')?.value || 0.75),
        repetition_penalty: parseFloat(document.getElementById('v-xtts-repetition_penalty')?.value || 5.0),
        top_k: parseInt(document.getElementById('v-xtts-topk')?.value || 50),
        top_p: parseFloat(document.getElementById('v-xtts-topp')?.value || 0.85),
        length_penalty: parseFloat(document.getElementById('v-xtts-length-penalty')?.value || 1.0)
    };
    
    if (!audioConfig.xtts) audioConfig.xtts = {};
    audioConfig.xtts.current_preset = name;
    
    saveAudioConfig().then(() => {
        if (window.showToast) window.showToast("Preset configuration updated!", "success");
    });
};

window.resetXTTSConfig = function() {
    window.hecosConfirm("Reset all XTTS parameters to their default values?", function() {
        const presetSelect = document.getElementById('v-xtts-preset');
        if (presetSelect) presetSelect.value = 'default';
        loadXTTSPreset();
    });
};

window.loadXTTSPreset = function() {
    const name = document.getElementById('v-xtts-preset')?.value;
    if (!name) return;

    if (name === 'default' || !audioConfig.xtts_presets || !audioConfig.xtts_presets[name]) {
        if (name === 'default') {
            if (document.getElementById('v-xtts-speed')) document.getElementById('v-xtts-speed').value = 1.0;
            if (document.getElementById('v-xtts-temperature')) document.getElementById('v-xtts-temperature').value = 0.75;
            if (document.getElementById('v-xtts-repetition_penalty')) document.getElementById('v-xtts-repetition_penalty').value = 5.0;
            if (document.getElementById('v-xtts-topk')) document.getElementById('v-xtts-topk').value = 50;
            if (document.getElementById('v-xtts-topp')) document.getElementById('v-xtts-topp').value = 0.85;
            if (document.getElementById('v-xtts-length-penalty')) document.getElementById('v-xtts-length-penalty').value = 1.0;
            if (document.getElementById('v-xtts-speaker')) document.getElementById('v-xtts-speaker').value = 'Claribel Dervla';
            if (document.getElementById('v-xtts-speaker-wav')) document.getElementById('v-xtts-speaker-wav').value = '';
            
            document.getElementById('v-xtts-speed')?.dispatchEvent(new Event('input'));
            document.getElementById('v-xtts-temperature')?.dispatchEvent(new Event('input'));
            document.getElementById('v-xtts-repetition_penalty')?.dispatchEvent(new Event('input'));
            document.getElementById('v-xtts-topk')?.dispatchEvent(new Event('input'));
            document.getElementById('v-xtts-topp')?.dispatchEvent(new Event('input'));
            document.getElementById('v-xtts-length-penalty')?.dispatchEvent(new Event('input'));
            
            audioConfig.xtts.current_preset = 'default';
            saveAudioConfig();
        }
        return;
    }
    
    const p = audioConfig.xtts_presets[name];
    if (document.getElementById('v-xtts-speed')) document.getElementById('v-xtts-speed').value = p.speed || 1.0;
    if (document.getElementById('v-xtts-lang')) document.getElementById('v-xtts-lang').value = p.language || 'it';
    if (document.getElementById('v-xtts-speaker')) document.getElementById('v-xtts-speaker').value = p.speaker || 'Claribel Dervla';
    if (document.getElementById('v-xtts-gpu')) document.getElementById('v-xtts-gpu').value = p.gpu_acceleration || 'auto';
    if (document.getElementById('v-xtts-chunk')) document.getElementById('v-xtts-chunk').checked = p.chunk_sentences ?? true;
    if (document.getElementById('v-xtts-speaker-wav')) document.getElementById('v-xtts-speaker-wav').value = p.speaker_wav || '';
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
    
    audioConfig.xtts.current_preset = name;
    saveAudioConfig();
};

window.deleteXTTSPreset = function() {
    const name = document.getElementById('v-xtts-preset').value;
    if (name === 'default') {
        if (window.showToast) window.showToast("Cannot delete the default preset.", "error");
        return;
    }
    
    window.hecosConfirm(`Are you sure you want to delete the preset '${name}'?`, function() {
        if (audioConfig.xtts_presets && audioConfig.xtts_presets[name]) {
            delete audioConfig.xtts_presets[name];
            audioConfig.xtts.current_preset = 'default';
            saveAudioConfig().then(() => {
                populateAudioUI();
                if (window.showToast) window.showToast("Preset deleted.", "info");
            });
        }
    });
};
