/**
 * MODULE: chat_message_actions.js
 * PURPOSE: Logic for inline message actions (copy, edit, regenerate, delete)
 * Loaded by chat.html. Depends on: addBubble(), sendMessage(), window.chatHistory[], chatArea
 */

// ── Toast Notification ───────────────────────────────────────────
function showToast(msg, duration = 2000) {
  const el = document.getElementById('chat-toast');
  if (!el) return;
  el.textContent = msg;
  el.classList.add('show');
  setTimeout(() => el.classList.remove('show'), duration);
}

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
    toggleEditMode(msgEl, historyIndex);
  };
  bar.appendChild(editBtn);

  // Regenerate (AI messages only)
  if (role === 'ai') {
    const regenBtn = document.createElement('button');
    regenBtn.className = 'msg-action-btn';
    regenBtn.innerHTML = `🔁 ${t('chat_btn_regenerate')}`;
    regenBtn.title = t('chat_btn_regenerate');
    regenBtn.onclick = () => {
        if (window.isStreaming) return;
        regenerateLastResponse(historyIndex);
    };
    bar.appendChild(regenBtn);
  }

  // Delete button (all messages)
  const delBtn = document.createElement('button');
  delBtn.className = 'msg-action-btn danger';
  delBtn.innerHTML = '🗑';
  delBtn.title = t('chat_btn_delete');
  delBtn.onclick = () => {
    if (window.isStreaming) return;
    deleteMessage(msgEl, historyIndex);
  };
  bar.appendChild(delBtn);

  return bar;
}

// Build the edit mode textarea area for a bubble
function buildEditArea(msgEl, historyIndex) {
  const wrap = document.createElement('div');
  wrap.className = 'msg-edit-wrap';

  const t = window.t || ((k) => k);

  const bubble = msgEl.querySelector('.msg-bubble');
  const textarea = document.createElement('textarea');
  textarea.className = 'msg-edit-textarea';
  textarea.value = bubble.innerText || bubble.textContent;
  textarea.rows = 3;
  wrap.appendChild(textarea);

  const controls = document.createElement('div');
  controls.className = 'msg-edit-controls';

  const cancelBtn = document.createElement('button');
  cancelBtn.className = 'msg-edit-cancel';
  cancelBtn.textContent = t('chat_edit_cancel');
  cancelBtn.onclick = () => wrap.classList.remove('active');

  const confirmBtn = document.createElement('button');
  confirmBtn.className = 'msg-edit-confirm';
  confirmBtn.textContent = `✓ ${t('chat_edit_save')}`;
  confirmBtn.onclick = () => {
    const newText = textarea.value.trim();
    if (!newText) return;
    bubble.innerHTML = window.renderMarkdown ? renderMarkdown(newText) : newText;
    // Update history if index is valid
    if (typeof historyIndex === 'number' && window.chatHistory && window.chatHistory[historyIndex]) {
        window.chatHistory[historyIndex].content = newText;
    }
    wrap.classList.remove('active');
    showToast(`✅ ${t('chat_msg_modified')}`);
  };

  controls.appendChild(cancelBtn);
  controls.appendChild(confirmBtn);
  wrap.appendChild(controls);

  return wrap;
}

// Toggle edit mode on a message
function toggleEditMode(msgEl, historyIndex) {
  let wrap = msgEl.querySelector('.msg-edit-wrap');
  if (!wrap) {
    wrap = buildEditArea(msgEl, historyIndex);
    msgEl.querySelector('.msg-bubble').parentNode.appendChild(wrap);
  }
  wrap.classList.toggle('active');
  if (wrap.classList.contains('active')) {
    wrap.querySelector('textarea').focus();
  }
}

// Delete a message from the chat (visual + history)
function deleteMessage(msgEl, historyIndex) {
  const t = window.t || ((k) => k);
  msgEl.style.opacity = '0';
  msgEl.style.transform = 'translateY(-8px)';
  msgEl.style.transition = 'all .25s';
  setTimeout(() => {
    msgEl.remove();
    if (typeof historyIndex === 'number' && window.chatHistory && window.chatHistory[historyIndex]) {
        window.chatHistory.splice(historyIndex, 1);
    }
    showToast(`🗑 ${t('chat_msg_deleted')}`);
  }, 250);
}

// Regenerate the last AI response (remove it and re-send the previous user message)
async function regenerateLastResponse(historyIndex) {
  const t = window.t || ((k) => k);
  
  if (!window.chatHistory || window.chatHistory.length < 2) {
    showToast(`⚠️ ${t('chat_regen_no_prev')}`);
    return;
  }
  
  // 1. Identify the AI message and the preceding User message
  // Note: historyIndex is the index where the AI message is stored in window.chatHistory
  const aiMsgObj = window.chatHistory[historyIndex];
  const prevUserMsgObj = window.chatHistory[historyIndex - 1];
  
  if (!aiMsgObj || aiMsgObj.role !== 'assistant') {
    showToast(`⚠️ ${t('chat_regen_invalid')}`);
    return;
  }
  if (!prevUserMsgObj || prevUserMsgObj.role !== 'user') {
    showToast(`⚠️ ${t('chat_regen_no_question')}`);
    return;
  }

  const textToResend = prevUserMsgObj.content;

  // 2. Remove visual AI message from DOM
  // We don't have a direct data-history attribute on the msg element by default unless we add it
  // But we know msgEl was passed to attachMessageActions.
  // Actually, we can just find the bubble that was clicked.
  // regenerateLastResponse is called by the button inside the bar inside the msgEl.
  // However, buildMessageActions doesn't pass msgEl to regenerateLastResponse, only the index.
  // We should find the msgEl by index if we tag it, or pass it.
  
  // Let's find all messages and pick the one matching the index? 
  // No, indices might shift if items are deleted.
  // The simplest is to find any .msg.ai that contains the button clicked.
  // But regenerateLastResponse already has historyIndex.
  
  const allMsgs = document.querySelectorAll('.msg');
  // This is risky because the order in DOM might not match history array if things were deleted/moved.
  // But usually they match.
  
  // A better way: attachMessageActions should tag the msgEl with the index.
  const aiMsgEl = document.querySelector(`.msg[data-hidx="${historyIndex}"]`);

  if (aiMsgEl) {
    aiMsgEl.style.opacity = '0';
    setTimeout(() => aiMsgEl.remove(), 250);
  }

  // 3. Remove AI message from history array
  window.chatHistory.splice(historyIndex, 1);
  
  // 4. Trigger regeneration using internal sender
  showToast(`🔁 ${t('chat_regen_toast')}`);
  if (typeof window.sendInternalMessage === 'function') {
    // Small delay to allow fade-out animation
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
