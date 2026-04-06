let history = [], isStreaming = false;
let autoScroll = true;

// --- AUDIO FEEDBACK SYNT ---
let _audioCtx = null;
function playSynthBeep(freq, duration=0.1) {
  try {
    if (!_audioCtx) _audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    const osc = _audioCtx.createOscillator();
    const gain = _audioCtx.createGain();
    osc.connect(gain);
    gain.connect(_audioCtx.destination);
    osc.type = 'sine';
    osc.frequency.setValueAtTime(freq, _audioCtx.currentTime);
    gain.gain.setValueAtTime(0, _audioCtx.currentTime);
    gain.gain.linearRampToValueAtTime(0.08, _audioCtx.currentTime + 0.01);
    gain.gain.linearRampToValueAtTime(0, _audioCtx.currentTime + duration);
    osc.start();
    osc.stop(_audioCtx.currentTime + duration);
  } catch(e) { console.error("PTT Audio Error:", e); }
}

let currentMicOn  = false;
let currentTTSOn  = false;
let currentPTTOn  = false;
let currentSTTSource = 'system';
let currentTTSDest   = 'web';
// Let currentAudio be handled globally by chat_renderer.js

const I18N = window.I18N || {};

const chatArea   = document.getElementById('chat-area');
const userInput  = document.getElementById('user-input');
const sendBtn    = document.getElementById('send-btn');
const welcome    = document.getElementById('welcome');
const micBtn     = document.getElementById('mic-btn');
const ttsBtn     = document.getElementById('tts-btn');
const pttBtn     = document.getElementById('ptt-btn');
const sttSelect  = document.getElementById('stt-source-select');
const ttsSelect  = document.getElementById('tts-dest-select');

function hideWelcome() { if(welcome) welcome.style.display = 'none'; }
function autoResize(ta) { ta.style.height='auto'; ta.style.height=Math.min(ta.scrollHeight,160)+'px'; }
function handleKey(e) { if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();sendMessage();} }
function startPrompt(text) { if(userInput) { userInput.value=text; autoResize(userInput); sendMessage(); } }

// ── Audio toggle helpers ──────────────────────────────────────────────────────

function _applyMicState(on) {
  currentMicOn = on;
  const label = on ? 'ON' : 'OFF';
  const labelEl = document.getElementById('mic-label');
  if (labelEl) labelEl.textContent = label;
  if (micBtn) micBtn.className = 'audio-toggle-btn ' + (on ? 'on' : 'off');
  const chip = document.getElementById('chip-mic');
  if (chip) {
      chip.textContent = '🎤 MIC: ' + label;
      chip.className   = 'topbar-chip ' + (on ? 'on' : 'off');
  }
  // If MIC is turned OFF, also reset PTT state visually
  if (!on) {
    _applyPTTState(false);
    // Gray out PTT button to signal it's unavailable
    if (pttBtn) pttBtn.title = 'Abilita prima il MIC per usare PTT';
  } else {
    if (pttBtn) pttBtn.title = 'Toggle Push-To-Talk (F8)';
  }
}

function _applyTTSState(on) {
  currentTTSOn = on;
  const label = on ? 'ON' : 'OFF';
  const labelEl = document.getElementById('tts-label');
  if (labelEl) labelEl.textContent = label;
  if (ttsBtn) ttsBtn.className = 'audio-toggle-btn ' + (on ? 'on' : 'off');
  const chip = document.getElementById('chip-tts');
  if (chip) {
      chip.textContent = '🔊 TTS: ' + label;
      chip.className   = 'topbar-chip ' + (on ? 'on' : 'off');
  }
}

function _applyPTTState(on) {
  currentPTTOn = on;
  const label = on ? 'ON' : 'OFF';
  const labelEl = document.getElementById('ptt-label');
  if (labelEl) labelEl.textContent = label;
  if (pttBtn) pttBtn.className = 'audio-toggle-btn ' + (on ? 'on' : 'off');
  const chip = document.getElementById('chip-ptt');
  if (chip) {
      chip.textContent = '⌨️ PTT: ' + label;
      chip.className   = 'topbar-chip ' + (on ? 'on' : 'off');
  }
  
  const hintEle = document.querySelector('.input-hint');
  if (hintEle) {
    if (on) {
      hintEle.innerHTML = `${I18N.chat_hint || ''} <span style="color:var(--accent); font-weight:600;">· ${I18N.ptt_hint || ''}</span>`;
    } else {
      hintEle.textContent = I18N.chat_hint || '';
    }
  }
}

