/**
 * chat_api.js
 * Handles sending messages to the backend and processing the SSE stream for the chat response.
 */

window.chatHistory = [];
window.isStreaming = false;
window.hecosTabId = Math.random().toString(36).substring(2, 15);

window.formatModelTooltip = function(jsonStr) {
    try {
        const p = JSON.parse(jsonStr);
        if (!p.model) return jsonStr;
        
        let lines = [];
        
        // Line 1: Model & Backend
        lines.push(`🤖 Model: ${p.model} (${p.backend || 'unknown'})`);
        
        // Line 2: Presets
        if (p.global_preset || p.session_preset) {
            let presetLine = '🎭 Preset: ';
            if (p.session_preset && p.session_preset !== p.global_preset) {
                presetLine += `${p.session_preset} (override)`;
            } else if (p.global_preset) {
                presetLine += p.global_preset;
            }
            lines.push(presetLine);
        }
        
        // Line 3: Persona
        if (p.persona) lines.push(`👤 Soul: ${p.persona}`);
        
        // Line 4: Inference Params
        lines.push(`⚙ Temp: ${p.temperature || '?'} | Top P: ${p.top_p || '?'} | Rep Pen: ${p.repeat_penalty || '?'}`);
        lines.push(`📊 Ctx: ${p.num_ctx || '?'} | Predict: ${p.num_predict || '?'} | GPU: ${p.num_gpu || 0}`);
        
        // Line 5: TTS
        if (p.tts_engine) {
            let vStr = p.tts_voice || '';
            if (vStr && (vStr.includes('/') || vStr.includes('\\'))) {
                vStr = vStr.split(/[/\\]/).pop().replace(/\.wav$/i, '');
            }
            lines.push(`🔊 TTS: ${p.tts_engine}${vStr ? ' / ' + vStr : ''}`);
        }
        
        // Line 6: Token Usage
        if (p.prompt_tokens || p.completion_tokens) {
            lines.push(`📈 Tokens: ${p.prompt_tokens || 0} in → ${p.completion_tokens || 0} out`);
        }
        
        return lines.join('\n');
    } catch(e) { return jsonStr; }
};

