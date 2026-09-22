/**
 * chat_api.js
 * Handles sending messages to the backend and processing the SSE stream for the chat response.
 */

window.chatHistory = [];
window.isStreaming = false;
window.hecosTabId = Math.random().toString(36).substring(2, 15);

window.sendMessage = async function() {
  if (typeof window.unlockAudioContext === 'function') {
      window.unlockAudioContext();
  }

  let text = window.userInput ? window.userInput.value.trim() : '';
  if(!text || window.isStreaming) return;

  // Intercept voice dictation triggers for slash commands
  const triggers = ["comando ", "command ", "slash "];
  for (const t of triggers) {
      if (text.toLowerCase().startsWith(t)) {
          text = "/" + text.substring(t.length);
          break;
      }
  }

  let attachCtx = '';
  let attachImgs = [];
  let savedFiles = [];
  if (typeof window.getAttachmentContext === 'function') {
    const attachData = await window.getAttachmentContext();
    attachCtx = attachData.context || '';
    attachImgs = attachData.images || [];
    savedFiles = attachData.saved_files || [];
  }
  const fullMessage = text + attachCtx;

  if (window.showStopVoiceBtn) window.showStopVoiceBtn(false);
  if (window.hideWelcome) window.hideWelcome();
  if (typeof window.saveInputHistory === 'function') window.saveInputHistory(text);
  if (window.userInput) { window.userInput.value = ''; window.autoResize(window.userInput); }
  
  let userHtml = text;
  // Render uploaded images as inline thumbnails
  if (attachImgs.length > 0) {
    let imgHtml = '<div style="display:flex; gap:8px; flex-wrap:wrap; margin-bottom:8px;">';
    attachImgs.forEach(img => {
      imgHtml += `<img src="data:${img.mime_type};base64,${img.data_b64}" style="max-height:100px; border-radius:6px; background:#0d0e14; border:1px solid rgba(255,255,255,0.1); cursor:pointer;" onclick="if(window.openLightbox) window.openLightbox(this.src)" title="${img.name}">`;
    });
    imgHtml += '</div>';
    userHtml = imgHtml + userHtml;
  }
  // Render uploaded files as interactive file cards immediately (no refresh needed)
  if (savedFiles.length > 0) {
    const iconMap = { pdf: 'fa-file-pdf', html: 'fa-file-code', htm: 'fa-file-code',
                      doc: 'fa-file-word', docx: 'fa-file-word', txt: 'fa-file-alt',
                      md: 'fa-file-alt', csv: 'fa-file-csv' };
    const colorMap = { pdf: '#e74c3c', html: '#3498db', htm: '#3498db',
                       doc: '#2980b9', docx: '#2980b9' };
    let cardsHtml = '';
    savedFiles.forEach(f => {
      const ext = (f.name.match(/\.([a-z0-9]+)$/i) || ['',''])[1].toLowerCase();
      const icon = iconMap[ext] || 'fa-file-alt';
      const color = colorMap[ext] || 'var(--accent)';
      const apiUrl = f.url || `/api/local_file?path=${encodeURIComponent(f.path)}`;
      let cardHtml = `<div class="chat-file-card" style="display:flex;align-items:center;gap:10px;padding:10px 14px;background:var(--bg2);border:1px solid var(--border-color);border-radius:10px;margin:6px 0;">
        <div class="chat-file-icon" style="font-size:1.6em;color:${color};"><i class="fas ${icon}"></i></div>
        <div class="chat-file-details" style="flex:1;min-width:0;">
          <div class="chat-file-name" style="font-weight:600;font-size:0.9em;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="${f.path}">${f.name}</div>
          <div class="chat-file-action" style="display:flex;gap:6px;margin-top:5px;">
            <a href="${apiUrl}" target="_blank" download style="padding:4px 10px; border-radius:5px; background:rgba(108,140,255,0.12); border:1px solid rgba(108,140,255,0.25); color:var(--muted); font-size:0.8em; text-decoration:none;"><i class="fas fa-download"></i> Download</a>
          </div>
        </div>
      </div>`;
      
      if (ext === 'html' || ext === 'htm') {
        const serveUrl = `/api/serve_html?path=${encodeURIComponent(f.path)}`;
        const iframeId = 'preview_' + Math.random().toString(36).substring(2, 10);
        const safeDocPath = f.path.replace(/\\/g, '/');
        cardHtml += `
        <div class="chat-html-preview">
          <div class="chat-html-preview-bar">
            <span>Preview: ${f.name}</span>
            <div style="display:flex; gap:10px; align-items:center;">
              <button onclick="if(window.openDocPreview) window.openDocPreview('${safeDocPath.replace(/'/g, "\\'")}');" style="background:rgba(108,140,255,0.2);border:1px solid var(--accent);color:var(--accent);border-radius:4px;padding:2px 8px;cursor:pointer;font-size:0.9em;"><i class="fas fa-magic"></i> Modifica Documento</button>
              <button onclick="document.getElementById('${iframeId}').src=document.getElementById('${iframeId}').src" style="background:none;border:none;color:var(--accent);cursor:pointer;"><i class="fas fa-sync-alt"></i></button>
            </div>
          </div>
          <div class="chat-html-preview-body">
            <iframe id="${iframeId}" src="${serveUrl}" style="width:100%;height:350px;border:none;display:block;" sandbox="allow-same-origin allow-scripts allow-popups"></iframe>
          </div>
        </div>`;
      } else if (ext === 'pdf') {
        const iframeId = 'preview_' + Math.random().toString(36).substring(2, 10);
        cardHtml += `
        <div class="chat-pdf-preview">
          <div class="chat-pdf-preview-bar">
            <span>Preview: ${f.name}</span>
            <button onclick="document.getElementById('${iframeId}').src=document.getElementById('${iframeId}').src" style="background:none;border:none;color:var(--accent);cursor:pointer;"><i class="fas fa-sync-alt"></i></button>
          </div>
          <div class="chat-pdf-preview-body">
            <iframe id="${iframeId}" src="${apiUrl}" style="width:100%;height:450px;border:none;display:block;"></iframe>
          </div>
        </div>`;
      }
      
      cardsHtml += cardHtml;
    });
    userHtml = cardsHtml + userHtml;
  }
  
  // Store the full message (with attachment markdown links) so history restore works correctly
  window.chatHistory.push({role:'user', content:fullMessage});
  const { bubble: userBubble } = window.addBubble('user', userHtml);
  userBubble.innerHTML = userHtml;
  if (typeof window.attachActionsToBubble === 'function') window.attachActionsToBubble(userBubble);

  window.chatHistory.push({role:'assistant', content:''});
  const { bubble: aiBubble } = window.addBubble('ai', '', 'ai-'+Date.now());
  const cursor = document.createElement('span');
  cursor.className = 'cursor';
  aiBubble.appendChild(cursor);
  
  if (window.sendBtn) window.sendBtn.disabled = true; 
  window.isStreaming = true; if (window.updateStopAllBtn) window.updateStopAllBtn();
  let aiText = '';

  try {
    const payload = {
      message: fullMessage, 
      history: window.chatHistory, 
      images: attachImgs,
      session_id: window.chatHistoryState?.activeSessionId,
      tab_id: window.hecosTabId
    };
    const res = await fetch('/api/chat', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if(!data.ok) throw new Error(data.error||'Server error');

    if (data.session_id && window.chatHistoryState && !window.chatHistoryState.activeSessionId) {
        window.chatHistoryState.activeSessionId = data.session_id;
        localStorage.setItem('hecos_active_session_id', data.session_id);
    }

    if (data.intercepted) {
      cursor.remove();
      const msg = window.I18N?.flows_input_sent || "Response sent to flow.";
      aiBubble.innerHTML = window.renderMarkdown(`✅ *${msg}*`);
      window.isStreaming = false; if (window.updateStopAllBtn) window.updateStopAllBtn();
      if (window.sendBtn) window.sendBtn.disabled = false;
      return;
    }

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
      } else if(ev.type === 'think') {
        if (window.renderThinkBlock) window.renderThinkBlock(ev.text, aiBubble);
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
        
        if (ev.model_info) {
          aiBubble.setAttribute('title', ev.model_info);
          aiBubble.style.cursor = 'help';
        }
        
        // Dynamically update the bubble's avatar and name if the persona changed during the run
        if (ev.persona_name) {
          const personaTitle = ev.persona_name.replace(/_/g, ' ').replace(/\.yaml$/i, '');
          const msgContainer = aiBubble.closest('.msg');
          if (msgContainer) {
            const nameEl = msgContainer.querySelector('.msg-name');
            if (nameEl) {
              const existingBadge = nameEl.querySelector('.think-badge');
              nameEl.textContent = personaTitle;
              if (existingBadge) nameEl.appendChild(existingBadge);
            }
            const avatarEl = msgContainer.querySelector('.msg-avatar');
            if (avatarEl) {
              fetch(`/api/persona/avatar?persona=${encodeURIComponent(ev.persona_name)}`)
                .then(r => r.json())
                .then(d => {
                  if (d.ok && d.avatar_path) {
                    const imgStyle = d.avatar_path !== "/assets/Hecos_Logo_SQR_NBG_LogoOnly.png"
                      ? "object-fit:cover; border-radius:50%;"
                      : "filter:drop-shadow(0 0 5px rgba(108,140,255,0.4));";
                    avatarEl.innerHTML = `
                      <div class="avatar-zoom-wrapper" style="width:100%; height:100%; display:flex; align-items:center; justify-content:center;" onclick="window.openAvatarFull('${d.avatar_path}')">
                        <img src="${d.avatar_path}" onerror="this.src='/assets/Hecos_Logo_SQR_NBG_LogoOnly.png';" style="${imgStyle}">
                        <div class="avatar-zoom-icon"><i class="fas fa-search-plus"></i></div>
                      </div>`;
                  }
                }).catch(() => {});
            }
          }
        }
        
        window.isStreaming = false; if (window.updateStopAllBtn) window.updateStopAllBtn();
        if (window.sendBtn) window.sendBtn.disabled = false;
        
      } else if(ev.type === 'audio_ready') {
        if (ev.audio_id) aiBubble.dataset.audioId = ev.audio_id;
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
      if (window.AgentUI) window.AgentUI.finalize();
      cursor.remove();
      if(!aiText) aiBubble.textContent='❌ ' + (window.I18N?.err_connected || 'Connection error') + ' - Reconnecting...';
      else aiBubble.innerHTML = window.renderMarkdown(aiText) + '<br><br><span style="color:#f39c12;font-size:0.9em;opacity:0.8;">⚠️ Connection lost. Waiting for Hecos to restart...</span>';
      evtSrc.close(); window.isStreaming = false; if (window.updateStopAllBtn) window.updateStopAllBtn(); if (window.sendBtn) window.sendBtn.disabled = false;

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
    window.isStreaming = false; if (window.updateStopAllBtn) window.updateStopAllBtn(); if (window.sendBtn) window.sendBtn.disabled = false;
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
  window.isStreaming = true; if (window.updateStopAllBtn) window.updateStopAllBtn();
  let aiText = '';

  try {
    const payload = {
      message: text, 
      history: window.chatHistory, 
      images: [],
      session_id: window.chatHistoryState?.activeSessionId,
      tab_id: window.hecosTabId
    };
    const res = await fetch('/api/chat', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if(!data.ok) throw new Error(data.error||'Server error');

    if (data.session_id && window.chatHistoryState && !window.chatHistoryState.activeSessionId) {
        window.chatHistoryState.activeSessionId = data.session_id;
        localStorage.setItem('hecos_active_session_id', data.session_id);
    }

    if (data.intercepted) {
      cursor.remove();
      const msg = window.I18N?.flows_input_sent || "Response sent to flow.";
      aiBubble.innerHTML = window.renderMarkdown(`✅ *${msg}*`);
      window.isStreaming = false; if (window.updateStopAllBtn) window.updateStopAllBtn();
      if (window.sendBtn) window.sendBtn.disabled = false;
      return;
    }

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
      } else if(ev.type === 'think') {
        if (window.renderThinkBlock) window.renderThinkBlock(ev.text, aiBubble);
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
        
        if (ev.model_info) {
          aiBubble.setAttribute('title', ev.model_info);
          aiBubble.style.cursor = 'help';
        }
        window.isStreaming = false; if (window.updateStopAllBtn) window.updateStopAllBtn();
        if (window.sendBtn) window.sendBtn.disabled = false;

      } else if(ev.type === 'audio_ready') {
        if (ev.audio_id) aiBubble.dataset.audioId = ev.audio_id;
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
      evtSrc.close(); window.isStreaming = false; if (window.updateStopAllBtn) window.updateStopAllBtn(); if (window.sendBtn) window.sendBtn.disabled = false;

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
    window.isStreaming = false; if (window.updateStopAllBtn) window.updateStopAllBtn(); if (window.sendBtn) window.sendBtn.disabled = false;
  }
};