function _applyRoutingState(stt, tts) {
  currentSTTSource = stt;
  currentTTSDest   = tts;
  if (sttSelect) for(let opt of sttSelect.options) { opt.selected = opt.value === stt; }
  if (ttsSelect) for(let opt of ttsSelect.options) { opt.selected = opt.value === tts; }
  
  const chipStt = document.getElementById('chip-stt-source');
  const chipTts = document.getElementById('chip-tts-dest');
  if (chipStt) chipStt.textContent = 'IN: ' + stt.toUpperCase();
  if (chipTts) chipTts.textContent   = 'OUT: ' + tts.toUpperCase();
}

async function toggleMic() {
  try {
    const url = window.location.origin + '/api/audio/toggle/mic';
    const r = await fetch(url, {method:'POST'});
    if (!r.ok) {
        console.error('[DEBUG-UI] Mic toggle HTTP Error:', r.status);
        return;
    }
    const data = await r.json();
    if (data.ok) {
        _applyMicState(data.listening_status);
        // If backend auto-disabled PTT because MIC went OFF
        if (data.ptt_forced_off) {
            _applyPTTState(false);
            currentPTTOn = false;
        }
    }
  } catch(e) {
    console.error('[DEBUG-UI] toggleMic exception:', e);
  }
}

async function toggleTTS() {
  try {
    const url = window.location.origin + '/api/audio/toggle/tts';
    const r = await fetch(url, {method:'POST'});
    if (!r.ok) {
        console.error('[DEBUG-UI] TTS toggle HTTP Error:', r.status);
        return;
    }
    const data = await r.json();
    if (data.ok) {
        _applyTTSState(data.voice_status);
        if (!data.voice_status) stopVoice();
    }
  } catch(e) {
    console.error('[DEBUG-UI] toggleTTS exception:', e);
  }
}

async function togglePTT() {
  // Guard: PTT requires MIC to be ON
  if (!currentMicOn) {
    if (window.showToast) showToast('🎤 Abilita prima il MIC per usare PTT');
    else console.warn('[Audio] PTT blocked: MIC is OFF');
    return;
  }
  try {
    const url = window.location.origin + '/api/audio/toggle/ptt';
    const r = await fetch(url, {method:'POST'});
    const data = await r.json();
    if (r.ok && data.ok) {
        _applyPTTState(data.push_to_talk);
    } else {
        // Backend rejected (e.g. MIC went OFF between check and API call)
        const msg = data.error || 'PTT non disponibile';
        if (window.showToast) showToast('⚠️ ' + msg);
        _applyPTTState(false);
    }
  } catch(e) {
    console.error('[DEBUG-UI] togglePTT exception:', e);
  }
}

async function setAudioRouting(key, val) {
  if (key === 'stt_source' && val === 'web') {
    if (window.showToast) showToast('⚠️ L\'ascolto da browser è in sviluppo. Il MIC di sistema verrà silenziato.', 'warn');
    else console.warn('[Audio] Web STT selected (In Sviluppo). System Mic is now ignored.');
  }
  try {
    const payload = {};
    payload[key] = val;
    const r = await fetch('/api/audio/config', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify(payload)
    });
    const data = await r.json();
    if (data.ok) {
       // Refresh via status poll
    }
  } catch(e) { console.error('[Audio] setAudioRouting failed', e); }
}

// ── Chat logic ────────────────────────────────────────────────────────────────

// (DOM rendering moved to chat_renderer.js)

