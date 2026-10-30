// chat_audio_player.js
// Handles Audio playback, TTS blobs, and iOS autoplay unlock logic

// --- Global TTS Player (Blessed for Autoplay) ---
const SILENT_WAV = "data:audio/wav;base64,UklGRigAAABXQVZFZm10IBIAAAABAAEARKwAAIhYAQACABAAAABkYXRhAgAAAAEA";
window.HecosTTSPlayer = document.createElement('audio');
window.HecosTTSPlayer.controls = true;
window.HecosTTSPlayer.style.display = 'block';
window.HecosTTSPlayer.style.marginTop = '10px';

// Append to body to ensure it's in the DOM for earlier interaction
document.addEventListener('DOMContentLoaded', () => {
  const container = document.createElement('div');
  container.id = 'hecos-player-container';
  container.style.display = 'none';
  document.body.appendChild(container);
  container.appendChild(window.HecosTTSPlayer);

  // Prevent <audio> elements from trapping the ESC key inside browser Shadow DOM.
  // Instead of blurring unconditionally on focus (which breaks the three-dots menu),
  // we intercept the ESC key during the capture phase and blur the audio element, 
  // allowing the event to propagate normally to our other document-level listeners.
  document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && document.activeElement && document.activeElement.tagName === 'AUDIO') {
          document.activeElement.blur();
      }
  }, true);
});

// ── Output VU Meter Hook ──
function initOutVuMeter(audioElement) {
    if (!window.outAudioContext) {
        window.outAudioContext = new (window.AudioContext || window.webkitAudioContext)();
        window.outAnalyser = window.outAudioContext.createAnalyser();
        window.outAnalyser.fftSize = 256;
        window.outAnalyser.connect(window.outAudioContext.destination);
        window.outDataArray = new Uint8Array(window.outAnalyser.frequencyBinCount);
        
        function drawOutVu() {
            requestAnimationFrame(drawOutVu);
            if (!window.outAnalyser) return;
            const meter = document.getElementById('out-vu-meter');
            const pctText = document.getElementById('out-pct');
            if (!meter) return;
            
            window.outAnalyser.getByteFrequencyData(window.outDataArray);
            let sum = 0;
            for(let i=0; i<window.outDataArray.length; i++) sum += window.outDataArray[i];
            let avg = sum / window.outDataArray.length;
            let percent = Math.min(100, (avg / 64) * 100);
            meter.style.width = percent + '%';
            if (pctText) pctText.textContent = Math.round(percent) + '%';
        }
        drawOutVu();
    }
    
    if (window.outAudioContext.state === 'suspended') {
        window.outAudioContext.resume().catch(()=>{});
    }
    
    if (!audioElement.dataset.vuHooked) {
        audioElement.dataset.vuHooked = "true";
        try {
            const source = window.outAudioContext.createMediaElementSource(audioElement);
            source.connect(window.outAnalyser);
        } catch (e) {
            console.warn("[OutVu] Could not hook audio element:", e);
        }
    }
}

// Helper to unlock autoplay on mobile during user interaction (called from sendMessage/bindWebPTT)
window.unlockAudioContext = function() {
  if (window.HecosTTSPlayer.src !== SILENT_WAV && !window.HecosTTSPlayer.src.includes('blob:')) {
    window.HecosTTSPlayer.src = SILENT_WAV;
    window.HecosTTSPlayer.play().catch(e => { console.warn("[Audio] Silent unlock failed:", e); });
  }
  
  // Also unlock the VU meter AudioContexts if suspended
  if (window.micAudioContext && window.micAudioContext.state === 'suspended') {
      window.micAudioContext.resume().catch(e => { console.warn("[Audio] Mic unlock failed:", e); });
  }
  if (window.outAudioContext && window.outAudioContext.state === 'suspended') {
      window.outAudioContext.resume().catch(e => { console.warn("[Audio] Out unlock failed:", e); });
  }
};

