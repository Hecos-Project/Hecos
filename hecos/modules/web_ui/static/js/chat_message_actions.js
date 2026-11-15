/**
 * MODULE: chat_message_actions.js
 * PURPOSE: Logic for inline message actions (copy, edit, regenerate, delete)
 * Loaded by chat.html. Depends on: addBubble(), sendMessage(), window.chatHistory[], chatArea
 */


// ── Build the action bar DOM for a message bubble ────────────────
function buildMessageActions(msgEl, role, historyIndex) {
  const bar = document.createElement('div');
  bar.className = 'msg-actions';

  const t = window.t || ((k) => k);

  // Copy button (all messages)
  const copyBtn = document.createElement('button');
  copyBtn.className = 'msg-action-btn';
  copyBtn.innerHTML = `📋 ${t('chat_btn_copy')}`;
  copyBtn.title = t('chat_btn_copy');
  copyBtn.onclick = () => {
    const bubble = msgEl.querySelector('.msg-bubble');
    navigator.clipboard.writeText(bubble.innerText || bubble.textContent)
      .then(() => showToast(`✅ ${t('chat_msg_copied')}`))
      .catch(() => showToast(`❌ ${t('chat_msg_copy_failed')}`));
  };
  bar.appendChild(copyBtn);

  // Edit button (all messages)
  const editBtn = document.createElement('button');
  editBtn.className = 'msg-action-btn';
  editBtn.innerHTML = `✏️ ${t('chat_btn_edit')}`;
  editBtn.title = t('chat_btn_edit');
  editBtn.onclick = () => {
    if (window.isStreaming) return;
    toggleEditMode(msgEl, _resolveMsgIndex(msgEl, historyIndex));
  };
  bar.appendChild(editBtn);

  // Resend button (User messages only)
  if (role === 'user') {
    const resendBtn = document.createElement('button');
    resendBtn.className = 'msg-action-btn';
    const resendLabel = t('chat_btn_resend') === 'chat_btn_resend' ? 'Resend' : t('chat_btn_resend');
    const resendTooltip = t('chat_btn_resend_tooltip') === 'chat_btn_resend_tooltip'
      ? 'Resend this message'
      : t('chat_btn_resend_tooltip');
    resendBtn.innerHTML = `🔄 ${resendLabel}`;
    resendBtn.title = resendTooltip;
    resendBtn.onclick = () => {
      if (window.isStreaming) return;
      resendUserMessage(msgEl, _resolveMsgIndex(msgEl, historyIndex));
    };
    bar.appendChild(resendBtn);
  }

  // Regenerate (AI messages only)
  if (role === 'ai') {
    const regenBtn = document.createElement('button');
    regenBtn.className = 'msg-action-btn';
    regenBtn.innerHTML = `🔁 ${t('chat_btn_regenerate')}`;
    regenBtn.title = t('chat_btn_regenerate');
    regenBtn.onclick = () => {
        if (window.isStreaming) return;
        regenerateLastResponse(_resolveMsgIndex(msgEl, historyIndex), msgEl);
    };
    bar.appendChild(regenBtn);

    // Thinking Block button
    const thinkTextRaw = msgEl.getAttribute('data-think-text');
    if (thinkTextRaw) {
        const thinkText = decodeURIComponent(thinkTextRaw);
        const thinkBtn = document.createElement('button');
        thinkBtn.className = 'msg-action-btn think-btn';
        thinkBtn.title = 'Toggle Reasoning';
        
        const isStreaming = msgEl.querySelector('.chat-spinner');
        
        // Ensure the thinking box content exists in the DOM
        let thinkBox = msgEl.querySelector('.think-content-expanded');
        let isExpandedState = false;
        
        if (!thinkBox) {
            thinkBox = document.createElement('div');
            thinkBox.className = 'think-content-expanded';
            thinkBox.textContent = thinkText;
            
            // Resolve initial display state: check session override first, then fallback to default setting
            const isDefaultCollapsed = window.HecosReasoningCollapsed !== undefined ? window.HecosReasoningCollapsed : true;
            isExpandedState = window._sessionThinkExpanded !== undefined ? window._sessionThinkExpanded : !isDefaultCollapsed;
            thinkBox.style.display = isExpandedState ? 'block' : 'none';
            
            // Append it right inside the bubble wrapper, BEFORE the bubble
            const wrapper = msgEl.querySelector('.msg-content-wrapper');
            const bubbleNode = msgEl.querySelector('.msg-bubble');
            if (wrapper && bubbleNode) {
                wrapper.insertBefore(thinkBox, bubbleNode);
            } else if (wrapper) {
                wrapper.appendChild(thinkBox);
            }
        } else {
            // Update text in case it's streaming
            thinkBox.textContent = thinkText;
            isExpandedState = thinkBox.style.display !== 'none';
        }

        thinkBtn.innerHTML = isStreaming ? `🧠 Thinking...` : (isExpandedState ? `💡 Hide Thinking` : `💡 Show Thinking`);

        thinkBtn.onclick = () => {
            const isCurrentlyHidden = thinkBox.style.display === 'none' || !thinkBox.style.display;
            const newState = isCurrentlyHidden ? 'block' : 'none';
            
            // Set the session override so future messages remember this choice
            window._sessionThinkExpanded = isCurrentlyHidden;
            
            // Apply to ALL thinking boxes in the chat to sync the state
            document.querySelectorAll('.think-content-expanded').forEach(box => {
                box.style.display = newState;
            });
            
            // Update button texts for all non-streaming think buttons
            document.querySelectorAll('.think-btn').forEach(btn => {
                const btnMsg = btn.closest('.msg');
                if (btnMsg && !btnMsg.querySelector('.chat-spinner')) {
                    btn.innerHTML = isCurrentlyHidden ? '💡 Hide Thinking' : '💡 Show Thinking';
                }
            });
        };
        bar.appendChild(thinkBtn);
    }

    // Listen (TTS) button
    const listenBtn = document.createElement('button');
    listenBtn.className = 'msg-action-btn';
    const listenLabel = t('chat_btn_listen') === 'chat_btn_listen' ? 'Listen' : t('chat_btn_listen');
    listenBtn.innerHTML = `🔊 ${listenLabel}`;
    
    const listenTooltipFallback = listenLabel + ' - Regenerate audio (entire message or selection)';
    listenBtn.title = t('chat_btn_listen_tooltip') === 'chat_btn_listen_tooltip' 
        ? listenTooltipFallback 
        : t('chat_btn_listen_tooltip');
    
    // Capture selected text before the click clears the selection
    let _capturedSelection = null;
    listenBtn.addEventListener('pointerdown', (e) => {
      // Prevent focus steal which clears the selection on most browsers
      if (e.pointerType === 'mouse') {
          e.preventDefault(); 
      }
      const sel = window.getSelection();
      if (sel && sel.toString().trim()) {
        _capturedSelection = sel.toString().trim();
      } else {
        _capturedSelection = null;
      }
    });
    
    listenBtn.onclick = async () => {
      if (window.isStreaming) return;
      const bubble = msgEl.querySelector('.msg-bubble');
      // Use captured selection if available, otherwise speak the full bubble
      const textToSpeak = _capturedSelection || bubble.innerText || bubble.textContent;
      _capturedSelection = null; // reset for next click
      
      if (!textToSpeak || !bubble) return;
      
      const generatingLabel = t('chat_toast_tts_gen') === 'chat_toast_tts_gen' ? 'Generating audio...' : t('chat_toast_tts_gen');
      showToast(`🔊 ${generatingLabel}`);
      listenBtn.disabled = true;
      listenBtn.style.opacity = '0.5';
      
      // Remove any existing progress bars or badges
      bubble.querySelectorAll('.audio-badge, .tts-progress-container').forEach(e => e.remove());

      const progressContainer = document.createElement('div');
      progressContainer.className = 'tts-progress-container';
      progressContainer.innerHTML = `
        <div class="tts-progress-header">
            <span class="tts-progress-text">Generating audio... (0%)</span>
            <button class="tts-cancel-btn" title="Cancel Generation">✖</button>
        </div>
        <div class="tts-progress-track">
            <div class="tts-progress-fill" style="width: 0%;"></div>
        </div>
      `;
      bubble.appendChild(progressContainer);
      
      const progressFill = progressContainer.querySelector('.tts-progress-fill');
      const progressText = progressContainer.querySelector('.tts-progress-text');
      const cancelBtn = progressContainer.querySelector('.tts-cancel-btn');
      
      let isCancelled = false;
      let evtSource = null;

      cancelBtn.onclick = () => {
          isCancelled = true;
          if (evtSource) evtSource.close();
          fetch('/api/audio/stop', { method: 'POST' }).catch(() => {});
          progressContainer.remove();
          listenBtn.disabled = false;
          listenBtn.style.opacity = '1';
          showToast(`❌ Generation Cancelled`);
      };
      
      try {
          const res = await fetch('/api/audio/test', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ 
                  text: textToSpeak, 
                  mode: 'web',
                  bypass_cache: true,
                  session_id: (window.chatHistoryState && window.chatHistoryState.activeSessionId) ? window.chatHistoryState.activeSessionId : null
              })
          });
          const data = await res.json();
          if (data.ok && data.job_id) {
              evtSource = new EventSource(`/api/audio/test/progress/${data.job_id}`);
              
              evtSource.onmessage = (event) => {
                  if (isCancelled) return;
                  const prog = JSON.parse(event.data);
                  
                  if (prog.status === 'not_found' || prog.status === 'error') {
                      evtSource.close();
                      progressContainer.remove();
                      listenBtn.disabled = false;
                      listenBtn.style.opacity = '1';
                      const errMsg = prog.error || 'TTS Error';
                      showToast(`❌ ${errMsg}`, 5000);
                      return;
                  }
                  
                  if (prog.total > 0) {
                      const pct = Math.round((prog.current / prog.total) * 100);
                      progressFill.style.width = `${pct}%`;
                      progressText.textContent = `Generating audio... (${pct}%)`;
                  }
                  
                  if (prog.status === 'done') {
                      evtSource.close();
                      progressContainer.remove();
                      listenBtn.disabled = false;
                      listenBtn.style.opacity = '1';
                      if (typeof window.tryLoadAudio === 'function') {
                          window._lastAiBubble = bubble;
                          // Use the precise audio_id from the SSE event for reliable retrieval.
                          // Fall back to the timestamp trick if audio_id is somehow missing.
                          const audioUrl = prog.audio_id
                              ? `/api/audio?id=${encodeURIComponent(prog.audio_id)}`
                              : `/api/audio?t=${Date.now()}`;
                          if (prog.audio_id) {
                              bubble.dataset.audioId = prog.audio_id;
                          }
                          window.tryLoadAudio(bubble, true, audioUrl);
                      }
                  }
              };
              
              evtSource.onerror = () => {
                  evtSource.close();
                  if (!isCancelled) {
                      progressContainer.remove();
                      listenBtn.disabled = false;
                      listenBtn.style.opacity = '1';
                      showToast(`❌ TTS Stream Error`);
                  }
              };
          } else {
              progressContainer.remove();
              listenBtn.disabled = false;
              listenBtn.style.opacity = '1';
              const errLabel = t('chat_toast_tts_err') === 'chat_toast_tts_err' ? 'TTS Error' : t('chat_toast_tts_err');
              showToast(`❌ ${errLabel}: ${data.error || 'Unknown Error'}`);
          }
      } catch (e) {
          progressContainer.remove();
          listenBtn.disabled = false;
          listenBtn.style.opacity = '1';
          const errNetLabel = t('chat_toast_err_net') === 'chat_toast_err_net' ? 'Network Error' : t('chat_toast_err_net');
          showToast(`❌ ${errNetLabel}: ${e.message}`);
      }
    };
    bar.appendChild(listenBtn);
  }

  // Delete button (all messages)
  const delBtn = document.createElement('button');
  delBtn.className = 'msg-action-btn danger';
  delBtn.innerHTML = '🗑';
  delBtn.title = t('chat_btn_delete');
  delBtn.onclick = () => {
    if (window.isStreaming) return;
    deleteMessage(msgEl, _resolveMsgIndex(msgEl, historyIndex));
  };
  bar.appendChild(delBtn);

  return bar;
}

