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

function buildAudioPayload() {
    const v = (typeof audioConfig !== 'undefined' ? audioConfig : {}) || {};
    const pdir = (window.sysOptions || {}).piper_dir || 'C:\\piper';
    const sel = getV('v-onnx-model', (v.onnx_model || '').split(/[\\/]/).pop());
    
    return {
        listening_status: getC('sys-mic-status', v.listening_status ?? false),
        voice_status:     getC('sys-voice-status', v.voice_status ?? false),
        piper_path:       getV('v-piper', v.piper_path || ''),
        onnx_model:       (sel.includes('\\') || sel.includes('/')) ? sel : pdir + '\\' + sel,
        speed:            parseFloat(getV('v-speed', v.speed)) || 1.0,
        noise_scale:      parseFloat(getV('v-noise', v.noise_scale)) || 0.8,
        noise_w:          parseFloat(getV('v-noisew', v.noise_w)) || 1.0,
        sentence_silence: parseFloat(getV('v-silence', v.sentence_silence)) || 0.2,
        piper_timeout:    parseInt(getV('v-timeout', v.piper_timeout)) || 180,
        energy_threshold: parseInt(getV('a-threshold', v.energy_threshold)) || 450,
        silence_timeout:  parseInt(getV('a-timeout', v.silence_timeout)) || 5,
        phrase_limit:     parseInt(getV('a-limit', v.phrase_limit)) || 15
    };
}

let currentTestAudio = null;

async function testVoice(mode) {
    const vTextEl = document.getElementById('v-test-text');
    const text = (vTextEl ? vTextEl.value : '') || 'Hecos test, everything is working correctly.';
    const sts = document.getElementById('v-test-status');
    const stopBtn = document.getElementById('v-test-stop');
    if (sts) sts.textContent = mode === 'web' ? 'Generating audio...' : 'Playing on server...';
    if (stopBtn) stopBtn.style.display = 'inline-block';

    try {
        const r = await fetch('/api/audio/test', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: text, mode: mode })
        });
        const data = await r.json();
        if (data.ok) {
            if (mode === 'web' && data.url) {
                if (sts) sts.textContent = 'Playing...';
                if (currentTestAudio) currentTestAudio.pause();
                currentTestAudio = new Audio(data.url);
                currentTestAudio.play();
                currentTestAudio.onended = () => {
                    if (sts) sts.textContent = 'Completed.';
                    if (stopBtn) stopBtn.style.display = 'none';
                    currentTestAudio = null;
                };
            } else {
                if (sts) sts.textContent = data.msg || 'Completed.';
                if (mode === 'console') {
                    setTimeout(() => { if (stopBtn) stopBtn.style.display = 'none'; }, 8000);
                }
            }
        } else {
            if (sts) sts.textContent = '❌ ' + (data.error || 'Unknown error.');
            if (stopBtn) stopBtn.style.display = 'none';
        }
    } catch (e) {
        if (sts) sts.textContent = '❌ Request failed: ' + e.message;
        if (stopBtn) stopBtn.style.display = 'none';
    }
}

async function stopVoice() {
    if (currentTestAudio) {
        currentTestAudio.pause();
        currentTestAudio.src = '';
        currentTestAudio = null;
    }
    try { await fetch('/api/audio/stop', { method: 'POST' }); } catch (e) {}
    const stopBtn = document.getElementById('v-test-stop');
    if (stopBtn) stopBtn.style.display = 'none';
    const sts = document.getElementById('v-test-status');
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

// Exports for Global Scope
window.populateAudioUI  = populateAudioUI;
window.buildAudioPayload = buildAudioPayload;
window.testVoice        = testVoice;
window.stopVoice        = stopVoice;
window.autoFixPiperPath = autoFixPiperPath;

window.browsePiperPath  = browsePiperPath;

