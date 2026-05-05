/**
 * chat_events.js
 * Handles backend notification streams (/api/events)
 */

window.initEvents = function() {
  const evtSrc = new EventSource('/api/events');
  evtSrc.onmessage = (e) => {
    const ev = JSON.parse(e.data);
    
    // Support dynamic handlers from plugins (like remote_triggers.js)
    if (window._hecosSSEHandlers && window._hecosSSEHandlers[ev.type]) {
        window._hecosSSEHandlers[ev.type](ev);
        return;
    }
    
    if (ev.type === 'agent_trace') {
      if (window.AgentUI) window.AgentUI.handleEvent(ev);
      
    } else if (ev.type === 'action_console') {
      const msgDiv = document.createElement('div');
      msgDiv.className = 'msg action-log';
      msgDiv.style.opacity = '0.9';
      
      const avatar = document.createElement('img');
      avatar.className = 'msg-avatar';
      // Use existing avatar, or a default terminal icon
      avatar.src = '/static/images/hecos_light.png'; 
      avatar.style.filter = "grayscale(100%) brightness(0.6)"; 
      
      const content = document.createElement('div');
      content.className = 'action-console-block';
      content.style = "background: var(--bg2); color: var(--text); padding: 10px 15px; border-radius: 8px; font-family: 'Consolas', 'Courier New', monospace; font-size: 0.85em; width: 100%; overflow-x: auto; border: 1px solid var(--border-color); margin: 5px 0;";
      
      const header = document.createElement('div');
      header.style = "color: var(--accent); font-weight: bold; margin-bottom: 5px;";
      header.innerText = "┌── [ACTION] " + (ev.tool_name || 'SYSTEM');
      
      const cmd = document.createElement('div');
      cmd.style = "color: var(--cyan); margin-bottom: 5px;";
      cmd.innerText = "│ $ " + (ev.command || '');
      
      const outBlock = document.createElement('div');
      outBlock.style = "white-space: pre-wrap; margin-left: 2px; color: var(--muted);";
      let previewText = (ev.output || '').trim();
      if (previewText.length > 500) {
          previewText = previewText.substring(0, 500) + "\n...[truncated]";
      }
      outBlock.innerText = previewText.split('\n').map(l => "│   " + l).join('\n');
      
      const footer = document.createElement('div');
      footer.style = "color: var(--accent); margin-top: 5px;";
      footer.innerText = "└" + "─".repeat(25);
      
      content.appendChild(header);
      content.appendChild(cmd);
      content.appendChild(outBlock);
      content.appendChild(footer);
      
      msgDiv.appendChild(avatar);
      msgDiv.appendChild(content);
      
      if (window.chatArea) {
          // If the AI is typing right now, we should insert this BEFORE the typing bubble
          if (window._liveBackendAiBubble) {
              const liveMsgContainer = window._liveBackendAiBubble.closest('.msg');
              if (liveMsgContainer) {
                  window.chatArea.insertBefore(msgDiv, liveMsgContainer);
              } else {
                  window.chatArea.appendChild(msgDiv);
              }
          } else {
              window.chatArea.appendChild(msgDiv);
          }
          window.chatArea.scrollTop = window.chatArea.scrollHeight;
      }
      
    } else if (ev.type === 'ptt_status') {
      const pttInd = document.getElementById('ptt-indicator');
      const sttSource = document.getElementById('stt-source');
      const isWebMic = sttSource && sttSource.value === 'web';
      
      if (ev.active) {
          if (pttInd) pttInd.classList.add('active');
          // Bypassing browser beep and auto-recording on backend PTT hardware events
          // to avoid double-echoing and double-recording contexts.
      } else {
          if (pttInd) pttInd.classList.remove('active');
      }
      
    } else if (ev.type === 'voice_detected' && ev.text) {
      console.log("[Audio] Voice command received:", ev.text);
      if (window.hideWelcome) window.hideWelcome();
      
      if (ev.standalone) {
          // In standalone mode, the frontend orchestrates generation
          if (window.addBubble) window.addBubble('user', ev.text);
          if (window.chatHistory) window.chatHistory.push({role: 'user', content: ev.text, images: []});
          if (window.sendInternalMessage) window.sendInternalMessage(ev.text);
      } else {
          // Native system is already processing it, just show the bubbles
          if (window.addBubble) window.addBubble('user', ev.text);
          
          if (window.addBubble) {
              const { bubble: aiBubble } = window.addBubble('ai', '', 'ai-live-'+Date.now());
              aiBubble.innerHTML = '<span class="cursor"></span>';
              window._liveBackendAiBubble = aiBubble;
          }
          
          window.isStreaming = true;
          if (window.sendBtn) window.sendBtn.disabled = true;
          if (window.showStopVoiceBtn) window.showStopVoiceBtn(true);
          if (window.chatArea) window.chatArea.scrollTop = window.chatArea.scrollHeight;
      }

    } else if (ev.type === 'processing_start') {
      if (window.hideWelcome) window.hideWelcome();
      
    } else if (ev.type === 'system_response') {
      if (window.AgentUI) window.AgentUI.finalize();

      console.log("[Audio] Backend response received.", ev);
      let aiText = ev.ai || '';
      const displayText = aiText || '<em style="color:var(--muted)">(nessuna risposta)</em>';
      
      if (window._liveBackendAiBubble) {
        window._liveBackendAiBubble.innerHTML = aiText ? window.renderMarkdown(aiText) : displayText;
        window._liveBackendAiBubble = null;
      } else {
        if (window.hideWelcome) window.hideWelcome();
        if (ev.user && window.addBubble) window.addBubble('user', ev.user);
        if (window.addBubble) window.addBubble('ai', aiText || '(nessuna risposta)');
      }
      
      window.isStreaming = false;
      if (window.sendBtn) window.sendBtn.disabled = false;
      if (window.showStopVoiceBtn) window.showStopVoiceBtn(false);
      
      if (ev.user) window.chatHistory.push({role: 'user', content: ev.user});
      if (aiText)  window.chatHistory.push({role: 'assistant', content: aiText});
      if (window.chatArea) window.chatArea.scrollTop = window.chatArea.scrollHeight;

    } else if (ev.type === 'audio_ready') {
      console.log("[Audio] Global audio ready from backend");
      // Use _lastAiBubble tracked at bubble creation time.
      // The old .msg.ai:last-child selector broke when action-log divs were inserted after.
      const targetBubble = window._lastAiBubble;
      if (targetBubble && window.tryLoadAudio) {
        window.tryLoadAudio(targetBubble);
      }

    } else if (ev.type === 'reminder_fire') {
      // ── Reminder Alert Banner ────────────────────────────────────────────
      // Shows a dismissable banner at the top of the chat when a reminder fires.
      const title = (ev.data && ev.data.title) ? ev.data.title : 'Promemoria';
      _showReminderBanner(title);
      // Refresh sidebar widget if present
      if (window.reminderWidget && window.reminderWidget.refresh) {
        window.reminderWidget.refresh();
      }
    }
  };
};