window.sendMessage = async function() {
  if (typeof window.unlockAudioContext === 'function') {
      window.unlockAudioContext();
  }

  let text = window.userInput ? window.userInput.value.trim() : '';
  const hasAttachments = window.pendingAttachments && window.pendingAttachments.length > 0;
  if ((!text && !hasAttachments) || window.isStreaming) return;

  const isDepositOnly = !text && hasAttachments;

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

  if (window.showStopVoiceBtn) window.showStopVoiceBtn(false);
  if (window.hideWelcome) window.hideWelcome();
  if (text && typeof window.saveInputHistory === 'function') window.saveInputHistory(text);
  if (window.userInput) { window.userInput.value = ''; window.autoResize(window.userInput); }
  if (typeof window.updateSendBtnState === 'function') window.updateSendBtnState();
  
  // Render uploaded images as inline thumbnails
  let imgHtml = '';
  if (attachImgs.length > 0) {
    imgHtml = '<div style="display:flex; gap:8px; flex-wrap:wrap; margin-bottom:8px;">';
    attachImgs.forEach(img => {
      imgHtml += `<img src="data:${img.mime_type};base64,${img.data_b64}" style="max-height:100px; border-radius:6px; background:#0d0e14; border:1px solid rgba(255,255,255,0.1); cursor:pointer;" onclick="if(window.openLightbox) window.openLightbox(this.src)" title="${img.name}">`;
    });
    imgHtml += '</div>';
  }
  
  // Construct the visible user message containing text and attachment markdown links
  let fileLinks = '';
  if (savedFiles && savedFiles.length > 0) {
    fileLinks = savedFiles.map(f => `[${f.name}](file:///${f.path.replace(/\\/g, '/')})`).join('\n\n');
  }
  const visibleMessage = text 
    ? (text + (fileLinks ? '\n\n' + fileLinks : '')) 
    : (fileLinks || (attachImgs.length ? '' : '📎 Attachment'));
  
  const fullMessage = (text + attachCtx).trim() || visibleMessage || '[Attachment]';

  // Store the full message (with attachment markdown links and context) so history restore and LLM work correctly
  window.chatHistory.push({role:'user', content:fullMessage});
  
  // Render user bubble through the exact same renderMarkdown pipeline that history restore uses
  const renderedContent = (imgHtml || '') + (typeof window.renderMarkdown === 'function' ? window.renderMarkdown(visibleMessage) : visibleMessage);
  
  const { bubble: userBubble, msg: userMsg } = window.addBubble('user', '');
  userBubble.innerHTML = renderedContent;
  if (userBubble.querySelector('.chat-pdf-preview')) {
    userBubble.classList.add('has-pdf');
    if (userMsg) userMsg.classList.add('has-pdf');
  }
  if (typeof window.attachActionsToBubble === 'function') window.attachActionsToBubble(userBubble);
  if (typeof window.docReaderScanCards === 'function') {
    setTimeout(window.docReaderScanCards, 50);
  }

  // ── Silent Deposit Branch: Save to DB & timeline without LLM inference ──
  if (isDepositOnly) {
    try {
      const payload = {
        message: fullMessage,
        session_id: window.chatHistoryState?.activeSessionId,
        tab_id: window.hecosTabId
      };
      const res = await fetch('/api/chat/deposit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (data && data.session_id && window.chatHistoryState) {
        window.chatHistoryState.activeSessionId = data.session_id;
      }
      if (window.showToast) {
        window.showToast('📁 Document deposited into chat');
      }
    } catch(e) {
      console.error('[Chat] Deposit error:', e);
      if (window.showToast) window.showToast('❌ Deposit error: ' + e.message);
    }
    return;
  }

  window.chatHistory.push({role:'assistant', content:''});
  const { bubble: aiBubble } = window.addBubble('ai', '', 'ai-'+Date.now(), { persona_name: window.HecosPersonaName || null });
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
        const tokenText = (ev.text !== undefined && ev.text !== null) ? ev.text : (ev.token || '');
        aiText += tokenText;
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
          const tooltipText = window.formatModelTooltip(ev.model_info);
          aiBubble.setAttribute('title', tooltipText);
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
                    if (d.avatar_type === 'video') {
                      avatarEl.innerHTML = `
                        <div class="avatar-zoom-wrapper" style="width:100%; height:100%; display:flex; align-items:center; justify-content:center;" onclick="if(window.openSoulGallery) window.openSoulGallery('${d.avatar_path}'); else window.openAvatarFull('${d.avatar_path}', 'video')">
                          <video src="${d.avatar_path}" autoplay loop muted playsinline style="width:100%; height:100%; object-fit:cover; border-radius:50%;"></video>
                          <div class="avatar-zoom-icon"><i class="fas fa-search-plus"></i></div>
                        </div>`;
                    } else {
                      const imgStyle = d.avatar_path !== "/assets/Hecos_Logo_SQR_NBG_LogoOnly.png"
                        ? "object-fit:cover; border-radius:50%;"
                        : "filter:drop-shadow(0 0 5px rgba(108,140,255,0.4));";
                      avatarEl.innerHTML = `
                        <div class="avatar-zoom-wrapper" style="width:100%; height:100%; display:flex; align-items:center; justify-content:center;" onclick="if(window.openSoulGallery) window.openSoulGallery('${d.avatar_path}'); else window.openAvatarFull('${d.avatar_path}', 'image')">
                          <img src="${d.avatar_path}" onerror="this.src='/assets/Hecos_Logo_SQR_NBG_LogoOnly.png';" style="${imgStyle}">
                          <div class="avatar-zoom-icon"><i class="fas fa-search-plus"></i></div>
                        </div>`;
                    }
                  }
                }).catch(() => {});
            }
          }
        }
        
        window.isStreaming = false; if (window.updateStopAllBtn) window.updateStopAllBtn();
        if (window.sendBtn) window.sendBtn.disabled = false;
        
      } else if(ev.type === 'audio_chunk') {
        // Ignored: single consolidated audio player used per message
      } else if(ev.type === 'audio_ready') {
        if (ev.audio_id) aiBubble.dataset.audioId = ev.audio_id;
        if (window.tryLoadAudio) window.tryLoadAudio(aiBubble, true);
      } else if(ev.type === 'system_audio_playing') {
        if (window.showStopVoiceBtn) window.showStopVoiceBtn(true);
        if (window._stopTimeout) clearTimeout(window._stopTimeout);
        window._stopTimeout = setTimeout(() => { if (window.showStopVoiceBtn) window.showStopVoiceBtn(false); }, 60000);
      } else if(ev.type === 'done' || ev.type === 'error') {
        if (window.AgentUI) window.AgentUI.finalize();
        cursor.remove();
        const existingBadge = aiBubble.querySelector('.audio-badge');
        aiBubble.innerHTML = window.renderMarkdown(aiText||(ev.type==='error'?'❌ '+ev.text:''));
        if (existingBadge) {
          aiBubble.appendChild(existingBadge);
        }
        evtSrc.close();
        
        if (window.loadChatSessions) window.loadChatSessions();
      }
    };
    evtSrc.onerror = () => {
      if (window.AgentUI) window.AgentUI.finalize();
      cursor.remove();
      // If streaming has already concluded and content exists, do not treat stream close as an error
      if (!window.isStreaming && aiText) {
        evtSrc.close();
        return;
      }
      evtSrc.close();
      window.isStreaming = false;
      if (window.updateStopAllBtn) window.updateStopAllBtn();
      if (window.sendBtn) window.sendBtn.disabled = false;

      const existingBadge = aiBubble.querySelector('.audio-badge');
      if (!aiText) {
        aiBubble.textContent = '❌ ' + (window.I18N?.err_connected || 'Connection error') + ' - Reconnecting...';
      } else {
        if (!aiBubble._chunksFinished && (!aiBubble._audioChunks || aiBubble._audioChunks.length === 0) && !aiBubble._isCurrentlyPlaying) {
          aiBubble.innerHTML = window.renderMarkdown(aiText) + '<br><br><span style="color:#f39c12;font-size:0.9em;opacity:0.8;">⚠️ Connection lost. Waiting for Hecos to restart...</span>';
          if (existingBadge) aiBubble.appendChild(existingBadge);
        }
      }

      if (!window.isReconnectingAuto) {
        window.isReconnectingAuto = true;
        let sawDown = false;
        const poller = setInterval(async () => {
            try {
                const r = await fetch('/hecos/status');
                if (!r.ok) {
                    sawDown = true;
                } else if (sawDown) {
                    clearInterval(poller);
                    window.location.reload();
                } else {
                    // Server is healthy and was never down; clear poller and resume normal state
                    clearInterval(poller);
                    window.isReconnectingAuto = false;
                }
            } catch(e) {
                sawDown = true;
            }
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
  
  // Intercept voice dictation triggers for slash commands
  const triggers = ["comando ", "command ", "slash ", "barra "];
  for (const t of triggers) {
      if (text.toLowerCase().startsWith(t)) {
          text = "/" + text.substring(t.length);
          break;
      }
  }
  text = text.replace(/^\/\s+/, '/');

  if (window.showStopVoiceBtn) window.showStopVoiceBtn(false);
  if (window.hideWelcome) window.hideWelcome();
  
  const { bubble: aiBubble } = window.addBubble('ai', '', 'ai-'+Date.now(), { persona_name: window.HecosPersonaName || null });
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
        const tokenText = (ev.text !== undefined && ev.text !== null) ? ev.text : (ev.token || '');
        aiText += tokenText;
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
          const tooltipText = window.formatModelTooltip(ev.model_info);
          aiBubble.setAttribute('title', tooltipText);
          aiBubble.style.cursor = 'help';
        }
        window.isStreaming = false; if (window.updateStopAllBtn) window.updateStopAllBtn();
        if (window.sendBtn) window.sendBtn.disabled = false;

      } else if(ev.type === 'audio_chunk') {
        // Ignored: single consolidated audio player used per message
      } else if(ev.type === 'audio_ready') {
        if (ev.audio_id) aiBubble.dataset.audioId = ev.audio_id;
        if (window.tryLoadAudio) window.tryLoadAudio(aiBubble, true);
      } else if(ev.type === 'system_audio_playing') {
        if (window.showStopVoiceBtn) window.showStopVoiceBtn(true);
        if (window._stopTimeout) clearTimeout(window._stopTimeout);
        window._stopTimeout = setTimeout(() => { if (window.showStopVoiceBtn) window.showStopVoiceBtn(false); }, 60000);
      } else if(ev.type === 'done' || ev.type === 'error') {
        if (window.AgentUI) window.AgentUI.finalize();
        cursor.remove();
        const existingBadge = aiBubble.querySelector('.audio-badge');
        aiBubble.innerHTML = window.renderMarkdown(aiText||(ev.type==='error'?'❌ '+ev.text:''));
        if (existingBadge) {
          aiBubble.appendChild(existingBadge);
        }
        evtSrc.close();

        if (window.loadChatSessions) window.loadChatSessions();
      }
    };
    evtSrc.onerror = () => {
      cursor.remove();
      if (!window.isStreaming && aiText) {
        evtSrc.close();
        return;
      }
      evtSrc.close(); 
      window.isStreaming = false; 
      if (window.updateStopAllBtn) window.updateStopAllBtn(); 
      if (window.sendBtn) window.sendBtn.disabled = false;

      const existingBadge = aiBubble.querySelector('.audio-badge');
      if (!aiText) {
        aiBubble.textContent = '❌ ' + (window.I18N?.err_connected || 'Connection error') + ' - Reconnecting...';
      } else {
        if (!aiBubble._chunksFinished && (!aiBubble._audioChunks || aiBubble._audioChunks.length === 0) && !aiBubble._isCurrentlyPlaying) {
          aiBubble.innerHTML = window.renderMarkdown(aiText) + '<br><br><span style="color:#f39c12;font-size:0.9em;opacity:0.8;">⚠️ Connection lost. Waiting for Hecos to restart...</span>';
          if (existingBadge) aiBubble.appendChild(existingBadge);
        }
      }

      if (!window.isReconnectingAuto) {
        window.isReconnectingAuto = true;
        let sawDown = false;
        const poller = setInterval(async () => {
            try {
                const r = await fetch('/hecos/status');
                if (!r.ok) {
                    sawDown = true;
                } else if (sawDown) {
                    clearInterval(poller);
                    window.location.reload();
                } else {
                    clearInterval(poller);
                    window.isReconnectingAuto = false;
                }
            } catch(e) {
                sawDown = true;
            }
        }, 2000);
      }
    };
  } catch(err) {
    cursor.remove();
    aiBubble.textContent = '❌ ' + (window.I18N?.err_general || 'Error') + ': ' + err.message;
    window.isStreaming = false; if (window.updateStopAllBtn) window.updateStopAllBtn(); if (window.sendBtn) window.sendBtn.disabled = false;
  }
};
