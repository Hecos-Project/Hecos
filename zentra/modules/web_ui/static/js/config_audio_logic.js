/**
 * Zentra Core WebUI - Audio Configuration Logic
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
    const obj = {};
    obj.listening_status = document.getElementById('sys-mic-status').checked;
    obj.voice_status     = document.getElementById('sys-voice-status').checked;
    
    obj.piper_path       = document.getElementById('v-piper').value;
    const pdir = sysOptions.piper_dir || 'C:\\piper';
    const sel  = document.getElementById('v-onnx-model').value;
    obj.onnx_model       = (sel.includes('\\') || sel.includes('/')) ? sel : pdir + '\\' + sel;
    
    obj.speed            = parseFloat(document.getElementById('v-speed').value) || 1.0;
    obj.noise_scale      = parseFloat(document.getElementById('v-noise').value) || 0.8;
    obj.noise_w          = parseFloat(document.getElementById('v-noisew').value) || 1.0;
    obj.sentence_silence = parseFloat(document.getElementById('v-silence').value) || 0.2;
    
    obj.energy_threshold = parseInt(document.getElementById('a-threshold').value) || 450;
    obj.silence_timeout  = parseInt(document.getElementById('a-timeout').value) || 5;
    obj.phrase_limit     = parseInt(document.getElementById('a-limit').value) || 15;
    
    return obj;
}

let currentTestAudio = null;
async function testVoice(mode) {
    const vTextEl = document.getElementById('v-test-text');
    const text = (vTextEl ? vTextEl.value : "") || "Test di Zentra Core, tutto funziona correttamente.";
    const sts = document.getElementById('v-test-status');
    const stopBtn = document.getElementById('v-test-stop');
    if (sts) sts.textContent = mode === 'web' ? "Generating..." : "Playing on console...";
    if(stopBtn) stopBtn.style.display = 'inline-block';
    
    try {
        const r = await fetch('/api/audio/test', {
            method: 'POST',
            body: JSON.stringify({ text: text, mode: mode })
        });
        const data = await r.json();
        if (data.ok) {
            if (mode === 'web' && data.url) {
                if (sts) sts.textContent = "Playing...";
                if (currentTestAudio) currentTestAudio.pause();
                currentTestAudio = new Audio(data.url);
                currentTestAudio.play();
                currentTestAudio.onended = () => { 
                    if (sts) sts.textContent = "Done."; 
                    if(stopBtn) stopBtn.style.display='none'; 
                    currentTestAudio = null;
                };
            } else {
                if (sts) sts.textContent = data.msg || "Done.";
                if(mode === 'console') {
                   setTimeout(() => { if(sts && sts.textContent!=="Generating...") if(stopBtn) stopBtn.style.display='none'; }, 8000);
                }
            }
        } else {
            if (sts) sts.textContent = "Error: " + data.error;
            if(stopBtn) stopBtn.style.display='none';
        }
    } catch(e) {
        if (sts) sts.textContent = "Request failed.";
        if(stopBtn) stopBtn.style.display='none';
    }
}

async function stopVoice() {
    if (currentTestAudio) {
        currentTestAudio.pause();
        currentTestAudio.src = "";
        currentTestAudio = null;
    }
    try { await fetch('/api/audio/stop', {method: 'POST'}); } catch(e) {}
    const stopBtn = document.getElementById('v-test-stop');
    if(stopBtn) stopBtn.style.display = 'none';
    const sts = document.getElementById('v-test-status');
    if(sts) sts.textContent = "Stopped.";
}

// Key Listener
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') stopVoice();
});

// Exports for Global Scope
window.populateAudioUI = populateAudioUI;
window.buildAudioPayload = buildAudioPayload;
window.testVoice = testVoice;
window.stopVoice = stopVoice;
