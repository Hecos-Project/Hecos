/**
 * AgentTraceUI
 * Subsystem per il rendering visuale dei Loop Agentici (Chain of Thought).
 * Inietta dinamicamente CSS e gestisce il ciclo di vita della "Nuvoletta di Pensiero".
 */

class AgentTraceUI {
  constructor() {
    this.activeBubble = null;
    this.activeCursor = null;
    this._injectStyles();
  }

  _injectStyles() {
    if (document.getElementById('agent-trace-styles')) return;
    const style = document.createElement('style');
    style.id = 'agent-trace-styles';
    style.textContent = `
      @keyframes spin-gear { 100% { transform: rotate(360deg); } }
      @keyframes pulse-trace { 0%, 100% { opacity: 1; } 50% { opacity: 0.6; } }
      
      .agent-trace-wrap {
        margin: 4px 0 12px 54px;
        padding: 6px 12px;
        background: var(--glass-b);
        border-left: 3px solid var(--accent);
        border-radius: 4px;
        color: var(--muted);
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.85em;
        display: inline-flex;
        align-items: center;
        gap: 8px;
        transition: all 0.3s ease;
        max-width: 80%;
      }
      
      .agent-trace-wrap.level-tool { border-left-color: #e5c07b; color: #e5c07b; }
      .agent-trace-wrap.level-error { border-left-color: var(--red); color: var(--red); }
      .agent-trace-wrap.level-success { border-left-color: var(--green); color: var(--green); }
      
      .agent-trace-wrap.finished {
        opacity: 0.6;
        border-left-color: #555 !important;
        color: #888 !important;
      }
      
      .agent-spinner {
        display: inline-block;
        animation: spin-gear 2s linear infinite;
        font-size: 1.1em;
      }
      .agent-trace-wrap.finished .agent-spinner { animation: none; opacity: 0.5; }
      
      .agent-trace-text {
        animation: pulse-trace 2s infinite ease-in-out;
      }
      .agent-trace-wrap.finished .agent-trace-text { animation: none; }
    `;
    document.head.appendChild(style);
  }

  handleEvent(ev, anchorEl) {
    const chatArea = document.getElementById('chat-area');
    if (!chatArea) return;

    // Support flat dictionary or nested 'data' dict
    const msg = ev.message || (ev.data ? ev.data.message : '') || '';
    const level = ev.level || (ev.data ? ev.data.level : 'info');

    if (!msg) return;

    if (!this.activeBubble) {
      const wrap = document.createElement('div');
      wrap.className = `agent-trace-wrap level-${level}`;
      
      const icon = document.createElement('div');
      icon.className = 'agent-spinner';
      icon.innerHTML = '⚙️';
      
      const textNode = document.createElement('span');
      textNode.className = 'agent-trace-text';
      textNode.textContent = msg;
      
      this.activeCursor = document.createElement('span');
      this.activeCursor.className = 'cursor';
      this.activeCursor.style.cssText = 'animation: blink 1s step-end infinite; border-right: 2px solid var(--accent); margin-left: 2px;';
      
      wrap.appendChild(icon);
      wrap.appendChild(textNode);
      wrap.appendChild(this.activeCursor);
      
      this.activeBubble = wrap;
      
      // If anchorEl (the AI bubble .msg wrapper) is provided, insert BEFORE it.
      // This ensures the trace appears between the user message and the AI response.
      // Fallback: insert before the last child or append.
      if (anchorEl && anchorEl.parentNode === chatArea) {
        chatArea.insertBefore(wrap, anchorEl);
      } else {
        // Legacy fallback: find the last user msg
        const allUserMsgs = chatArea.querySelectorAll('.msg.user');
        const lastUserMsg = allUserMsgs.length ? allUserMsgs[allUserMsgs.length - 1] : null;
        if (lastUserMsg && lastUserMsg.nextSibling) {
          chatArea.insertBefore(wrap, lastUserMsg.nextSibling);
        } else {
          chatArea.appendChild(wrap);
        }
      }
      chatArea.scrollTop = chatArea.scrollHeight;
      
    } else {
      // Update existing bubble text and level
      this.activeBubble.className = `agent-trace-wrap level-${level}`;
      const textNode = this.activeBubble.querySelector('.agent-trace-text');
      if (textNode) {
        textNode.textContent = msg;
      }
    }
  }

  finalize() {
    if (this.activeBubble) {
      this.activeBubble.classList.add('finished');
      if (this.activeCursor) this.activeCursor.remove();
      this.activeBubble = null;
      this.activeCursor = null;
    }
  }
}

// Instantiate globally
window.AgentUI = new AgentTraceUI();