async function tryLoadAudio(bubble, autoplay = true, forceUrl = null) {
  if (!bubble) return;

  // Prefer the persistent audio_id stored on the bubble (survives page refresh)
  const audioId = bubble.dataset?.audioId || null;
  const url = forceUrl ? forceUrl : (audioId
    ? `/api/audio?id=${encodeURIComponent(audioId)}`
    : `/api/audio?t=${Date.now()}`);

  // Prevent duplicate load calls on the same bubble for the same audio
  if (audioId && bubble.dataset.audioLoaded === audioId && bubble.querySelector('audio')) {
    console.log("[Audio] Audio already loaded for bubble:", audioId);
    return;
  }

  console.log("[Audio] Attempting to load audio from:", url, "autoplay:", autoplay);
  
  // Remove existing audio badges and any rogue audio elements to guarantee a single player
  const existingBadges = bubble.querySelectorAll('.audio-badge');
  existingBadges.forEach(b => b.remove());
  bubble.querySelectorAll('audio').forEach(a => {
    if (a !== window.HecosTTSPlayer) a.remove();
  });

  const badge = document.createElement('div');
  badge.className='audio-badge';
  badge.innerHTML = '<i class="fas fa-volume-up"></i> ';
  
  // Under HTTPS, sometimes the browser blocks direct src assignment for self-signed
  // Fetch it as a blob to prevent CORS/SSL playback issues
  let blobUrl = "";
  try {
    const response = await fetch(url);
    if (!response.ok) throw new Error(`HTTP Error ${response.status}`);
    const blob = await response.blob();
    blobUrl = URL.createObjectURL(blob);
    console.log("[Audio] Blob created successfully for:", audioId || 'live');
  } catch (e) {
    console.error("[Audio] Fetch failed (possibly SSL/CORS):", e);
    badge.innerHTML = '<i class="fas fa-exclamation-triangle"></i> Audio Error (Click to retry)';
    badge.style.cursor = 'pointer';
    badge.onclick = () => tryLoadAudio(bubble, autoplay, forceUrl);
    bubble.appendChild(badge);
    return;
  }

  if (audioId) {
    bubble.dataset.audioLoaded = audioId;
  }

  // If this is a historical message (no autoplay), we don't need the global singleton player.
  if (!autoplay) {
      const historicalPlayer = document.createElement('audio');
      historicalPlayer.controls = true;
      historicalPlayer.style.display = 'block';
      historicalPlayer.style.marginTop = '10px';
      historicalPlayer.src = blobUrl;
      if (window.globalTTSVolume !== undefined) {
          historicalPlayer.volume = window.globalTTSVolume;
      }
      
      historicalPlayer.onplay = () => {
          window.currentAudio = historicalPlayer;
          window.showStopVoiceBtn(true);
          if (typeof initOutVuMeter === 'function') initOutVuMeter(historicalPlayer);
      };
      
      historicalPlayer.onpause = () => {
          window.showStopVoiceBtn(false);
          fetch('/api/audio/speaking/stop', { method: 'POST' }).catch(() => {});
      };
      
      historicalPlayer.onended = () => {
          window.showStopVoiceBtn(false);
          fetch('/api/audio/speaking/stop', { method: 'POST' }).catch(() => {});
      };
      
      badge.appendChild(historicalPlayer);
      bubble.appendChild(badge);
      return;
  }

  // ── Live Audio (Autoplay = true) ──
  // If the global player is currently attached to another bubble in the document,
  // leave a static clone on that other bubble so the user can replay earlier messages.
  const oldParent = window.HecosTTSPlayer.parentNode;
  const isAttachedToAnotherBubble = oldParent && 
                                   document.body.contains(window.HecosTTSPlayer) && 
                                   !bubble.contains(window.HecosTTSPlayer);

  if (isAttachedToAnotherBubble) {
      const oldSrc = window.HecosTTSPlayer.src;
      if (oldSrc && !oldSrc.startsWith('data:')) {
          const clone = document.createElement('audio');
          clone.controls = true;
          clone.style.display = 'block';
          clone.style.marginTop = '10px';
          clone.src = oldSrc;
          oldParent.replaceChild(clone, window.HecosTTSPlayer);
      } else {
          oldParent.removeChild(window.HecosTTSPlayer);
      }
  } else if (oldParent && oldParent !== badge) {
      oldParent.removeChild(window.HecosTTSPlayer);
  }

  window.HecosTTSPlayer.oncanplaythrough = null;
  window.HecosTTSPlayer.src = blobUrl;
  if (window.globalTTSVolume !== undefined) {
      window.HecosTTSPlayer.volume = window.globalTTSVolume;
  }
  window.currentAudio = window.HecosTTSPlayer;
  badge.appendChild(window.HecosTTSPlayer);
  bubble.appendChild(badge);
  
  window.HecosTTSPlayer.oncanplaythrough = () => {
    console.log("[Audio] Can play through, attempting autoplay...");
    window.HecosTTSPlayer.play().then(() => {
        console.log("[Audio] Autoplay success");
    }).catch(err => {
      console.warn("[Audio] Autoplay blocked by browser. User must click play.", err);
      const hint = document.createElement('span');
      hint.style.fontSize = '11px';
      hint.style.color = 'var(--accent)';
      hint.style.display = 'block';
      hint.style.marginTop = '4px';
      hint.textContent = '👆 Clicca Play per ascoltare (Blocco Autoplay Browser)';
      badge.appendChild(hint);
    });
  };

  window.HecosTTSPlayer.onplay = () => {
      window.showStopVoiceBtn(true);
      if (typeof initOutVuMeter === 'function') initOutVuMeter(window.HecosTTSPlayer);
      fetch('/api/audio/speaking/start', { method: 'POST' }).catch(() => {});
  };

  window.HecosTTSPlayer.onpause = () => {
      window.showStopVoiceBtn(false);
      fetch('/api/audio/speaking/stop', { method: 'POST' }).catch(() => {});
  };

  window.HecosTTSPlayer.onended = () => { 
      window.currentAudio = null; 
      window.showStopVoiceBtn(false); 
      fetch('/api/audio/speaking/stop', { method: 'POST' }).catch(() => {});
  };
  window.HecosTTSPlayer.onerror = () => {
    console.error("[Audio] Player error:", window.HecosTTSPlayer.error ? window.HecosTTSPlayer.error.code : 'unknown');
    window.currentAudio = null; 
    window.showStopVoiceBtn(false);
    fetch('/api/audio/speaking/stop', { method: 'POST' }).catch(() => {});
  };
}