function _reindexDomMessages() {
  const allMsgs = document.querySelectorAll('#chat-area > .msg');
  allMsgs.forEach((el, idx) => {
    el.setAttribute('data-hidx', idx);
  });
}

function _resolveMsgIndex(msgEl, fallbackIndex) {
  if (msgEl) {
    const allMsgs = Array.from(document.querySelectorAll('#chat-area > .msg'));
    const domIdx = allMsgs.indexOf(msgEl);
    if (domIdx !== -1) return domIdx;
    const attrIdx = parseInt(msgEl.getAttribute('data-hidx'), 10);
    if (!isNaN(attrIdx)) return attrIdx;
  }
  return typeof fallbackIndex === 'number' ? fallbackIndex : -1;
}

function _syncDeleteBackend(index, role, content) {
  try {
    const sid = (window.chatHistoryState && window.chatHistoryState.activeSessionId)
      ? window.chatHistoryState.activeSessionId
      : null;
    fetch('/api/chat/messages/delete', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sid, index, role, content })
    }).catch(() => {});
  } catch (e) {}
}

function _syncEditBackend(index, role, content) {
  try {
    const sid = (window.chatHistoryState && window.chatHistoryState.activeSessionId)
      ? window.chatHistoryState.activeSessionId
      : null;
    fetch('/api/chat/messages/edit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sid, index, role, content })
    }).catch(() => {});
  } catch (e) {}
}

