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

  // Prevent <audio> elements from trapping keyboard focus inside browser Shadow DOM.
  // When an <audio controls> element has focus, the browser's internal shadow root
  // consumes ESC (and other keys) before they reach our document-level listeners.
  // By immediately blurring any audio that gains focus, ESC always propagates to our handlers.
  document.addEventListener('focusin', (e) => {
      if (e.target && e.target.tagName === 'AUDIO') {
          e.target.blur();
      }
  });
});

// Helper to unlock autoplay on mobile during user interaction (called from sendMessage/bindWebPTT)
window.unlockAudioContext = function() {
  if (window.HecosTTSPlayer.src !== SILENT_WAV && !window.HecosTTSPlayer.src.includes('blob:')) {
    window.HecosTTSPlayer.src = SILENT_WAV;
    window.HecosTTSPlayer.play().catch(e => { console.warn("[Audio] Silent unlock failed:", e); });
  }
  
  // Also unlock the VU meter AudioContext if suspended
  if (window.micAudioContext && window.micAudioContext.state === 'suspended') {
      window.micAudioContext.resume().catch(e => { console.warn("[Audio] Mic unlock failed:", e); });
  }
};

async function tryLoadAudio(bubble, autoplay = true, forceUrl = null) {
  // Prefer the persistent audio_id stored on the bubble (survives page refresh)
  const audioId = bubble.dataset?.audioId || null;
  const url = forceUrl ? forceUrl : (audioId
    ? `/api/audio?id=${encodeURIComponent(audioId)}`
    : `/api/audio?t=${Date.now()}`);
  console.log("[Audio] Attempting to load audio from:", url, "autoplay:", autoplay);
  
  // Remove existing audio badges to prevent duplicates
  const existingBadges = bubble.querySelectorAll('.audio-badge');
  existingBadges.forEach(b => b.remove());

  const badge = document.createElement('div');
  badge.className='audio-badge';
  badge.innerHTML = '<i class="fas fa-volume-up"></i> ';
  
  // Under HTTPS, sometimes the browser blocks direct src assignment for self-signed
  // Let's try to fetch it as a blob to see if it's a network/security error
  let blobUrl = "";
  try {
    const response = await fetch(url);
    if (!response.ok) throw new Error(`HTTP Error ${response.status}`);
    const blob = await response.blob();
    blobUrl = URL.createObjectURL(blob);
    console.log("[Audio] Blob created successfully");
  } catch (e) {
    console.error("[Audio] Fetch failed (possibly SSL/CORS):", e);
    badge.innerHTML = '<i class="fas fa-exclamation-triangle"></i> Audio Error (Click to retry)';
    badge.style.cursor = 'pointer';
    badge.onclick = () => tryLoadAudio(bubble, autoplay);
    bubble.appendChild(badge);
    return;
  }

  // If this is a historical message (no autoplay), we don't need the global singleton player.
  // Using the singleton causes race conditions when loading multiple historical messages concurrently.
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
  // If the global player is already in another bubble, clone it there so the user keeps a play button for history
  if (window.HecosTTSPlayer.parentNode) {
      const oldSrc = window.HecosTTSPlayer.src;
      const clone = document.createElement('audio');
      clone.controls = true;
      clone.style.display = 'block';
      clone.style.marginTop = '10px';
      clone.src = oldSrc;
      window.HecosTTSPlayer.parentNode.replaceChild(clone, window.HecosTTSPlayer);
  }

  window.HecosTTSPlayer.src = blobUrl;
  if (window.globalTTSVolume !== undefined) {
      window.HecosTTSPlayer.volume = window.globalTTSVolume;
  }
  window.currentAudio = window.HecosTTSPlayer;
  badge.appendChild(window.HecosTTSPlayer);
  bubble.appendChild(badge);
  
  window.HecosTTSPlayer.oncanplaythrough = () => {
    console.log("[Audio] Can play through...");
    console.log("[Audio] Attempting autoplay...");
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

function showStopVoiceBtn(visible) {
  const btn1 = document.getElementById('sidebar-stop-voice-btn');
  const btn2 = document.getElementById('topbar-stop-voice-btn');
  const display = visible ? 'inline-flex' : 'none';
  if (btn1) btn1.style.display = display;
  if (btn2) btn2.style.display = display;
}

// Global Exports
window.tryLoadAudio = tryLoadAudio;
window.showStopVoiceBtn = showStopVoiceBtn;
