/**
 * chat_ui.js
 * Handles general DOM interactions, keyboard shortcuts, plugins sidebar, and UI state polling.
 */

window.I18N = window.I18N || {};

const chatArea   = document.getElementById('chat-area');
const userInput  = document.getElementById('user-input');
const sendBtn    = document.getElementById('send-btn');
const welcome    = document.getElementById('welcome');

window.chatArea = chatArea;
window.userInput = userInput;
window.sendBtn = sendBtn;

window.isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);

// --- Input History Logic ---
window._ihIndex = -1;
window._ihDraft = "";

window.saveInputHistory = function(text) {
    const cfg = (window.cfg && window.cfg.input_history) ? window.cfg.input_history : { enabled: true, persist: true, deduplicate: true, max_entries: 5 };
    console.log('[InputHistory:Web] saveInputHistory called. enabled=', cfg.enabled, 'text=', text);
    if (!cfg.enabled) { console.log('[InputHistory:Web] Disabled, skipping.'); return; }
    
    let hist = [];
    const storage = cfg.persist ? localStorage : sessionStorage;
    try { hist = JSON.parse(storage.getItem('hecos_ih') || '[]'); } catch(e){ console.warn('[InputHistory:Web] Parse error:', e); }
    
    if (cfg.deduplicate && hist.length > 0 && hist[hist.length - 1] === text) {
        console.log('[InputHistory:Web] Deduplicate: same as last entry, skipping.');
        window._ihIndex = -1;
        return;
    }
    
    hist.push(text);
    if (hist.length > (cfg.max_entries || 5)) hist = hist.slice(-(cfg.max_entries || 5));
    
    storage.setItem('hecos_ih', JSON.stringify(hist));
    window._ihIndex = -1;
    window._ihDraft = "";
    console.log('[InputHistory:Web] Saved. Total entries:', hist.length, '| Storage:', cfg.persist ? 'localStorage' : 'sessionStorage');
};

window.clearInputHistory = function() {
    localStorage.removeItem('hecos_ih');
    sessionStorage.removeItem('hecos_ih');
    window._ihIndex = -1;
    console.log('[InputHistory:Web] History cleared.');
};

function _initInputHistoryListener() {
    const inp = document.getElementById('user-input');
    if (!inp) {
        console.warn('[InputHistory:Web] user-input element not found, will retry...');
        setTimeout(_initInputHistoryListener, 500);
        return;
    }
    console.log('[InputHistory:Web] Listener registered on #user-input');
    inp.addEventListener('keydown', function(e) {
        if (e.key !== 'ArrowUp' && e.key !== 'ArrowDown') return;
        
        const cfg = (window.cfg && window.cfg.input_history) ? window.cfg.input_history : { enabled: true, persist: true };
        if (!cfg.enabled) { console.log('[InputHistory:Web] Disabled.'); return; }
        
        const storage = cfg.persist ? localStorage : sessionStorage;
        let hist = [];
        try { hist = JSON.parse(storage.getItem('hecos_ih') || '[]'); } catch(err){}
        
        console.log('[InputHistory:Web] ArrowKey pressed. History size:', hist.length, '| idx:', window._ihIndex);
        
        if (hist.length === 0) {
            console.log('[InputHistory:Web] No history in storage.');
            // Show a brief hint below the input box
            let hint = document.getElementById('_ih_empty_hint');
            if (!hint) {
                hint = document.createElement('div');
                hint.id = '_ih_empty_hint';
                hint.style.cssText = [
                    'position:absolute', 'bottom:calc(100% + 6px)', 'left:50%',
                    'transform:translateX(-50%)', 'background:rgba(30,30,40,0.92)',
                    'color:#aaa', 'font-size:12px', 'padding:5px 14px',
                    'border-radius:8px', 'pointer-events:none',
                    'border:1px solid rgba(255,255,255,0.08)',
                    'white-space:nowrap', 'opacity:0',
                    'transition:opacity 0.2s ease', 'z-index:9999'
                ].join(';');
                hint.textContent = '⏱ No input history yet — type a message and press Enter';
                (inp.parentElement || document.body).style.position = 'relative';
                (inp.parentElement || document.body).appendChild(hint);
            }
            hint.style.opacity = '1';
            clearTimeout(hint._hideTimer);
            hint._hideTimer = setTimeout(() => { hint.style.opacity = '0'; }, 2000);
            e.preventDefault();
            return;
        }

        if (window._ihIndex === -1) {
            window._ihDraft = inp.value;
            window._ihIndex = hist.length;
        }

        if (e.key === 'ArrowUp') {
            if (window._ihIndex > 0) window._ihIndex--;
        } else {
            if (window._ihIndex < hist.length) window._ihIndex++;
        }

        if (window._ihIndex >= hist.length) {
            inp.value = window._ihDraft;
            window._ihIndex = -1;
        } else {
            inp.value = hist[window._ihIndex];
        }
        if (typeof window.autoResize === 'function') window.autoResize(inp);
        console.log('[InputHistory:Web] Set input to:', inp.value, '| idx:', window._ihIndex);
        e.preventDefault();
    });
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', _initInputHistoryListener);
} else {
    _initInputHistoryListener();
}
// ---------------------------

