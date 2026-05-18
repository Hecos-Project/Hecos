/**
 * audio_controls.js
 * Handles UI toggles and API calls for Mic, TTS, and routing.
 */

window.currentMicOn  = false;
window.currentTTSOn  = false;
window.currentPTTOn  = false;
window.currentSTTSource = 'system';
window.currentTTSDest   = 'web';

function _applyMicState(on) {
  window.currentMicOn = on;
  const label = on ? 'ON' : 'OFF';
  const labelEl = document.getElementById('mic-label');
  if (labelEl) labelEl.textContent = label;
  const micBtn = document.getElementById('mic-btn');
  if (micBtn) micBtn.className = 'audio-toggle-btn ' + (on ? 'on' : 'off');
  const chip = document.getElementById('chip-mic');
  if (chip) {
      chip.textContent = '🎤 MIC: ' + label;
      chip.className   = 'topbar-chip ' + (on ? 'on' : 'off');
  }
  const pttBtn = document.getElementById('ptt-btn');
  // If MIC is turned OFF, also reset PTT state visually
  if (!on) {
    _applyPTTState(false);
    // Gray out PTT button to signal it's unavailable
    if (pttBtn) pttBtn.title = 'Abilita prima il MIC per usare PTT';
  } else {
    if (pttBtn) pttBtn.title = 'Toggle Push-To-Talk (F8)';
  }
  
  // Sync with Configuration Hub state to avoid auto-save regressions
  if (typeof audioConfig !== 'undefined' && audioConfig) {
      audioConfig.listening_status = on;
  }
  const domChk = document.getElementById('sys-mic-status');
  if (domChk) domChk.checked = on;
}

function _applyTTSState(on) {
  window.currentTTSOn = on;
  const label = on ? 'ON' : 'OFF';
  const labelEl = document.getElementById('tts-label');
  if (labelEl) labelEl.textContent = label;
  const ttsBtn = document.getElementById('tts-btn');
  if (ttsBtn) ttsBtn.className = 'audio-toggle-btn ' + (on ? 'on' : 'off');
  const chip = document.getElementById('chip-tts');
  if (chip) {
      chip.textContent = '🔊 TTS: ' + label;
      chip.className   = 'topbar-chip ' + (on ? 'on' : 'off');
  }
  
  // Sync with Configuration Hub state
  if (typeof audioConfig !== 'undefined' && audioConfig) {
      audioConfig.voice_status = on;
  }
  const domChk = document.getElementById('sys-voice-status');
  if (domChk) domChk.checked = on;
}

function _applyPTTState(on) {
  window.currentPTTOn = on;
  const label = on ? 'ON' : 'OFF';
  const labelEl = document.getElementById('ptt-label');
  if (labelEl) labelEl.textContent = label;
  const pttBtn = document.getElementById('ptt-btn');
  if (pttBtn) pttBtn.className = 'audio-toggle-btn ' + (on ? 'on' : 'off');
  const chip = document.getElementById('chip-ptt');
  if (chip) {
      chip.textContent = '⌨️ PTT: ' + label;
      chip.className   = 'topbar-chip ' + (on ? 'on' : 'off');
  }
  
  // Sync with Configuration Hub state
  if (typeof audioConfig !== 'undefined' && audioConfig) {
      audioConfig.push_to_talk = on;
  }
  
  const hintEle = document.querySelector('.input-hint');
  if (hintEle) {
    if (on && !window.isMobile) {
      hintEle.innerHTML = `${window.I18N?.chat_hint || ''} <span style="color:var(--accent); font-weight:600;">· ${window.I18N?.ptt_hint || ''}</span>`;
    } else {
      hintEle.textContent = (window.isMobile ? '' : (window.I18N?.chat_hint || ''));
    }
  }
}



window.toggleMic = async function() {
  try {
    const url = window.location.origin + '/api/audio/toggle/mic';
    const r = await fetch(url, {method:'POST'});
    if (!r.ok) return;
    const data = await r.json();
    if (data.ok) {
        _applyMicState(data.listening_status);
        if (data.ptt_forced_off) {
            _applyPTTState(false);
        }
    }
  } catch(e) { console.error('[DEBUG-UI] toggleMic exception:', e); }
};

window.toggleTTS = async function() {
  try {
    const url = window.location.origin + '/api/audio/toggle/tts';
    const r = await fetch(url, {method:'POST'});
    if (!r.ok) return;
    const data = await r.json();
    if (data.ok) {
        _applyTTSState(data.voice_status);
        if (!data.voice_status && window.stopVoice) window.stopVoice();
    }
  } catch(e) { console.error('[DEBUG-UI] toggleTTS exception:', e); }
};

window.togglePTT = async function() {
  if (!window.currentMicOn) {
    if (window.showToast) showToast('🎤 Abilita prima il MIC per usare PTT');
    return;
  }
  try {
    const url = window.location.origin + '/api/audio/toggle/ptt';
    const r = await fetch(url, {method:'POST'});
    const data = await r.json();
    if (r.ok && data.ok) {
        _applyPTTState(data.push_to_talk);
    } else {
        const msg = data.error || 'PTT non disponibile';
        if (window.showToast) showToast('⚠️ ' + msg);
        _applyPTTState(false);
    }
  } catch(e) { console.error('[DEBUG-UI] togglePTT exception:', e); }
};

window._applyMicState = _applyMicState;
window._applyTTSState = _applyTTSState;
window._applyPTTState = _applyPTTState;