// Build the edit mode textarea area for a bubble
function buildEditArea(msgEl, historyIndex) {
  const wrap = document.createElement('div');
  wrap.className = 'msg-edit-wrap';

  const t = window.t || ((k) => k);
  const isUser = msgEl.classList.contains('user');

  const bubble = msgEl.querySelector('.msg-bubble');
  const textarea = document.createElement('textarea');
  textarea.className = 'msg-edit-textarea';
  textarea.value = msgEl.dataset.rawContent || bubble.innerText || bubble.textContent;
  textarea.rows = 3;
  wrap.appendChild(textarea);

  const controls = document.createElement('div');
  controls.className = 'msg-edit-controls';

  const cancelBtn = document.createElement('button');
  cancelBtn.className = 'msg-edit-cancel';
  cancelBtn.textContent = t('chat_edit_cancel');
  cancelBtn.onclick = () => wrap.classList.remove('active');

  const applyEdit = () => {
    const newText = textarea.value.trim();
    if (!newText) return null;
    bubble.innerHTML = window.renderMarkdown ? renderMarkdown(newText) : newText;
    msgEl.dataset.rawContent = newText;
    const liveIdx = _resolveMsgIndex(msgEl, historyIndex);
    if (liveIdx >= 0 && window.chatHistory && window.chatHistory[liveIdx]) {
      window.chatHistory[liveIdx].content = newText;
    }
    _syncEditBackend(liveIdx, isUser ? 'user' : 'assistant', newText);
    wrap.classList.remove('active');
    return { newText, liveIdx };
  };

  const confirmBtn = document.createElement('button');
  confirmBtn.className = 'msg-edit-confirm';
  confirmBtn.textContent = `✓ ${t('chat_edit_save')}`;
  confirmBtn.onclick = () => {
    const res = applyEdit();
    if (!res) return;
    showToast(`✅ ${t('chat_msg_modified')}`);
  };

  controls.appendChild(cancelBtn);
  controls.appendChild(confirmBtn);

  if (isUser) {
    const saveResendBtn = document.createElement('button');
    saveResendBtn.className = 'msg-edit-confirm';
    const srLabel = t('chat_edit_save_resend') === 'chat_edit_save_resend'
      ? 'Save & Resend'
      : t('chat_edit_save_resend');
    saveResendBtn.textContent = `🔄 ${srLabel}`;
    saveResendBtn.onclick = () => {
      if (window.isStreaming) return;
      const res = applyEdit();
      if (!res) return;
      resendUserMessage(msgEl, res.liveIdx);
    };
    controls.appendChild(saveResendBtn);
  }

  wrap.appendChild(controls);

  return wrap;
}

