/**
 * chat_api.js
 * Handles sending messages to the backend and processing the SSE stream for the chat response.
 */

window.chatHistory = [];
window.isStreaming = false;
window.hecosTabId = Math.random().toString(36).substring(2, 15);

function _syncPdfPreviewClasses(bubble) {
    if (!bubble) return;
    if (bubble.querySelector('.chat-pdf-preview, .chat-html-preview')) {
        bubble.classList.add('has-pdf');
        const msg = bubble.closest('.msg');
        if (msg) msg.classList.add('has-pdf');
    }
}

function _extractHSearchTokens(rawText) {
    const found = [];
    const seen = new Set();
    const re = /\[\[H(SEARCH|MEDIA):([a-zA-Z0-9_-]+)\]\]/g;
    let m;
    while ((m = re.exec(rawText || '')) !== null) {
        const sid = m[2];
        if (sid && !seen.has(sid)) {
            seen.add(sid);
            found.push({ sid, isMedia: m[1] === 'MEDIA' });
        }
    }
    return found;
}

function _renderBubbleWithHSearch(aiBubble, aiText, cursor, isFinal, fallbackErrorText) {
    const sourceText = aiText || (fallbackErrorText ? ('❌ ' + fallbackErrorText) : '');
    const tokens = _extractHSearchTokens(sourceText);
    const existingCards = aiBubble.querySelectorAll('.hsearch-chat-card');

    if (tokens.length === 0 && existingCards.length === 0) {
        if (!isFinal || fallbackErrorText || aiBubble.dataset.renderedText !== sourceText) {
            aiBubble.innerHTML = window.renderMarkdown(sourceText);
            aiBubble.dataset.renderedText = sourceText;
        }
        _syncPdfPreviewClasses(aiBubble);
        if (!isFinal && cursor) aiBubble.appendChild(cursor);
        return;
    }

    const textPart = sourceText.replace(/\[\[H(?:SEARCH|MEDIA):[a-zA-Z0-9_-]+\]\]/g, '');
    let textEl = aiBubble.querySelector('.hsearch-pre-text');
    if (!textEl && existingCards.length === 0) {
        aiBubble.innerHTML = '';
    }
    if (!textEl) {
        textEl = document.createElement('div');
        textEl.className = 'hsearch-pre-text';
        if (aiBubble.firstChild) {
            aiBubble.insertBefore(textEl, aiBubble.firstChild);
        } else {
            aiBubble.appendChild(textEl);
        }
    }
    textEl.innerHTML = window.renderMarkdown(textPart);

    tokens.forEach(({ sid, isMedia }) => {
        if (aiBubble.querySelector(`.hsearch-chat-card[data-session-id="${sid}"]`)) return;
        const cardHtml = (typeof window.renderHSearchCard === 'function')
            ? window.renderHSearchCard(sid, isMedia)
            : '';
        if (cardHtml) {
            const tmp = document.createElement('div');
            tmp.innerHTML = cardHtml;
            while (tmp.firstChild) aiBubble.appendChild(tmp.firstChild);
        }
    });

    aiBubble.dataset.renderedText = sourceText;
    _syncPdfPreviewClasses(aiBubble);
    if (isFinal && typeof window.linkifyHSearchCitations === 'function') {
        window.linkifyHSearchCitations(aiBubble);
    }
    if (!isFinal && cursor) {
        aiBubble.appendChild(cursor);
    }
}

