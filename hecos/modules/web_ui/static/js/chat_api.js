/**
 * chat_api.js
 * Handles sending messages to the backend and processing the SSE stream for the chat response.
 */

window.chatHistory = [];
window.isStreaming = false;

window.sendMessage = async function() {
  if (typeof window.unlockAudioContext === 'function') {
      window.unlockAudioContext();
  }

  const text = window.userInput ? window.userInput.value.trim() : '';
  if(!text || window.isStreaming) return;

  let attachCtx = '';
  let attachImgs = [];
  if (typeof window.getAttachmentContext === 'function') {
    const attachData = await window.getAttachmentContext();
    attachCtx = attachData.context || '';
    attachImgs = attachData.images || [];
  }
  const fullMessage = text + attachCtx;

  if (window.showStopVoiceBtn) window.showStopVoiceBtn(false);
  if (window.hideWelcome) window.hideWelcome();
  if (window.userInput) { window.userInput.value = ''; window.autoResize(window.userInput); }
  
  let userHtml = text;
  if (attachImgs.length > 0) {
    let imgHtml = '<div style="display:flex; gap:8px; flex-wrap:wrap; margin-bottom:8px;">';
    attachImgs.forEach(img => {
      imgHtml += `<img src="data:${img.mime_type};base64,${img.data_b64}" style="max-height:100px; border-radius:6px; background:#0d0e14; border:1px solid rgba(255,255,255,0.1); cursor:pointer;" onclick="if(window.openLightbox) window.openLightbox(this.src)" title="${img.name}">`;
    });
    imgHtml += '</div>';
    userHtml = imgHtml + userHtml;
  }
  
  window.chatHistory.push({role:'user', content:text});
  const { bubble: userBubble } = window.addBubble('user', userHtml);
  userBubble.innerHTML = userHtml;
  if (typeof window.attachActionsToBubble === 'function') window.attachActionsToBubble(userBubble);

  window.chatHistory.push({role:'assistant', content:''});
  const { bubble: aiBubble } = window.addBubble('ai', '', 'ai-'+Date.now());
  const cursor = document.createElement('span');
  cursor.className = 'cursor';
  aiBubble.appendChild(cursor);
  
  if (window.sendBtn) window.sendBtn.disabled = true; 
  window.isStreaming = true;
  let aiText = '';

  try {
    const payload = {
      message: fullMessage, 
      history: window.chatHistory, 
      images: attachImgs,
      session_id: window.chatHistoryState?.activeSessionId
    };
    const res = await fetch('/api/chat', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if(!data.ok) throw new Error(data.error||'Server error');

    // Lock privacy mode on first sent message
    if (window.chatHistoryState) {
      window.chatHistoryState.chatModeHasMessages = true;
      if (window.updateModeUI) window.updateModeUI();
    }

    const evtSrc = new EventSource(`/api/stream/${data.session_id}`);
    evtSrc.onmessage = (e) => {
      const ev = JSON.parse(e.data);
      if(ev.type === 'agent_trace') {
        if (window.AgentUI) window.AgentUI.handleEvent(ev, aiBubble.closest('.msg') || aiBubble.parentElement);
      } else if(ev.type === 'token') {
        aiText += ev.text;
        aiBubble.innerHTML = window.renderMarkdown(aiText);
        aiBubble.appendChild(cursor);
        if (window.chatArea) window.chatArea.scrollTop = window.chatArea.scrollHeight;
      } else if(ev.type === 'camera_request') {
        if (window.ClientCameraManager) window.ClientCameraManager.showCameraButton(aiBubble);
      } else if(ev.type === 'trace_done') {
        if (window.AgentUI) window.AgentUI.finalize();
        // Prompt unlock as soon as TEXT is fully rendered (does not wait for Piper audio generation)
        if (window.chatHistory.length > 0) {
          window.chatHistory[window.chatHistory.length - 1].content = aiText;
        }
        window.isStreaming = false; 
        if (window.sendBtn) window.sendBtn.disabled = false;
        
      } else if(ev.type === 'audio_ready') {
        if (window.tryLoadAudio) window.tryLoadAudio(aiBubble);
      } else if(ev.type === 'system_audio_playing') {
        if (window.showStopVoiceBtn) window.showStopVoiceBtn(true);
        if (window._stopTimeout) clearTimeout(window._stopTimeout);
        window._stopTimeout = setTimeout(() => { if (window.showStopVoiceBtn) window.showStopVoiceBtn(false); }, 60000);
      } else if(ev.type === 'done' || ev.type === 'error') {
        if (window.AgentUI) window.AgentUI.finalize();
        cursor.remove();
        aiBubble.innerHTML = window.renderMarkdown(aiText||(ev.type==='error'?'❌ '+ev.text:''));
        evtSrc.close();
        
        if (window.loadChatSessions) window.loadChatSessions();
      }
    };
    evtSrc.onerror = () => {
      cursor.remove();
      if(!aiText) aiBubble.textContent='❌ ' + (window.I18N?.err_connected || 'Connection error') + ' - Reconnecting...';
      else aiBubble.innerHTML = window.renderMarkdown(aiText) + '<br><br><span style="color:#f39c12;font-size:0.9em;opacity:0.8;">⚠️ Connection lost. Waiting for Hecos to restart...</span>';
      evtSrc.close(); window.isStreaming = false; if (window.sendBtn) window.sendBtn.disabled = false;

      if (!window.isReconnectingAuto) {
        window.isReconnectingAuto = true;
        const poller = setInterval(async () => {
            try {
                const r = await fetch('/hecos/status');
                if(r.ok) { clearInterval(poller); window.location.reload(); }
            } catch(e) {}
        }, 2000);
      }
    };
  } catch(err) {
    cursor.remove();
    aiBubble.textContent = '❌ ' + (window.I18N?.err_general || 'Error') + ': ' + err.message;
    window.isStreaming = false; if (window.sendBtn) window.sendBtn.disabled = false;
  }
};

window.sendInternalMessage = async function(text) {
  if(!text || window.isStreaming) return;
  
  if (window.showStopVoiceBtn) window.showStopVoiceBtn(false);
  if (window.hideWelcome) window.hideWelcome();
  
  const { bubble: aiBubble } = window.addBubble('ai', '', 'ai-'+Date.now());
  const cursor = document.createElement('span');
  cursor.className = 'cursor';
  aiBubble.appendChild(cursor);
  
  if (window.sendBtn) window.sendBtn.disabled = true; 
  window.isStreaming = true;
  let aiText = '';

  try {
    const payload = {
      message: text, 
      history: window.chatHistory, 
      images: [],
      session_id: window.chatHistoryState?.activeSessionId
    };
    const res = await fetch('/api/chat', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if(!data.ok) throw new Error(data.error||'Server error');

    // Lock privacy mode on first sent message
    if (window.chatHistoryState) {
      window.chatHistoryState.chatModeHasMessages = true;
      if (window.updateModeUI) window.updateModeUI();
    }

    const evtSrc = new EventSource(`/api/stream/${data.session_id}`);
    evtSrc.onmessage = (e) => {
      const ev = JSON.parse(e.data);
      if(ev.type === 'agent_trace') {
        if (window.AgentUI) window.AgentUI.handleEvent(ev, aiBubble.closest('.msg') || aiBubble.parentElement);
      } else if(ev.type === 'token') {
        aiText += ev.text;
        aiBubble.innerHTML = window.renderMarkdown(aiText);
        aiBubble.appendChild(cursor);
        if (window.chatArea) window.chatArea.scrollTop = window.chatArea.scrollHeight;
      } else if(ev.type === 'camera_request') {
        if (window.ClientCameraManager) window.ClientCameraManager.showCameraButton(aiBubble);
      } else if(ev.type === 'trace_done') {
        if (window.AgentUI) window.AgentUI.finalize();
        // Synchronize and unlock as soon as TEXT finishes
        if (window.chatHistory.length > 0) {
          window.chatHistory[window.chatHistory.length - 1].content = aiText;
        }
        window.isStreaming = false; 
        if (window.sendBtn) window.sendBtn.disabled = false;

      } else if(ev.type === 'audio_ready') {
        if (window.tryLoadAudio) window.tryLoadAudio(aiBubble);
      } else if(ev.type === 'system_audio_playing') {
        if (window.showStopVoiceBtn) window.showStopVoiceBtn(true);
        if (window._stopTimeout) clearTimeout(window._stopTimeout);
        window._stopTimeout = setTimeout(() => { if (window.showStopVoiceBtn) window.showStopVoiceBtn(false); }, 60000);
      } else if(ev.type === 'done' || ev.type === 'error') {
        if (window.AgentUI) window.AgentUI.finalize();
        cursor.remove();
        aiBubble.innerHTML = window.renderMarkdown(aiText||(ev.type==='error'?'❌ '+ev.text:''));
        evtSrc.close();

        if (window.loadChatSessions) window.loadChatSessions();
      }
    };
    evtSrc.onerror = () => {
      cursor.remove();
      if(!aiText) aiBubble.textContent='❌ ' + (window.I18N?.err_connected || 'Connection error') + ' - Reconnecting...';
      else aiBubble.innerHTML = window.renderMarkdown(aiText) + '<br><br><span style="color:#f39c12;font-size:0.9em;opacity:0.8;">⚠️ Connection lost. Waiting for Hecos to restart...</span>';
      evtSrc.close(); window.isStreaming = false; if (window.sendBtn) window.sendBtn.disabled = false;

      if (!window.isReconnectingAuto) {
        window.isReconnectingAuto = true;
        const poller = setInterval(async () => {
            try {
                const r = await fetch('/hecos/status');
                if(r.ok) { clearInterval(poller); window.location.reload(); }
            } catch(e) {}
        }, 2000);
      }
    };
  } catch(err) {
    cursor.remove();
    aiBubble.textContent = '❌ ' + (window.I18N?.err_general || 'Error') + ': ' + err.message;
    window.isStreaming = false; if (window.sendBtn) window.sendBtn.disabled = false;
  }
};
