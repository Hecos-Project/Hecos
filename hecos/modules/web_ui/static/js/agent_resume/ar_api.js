/**
 * MODULE: agent_resume/ar_api.js
 * PURPOSE: HTTP & SSE streaming bridge for Agent Checkpoint recovery.
 */

(function () {
  const ns = (window._HecosAgentResume = window._HecosAgentResume || {});

  function _resolveSessionId(explicitSid) {
    return (
      explicitSid ||
      window.chatHistoryState?.activeSessionId ||
      localStorage.getItem('hecos_active_session_id') ||
      ''
    );
  }

  async function fetchCheckpoint(explicitSid = '') {
    const sid = _resolveSessionId(explicitSid);
    const qs = sid ? `?session_id=${encodeURIComponent(sid)}` : '';
    const resp = await fetch(`/api/agent/checkpoints${qs}`);
    if (!resp.ok) return null;
    return await resp.json();
  }

  async function dismissCheckpoint(explicitSid = '') {
    const sid = _resolveSessionId(explicitSid);
    if (!sid) return { ok: false };
    const resp = await fetch('/api/agent/checkpoints/dismiss', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sid }),
    });
    return await resp.json();
  }

  async function resumeCheckpoint(explicitSid = '') {
    const sid = _resolveSessionId(explicitSid);
    if (!sid || window.isStreaming) return null;

    const resp = await fetch('/api/agent/checkpoints/resume', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sid, tab_id: window.hecosTabId || '' }),
    });
    const data = await resp.json();
    if (!resp.ok || !data.ok) {
      throw new Error(data.error || `HTTP ${resp.status}`);
    }

    if (typeof window.hideWelcome === 'function') window.hideWelcome();
    window.chatHistory = window.chatHistory || [];
    window.chatHistory.push({ role: 'assistant', content: '' });

    const { bubble: aiBubble } = window.addBubble('ai', '', 'ai-' + Date.now(), {
      persona_name: window.HecosPersonaName || null,
    });
    const cursor = document.createElement('span');
    cursor.className = 'cursor';
    aiBubble.appendChild(cursor);

    if (window.HecosChatStatus) {
      window.HecosChatStatus.markStreamStart(sid, { personaName: window.HecosPersonaName || null });
    } else {
      if (window.sendBtn) window.sendBtn.disabled = true;
      window.isStreaming = true;
      window.updateStopAllBtn?.();
    }

    const evtSrc = new EventSource(`/api/stream/${encodeURIComponent(sid)}`);
    if (typeof window._attachChatStreamListeners === 'function') {
      window._attachChatStreamListeners({ evtSrc, sessionId: sid, aiBubble, cursor });
    }
    return data;
  }

  ns.api = {
    resolveSessionId: _resolveSessionId,
    fetchCheckpoint,
    dismissCheckpoint,
    resumeCheckpoint,
  };
})();