window.formatModelTooltip = function(jsonStr) {
    try {
        const p = typeof jsonStr === 'string' ? JSON.parse(jsonStr) : jsonStr;
        if (!p || typeof p !== 'object') return String(jsonStr || '');

        let modelName = p.model || '';
        let backendName = p.backend || '';
        const trace = (p.agent_trace && typeof p.agent_trace === 'object') ? p.agent_trace : null;

        // Recover model/backend from trace LLM step for legacy messages without top-level metadata
        if (!modelName && trace && Array.isArray(trace.steps)) {
            const llmStep = trace.steps.find((s) => s && s.kind === 'llm' && s.detail);
            if (llmStep && llmStep.detail) {
                const m = String(llmStep.detail).match(/^(.+?)\s+\(([^)]+)\)\s*$/);
                if (m) {
                    modelName = m[1].trim();
                    backendName = backendName || m[2].trim();
                } else {
                    modelName = String(llmStep.detail).trim();
                }
            }
        }

        if (!modelName && !trace) {
            return typeof jsonStr === 'string' ? jsonStr : JSON.stringify(jsonStr);
        }

        const lines = [];

        // Line 1: Model & Backend
        if (modelName) {
            lines.push(`🤖 Model: ${modelName} (${backendName || 'unknown'})`);
        }

        // Line 2: Presets (matching sidebar tooltip format)
        if (p.global_preset || p.session_preset) {
            let presetLine = '🎭 Preset: ';
            if (p.session_preset && p.session_preset !== p.global_preset) {
                presetLine += `${p.session_preset} (override)`;
            } else {
                presetLine += (p.global_preset || p.session_preset);
            }
            lines.push(presetLine);
        }

        // Line 3: Soul / Persona
        if (p.persona) {
            const cleanSoul = String(p.persona).replace(/\.yaml$/i, '');
            lines.push(`👤 Soul: ${cleanSoul}`);
        }

        // Line 4: Inference Params (nullish coalescing so 0 values display cleanly)
        if (p.temperature !== undefined || p.top_p !== undefined || p.repeat_penalty !== undefined) {
            lines.push(`⚙ Temp: ${p.temperature ?? '?'} | Top P: ${p.top_p ?? '?'} | Rep Pen: ${p.repeat_penalty ?? '?'}`);
        }
        if (p.num_ctx !== undefined || p.num_predict !== undefined || p.num_gpu !== undefined) {
            lines.push(`📊 Ctx: ${p.num_ctx ?? '?'} | Predict: ${p.num_predict ?? '?'} | GPU: ${p.num_gpu ?? 0}`);
        }

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

        // Line 7: Agent Trace summary (compact summary instead of dumping raw JSON)
        if (trace) {
            const parts = [];
            if (trace.total_steps !== undefined) parts.push(`${trace.total_steps} step(s)`);
            if (typeof trace.duration_ms === 'number') parts.push(`${(trace.duration_ms / 1000).toFixed(1)}s`);
            if (trace.status) parts.push(trace.status);
            const tools = (Array.isArray(trace.tools_used) && trace.tools_used.length)
                ? ` | Tools: ${trace.tools_used.join(', ')}`
                : '';
            lines.push(`🔍 Trace: ${parts.join(' · ') || 'active'}${tools}`);
        }

        return lines.join('\n');
    } catch (e) {
        return typeof jsonStr === 'string' ? jsonStr : JSON.stringify(jsonStr);
    }
};