window.hideWelcome = function() {
  if (welcome) welcome.style.display = 'none';
};

window.autoResize = function(ta) {
  ta.style.height = 'auto';
  ta.style.height = Math.min(ta.scrollHeight, 160) + 'px';
};

window.handleKey = function(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    if (window.sendMessage) window.sendMessage();
  }
};

window.startPrompt = function(text) {
  if (userInput) {
    userInput.value = text;
    window.autoResize(userInput);
    if (window.sendMessage) window.sendMessage();
  }
};

window.clearChat = async function() {
  // If chat history manager is available, create a new session (handles auto-wipe internally)
  if (window.newChatSession) {
    await window.newChatSession();
    return;  // newChatSession already calls clearChat UI-side
  }
  // Fallback: just clear the DOM
  window.chatHistory = [];
  if (chatArea) chatArea.innerHTML = '';
  if (welcome) {
      chatArea.appendChild(welcome);
      welcome.style.display = 'flex';
  }
};

window._clearChatDOM = function() {
  window.chatHistory = [];
  if (chatArea) chatArea.innerHTML = '';
  if (welcome) {
      chatArea.appendChild(welcome);
      welcome.style.display = 'flex';
  }
};

window.clearInput = function() {
  if (window.userInput) {
    window.userInput.value = '';
    window.autoResize(window.userInput);
    window.userInput.focus();
  }
};

window.stopVoice = async function() {
  console.log("[Audio] stopVoice triggered");
  if (window._stopVoiceTimeout) return;
  window._stopVoiceTimeout = true;
  setTimeout(() => { window._stopVoiceTimeout = false; }, 1000);

  if (window.currentAudio) {
    window.currentAudio.pause();
    window.currentAudio.src = '';
    window.currentAudio = null;
  }
  try { fetch('/api/audio/stop', {method: 'POST'}).catch(()=>{}); } catch(e) {}
  try { fetch('/api/system/stop', {method: 'POST'}).catch(()=>{}); } catch(e) {}
  
  window.isStreaming = false;
  if (sendBtn) sendBtn.disabled = false;
  if (window._liveBackendAiBubble) {
    window._liveBackendAiBubble.innerHTML = `<em style="color:var(--muted)"><i class="fas fa-ban"></i> ${window.I18N?.webui_chat_interrupted || 'Stopped'}</em>`;
    window._liveBackendAiBubble = null;
  }
  if (window.showStopVoiceBtn) window.showStopVoiceBtn(false);
};

// Hotkeys
document.addEventListener('keydown', function(e) {
  if (e.key === 'Escape') {
    window.stopVoice();
  }
  if (e.key === 'F4') { e.preventDefault(); if(window.toggleMic) window.toggleMic(); }
  if (e.key === 'F6') { e.preventDefault(); if(window.toggleTTS) window.toggleTTS(); }
  if (e.key === 'F7') { 
    e.preventDefault(); 
    window.open('/hecos/config/ui', '_blank'); 
  }
  if (e.key === 'F8') { e.preventDefault(); if(window.togglePTT) window.togglePTT(); }
});

