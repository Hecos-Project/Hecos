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

window.clearChat = function() {
  window.chatHistory = [];
  if (chatArea) chatArea.innerHTML = '';
  if (welcome) {
      chatArea.appendChild(welcome);
      welcome.style.display = 'flex';
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
    window._liveBackendAiBubble.innerHTML = '<em style="color:var(--muted)">⛔ Interrotto</em>';
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
    window.open('/zentra/config/ui', '_blank'); 
  }
  if (e.key === 'F8') { e.preventDefault(); if(window.togglePTT) window.togglePTT(); }
});

window.refreshStatus = async function() {
  try {
    const d = await (await fetch('/zentra/status')).json();
    const sbB = document.getElementById('sb-backend');
    const sbM = document.getElementById('sb-model');
    const tbM = document.getElementById('tb-model');
    if (sbB) sbB.textContent = d.backend || '—';
    if (sbM) sbM.textContent = d.model || '—';
    if (tbM) tbM.textContent = d.model || (window.I18N.offline || 'Offline');

    if (window._applyMicState) window._applyMicState(d.mic === 'ON');
    if (window._applyTTSState) window._applyTTSState(d.tts === 'ON');
    if (window._applyPTTState) window._applyPTTState(d.ptt === 'ON');
    
    const ac = d.audio_config || {};
    if (window._applyRoutingState) window._applyRoutingState(ac.stt_source || 'system', ac.tts_destination || 'web');

  } catch(e) {
    const tbM = document.getElementById('tb-model');
    if (tbM) tbM.textContent = window.I18N.offline || 'Offline';
  }
};

window.loadPlugins = async function() {
  try {
    const cfg  = await (await fetch('/zentra/config')).json();
    const icons = {DASHBOARD:'📊',FILE_MANAGER:'📁',HELP:'❓',MEDIA:'🎵',ROLEPLAY:'🎭',SYSTEM:'⚙',WEB:'🌐',WEBCAM:'📷',WEB_UI:'💻'};
    const prompts = {
      DASHBOARD: window.I18N.prompt_dashboard,
      FILE_MANAGER: 'read: config/system.yaml',
      HELP: window.I18N.prompt_help,
      MEDIA: window.I18N.prompt_media,
      ROLEPLAY: window.I18N.prompt_roleplay,
      SYSTEM: window.I18N.prompt_system,
      WEB: window.I18N.prompt_web,
      WEBCAM: window.I18N.prompt_webcam
    };
    let html = '';
    for(const [tag,pc] of Object.entries(cfg.plugins||{})) {
      const on = pc.enabled !== false;
      const pText = prompts[tag] ? prompts[tag].replace(/'/g, "\\'") : '';
      const onClick = on && pText ? `onclick="window.startPrompt('${pText}')"` : '';
      const cursor = on && pText ? 'cursor:pointer;' : (on ? 'cursor:default;' : 'cursor:not-allowed;');
      html+=`<div class="sidebar-btn" ${onClick} style="font-size:12px;${!on?'opacity:.4;':''}${cursor}"><span class="icon">${icons[tag]||'🧩'}</span> ${tag}</div>`;
    }
    const sbP = document.getElementById('sb-plugins');
    if (sbP) sbP.innerHTML = html || `<div style="font-size:12px;color:var(--muted);">${window.I18N.none || 'None'}</div>`;
  } catch(e){}
};

// Start periodic checks
document.addEventListener('DOMContentLoaded', () => {
    window.refreshStatus();
    window.loadPlugins();
    setInterval(window.refreshStatus, 4000);
    
    if (window.userInput) window.userInput.focus();
    
    // Heartbeat
    setInterval(() => {
      fetch('/zentra/heartbeat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ type: 'chat' })
      }).catch(() => {});
    }, 5000);
});
