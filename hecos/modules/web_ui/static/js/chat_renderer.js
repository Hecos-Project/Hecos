// chat_renderer.js
// Handles DOM manipulation, Markdown parsing, and UI Bubble logic

window.currentAudio = null;

function addBubble(role, text, id, opts) {
  const isUser = role === 'user';
  const msg = document.createElement('div');
  msg.className = `msg ${isUser?'user':'ai'}`;
  if(id) msg.id = id;

  const avatar = document.createElement('div');
  avatar.className = `msg-avatar`;
  
  if (isUser) {
    const usrSrc = window.HecosUserAvatar;
    if (usrSrc) {
        avatar.innerHTML = `<img src="${usrSrc}" style="width:100%; height:100%; object-fit:cover; border-radius:50%;" onerror="this.outerHTML='<i class=\'fas fa-user\'></i>'">`;
    } else {
        avatar.innerHTML = '<i class="fas fa-user"></i>';
    }
  } else {
    const avatarSrc = window.HecosAvatar || "/assets/Hecos_Logo_SQR_NBG_LogoOnly.png";
    const imgStyle = window.HecosAvatar ? 
      "object-fit:cover; border-radius:50%;" : 
      "filter:drop-shadow(0 0 5px rgba(108,140,255,0.4));";
    
    // Wrap in a zoomable container
    avatar.innerHTML = `
      <div class="avatar-zoom-wrapper" style="width:100%; height:100%; display:flex; align-items:center; justify-content:center;" onclick="window.openAvatarFull('${avatarSrc}')">
        <img src="${avatarSrc}" onerror="this.src='/assets/Hecos_Logo_SQR_NBG_LogoOnly.png';" style="${imgStyle}">
        <div class="avatar-zoom-icon"><i class="fas fa-search-plus"></i></div>
      </div>`;

  }
  
  const wrapper = document.createElement('div');
  wrapper.className = 'msg-content-wrapper';

  const header = document.createElement('div');
  header.className = 'msg-header';

  const nameEl = document.createElement('span');
  nameEl.className = 'msg-name';
  nameEl.textContent = isUser ? (window.HecosUserName || 'User') : (window.HecosPersonaName || 'Hecos');

  const timeEl = document.createElement('span');
  timeEl.className = 'msg-time';
  const ts = (opts && opts.timestamp) ? new Date(opts.timestamp) : new Date();
  timeEl.textContent = ts.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});

  header.appendChild(nameEl);
  header.appendChild(timeEl);
  wrapper.appendChild(header);

  const bubble = document.createElement('div');
  bubble.className = 'msg-bubble';
  if(text) bubble.innerHTML = renderMarkdown(text);
  
  wrapper.appendChild(bubble);

  msg.appendChild(avatar);
  msg.appendChild(wrapper);
  
  const chatArea = document.getElementById('chat-area');
  if (chatArea) {
      chatArea.appendChild(msg);
      chatArea.scrollTop = chatArea.scrollHeight;
  }
  
  // Track last real AI bubble for audio_ready (don't use :last-child which breaks when action-log divs follow)
  if (!isUser) window._lastAiBubble = bubble;
  
  const hIdx = (opts && opts.historyIndex !== undefined) ? opts.historyIndex : 
               ((window.chatHistory) ? window.chatHistory.length - 1 : -1);

  if (typeof window.attachMessageActions === 'function') {
    window.attachMessageActions(msg, isUser ? 'user' : 'ai', hIdx);
  }
  return { msg, bubble };
}

// Fullscreen Avatar View
window.openAvatarFull = function(src) {
  let lb = document.getElementById('avatar-lightbox');
  if (!lb) {
    lb = document.createElement('div');
    lb.id = 'avatar-lightbox';
    lb.onclick = () => lb.classList.remove('active');
    document.body.appendChild(lb);
  }
  lb.innerHTML = `<img src="${src}">`;
  setTimeout(() => lb.classList.add('active'), 10);
};


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
});

// Helper to unlock autoplay on mobile during user interaction (called from sendMessage/bindWebPTT)
window.unlockAudioContext = function() {
  if (window.HecosTTSPlayer.src !== SILENT_WAV && !window.HecosTTSPlayer.src.includes('blob:')) {
    window.HecosTTSPlayer.src = SILENT_WAV;
    window.HecosTTSPlayer.play().catch(e => { console.warn("[Audio] Silent unlock failed:", e); });
  }
};

async function tryLoadAudio(bubble) {
  const url = '/api/audio?t=' + Date.now();
  console.log("[Audio] Attempting to load audio from:", url);
  
  const badge = document.createElement('div');
  badge.className='audio-badge';
  badge.innerHTML = '<i class="fas fa-volume-up"></i> ';
  
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
    badge.onclick = () => tryLoadAudio(bubble);
    bubble.appendChild(badge);
    return;
  }

  window.HecosTTSPlayer.src = blobUrl;
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
      showStopVoiceBtn(true);
      fetch('/api/audio/speaking/start', { method: 'POST' }).catch(() => {});
  };

  window.HecosTTSPlayer.onpause = () => {
      showStopVoiceBtn(false);
      fetch('/api/audio/speaking/stop', { method: 'POST' }).catch(() => {});
  };

  window.HecosTTSPlayer.onended = () => { 
      window.currentAudio = null; 
      showStopVoiceBtn(false); 
      fetch('/api/audio/speaking/stop', { method: 'POST' }).catch(() => {});
  };
  window.HecosTTSPlayer.onerror = () => {
    console.error("[Audio] Player error:", window.HecosTTSPlayer.error ? window.HecosTTSPlayer.error.code : 'unknown');
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

// Alias used by chat_history.js to restore historical messages
window.appendMessage = function(role, text, opts = {}) {
    if (!text || opts.noSave === undefined) opts.noSave = true;
    // Only add if there is actual content
    if (text && text.trim()) {
        window.addBubble(role, text, null, opts);
    }
};