function _attachChatStreamListeners({ evtSrc, sessionId, aiBubble, cursor }) {
  let aiText = '';
  const resolveMeta = () => ({
    sessionId,
    sessionTitle: window.HecosChatStatus?.resolveSessionTitle?.(sessionId) || '',
    personaName: aiBubble?.dataset?.personaTitle || window.HecosChatStatus?.resolvePersonaName?.() || ''
  });
  const isCurrentView = () => !sessionId || !window.chatHistoryState?.activeSessionId || window.chatHistoryState.activeSessionId === sessionId;

  if (aiBubble && sessionId) aiBubble.dataset.sessionId = sessionId;
  if (window.HecosChatStatus && sessionId) {
    window.HecosChatStatus.markStreamStart(sessionId, resolveMeta());
  }

  evtSrc.onmessage = (e) => {
    const ev = JSON.parse(e.data);
    if (ev.type === 'action_plan') {
      if (window.ActionPlanChat && isCurrentView()) {
        window.ActionPlanChat.handleSseEvent(ev);
      }
    } else if (ev.type === 'agent_trace') {
      if (window.AgentUI && isCurrentView()) {
        window.AgentUI.handleEvent(ev, aiBubble.closest('.msg') || aiBubble.parentElement);
      }
      const trStep = ev.step || {};
      const trText = `${trStep.module_name || ''} ${trStep.label || ''} ${trStep.result_preview || ''} ${ev.message || ''}`;
      if (/Executor|verified on disk|Directory created|patched|write_file|patch_file|create_dir|delete_file|move_path|run_aider|start_app|stop_app/i.test(trText)) {
        window._HecosWorkspaceShared?.notifyFilesChanged?.('chat_trace');
      }
    } else if (ev.type === 'think') {
      if (window.renderThinkBlock) window.renderThinkBlock(ev.text, aiBubble);
    } else if (ev.type === 'token') {
      const tokenText = (ev.text !== undefined && ev.text !== null) ? ev.text : (ev.token || '');
      aiText += tokenText;
      _renderBubbleWithHSearch(aiBubble, aiText, cursor, false, null);
      if (isCurrentView() && window.chatArea) window.chatArea.scrollTop = window.chatArea.scrollHeight;
    } else if (ev.type === 'camera_request') {
      if (isCurrentView() && window.ClientCameraManager) window.ClientCameraManager.showCameraButton(aiBubble);
    } else if (ev.type === 'trace_done') {
      window._HecosWorkspaceShared?.notifyFilesChanged?.('trace_done');
      if (window.AgentUI && isCurrentView()) window.AgentUI.finalize(ev.trace_summary || null);
      if (isCurrentView() && window.chatHistory.length > 0) {
        window.chatHistory[window.chatHistory.length - 1].content = aiText;
      }

      if (ev.model_info && typeof window.attachModelInfoTooltip === 'function') {
        window.attachModelInfoTooltip(aiBubble, ev.model_info);
      }

      if (ev.persona_name) {
        const personaTitle = ev.persona_name.replace(/_/g, ' ').replace(/\.yaml$/i, '');
        aiBubble.dataset.personaTitle = personaTitle;
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

      if (window.HecosChatStatus && sessionId) {
        window.HecosChatStatus.markInputReady(sessionId);
      } else {
        window.isStreaming = false;
        if (window.updateStopAllBtn) window.updateStopAllBtn();
        if (window.sendBtn) window.sendBtn.disabled = false;
      }

    } else if (ev.type === 'audio_chunk') {
      // Ignored: single consolidated audio player used per message
    } else if (ev.type === 'audio_ready') {
      if (ev.audio_id) aiBubble.dataset.audioId = ev.audio_id;
      const meta = resolveMeta();
      if (window.tryLoadAudio) window.tryLoadAudio(aiBubble, true, null, meta);
    } else if (ev.type === 'system_audio_playing') {
      const meta = { ...resolveMeta(), ttlMs: 65000 };
      if (window.HecosChatStatus && sessionId) {
        window.HecosChatStatus.setLocalState(sessionId, 'speaking', meta);
      }
      if (window.showStopVoiceBtn) window.showStopVoiceBtn(true);
      if (window._stopTimeout) clearTimeout(window._stopTimeout);
      window._stopTimeout = setTimeout(() => {
        if (window.showStopVoiceBtn) window.showStopVoiceBtn(false);
        if (window.HecosChatStatus && sessionId) {
          const cur = window.HecosChatStatus.getSessionState(sessionId);
          if (cur && cur.status === 'speaking') {
            window.HecosChatStatus.setLocalState(sessionId, 'idle', meta);
          }
        }
      }, 60000);
    } else if (ev.type === 'done' || ev.type === 'error') {
      if (window.AgentUI && isCurrentView()) window.AgentUI.finalize();
      cursor.remove();
      const existingBadge = aiBubble.querySelector('.audio-badge');
      _renderBubbleWithHSearch(aiBubble, aiText, null, true, ev.type === 'error' ? ev.text : null);
      if (existingBadge && !aiBubble.contains(existingBadge)) {
        aiBubble.appendChild(existingBadge);
      }
      evtSrc.close();

      if (window.HecosChatStatus && sessionId) {
        window.HecosChatStatus.markStreamEnd(sessionId, ev.type === 'error' ? 'error' : 'done', resolveMeta());
      } else {
        window.isStreaming = false;
        if (window.updateStopAllBtn) window.updateStopAllBtn();
        if (window.sendBtn) window.sendBtn.disabled = false;
      }
      if (window.loadChatSessions) window.loadChatSessions();
      if (window.AgentResume && typeof window.AgentResume.refreshBanner === 'function') {
        window.AgentResume.refreshBanner(sessionId);
      }
      if (window.ActionPlanChat && typeof window.ActionPlanChat.refreshForSession === 'function') {
        window.ActionPlanChat.refreshForSession(sessionId);
      }
    }
  };

  evtSrc.onerror = () => {
    const wasStreaming = window.HecosChatStatus && sessionId
      ? window.HecosChatStatus.isSessionStreaming(sessionId)
      : !!window.isStreaming;
    if (window.AgentUI && isCurrentView()) window.AgentUI.finalize();
    cursor.remove();
    if (!wasStreaming && aiText) {
      evtSrc.close();
      if (window.HecosChatStatus && sessionId) window.HecosChatStatus.markStreamEnd(sessionId, 'done');
      return;
    }
    evtSrc.close();
    if (window.HecosChatStatus && sessionId) {
      window.HecosChatStatus.markStreamEnd(sessionId, 'error');
    } else {
      window.isStreaming = false;
      if (window.updateStopAllBtn) window.updateStopAllBtn();
      if (window.sendBtn) window.sendBtn.disabled = false;
    }

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
        } catch (e) {
          sawDown = true;
        }
      }, 2000);
    }
  };
}