// Toggle edit mode on a message
function toggleEditMode(msgEl, historyIndex) {
  let wrap = msgEl.querySelector('.msg-edit-wrap');
  if (!wrap) {
    wrap = buildEditArea(msgEl, historyIndex);
    msgEl.querySelector('.msg-bubble').parentNode.appendChild(wrap);
  } else {
    const ta = wrap.querySelector('.msg-edit-textarea');
    const bubble = msgEl.querySelector('.msg-bubble');
    if (ta && !wrap.classList.contains('active')) {
      ta.value = msgEl.dataset.rawContent || (bubble ? (bubble.innerText || bubble.textContent) : '');
    }
  }
  wrap.classList.toggle('active');
  if (wrap.classList.contains('active')) {
    wrap.querySelector('textarea').focus();
  }
}

// Delete a message from the chat (visual + history + DB)
function deleteMessage(msgEl, historyIndex) {
  const t = window.t || ((k) => k);
  const liveIdx = _resolveMsgIndex(msgEl, historyIndex);
  const isUser = msgEl.classList.contains('user');
  const bubble = msgEl.querySelector('.msg-bubble');
  const rawContent = msgEl.dataset.rawContent
    || (liveIdx >= 0 && window.chatHistory && window.chatHistory[liveIdx] ? window.chatHistory[liveIdx].content : '')
    || (bubble ? (bubble.innerText || bubble.textContent) : '');

  _syncDeleteBackend(liveIdx, isUser ? 'user' : 'assistant', rawContent);

  msgEl.style.opacity = '0';
  msgEl.style.transform = 'translateY(-8px)';
  msgEl.style.transition = 'all .25s';
  setTimeout(() => {
    const idxNow = _resolveMsgIndex(msgEl, liveIdx);
    msgEl.remove();
    if (idxNow >= 0 && window.chatHistory && window.chatHistory[idxNow]) {
      window.chatHistory.splice(idxNow, 1);
    }
    _reindexDomMessages();
    showToast(`🗑 ${t('chat_msg_deleted')}`);
  }, 250);
}

