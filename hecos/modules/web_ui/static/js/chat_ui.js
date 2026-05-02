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
  if (window.currentAudio) {
    window.currentAudio.pause();
    window.currentAudio.src = '';
    window.currentAudio = null;
  }
  try { await fetch('/api/audio/stop', {method: 'POST'}); } catch(e) {}
  try { await fetch('/api/system/stop', {method: 'POST'}); } catch(e) {}
  
  window.isStreaming = false;
  if (sendBtn) sendBtn.disabled = false;
  if (window._liveBackendAiBubble) {
    window._liveBackendAiBubble.innerHTML = `<em style="color:var(--muted)">⛔ ${window.I18N?.webui_chat_interrupted || 'Stopped'}</em>`;
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
    if (sbM) sbM.textContent = d.model || '—';
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