// ── Audio Ready Handler (Single File) ──
function handleAudioReady(bubble, finalAudioId) {
  if (!bubble || !finalAudioId) return;
  console.log("[Audio] Single consolidated audio ready:", finalAudioId);
  bubble.dataset.audioId = finalAudioId;
  tryLoadAudio(bubble, true);
}

// ── Deprecated progressive chunk stub ──
function handleAudioChunk(bubble, ev) {
  // Ignored: audio is consolidated into a single WAV file before playback
  console.log("[Audio] Chunk progress:", (ev.chunk_index || 0) + 1, "/", ev.total_chunks);
}

function showStopVoiceBtn(visible) {
  const btn1 = document.getElementById('sidebar-stop-voice-btn');
  const btn2 = document.getElementById('topbar-stop-voice-btn');
  const display = visible ? 'inline-flex' : 'none';
  if (btn1) btn1.style.display = display;
  if (btn2) btn2.style.display = display;
  if (window.updateStopAllBtn) window.updateStopAllBtn();
}

window.stopVoice = function(engine = null) {
  if (window.HecosTTSPlayer) {
    try { window.HecosTTSPlayer.pause(); } catch(e) {}
  }
  if (window.currentAudio) {
    try { window.currentAudio.pause(); } catch(e) {}
    window.currentAudio = null;
  }
  if (window._lastAiBubble) {
    window._lastAiBubble._audioChunks = [];
    window._lastAiBubble._isCurrentlyPlaying = false;
    window._lastAiBubble._chunksFinished = true;
  }
  window.showStopVoiceBtn(false);
  fetch('/api/audio/speaking/stop', { method: 'POST' }).catch(() => {});
  fetch('/api/audio/stop', { method: 'POST' }).catch(() => {});
};

// Global Exports
window.tryLoadAudio = tryLoadAudio;
window.handleAudioChunk = handleAudioChunk;
window.handleAudioReady = handleAudioReady;
window.showStopVoiceBtn = showStopVoiceBtn;
