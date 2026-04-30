/**
 * audio_recorder.js
 * Core MediaRecorder logic for PTT/Toggle modes.
 */

window.webAudioRecorder = null;
window.webAudioStream = null;
window.webAudioChunks = [];
window.isWebAudioRecording = false;

window.initWebAudio = async function() {
  if (window.webAudioStream) return true;
  try {
    window.webAudioStream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
    return true;
  } catch (err) {
    console.error('[WebAudio] Failed to acquire microphone:', err);
    return false;
  }
};

window.startWebAudioRecording = async function() {
  if (window.isWebAudioRecording) return;

  if (window._webptt_setButtonState) window._webptt_setButtonState('idle'); 
  const btn = document.getElementById('web-ptt-btn');
  if (btn) btn.innerHTML = '⏳';

  const ready = await window.initWebAudio();
  if (!ready) {
    if (window._webptt_setButtonState) window._webptt_setButtonState('idle');
    if (window.showToast) window.showToast('❌ Impossibile accedere al microfono. Controlla i permessi del browser.');
    else alert('Impossibile accedere al microfono. Controlla i permessi del browser.');
    return;
  }

  if (!window.isTouchHold && !window.isLockedMode) {
    if (window._webptt_setButtonState) window._webptt_setButtonState('idle');
    return;
  }

  window.webAudioChunks = [];
  const mimeType = MediaRecorder.isTypeSupported('audio/webm') ? 'audio/webm' : '';
  const options = mimeType ? { mimeType } : {};

  try {
    window.webAudioRecorder = new MediaRecorder(window.webAudioStream, options);
  } catch (e) {
    window.webAudioRecorder = new MediaRecorder(window.webAudioStream);
  }

  window.webAudioRecorder.ondataavailable = (e) => {
    if (e.data.size > 0) window.webAudioChunks.push(e.data);
  };

  const capturedLockedMode = window.isLockedMode;
  window.webAudioRecorder.onstop = () => uploadWebAudio(capturedLockedMode);
  window.webAudioRecorder.start();
  window.isWebAudioRecording = true;

  if (window._webptt_beep) window._webptt_beep(880, 0.1);
  if (window._webptt_setButtonState) window._webptt_setButtonState('listening');
  console.log('[WebAudio] Recording started... lockedMode=', capturedLockedMode);
};

window.stopWebAudioRecording = function() {
  if (!window.isWebAudioRecording || !window.webAudioRecorder) {
    const btn = document.getElementById('web-ptt-btn');
    if (btn && btn.innerHTML === '⏳') {
      if (window._webptt_setButtonState) window._webptt_setButtonState('idle');
    }
    return;
  }

  if (window._webptt_beep) window._webptt_beep(440, 0.15);
  if (window._webptt_setButtonState) window._webptt_setButtonState('transcribing');

  window.webAudioRecorder.stop();
  window.isWebAudioRecording = false;
  console.log('[WebAudio] Recording stopped, preparing payload...');
};

async function uploadWebAudio(wasLockedMode) {
  if (window.webAudioChunks.length === 0) {
    if (window._webptt_setButtonState) window._webptt_setButtonState('idle');
    return;
  }

  const type = window.webAudioRecorder.mimeType || 'audio/webm';
  const audioBlob = new Blob(window.webAudioChunks, { type });
  window.webAudioChunks = [];

  const chatInput = document.getElementById('message-input') || document.getElementById('user-input');
  const originalPlace = chatInput ? chatInput.placeholder : '';

  if (chatInput) {
    chatInput.placeholder = '🗣️ Trascrizione in corso...';
    chatInput.disabled = true;
  }

  try {
    const arrayBuffer = await audioBlob.arrayBuffer();
    
    // Fallback if _webptt_audioCtx isn't ready
    if (!window._webptt_audioCtx) {
      window._webptt_audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    }
    const audioBuffer = await window._webptt_audioCtx.decodeAudioData(arrayBuffer);
    
    // Use standalone encoder component
    const wavBlob = await window._audioBufferToWav(audioBuffer);
    
    const formData = new FormData();
    formData.append('audio_file', wavBlob, 'speech.wav');

    const res = await fetch('/api/audio/transcribe', { method: 'POST', body: formData });
    const data = await res.json();

    if (data.ok && data.text) {
      const transcribed = data.text.trim();
      console.log('[WebAudio] Transcribed:', transcribed);

      const shouldAutoSend = window._webptt_shouldAutoSend ? window._webptt_shouldAutoSend(wasLockedMode) : false;

      if (shouldAutoSend) {
        if (chatInput) {
          chatInput.value = transcribed;
          chatInput.disabled = false;
          if (typeof window.autoResize === 'function') window.autoResize(chatInput);
        }
        if (typeof window.sendMessage === 'function') window.sendMessage();
      } else {
        if (chatInput) {
          chatInput.value = (chatInput.value + ' ' + transcribed).trim();
          chatInput.dispatchEvent(new Event('input', { bubbles: true }));
          chatInput.focus();
        }
      }

    } else if (!data.ok) {
      console.error('[WebAudio] Transcription error:', data.error);
      if (window.showToast) window.showToast('❌ Errore trascrizione: ' + (data.error || 'sconosciuto'));
    }
  } catch (err) {
    console.error('[WebAudio] Network error during transcription:', err);
    if (window.showToast) window.showToast('❌ Errore di rete durante la trascrizione.');
  } finally {
    if (window._webptt_setButtonState) window._webptt_setButtonState('idle');
    if (chatInput) {
      chatInput.placeholder = originalPlace;
      chatInput.disabled = false;
    }
  }
}