async function sendMessage() {
  const text = userInput ? userInput.value.trim() : '';
  if(!text || isStreaming) return;

  let attachCtx = '';
  let attachImgs = [];
  if (typeof window.getAttachmentContext === 'function') {
    const attachData = await window.getAttachmentContext();
    attachCtx = attachData.context || '';
    attachImgs = attachData.images || [];
  }
  const fullMessage = text + attachCtx;

  showStopVoiceBtn(false);
  hideWelcome();
  if (userInput) { userInput.value=''; autoResize(userInput); }
  
  let userHtml = text;
  if (attachImgs.length > 0) {
    let imgHtml = '<div style="display:flex; gap:8px; flex-wrap:wrap; margin-bottom:8px;">';
    attachImgs.forEach(img => {
      imgHtml += `<img src="data:${img.mime_type};base64,${img.data_b64}" style="max-height:100px; border-radius:6px; background:#0d0e14; border:1px solid rgba(255,255,255,0.1); cursor:pointer;" onclick="if(window.openLightbox) window.openLightbox(this.src)" title="${img.name}">`;
    });
    imgHtml += '</div>';
    userHtml = imgHtml + userHtml;
  }
  
  const { bubble: userBubble } = addBubble('user', userHtml);
  userBubble.innerHTML = userHtml;
  if (typeof window.attachActionsToBubble === 'function') window.attachActionsToBubble(userBubble);

  const { bubble: aiBubble } = addBubble('ai', '', 'ai-'+Date.now());
  const cursor = document.createElement('span');
  cursor.className = 'cursor';
  aiBubble.appendChild(cursor);
  if (sendBtn) sendBtn.disabled = true; 
  isStreaming = true;
  let aiText = '';

  try {
    const res = await fetch('/api/chat', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({message: fullMessage, history, images: attachImgs})
    });
    const data = await res.json();
    if(!data.ok) throw new Error(data.error||'Server error');

    const evtSrc = new EventSource(`/api/stream/${data.session_id}`);
    evtSrc.onmessage = (e) => {
      const ev = JSON.parse(e.data);
      if(ev.type==='agent_trace') {
        // Pass the AI .msg wrapper as anchor so the trace is INSERTED BEFORE IT
        if (window.AgentUI) window.AgentUI.handleEvent(ev, aiBubble.closest('.msg') || aiBubble.parentElement);
      } else if(ev.type==='token') {
        aiText += ev.text;
        if(window.ClientCameraManager) aiText = window.ClientCameraManager.interceptStream(aiText, data.session_id, aiBubble);
        aiBubble.innerHTML = renderMarkdown(aiText);
        aiBubble.appendChild(cursor);
        if (chatArea) chatArea.scrollTop = chatArea.scrollHeight;
      } else if(ev.type==='audio_ready') {
        tryLoadAudio(aiBubble);
      } else if(ev.type==='system_audio_playing') {
        showStopVoiceBtn(true);
        if (window._stopTimeout) clearTimeout(window._stopTimeout);
        window._stopTimeout = setTimeout(() => showStopVoiceBtn(false), 60000);
      } else if(ev.type==='done'||ev.type==='error') {
        if (window.AgentUI) window.AgentUI.finalize();
        cursor.remove();
        aiBubble.innerHTML = renderMarkdown(aiText||(ev.type==='error'?'❌ '+ev.text:''));
        evtSrc.close();
        history.push({role:'user',content:text});
        history.push({role:'assistant',content:aiText});
        isStreaming=false; if (sendBtn) sendBtn.disabled=false;
      }
    };
    evtSrc.onerror = () => {
      cursor.remove();
      if(!aiText) aiBubble.textContent='❌ ' + (I18N.err_connected || 'Connection error');
      evtSrc.close(); isStreaming=false; if (sendBtn) sendBtn.disabled=false;
    };
  } catch(err) {
    cursor.remove();
    aiBubble.textContent = '❌ ' + (I18N.err_general || 'Error') + ': ' + err.message;
    isStreaming=false; if (sendBtn) sendBtn.disabled=false;
  }
}

window.sendInternalMessage = async function(text) {
  if(!text || isStreaming) return;
  
  showStopVoiceBtn(false);
  hideWelcome();
  const { bubble: aiBubble } = addBubble('ai', '', 'ai-'+Date.now());
  const cursor = document.createElement('span');
  cursor.className = 'cursor';
  aiBubble.appendChild(cursor);
  if (sendBtn) sendBtn.disabled = true; 
  isStreaming = true;
  let aiText = '';

  try {
    const res = await fetch('/api/chat', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({message: text, history: history, images: []})
    });
    const data = await res.json();
    if(!data.ok) throw new Error(data.error||'Server error');

    const evtSrc = new EventSource(`/api/stream/${data.session_id}`);
    evtSrc.onmessage = (e) => {
      const ev = JSON.parse(e.data);
      if(ev.type==='agent_trace') {
        // Pass the AI .msg wrapper as anchor so the trace is INSERTED BEFORE IT
        if (window.AgentUI) window.AgentUI.handleEvent(ev, aiBubble.closest('.msg') || aiBubble.parentElement);
      } else if(ev.type==='token') {
        aiText += ev.text;
        if(window.ClientCameraManager) aiText = window.ClientCameraManager.interceptStream(aiText, data.session_id, aiBubble);
        aiBubble.innerHTML = renderMarkdown(aiText);
        aiBubble.appendChild(cursor);
        if (chatArea) chatArea.scrollTop = chatArea.scrollHeight;
      } else if(ev.type==='audio_ready') {
        tryLoadAudio(aiBubble);
      } else if(ev.type==='system_audio_playing') {
        showStopVoiceBtn(true);
        if (window._stopTimeout) clearTimeout(window._stopTimeout);
        window._stopTimeout = setTimeout(() => showStopVoiceBtn(false), 60000);
      } else if(ev.type==='done'||ev.type==='error') {
        if (window.AgentUI) window.AgentUI.finalize();
        cursor.remove();
        aiBubble.innerHTML = renderMarkdown(aiText||(ev.type==='error'?'❌ '+ev.text:''));
        evtSrc.close();
        history.push({role:'user',content:text});
        history.push({role:'assistant',content:aiText});
        isStreaming=false; if (sendBtn) sendBtn.disabled=false;
      }
    };
    evtSrc.onerror = () => {
      cursor.remove();
      if(!aiText) aiBubble.textContent='❌ ' + (I18N.err_connected || 'Connection error');
      evtSrc.close(); isStreaming=false; if (sendBtn) sendBtn.disabled=false;
    };
  } catch(err) {
    cursor.remove();
    aiBubble.textContent = '❌ ' + (I18N.err_general || 'Error') + ': ' + err.message;
    isStreaming=false; if (sendBtn) sendBtn.disabled=false;
  }
};

