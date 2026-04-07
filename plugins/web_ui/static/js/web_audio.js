/**
 * Zentra Web Audio (Mobile PTT / WebRTC)
 * Handles client-side microphone capture using MediaRecorder.
 *
 * MODES:
 *  - PTT  (hold ≥400ms then release) : by default auto-sends. Configurable via localStorage.
 *  - Toggle (quick tap, then tap again): by default places text in textarea. Configurable.
 *
 * SETTINGS (localStorage):
 *  webptt_ptt_autosend    = "1" | "0"   (default "1" - auto-send on release)
 *  webptt_toggle_autosend = "1" | "0"   (default "0" - leave in textarea)
 */

let webAudioRecorder = null;
let webAudioStream = null;
let webAudioChunks = [];
let isWebAudioRecording = false;
let isTouchHold = false;
let isLockedMode = false;
let pressStartTime = 0;

// ── Helpers ────────────────────────────────────────────────────────────────

/**
 * Read user preference for auto-send.
 * @param {boolean} lockedMode - true if Toggle/Locked mode, false if PTT
 */
function _webptt_shouldAutoSend(lockedMode) {
  if (lockedMode) {
    // Toggle mode: default OFF (show in textarea)
    return localStorage.getItem('webptt_toggle_autosend') !== '0'
      ? (localStorage.getItem('webptt_toggle_autosend') === '1')
      : false;
  } else {
    // PTT mode: default ON (auto-send)
    const val = localStorage.getItem('webptt_ptt_autosend');
    return val === null || val === '1';
  }
}

function _webptt_setStatus(text) {
  const el = document.getElementById('web-ptt-status-bar');
  if (el) el.textContent = text;
}

function _webptt_setButtonState(state) {
  const btn = document.getElementById('web-ptt-btn');
  if (!btn) return;
  btn.classList.remove('listening', 'transcribing');
  switch (state) {
    case 'idle':
      btn.innerHTML = '🎙️';
      btn.setAttribute('aria-label', 'Microfono — tieni premuto per PTT, tocca per bloccare');
      _webptt_setStatus('Tieni premuto · Tocca per bloccare');
      break;
    case 'listening':
      btn.innerHTML = '🔴';
      btn.classList.add('listening');
      btn.setAttribute('aria-label', 'Registrazione in corso — rilascia per inviare');
      _webptt_setStatus(isLockedMode ? '🔴 Ascolto (bloccato) — tocca per fermare' : '🔴 Ascolto...');
      break;
    case 'transcribing':
      btn.innerHTML = '⏳';
      btn.classList.add('transcribing');
      btn.setAttribute('aria-label', 'Trascrizione in corso...');
      _webptt_setStatus('🗣️ Trascrizione in corso...');
      break;
  }
}

// ── Local AudioContext Beep & WAV Encoder ───────────────────────────────────
let _webptt_audioCtx = null;
function _webptt_beep(freq, duration) {
  try {
    if (!_webptt_audioCtx) {
      const AudioContext = window.AudioContext || window.webkitAudioContext;
      _webptt_audioCtx = new AudioContext();
    }
    // Resume context if suspended (browser auto-play policies)
    if (_webptt_audioCtx.state === 'suspended') {
      _webptt_audioCtx.resume();
    }
    const osc = _webptt_audioCtx.createOscillator();
    const gain = _webptt_audioCtx.createGain();
    osc.connect(gain);
    gain.connect(_webptt_audioCtx.destination);
    
    osc.type = 'sine';
    osc.frequency.setValueAtTime(freq, _webptt_audioCtx.currentTime);
    
    gain.gain.setValueAtTime(0, _webptt_audioCtx.currentTime);
    gain.gain.linearRampToValueAtTime(0.08, _webptt_audioCtx.currentTime + 0.01);
    gain.gain.linearRampToValueAtTime(0, _webptt_audioCtx.currentTime + duration);
    
    osc.start();
    osc.stop(_webptt_audioCtx.currentTime + duration);
  } catch(e) {
    console.error("[WebAudio] Beep error:", e);
  }
}