// Resend a user message:
// - If this user message is already at the bottom of the chat (e.g. AI reply was deleted or failed),
//   re-triggers AI generation directly below this user bubble without duplicating the user bubble.
// - Otherwise (if followed by a normal AI response/conversation), sends the same message as a new turn at the bottom.
async function resendUserMessage(msgEl, historyIndex) {
  const t = window.t || ((k) => k);
  if (window.isStreaming) return;

  const liveIdx = _resolveMsgIndex(msgEl, historyIndex);
  const bubble = msgEl ? msgEl.querySelector('.msg-bubble') : null;
  const textToResend = (
    (msgEl && msgEl.dataset.rawContent) ||
    (liveIdx >= 0 && window.chatHistory && window.chatHistory[liveIdx] ? window.chatHistory[liveIdx].content : '') ||
    (bubble ? (bubble.innerText || bubble.textContent) : '')
  ).trim();

  if (!textToResend) return;

  const allMsgs = Array.from(document.querySelectorAll('#chat-area > .msg'));
  const domIdx = allMsgs.indexOf(msgEl);
  const isLastMsg = (domIdx !== -1 && domIdx === allMsgs.length - 1);

  // Check if the only message after this user message is a trailing AI error/interrupted bubble
  let hasTrailingErrorBubble = false;
  let trailingAiEl = null;
  if (domIdx !== -1 && domIdx === allMsgs.length - 2) {
    const nextEl = allMsgs[domIdx + 1];
    if (nextEl && nextEl.classList.contains('ai')) {
      const nextBubble = nextEl.querySelector('.msg-bubble');
      const nextTxt = (nextBubble ? (nextBubble.innerText || nextBubble.textContent) : '').trim();
      if (!nextTxt || nextTxt.startsWith('❌') || nextTxt.startsWith('⚠️') || nextTxt === 'Stopped' || nextTxt === 'Interrotto') {
        hasTrailingErrorBubble = true;
        trailingAiEl = nextEl;
      }
    }
  }

  const resendToast = t('chat_resend_toast') === 'chat_resend_toast' ? 'Resending message...' : t('chat_resend_toast');
  showToast(`🔄 ${resendToast}`);

  if (isLastMsg || hasTrailingErrorBubble) {
    if (trailingAiEl) {
      const aiIdx = _resolveMsgIndex(trailingAiEl, domIdx + 1);
      const aiBubble = trailingAiEl.querySelector('.msg-bubble');
      const aiTxt = (aiBubble ? (aiBubble.innerText || aiBubble.textContent) : '').trim();
      _syncDeleteBackend(aiIdx, 'assistant', aiTxt);
      trailingAiEl.remove();
      if (aiIdx >= 0 && window.chatHistory && window.chatHistory[aiIdx]) {
        window.chatHistory.splice(aiIdx, 1);
      }
      _reindexDomMessages();
    }
    if (typeof window.sendInternalMessage === 'function') {
      await window.sendInternalMessage(textToResend);
    }
  } else {
    // Send as a fresh turn at the bottom of the chat
    if (window.userInput && typeof window.sendMessage === 'function') {
      window.userInput.value = textToResend;
      if (typeof window.autoResize === 'function') window.autoResize(window.userInput);
      await window.sendMessage();
    } else if (typeof window.sendInternalMessage === 'function') {
      await window.sendInternalMessage(textToResend);
    }
  }
}