/**
 * Displays a dismissable reminder alert banner at the top of the chat area.
 * Auto-dismisses after 10 seconds.
 */
function _showReminderBanner(title) {
  // Remove existing banner if present
  const existing = document.getElementById('hecos-reminder-banner');
  if (existing) existing.remove();

  const banner = document.createElement('div');
  banner.id = 'hecos-reminder-banner';
  banner.style.cssText = [
    'position: fixed',
    'top: 70px',
    'left: 50%',
    'transform: translateX(-50%)',
    'background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%)',
    'color: #fff',
    'border: 1px solid rgba(255,200,60,0.5)',
    'border-radius: 12px',
    'padding: 14px 20px',
    'z-index: 9999',
    'display: flex',
    'align-items: center',
    'gap: 12px',
    'box-shadow: 0 8px 32px rgba(0,0,0,0.4)',
    'min-width: 300px',
    'max-width: 500px',
    'animation: hecos-slide-down 0.3s ease',
  ].join(';');

  banner.innerHTML = `
    <span style="font-size:1.5em;">🔔</span>
    <div style="flex:1">
      <div style="font-weight:600;font-size:0.95em;color:#ffc83c;">Promemoria</div>
      <div style="font-size:0.9em;color:#e0e0e0;margin-top:2px;">${_escapeHtml(title)}</div>
    </div>
    <button onclick="document.getElementById('hecos-reminder-banner').remove()"
      style="background:none;border:none;color:#aaa;cursor:pointer;font-size:1.1em;padding:0 4px;"
      title="Chiudi">✕</button>
  `;

  // Inject keyframe if not already present
  if (!document.getElementById('hecos-reminder-style')) {
    const style = document.createElement('style');
    style.id = 'hecos-reminder-style';
    style.textContent = `
      @keyframes hecos-slide-down {
        from { opacity:0; transform: translateX(-50%) translateY(-20px); }
        to   { opacity:1; transform: translateX(-50%) translateY(0); }
      }
    `;
    document.head.appendChild(style);
  }

  document.body.appendChild(banner);

  // Auto-dismiss after 10 seconds
  setTimeout(() => { if (banner.parentNode) banner.remove(); }, 10000);

  // Optional: browser notification if tab is not focused
  if (document.hidden && 'Notification' in window && Notification.permission === 'granted') {
    new Notification('Hecos — Promemoria', { body: title, icon: '/static/images/hecos_light.png' });
  }
}

function _escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

document.addEventListener('DOMContentLoaded', () => {
    window.initEvents();
});