function _audioBufferToWav(buffer) {
  const numChannels = 1; // Force mono for speech_recognition
  const sampleRate = 16000; // Force 16kHz
  
  // We need to resample if the buffer is not 16000... 
  // Actually OfflineAudioContext is best for resampling
  return new Promise((resolve) => {
    const offlineCtx = new OfflineAudioContext(numChannels, buffer.duration * sampleRate, sampleRate);
    const source = offlineCtx.createBufferSource();
    source.buffer = buffer;
    source.connect(offlineCtx.destination);
    source.start();
    offlineCtx.startRendering().then(renderedBuffer => {
      const length = renderedBuffer.length * 2;
      const wav = new ArrayBuffer(44 + length);
      const view = new DataView(wav);
      const channels = [];
      let sample = 0;
      let offset = 0;
      
      function writeString(s) { for (let i=0; i<s.length; i++) { view.setUint8(offset + i, s.charCodeAt(i)); } offset += s.length; }
      
      writeString('RIFF');
      view.setUint32(offset, 36 + length, true); offset += 4;
      writeString('WAVE');
      writeString('fmt ');
      view.setUint32(offset, 16, true); offset += 4;
      view.setUint16(offset, 1, true); offset += 2;
      view.setUint16(offset, numChannels, true); offset += 2;
      view.setUint32(offset, sampleRate, true); offset += 4;
      view.setUint32(offset, sampleRate * 2, true); offset += 4;
      view.setUint16(offset, 2, true); offset += 2;
      view.setUint16(offset, 16, true); offset += 2;
      writeString('data');
      view.setUint32(offset, length, true); offset += 4;
      
      const channelData = renderedBuffer.getChannelData(0);
      let pcmIndex = 0;
      while (pcmIndex < channelData.length) {
        let s = Math.max(-1, Math.min(1, channelData[pcmIndex]));
        s = s < 0 ? s * 0x8000 : s * 0x7FFF;
        view.setInt16(offset, s, true);
        offset += 2;
        pcmIndex++;
      }
      resolve(new Blob([view], { type: 'audio/wav' }));
    });
  });
}

// ── Core recording functions ───────────────────────────────────────────────

async function initWebAudio() {
  if (webAudioStream) return true;
  try {
    webAudioStream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
    return true;
  } catch (err) {
    console.error('[WebAudio] Failed to acquire microphone:', err);
    return false;
  }
}

async function startWebAudioRecording() {
  if (isWebAudioRecording) return;

  _webptt_setButtonState('idle'); // show ⏳ briefly while acquiring mic
  const btn = document.getElementById('web-ptt-btn');
  if (btn) { btn.innerHTML = '⏳'; }

  const ready = await initWebAudio();
  if (!ready) {
    _webptt_setButtonState('idle');
    if (window.showToast) showToast('❌ Impossibile accedere al microfono. Controlla i permessi del browser.');
    else alert('Impossibile accedere al microfono. Controlla i permessi del browser.');
    return;
  }

  // RACE CONDITION FIX: Abort if finger was lifted AND it wasn't a quick tap lock
  if (!isTouchHold && !isLockedMode) {
    _webptt_setButtonState('idle');
    return;
  }

  webAudioChunks = [];
  const mimeType = MediaRecorder.isTypeSupported('audio/webm') ? 'audio/webm' : '';
  const options = mimeType ? { mimeType } : {};

  try {
    webAudioRecorder = new MediaRecorder(webAudioStream, options);
  } catch (e) {
    webAudioRecorder = new MediaRecorder(webAudioStream);
  }

  webAudioRecorder.ondataavailable = (e) => {
    if (e.data.size > 0) webAudioChunks.push(e.data);
  };

  // Capture the mode at recording-start time to avoid race conditions later
  const capturedLockedMode = isLockedMode;
  webAudioRecorder.onstop = () => uploadWebAudio(capturedLockedMode);
  webAudioRecorder.start();
  isWebAudioRecording = true;

  // Audio beep: HIGH = start
  _webptt_beep(880, 0.1);

  _webptt_setButtonState('listening');
  console.log('[WebAudio] Recording started... lockedMode=', capturedLockedMode);
}

function stopWebAudioRecording() {
  if (!isWebAudioRecording || !webAudioRecorder) {
    // If we weren't recording yet, reset button anyway (handles aborts)
    const btn = document.getElementById('web-ptt-btn');
    if (btn && btn.innerHTML === '⏳') {
      _webptt_setButtonState('idle');
    }
    return;
  }

  // Audio beep: LOW = stop
  _webptt_beep(440, 0.15);

  _webptt_setButtonState('transcribing');

  webAudioRecorder.stop();
  isWebAudioRecording = false;
  console.log('[WebAudio] Recording stopped, preparing payload...');
}

