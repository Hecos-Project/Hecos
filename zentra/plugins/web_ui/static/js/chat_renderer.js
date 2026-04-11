// chat_renderer.js
// Handles DOM manipulation, Markdown parsing, and UI Bubble logic

window.currentAudio = null;

function addBubble(role, text, id) {
  const isUser = role === 'user';
  const msg = document.createElement('div');
  msg.className = `msg ${isUser?'user':'ai'}`;
  if(id) msg.id = id;
  const avatar = document.createElement('div');
  avatar.className = 'msg-avatar';
  if (isUser) {
    avatar.textContent = '👤';
  } else {
    avatar.innerHTML = `<img src="/assets/Zentra_Core_Logo_NBG.png" style="width:24px; height:24px; filter:drop-shadow(0 0 5px rgba(108,140,255,0.4));">`;
  }
  const bubble = document.createElement('div');
  bubble.className = 'msg-bubble';
  if(text) bubble.innerHTML = renderMarkdown(text);
  msg.appendChild(avatar);
  msg.appendChild(bubble);
  
  const chatArea = document.getElementById('chat-area');
  if (chatArea) {
      chatArea.appendChild(msg);
      chatArea.scrollTop = chatArea.scrollHeight;
  }
  
  const hIdx = (window.historyList) ? window.historyList.length : -1;
  if (typeof window.attachMessageActions === 'function') {
    window.attachMessageActions(msg, isUser ? 'user' : 'ai', hIdx);
  }
  return { msg, bubble };
}

function renderMarkdown(text) {
  let html = text
    .replace(/```(\w+)?\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>')
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/\n/g, '<br>');
    
  if (typeof window.processAiImages === 'function') {
    html = window.processAiImages(html);
  }
  return html;
}

// --- Global TTS Player (Blessed for Autoplay) ---
const SILENT_WAV = "data:audio/wav;base64,UklGRigAAABXQVZFZm10IBIAAAABAAEARKwAAIhYAQACABAAAABkYXRhAgAAAAEA";
window.ZentraTTSPlayer = document.createElement('audio');
window.ZentraTTSPlayer.controls = true;
window.ZentraTTSPlayer.style.display = 'block';
window.ZentraTTSPlayer.style.marginTop = '10px';

// Append to body to ensure it's in the DOM for earlier interaction
document.addEventListener('DOMContentLoaded', () => {
  const container = document.createElement('div');
  container.id = 'zentra-player-container';
  container.style.display = 'none';
  document.body.appendChild(container);
  container.appendChild(window.ZentraTTSPlayer);
});

// Helper to unlock autoplay on mobile during user interaction (called from sendMessage/bindWebPTT)
window.unlockAudioContext = function() {
  if (window.ZentraTTSPlayer.src !== SILENT_WAV && !window.ZentraTTSPlayer.src.includes('blob:')) {
    window.ZentraTTSPlayer.src = SILENT_WAV;
    window.ZentraTTSPlayer.play().catch(e => { console.warn("[Audio] Silent unlock failed:", e); });
  }
};

async function tryLoadAudio(bubble) {
  const url = '/api/audio?t=' + Date.now();
  console.log("[Audio] Attempting to load audio from:", url);
  
  const badge = document.createElement('div');
  badge.className='audio-badge';
  badge.innerHTML = '🔊 ';
  
  // If the global player is already in another bubble, clone it there so the user keeps a play button for history
  if (window.ZentraTTSPlayer.parentNode) {
      const oldSrc = window.ZentraTTSPlayer.src;
      const clone = document.createElement('audio');
      clone.controls = true;
      clone.style.display = 'block';
      clone.style.marginTop = '10px';
      clone.src = oldSrc;
      window.ZentraTTSPlayer.parentNode.replaceChild(clone, window.ZentraTTSPlayer);
  }

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
    badge.innerHTML = '⚠️ Audio Error (Click to retry)';
    badge.style.cursor = 'pointer';
    badge.onclick = () => tryLoadAudio(bubble);
    bubble.appendChild(badge);
    return;
  }

  window.ZentraTTSPlayer.src = blobUrl;
  window.currentAudio = window.ZentraTTSPlayer;
  badge.appendChild(window.ZentraTTSPlayer);
  bubble.appendChild(badge);
  showStopVoiceBtn(true);
  
  window.ZentraTTSPlayer.oncanplaythrough = () => {
    console.log("[Audio] Can play through, attempting autoplay...");
    window.ZentraTTSPlayer.play().then(() => {
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

  window.ZentraTTSPlayer.onplay = () => {
      fetch('/api/audio/speaking/start', { method: 'POST' }).catch(() => {});
  };

  window.ZentraTTSPlayer.onpause = () => {
      fetch('/api/audio/speaking/stop', { method: 'POST' }).catch(() => {});
  };

  window.ZentraTTSPlayer.onended = () => { 
      window.currentAudio = null; 
      showStopVoiceBtn(false); 
      fetch('/api/audio/speaking/stop', { method: 'POST' }).catch(() => {});
  };
  window.ZentraTTSPlayer.onerror = () => {
    console.error("[Audio] Player error:", window.ZentraTTSPlayer.error ? window.ZentraTTSPlayer.error.code : 'unknown');
    window.currentAudio = null; showStopVoiceBtn(false);
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
window.addBubble = addBubble;
window.renderMarkdown = renderMarkdown;
window.tryLoadAudio = tryLoadAudio;
window.showStopVoiceBtn = showStopVoiceBtn;
