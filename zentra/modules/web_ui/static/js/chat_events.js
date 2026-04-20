/**
 * chat_events.js
 * Handles backend notification streams (/api/events)
 */

window.initEvents = function() {
  const evtSrc = new EventSource('/api/events');
  evtSrc.onmessage = (e) => {
    const ev = JSON.parse(e.data);
    
    // Support dynamic handlers from plugins (like remote_triggers.js)
    if (window._zentraSSEHandlers && window._zentraSSEHandlers[ev.type]) {
        window._zentraSSEHandlers[ev.type](ev);
        return;
    }
    
    if (ev.type === 'agent_trace') {
      if (window.AgentUI) window.AgentUI.handleEvent(ev);
      
    } else if (ev.type === 'ptt_status') {
      const pttInd = document.getElementById('ptt-indicator');
      if (ev.active) {
          if (pttInd) pttInd.classList.add('active');
          if (window._webptt_beep) window._webptt_beep(880, 0.08); // High tone for START
      } else {
          if (pttInd) pttInd.classList.remove('active');
          if (window._webptt_beep) window._webptt_beep(440, 0.12); // Low tone for END
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
      const targetBubble = document.querySelector('.msg.ai:last-child .msg-bubble');
      if (targetBubble && window.tryLoadAudio) {
        window.tryLoadAudio(targetBubble);
      }
    }
  };
};

document.addEventListener('DOMContentLoaded', () => {
    window.initEvents();
});