// (Audio initialization UI logic moved to chat_renderer.js)
async function stopVoice() {
  console.log("[Audio] stopVoice triggered");
  if (window.currentAudio) {
    window.currentAudio.pause();
    window.currentAudio.src = '';
    window.currentAudio = null;
  }
  try { await fetch('/api/audio/stop', {method: 'POST'}); } catch(e) {}
  try { await fetch('/api/system/stop', {method: 'POST'}); } catch(e) {}
  
  // Always unblock UI — works regardless of isStreaming timing
  isStreaming = false;
  if (sendBtn) sendBtn.disabled = false;
  if (window._liveBackendAiBubble) {
    window._liveBackendAiBubble.innerHTML = '<em style="color:var(--muted)">⛔ Interrotto</em>';
    window._liveBackendAiBubble = null;
  }
  showStopVoiceBtn(false);
}

document.addEventListener('keydown', function(e) {
  if (e.key === 'Escape') {
    stopVoice();
  }
  if (e.key === 'F4') { e.preventDefault(); toggleMic(); }
  if (e.key === 'F6') { e.preventDefault(); toggleTTS(); }
  if (e.key === 'F7') { 
    e.preventDefault(); 
    window.open('/zentra/config/ui', '_blank'); 
  }
  if (e.key === 'F8') { e.preventDefault(); togglePTT(); }
});

window.clearChat = function() {
  history=[];
  if (chatArea) chatArea.innerHTML='';
  if (welcome) {
      chatArea.appendChild(welcome);
      welcome.style.display='flex';
  }
}

async function refreshStatus() {
  try {
    const d = await (await fetch('/zentra/status')).json();
    const sbB = document.getElementById('sb-backend');
    const sbM = document.getElementById('sb-model');
    const tbM = document.getElementById('tb-model');
    if (sbB) sbB.textContent = d.backend||'—';
    if (sbM) sbM.textContent = d.model||'—';
    if (tbM) tbM.textContent = d.model||(I18N.offline || 'Offline');

    _applyMicState(d.mic === 'ON');
    _applyTTSState(d.tts === 'ON');
    _applyPTTState(d.ptt === 'ON');
    
    const ac = d.audio_config || {};
    _applyRoutingState(ac.stt_source || 'system', ac.tts_destination || 'web');

  } catch(e) {
    const tbM = document.getElementById('tb-model');
    if (tbM) tbM.textContent = I18N.offline || 'Offline';
  }
}

