/**
 * audio_ui.js
 * DOM interactions for the voice configuration panel and the PTT button.
 */

window.isTouchHold = false;
window.isLockedMode = false;
window.pressStartTime = 0;
window._webptt_audioCtx = null;

window._webptt_shouldAutoSend = function(lockedMode) {
  if (lockedMode) {
    const previewOn = localStorage.getItem('webptt_toggle_preview') === 'true';
    return !previewOn;
  } else {
    const previewOn = localStorage.getItem('webptt_ptt_preview') === 'true';
    return !previewOn;
  }
};

window._webptt_setStatus = function(text) {
  const el = document.getElementById('web-ptt-status-bar');
  if (el) el.textContent = text;
};

window._webptt_setButtonState = function(state) {
  const btn = document.getElementById('web-ptt-btn');
  if (!btn) return;
  btn.classList.remove('listening', 'transcribing');
  switch (state) {
    case 'idle':
      btn.innerHTML = '🎙️';
      btn.setAttribute('aria-label', 'Microfono — tieni premuto per PTT, tocca per bloccare');
      window._webptt_setStatus('Tieni premuto · Tocca per bloccare');
      break;
    case 'listening':
      btn.innerHTML = '🔴';
      btn.classList.add('listening');
      btn.setAttribute('aria-label', 'Registrazione in corso — rilascia per inviare');
      window._webptt_setStatus(window.isLockedMode ? '🔴 Ascolto (bloccato) — tocca per fermare' : '🔴 Ascolto...');
      break;
    case 'transcribing':
      btn.innerHTML = '⏳';
      btn.classList.add('transcribing');
      btn.setAttribute('aria-label', 'Trascrizione in corso...');
      window._webptt_setStatus('🗣️ Trascrizione in corso...');
      break;
  }
};

window._webptt_beep = function(freq, duration) {
  try {
    if (!window._webptt_audioCtx) {
      const AudioContext = window.AudioContext || window.webkitAudioContext;
      window._webptt_audioCtx = new AudioContext();
    }
    if (window._webptt_audioCtx.state === 'suspended') {
      window._webptt_audioCtx.resume();
    }
    const osc = window._webptt_audioCtx.createOscillator();
    const gain = window._webptt_audioCtx.createGain();
    osc.connect(gain);
    gain.connect(window._webptt_audioCtx.destination);
    
    osc.type = 'sine';
    osc.frequency.setValueAtTime(freq, window._webptt_audioCtx.currentTime);
    
    gain.gain.setValueAtTime(0, window._webptt_audioCtx.currentTime);
    gain.gain.linearRampToValueAtTime(0.08, window._webptt_audioCtx.currentTime + 0.01);
    gain.gain.linearRampToValueAtTime(0, window._webptt_audioCtx.currentTime + duration);
    
    osc.start();
    osc.stop(window._webptt_audioCtx.currentTime + duration);
  } catch(e) {
    console.error("[WebAudio] Beep error:", e);
  }
};

window.bindWebPTT = function(buttonId) {
  const btn = document.getElementById(buttonId);
  if (!btn) return;

  const startFn = (e) => {
    e.preventDefault();
    if (typeof window.unlockAudioContext === 'function') window.unlockAudioContext();

    if (window.isWebAudioRecording) {
      if (window.isLockedMode) {
        window.isLockedMode = false;
        if (window.stopWebAudioRecording) window.stopWebAudioRecording();
      }
      return;
    }
    window.pressStartTime = Date.now();
    window.isTouchHold = true;
    if (window.startWebAudioRecording) window.startWebAudioRecording();
  };

  const stopFn = (e) => {
    e.preventDefault();
    if (!window.isTouchHold) return;
    window.isTouchHold = false;

    const elapsed = Date.now() - window.pressStartTime;
    const isTapEvent = e.type === 'mouseup' || e.type === 'touchend';

    if (isTapEvent && elapsed < 400 && !window.isLockedMode) {
      window.isLockedMode = true;
      if (window.isWebAudioRecording) {
        window._webptt_setButtonState('listening');
      }
      return;
    }

    if (!window.isWebAudioRecording) return;
    if (window.isLockedMode && e.type === 'mouseleave') return;

    window.isLockedMode = false;
    if (window.stopWebAudioRecording) window.stopWebAudioRecording();
  };

  btn.addEventListener('mousedown', startFn);
  btn.addEventListener('mouseup', stopFn);
  btn.addEventListener('mouseleave', stopFn);
  btn.addEventListener('touchstart', startFn, { passive: false });
  btn.addEventListener('touchend', stopFn, { passive: false });
  btn.addEventListener('touchcancel', stopFn, { passive: false });
};

window.webptt_getPref = function(key) { return localStorage.getItem(key); };
window.webptt_setPref = function(key, val) { localStorage.setItem(key, val ? 'true' : 'false'); };

window.webptt_loadPrefs = function() {
  const pttPref    = localStorage.getItem('webptt_ptt_preview');
  const togglePref = localStorage.getItem('webptt_toggle_preview');
  const pttEl    = document.getElementById('webptt-ptt-preview');
  const toggleEl = document.getElementById('webptt-toggle-preview');
  
  if (pttEl)    pttEl.checked    = (pttPref === 'true');
  if (toggleEl) toggleEl.checked = (togglePref === 'true');
};

document.addEventListener('DOMContentLoaded', () => {
  if (window.bindWebPTT) window.bindWebPTT('web-ptt-btn');
  if (window._webptt_setButtonState) window._webptt_setButtonState('idle');
  if (window.webptt_loadPrefs) window.webptt_loadPrefs();
});