window._attachChatStreamListeners = _attachChatStreamListeners;

window.sendMessage = async function() {
  if (typeof window.unlockAudioContext === 'function') {
      window.unlockAudioContext();
  }

  let text = window.userInput ? window.userInput.value.trim() : '';
  const hasAttachments = window.pendingAttachments && window.pendingAttachments.length > 0;
  if ((!text && !hasAttachments) || window.isStreaming) return;

  if (text) {
    window._lastVoiceCmdText = text;
    window._lastVoiceCmdTime = Date.now();
  }

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
  if (userMsg) userMsg.dataset.rawContent = fullMessage;
  userBubble.innerHTML = renderedContent;
  _syncPdfPreviewClasses(userBubble);
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
  const pendingSid = window.chatHistoryState?.activeSessionId || null;
  const { bubble: aiBubble } = window.addBubble('ai', '', 'ai-'+Date.now(), { persona_name: window.HecosPersonaName || null });
  const cursor = document.createElement('span');
  cursor.className = 'cursor';
  aiBubble.appendChild(cursor);
  
  if (window.HecosChatStatus && pendingSid) {
    window.HecosChatStatus.markStreamStart(pendingSid, { personaName: window.HecosPersonaName || null });
  } else {
    if (window.sendBtn) window.sendBtn.disabled = true;
    window.isStreaming = true;
    if (window.updateStopAllBtn) window.updateStopAllBtn();
  }

  try {
    const payload = {
      message: fullMessage, 
      history: window.chatHistory, 
      images: attachImgs,
      session_id: pendingSid,
      tab_id: window.hecosTabId
    };
    const res = await fetch('/api/chat', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if(!data.ok) throw new Error(data.error||'Server error');

    const streamSessionId = data.session_id || pendingSid;
    if (pendingSid && streamSessionId && streamSessionId !== pendingSid && window.HecosChatStatus) {
      window.HecosChatStatus.markStreamEnd(pendingSid, 'done');
    }

    if (data.session_id && window.chatHistoryState && !window.chatHistoryState.activeSessionId) {
        window.chatHistoryState.activeSessionId = data.session_id;
        localStorage.setItem('hecos_active_session_id', data.session_id);
    }

    if (data.intercepted) {
      cursor.remove();
      const msg = window.I18N?.flows_input_sent || "Response sent to flow.";
      aiBubble.innerHTML = window.renderMarkdown(`✅ *${msg}*`);
      if (window.HecosChatStatus && streamSessionId) {
        window.HecosChatStatus.markStreamEnd(streamSessionId, 'done');
      } else {
        window.isStreaming = false; if (window.updateStopAllBtn) window.updateStopAllBtn();
        if (window.sendBtn) window.sendBtn.disabled = false;
      }
      return;
    }

    // Lock privacy mode on first sent message
    if (window.chatHistoryState) {
      window.chatHistoryState.chatModeHasMessages = true;
      if (window.updateModeUI) window.updateModeUI();
    }

    const evtSrc = new EventSource(`/api/stream/${data.session_id}`);
    _attachChatStreamListeners({ evtSrc, sessionId: streamSessionId, aiBubble, cursor });
  } catch(err) {
    cursor.remove();
    aiBubble.textContent = '❌ ' + (window.I18N?.err_general || 'Error') + ': ' + err.message;
    if (window.HecosChatStatus && pendingSid) {
      window.HecosChatStatus.markStreamEnd(pendingSid, 'error');
    } else {
      window.isStreaming = false; if (window.updateStopAllBtn) window.updateStopAllBtn(); if (window.sendBtn) window.sendBtn.disabled = false;
    }
  }
};

window.sendInternalMessage = async function(text) {
  if(!text || window.isStreaming) return;

  window._lastVoiceCmdText = text;
  window._lastVoiceCmdTime = Date.now();
  
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
  
  window.chatHistory.push({role:'assistant', content:''});
  const pendingSid = window.chatHistoryState?.activeSessionId || null;
  const { bubble: aiBubble } = window.addBubble('ai', '', 'ai-'+Date.now(), { persona_name: window.HecosPersonaName || null });
  const cursor = document.createElement('span');
  cursor.className = 'cursor';
  aiBubble.appendChild(cursor);
  
  if (window.HecosChatStatus && pendingSid) {
    window.HecosChatStatus.markStreamStart(pendingSid, { personaName: window.HecosPersonaName || null });
  } else {
    if (window.sendBtn) window.sendBtn.disabled = true;
    window.isStreaming = true;
    if (window.updateStopAllBtn) window.updateStopAllBtn();
  }

  try {
    const payload = {
      message: text, 
      history: window.chatHistory, 
      images: [],
      session_id: pendingSid,
      tab_id: window.hecosTabId
    };
    const res = await fetch('/api/chat', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if(!data.ok) throw new Error(data.error||'Server error');

    const streamSessionId = data.session_id || pendingSid;
    if (pendingSid && streamSessionId && streamSessionId !== pendingSid && window.HecosChatStatus) {
      window.HecosChatStatus.markStreamEnd(pendingSid, 'done');
    }

    if (data.session_id && window.chatHistoryState && !window.chatHistoryState.activeSessionId) {
        window.chatHistoryState.activeSessionId = data.session_id;
        localStorage.setItem('hecos_active_session_id', data.session_id);
    }

    if (data.intercepted) {
      cursor.remove();
      const msg = window.I18N?.flows_input_sent || "Response sent to flow.";
      aiBubble.innerHTML = window.renderMarkdown(`✅ *${msg}*`);
      if (window.HecosChatStatus && streamSessionId) {
        window.HecosChatStatus.markStreamEnd(streamSessionId, 'done');
      } else {
        window.isStreaming = false; if (window.updateStopAllBtn) window.updateStopAllBtn();
        if (window.sendBtn) window.sendBtn.disabled = false;
      }
      return;
    }

    if (window.chatHistoryState) {
      window.chatHistoryState.chatModeHasMessages = true;
      if (window.updateModeUI) window.updateModeUI();
    }

    const evtSrc = new EventSource(`/api/stream/${data.session_id}`);
    _attachChatStreamListeners({ evtSrc, sessionId: streamSessionId, aiBubble, cursor });
  } catch(err) {
    cursor.remove();
    aiBubble.textContent = '❌ ' + (window.I18N?.err_general || 'Error') + ': ' + err.message;
    if (window.HecosChatStatus && pendingSid) {
      window.HecosChatStatus.markStreamEnd(pendingSid, 'error');
    } else {
      window.isStreaming = false; if (window.updateStopAllBtn) window.updateStopAllBtn(); if (window.sendBtn) window.sendBtn.disabled = false;
    }
  }
};