async function loadPlugins() {
  try {
    const cfg  = await (await fetch('/zentra/config')).json();
    const icons = {DASHBOARD:'📊',FILE_MANAGER:'📁',HELP:'❓',MEDIA:'🎵',ROLEPLAY:'🎭',SYSTEM:'⚙',WEB:'🌐',WEBCAM:'📷',WEB_UI:'💻'};
    const prompts = {
      DASHBOARD: I18N.prompt_dashboard,
      FILE_MANAGER: 'read: config/system.yaml',
      HELP: I18N.prompt_help,
      MEDIA: I18N.prompt_media,
      ROLEPLAY: I18N.prompt_roleplay,
      SYSTEM: I18N.prompt_system,
      WEB: I18N.prompt_web,
      WEBCAM: I18N.prompt_webcam
    };
    let html = '';
    for(const [tag,pc] of Object.entries(cfg.plugins||{})) {
      const on = pc.enabled!==false;
      const pText = prompts[tag] ? prompts[tag].replace(/'/g, "\\'") : '';
      const onClick = on && pText ? `onclick="startPrompt('${pText}')"` : '';
      const cursor = on && pText ? 'cursor:pointer;' : (on ? 'cursor:default;' : 'cursor:not-allowed;');
      html+=`<div class="sidebar-btn" ${onClick} style="font-size:12px;${!on?'opacity:.4;':''}${cursor}"><span class="icon">${icons[tag]||'🧩'}</span> ${tag}</div>`;
    }
    const sbP = document.getElementById('sb-plugins');
    if (sbP) sbP.innerHTML = html||`<div style="font-size:12px;color:var(--muted);">${I18N.none || 'None'}</div>`;
  } catch(e){}
}

function initEvents() {
  const evtSrc = new EventSource('/api/events');
  evtSrc.onmessage = (e) => {
    const ev = JSON.parse(e.data);
    
    if (ev.type === 'agent_trace') {
      if (window.AgentUI) window.AgentUI.handleEvent(ev);
    } else if (ev.type === 'ptt_status') {
      const pttInd = document.getElementById('ptt-indicator');
      if (ev.active) {
          if (pttInd) pttInd.classList.add('active');
          playSynthBeep(880, 0.08); // High tone for START
      } else {
          if (pttInd) pttInd.classList.remove('active');
          playSynthBeep(440, 0.12); // Low tone for END
      }
    } else if (ev.type === 'voice_detected' && ev.text) {
      console.log("[Audio] Voice command received:", ev.text);
      hideWelcome();
      
      if (ev.standalone) {
          // In standalone mode, the frontend must orchestrate generation
          // This will render the user bubble, lock UI, and call /api/chat
          sendInternalMessage(ev.text);
      } else {
          // Native Console system is already processing it, just show the bubbles
          addBubble('user', ev.text);
          
          // Create a temporary AI loading bubble
          const { bubble: aiBubble } = addBubble('ai', '', 'ai-live-'+Date.now());
          aiBubble.innerHTML = '<span class="cursor"></span>';
          window._liveBackendAiBubble = aiBubble;
          
          // Lock input + show stop button so user knows something is running
          isStreaming = true;
          if (sendBtn) sendBtn.disabled = true;
          showStopVoiceBtn(true);
          if (chatArea) chatArea.scrollTop = chatArea.scrollHeight;
      }

    } else if (ev.type === 'processing_start') {
      hideWelcome();
      
    } else if (ev.type === 'system_response') {
      if (window.AgentUI) window.AgentUI.finalize();

      console.log("[Audio] Backend response received.", ev);
      let aiText = ev.ai || '';
      // Ensure something is always rendered even if aiText is empty
      const displayText = aiText || '<em style="color:var(--muted)">(nessuna risposta)</em>';
      
      if (window._liveBackendAiBubble) {
        window._liveBackendAiBubble.innerHTML = aiText ? renderMarkdown(aiText) : displayText;
        window._liveBackendAiBubble = null;
      } else {
        // Fallback in case we missed the initialization event
        hideWelcome();
        if (ev.user) addBubble('user', ev.user);
        addBubble('ai', aiText || '(nessuna risposta)');
      }
      
      // Always unlock input when any response arrives
      isStreaming = false;
      if (sendBtn) sendBtn.disabled = false;
      showStopVoiceBtn(false);
      
      // Push to local array just to keep it somewhat in sync
      if (ev.user) history.push({role: 'user', content: ev.user});
      if (aiText)  history.push({role: 'assistant', content: aiText});
      if (chatArea) chatArea.scrollTop = chatArea.scrollHeight;

    } else if (ev.type === 'audio_ready') {
      console.log("[Audio] Global audio ready from backend");
      // Find the last AI bubble to attach the audio player to
      const targetBubble = document.querySelector('.msg.ai:last-child .msg-bubble');
      if (targetBubble) {
        tryLoadAudio(targetBubble);
      }
    }
  };
}

// Exposure to global scope
window.toggleMic = toggleMic;
window.toggleTTS = toggleTTS;
window.togglePTT = togglePTT;
window.stopVoice = stopVoice;
window.sendMessage = sendMessage;
window.handleKey = handleKey;
window.autoResize = autoResize;
window.startPrompt = startPrompt;
window.setAudioRouting = setAudioRouting;

refreshStatus();
loadPlugins();
initEvents();
setInterval(refreshStatus, 4000);
if (userInput) userInput.focus();

setInterval(() => {
  fetch('/zentra/heartbeat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ type: 'chat' })
  }).catch(() => {});
}, 5000);