window.refreshStatus = async function() {
  try {
    const d = await (await fetch('/hecos/status')).json();
    const sbB = document.getElementById('sb-backend');
    const sbM = document.getElementById('sb-model');
    const sbS = document.getElementById('sb-soul');
    const tbM = document.getElementById('tb-model');
    if (sbB) sbB.textContent = d.backend || '—';
    if (sbM) {
        const fullModel = d.model || '—';
        sbM.title = fullModel;
        sbM.textContent = fullModel.includes('/') ? fullModel.split('/').pop() : fullModel;
    }
    if (sbS) sbS.textContent = d.persona || '—';

    window.HecosPersonaName = d.persona || 'Hecos';

    const isConnected = !!d.model;
    if (tbM) {
        tbM.textContent = isConnected ? 'Online' : (window.I18N?.webui_chat_offline || 'Offline');
        tbM.style.color = isConnected ? 'var(--green)' : 'var(--red)';
    }
    const tbDot = document.getElementById('tb-status-dot');
    if (tbDot) {
        tbDot.style.background = isConnected ? 'var(--green)' : 'var(--red)';
        tbDot.style.boxShadow = isConnected ? '0 0 8px var(--green)' : '0 0 8px var(--red)';
        tbDot.className = isConnected ? 'pulsing' : '';
    }
    
    if (d.avatar) {
        window.HecosAvatar = d.avatar;
    }
    if (d.avatar_size) {
        window.HecosAvatarSize = d.avatar_size;
        // Apply size class globally to chat area
        const chatArea = document.getElementById('chat-area');
        if (chatArea) {
            chatArea.classList.remove('size-small', 'size-medium', 'size-large');
            chatArea.classList.add('size-' + d.avatar_size);
        }
    }



    const micIsOn = (d.mic === 'ON');
    const pttIsOn = (d.ptt === 'ON');
    if (window._applyMicState) window._applyMicState(micIsOn);
    if (window._applyTTSState) window._applyTTSState(d.tts === 'ON');
    // PTT can only be ON if MIC is also ON — enforce this dependency client-side
    if (window._applyPTTState) window._applyPTTState(micIsOn && pttIsOn);
    


  } catch(e) {
    const tbM = document.getElementById('tb-model');
    const tbDot = document.getElementById('tb-status-dot');
    if (tbM) {
        tbM.textContent = (window.I18N && window.I18N.webui_chat_offline) ? window.I18N.webui_chat_offline : 'Offline';
        tbM.style.color = 'var(--red)';
    }
    if (tbDot) {
        tbDot.style.background = 'var(--red)';
        tbDot.style.boxShadow = '0 0 8px var(--red)';
        tbDot.className = '';
    }
  }
};

window.loadPlugins = async function() {
  // HIDDEN: the user requested to remove the Active Plugins section from the sidebar for now
  // to save space and unnecessary processing.
};

window.toggleSidebarDesktop = function() {
  const sb = document.getElementById('sidebar');
  if(!sb) return;
  const isCollapsed = sb.classList.toggle('collapsed');
  localStorage.setItem('sidebarCollapsed', isCollapsed);
};

// Start periodic checks
document.addEventListener('DOMContentLoaded', () => {
    if (localStorage.getItem('sidebarCollapsed') === 'true') {
      const sb = document.getElementById('sidebar');
      if (sb) sb.classList.add('collapsed');
    }
    window.refreshStatus();
    window.loadPlugins();
    setInterval(window.refreshStatus, 4000);
    
    if (window.userInput) window.userInput.focus();
    
    // Heartbeat
    setInterval(() => {
      fetch('/hecos/heartbeat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ type: 'chat' })
      }).catch(() => {});
    }, 5000);
});
