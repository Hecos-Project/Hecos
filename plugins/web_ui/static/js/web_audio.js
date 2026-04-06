/**
 * Zentra Web Audio (Mobile PTT / WebRTC)
 * Handles client-side microphone capture using MediaRecorder.
 */

let webAudioRecorder = null;
let webAudioStream = null;
let webAudioChunks = [];
let isWebAudioRecording = false;
let isTouchHold = false;
let isLockedMode = false;
let pressStartTime = 0;

async function initWebAudio() {
  if (webAudioStream) return true;
  try {
    webAudioStream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
    return true;
  } catch (err) {
    console.error("[WebAudio] Failed to acquire microphone:", err);
    return false;
  }
}

async function startWebAudioRecording() {
  if (isWebAudioRecording) return;
  
  const pttBtn = document.getElementById("web-ptt-btn");
  if (pttBtn) {
      pttBtn.innerHTML = "⏳";
      pttBtn.classList.add("recording");
  }

  const ready = await initWebAudio();
  if (!ready) {
    if (pttBtn) { pttBtn.innerHTML = "🎙️"; pttBtn.classList.remove("recording"); }
    alert("Impossibile accedere al microfono. Controlla i permessi del browser.");
    return;
  }

  // RACE CONDITION FIX: Abort if finger was lifted AND it wasn't a quick tap lock
  if (!isTouchHold && !isLockedMode) {
     if (pttBtn) { pttBtn.innerHTML = "🎙️"; pttBtn.classList.remove("recording"); }
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

  webAudioRecorder.onstop = uploadWebAudio;
  webAudioRecorder.start();
  isWebAudioRecording = true;
  
  if (pttBtn) pttBtn.innerHTML = isLockedMode ? "🔴 🔓" : "🔴";
  console.log("[WebAudio] Recording started...");
}

function stopWebAudioRecording() {
  if (!isWebAudioRecording || !webAudioRecorder) {
      // If we weren't recording yet, reset button anyway (handles aborts)
      const pttBtn = document.getElementById("web-ptt-btn");
      if (pttBtn && pttBtn.innerHTML === "⏳") {
          pttBtn.innerHTML = "🎙️";
          pttBtn.classList.remove("recording");
      }
      return;
  }
  
  const pttBtn = document.getElementById("web-ptt-btn");
  if (pttBtn) {
      pttBtn.innerHTML = "📤"; // Sending state
      pttBtn.classList.remove("recording");
  }

  webAudioRecorder.stop();
  isWebAudioRecording = false;
  console.log("[WebAudio] Recording stopped, preparing payload...");
}

async function uploadWebAudio() {
  if (webAudioChunks.length === 0) return;

  const type = webAudioRecorder.mimeType || 'audio/webm';
  const audioBlob = new Blob(webAudioChunks, { type: type });
  webAudioChunks = [];

  const formData = new FormData();
  const ext = type.includes('mp4') ? 'mp4' : (type.includes('ogg') ? 'ogg' : 'webm');
  formData.append("audio_file", audioBlob, `speech.${ext}`);

  const chatInput = document.getElementById("message-input") || document.getElementById("user-input");
  const pttBtn = document.getElementById("web-ptt-btn");
  const originalPlace = chatInput ? chatInput.placeholder : "";

  if (chatInput) {
    chatInput.placeholder = "🗣️ Trascrizione in corso...";
    chatInput.disabled = true;
  }

  try {
    const res = await fetch("/api/audio/transcribe", { method: "POST", body: formData });
    const data = await res.json();
    
    if (data.ok && data.text) {
      console.log("[WebAudio] Transcribed:", data.text);
      if (chatInput) {
         chatInput.value = (chatInput.value + " " + data.text).trim();
         chatInput.dispatchEvent(new Event('input', { bubbles: true }));
      }
    } else if (!data.ok) {
      console.error("[WebAudio] Transcription error:", data.error);
    }
  } catch (err) {
    console.error("[WebAudio] Network error during transcription:", err);
  } finally {
    if (pttBtn) pttBtn.innerHTML = "🎙️";
    if (chatInput) {
      chatInput.placeholder = originalPlace;
      chatInput.disabled = false;
      chatInput.focus();
    }
  }
}

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
    const isTapEvent = e.type === "mouseup" || e.type === "touchend";

    // If tapped (<400ms duration), transition into Locked Mode
    if (isTapEvent && elapsed < 400 && !isLockedMode) {
      isLockedMode = true;
      if (isWebAudioRecording) {
         const pttBtn = document.getElementById("web-ptt-btn");
         if (pttBtn) pttBtn.innerHTML = "🔴 🔓";
      }
      return;
    }

    if (!isWebAudioRecording) return;
    if (isLockedMode && e.type === "mouseleave") return;

    isLockedMode = false;
    stopWebAudioRecording();
  };

  btn.addEventListener("mousedown", startFn);
  btn.addEventListener("mouseup", stopFn);
  btn.addEventListener("mouseleave", stopFn); 
  btn.addEventListener("touchstart", startFn, { passive: false });
  btn.addEventListener("touchend", stopFn, { passive: false });
  btn.addEventListener("touchcancel", stopFn, { passive: false });
}

document.addEventListener("DOMContentLoaded", () => {
    bindWebPTT("web-ptt-btn");
});