async function uploadWebAudio(wasLockedMode) {
  if (webAudioChunks.length === 0) {
    _webptt_setButtonState('idle');
    return;
  }

  const type = webAudioRecorder.mimeType || 'audio/webm';
  const audioBlob = new Blob(webAudioChunks, { type });
  webAudioChunks = [];

  const chatInput = document.getElementById('message-input') || document.getElementById('user-input');
  const originalPlace = chatInput ? chatInput.placeholder : '';

  if (chatInput) {
    chatInput.placeholder = '🗣️ Trascrizione in corso...';
    chatInput.disabled = true;
  }

  try {
    // Decode WebM/MP4 into AudioBuffer
    const arrayBuffer = await audioBlob.arrayBuffer();
    if (!_webptt_audioCtx) {
      const AudioContext = window.AudioContext || window.webkitAudioContext;
      _webptt_audioCtx = new AudioContext();
    }
    const audioBuffer = await _webptt_audioCtx.decodeAudioData(arrayBuffer);
    
    // Resample and encode to standard 16kHz mono WAV in the browser
    const wavBlob = await _audioBufferToWav(audioBuffer);
    
    const formData = new FormData();
    formData.append('audio_file', wavBlob, 'speech.wav');

    const res = await fetch('/api/audio/transcribe', { method: 'POST', body: formData });
    const data = await res.json();

    if (data.ok && data.text) {
      const transcribed = data.text.trim();
      console.log('[WebAudio] Transcribed:', transcribed);

      const shouldAutoSend = _webptt_shouldAutoSend(wasLockedMode);

      if (shouldAutoSend) {
        // AUTO-SEND: inject into textarea then trigger sendMessage()
        // This ensures the user bubble appears in chat just like a keyboard message
        if (chatInput) {
          chatInput.value = transcribed;
          chatInput.disabled = false; // re-enable before send
          if (typeof autoResize === 'function') autoResize(chatInput);
        }
        if (typeof sendMessage === 'function') {
          sendMessage();
        }
      } else {
        // MANUAL-SEND: place text in textarea for user to review/edit
        if (chatInput) {
          chatInput.value = (chatInput.value + ' ' + transcribed).trim();
          chatInput.dispatchEvent(new Event('input', { bubbles: true }));
          chatInput.focus();
        }
      }

    } else if (!data.ok) {
      console.error('[WebAudio] Transcription error:', data.error);
      if (window.showToast) showToast('❌ Errore trascrizione: ' + (data.error || 'sconosciuto'));
    }
  } catch (err) {
    console.error('[WebAudio] Network error during transcription:', err);
    if (window.showToast) showToast('❌ Errore di rete durante la trascrizione.');
  } finally {
    _webptt_setButtonState('idle');
    if (chatInput) {
      chatInput.placeholder = originalPlace;
      chatInput.disabled = false;
    }
  }
}

// ── Event binding ─────────────────────────────────────────────────────────

function bindWebPTT(buttonId) {
  const btn = document.getElementById(buttonId);
  if (!btn) return;

  const startFn = (e) => {
    e.preventDefault();
    if (typeof window.unlockAudioContext === 'function') window.unlockAudioContext();

    if (isWebAudioRecording) {
      if (isLockedMode) {
        // Tap while locked -> Stop
        isLockedMode = false;
        stopWebAudioRecording();
      }
      return;
    }
    pressStartTime = Date.now();
    isTouchHold = true;
    startWebAudioRecording();
  };

  const stopFn = (e) => {
    e.preventDefault();
    if (!isTouchHold) return;
    isTouchHold = false;

    const elapsed = Date.now() - pressStartTime;
    const isTapEvent = e.type === 'mouseup' || e.type === 'touchend';

    // If tapped (<400ms duration), transition into Locked/Toggle Mode
    if (isTapEvent && elapsed < 400 && !isLockedMode) {
      isLockedMode = true;
      if (isWebAudioRecording) {
        _webptt_setButtonState('listening'); // refresh to show locked state
      }
      return;
    }

    if (!isWebAudioRecording) return;
    if (isLockedMode && e.type === 'mouseleave') return;

    isLockedMode = false;
    stopWebAudioRecording();
  };

  btn.addEventListener('mousedown', startFn);
  btn.addEventListener('mouseup', stopFn);
  btn.addEventListener('mouseleave', stopFn);
  btn.addEventListener('touchstart', startFn, { passive: false });
  btn.addEventListener('touchend', stopFn, { passive: false });
  btn.addEventListener('touchcancel', stopFn, { passive: false });
}

// ── localStorage preference API (used by config_voice.html) ───────────────

window.webptt_getPref = function(key) {
  return localStorage.getItem(key);
};

window.webptt_setPref = function(key, val) {
  localStorage.setItem(key, val ? '1' : '0');
};

window.webptt_loadPrefs = function() {
  const pttPref    = localStorage.getItem('webptt_ptt_autosend');
  const togglePref = localStorage.getItem('webptt_toggle_autosend');
  const pttEl    = document.getElementById('webptt-ptt-autosend');
  const toggleEl = document.getElementById('webptt-toggle-autosend');
  if (pttEl)    pttEl.checked    = (pttPref    === null || pttPref    === '1');
  if (toggleEl) toggleEl.checked = (togglePref === '1');
};

// ── Init ──────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  bindWebPTT('web-ptt-btn');
  _webptt_setButtonState('idle');
  window.webptt_loadPrefs();
});