// Regenerate the AI response (remove it and re-send the preceding user message)
async function regenerateLastResponse(historyIndex, passedMsgEl) {
  const t = window.t || ((k) => k);
  const aiMsgEl = passedMsgEl || document.querySelector(`.msg[data-hidx="${historyIndex}"]`);
  const liveIdx = _resolveMsgIndex(aiMsgEl, historyIndex);

  if (!window.chatHistory || window.chatHistory.length < 2 || liveIdx < 1) {
    showToast(`⚠️ ${t('chat_regen_no_prev')}`);
    return;
  }

  const aiMsgObj = window.chatHistory[liveIdx];
  const prevUserMsgObj = window.chatHistory[liveIdx - 1];

  if (!aiMsgObj || aiMsgObj.role !== 'assistant') {
    showToast(`⚠️ ${t('chat_regen_invalid')}`);
    return;
  }
  if (!prevUserMsgObj || prevUserMsgObj.role !== 'user') {
    showToast(`⚠️ ${t('chat_regen_no_question')}`);
    return;
  }

  const textToResend = prevUserMsgObj.content;

  // Delete old AI response from backend DB so it doesn't stay in history
  _syncDeleteBackend(liveIdx, 'assistant', aiMsgObj.content || '');

  if (aiMsgEl) {
    aiMsgEl.style.opacity = '0';
    setTimeout(() => {
      aiMsgEl.remove();
      _reindexDomMessages();
    }, 250);
  }

  // Remove AI message from history array
  window.chatHistory.splice(liveIdx, 1);

  // Trigger regeneration using internal sender
  showToast(`🔁 ${t('chat_regen_toast')}`);
  if (typeof window.sendInternalMessage === 'function') {
    setTimeout(async () => {
      await window.sendInternalMessage(textToResend);
    }, 260);
  } else {
    showToast(`❌ ${t('chat_regen_err_internal')}`);
  }
}

// ── Attach action bars to all rendered messages ─────────────────
// Called after each bubble is added. Exposed globally.
window.attachMessageActions = function(msgEl, role, historyIndex) {
  // Tag the element with the history index so actions can find it
  msgEl.setAttribute('data-hidx', historyIndex);
  
  const actionBar = buildMessageActions(msgEl, role, historyIndex);
  // Append after the bubble
  const bubble = msgEl.querySelector('.msg-bubble');
  if (bubble && bubble.parentNode) {
    bubble.parentNode.insertBefore(actionBar, bubble.nextSibling);
  }
};
