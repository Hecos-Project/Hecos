/**
 * agent_traces.js
 * ─────────────────────────────────────────────────────────────────────────────
 * Hecos AgentTraceUI (Phase 2)
 * Renders live, gear-free status indicators and expandable multi-step timelines
 * inside AI message cards, with full support for automatic tool descriptions,
 * live package substeps, inline Action Console logs, and history restoration.
 * ─────────────────────────────────────────────────────────────────────────────
 */

class AgentTraceUI {
  constructor() {
    this.activeCard = null;
    this.stepsMap = new Map();
    this.stepsOrder = [];
    this.turnStartMs = 0;
    this.timerInterval = null;
    this.turnMeta = {
      trace_mode: 'detailed',
      trace_after_done: 'summary',
      trace_show_args: true,
      action_console_mode: 'inline',
    };
  }

  _getConfig() {
    const a = (window.cfg && window.cfg.agent) ? window.cfg.agent : {};
    return {
      trace_mode: a.trace_mode || (a.verbose_traces === false ? 'off' : 'detailed'),
      trace_after_done: a.trace_after_done || 'summary',
      trace_show_args: a.trace_show_args !== undefined ? a.trace_show_args : true,
      action_console_mode: a.action_console_mode || (a.action_console_enabled === false ? 'off' : 'inline'),
    };
  }

  _isItalian() {
    const lang = (document.documentElement && document.documentElement.lang) || (window.cfg && window.cfg.language) || 'it';
    return String(lang).toLowerCase().startsWith('it');
  }

  _formatMs(ms) {
    const n = Math.max(0, Number(ms) || 0);
    if (n < 1000) return `${Math.round(n)}ms`;
    return `${(n / 1000).toFixed(1)}s`;
  }

  _ensureCard(anchorEl) {
    if (this.activeCard && document.body.contains(this.activeCard)) {
      return this.activeCard;
    }

    const chatArea = document.getElementById('chat-area');
    if (!chatArea) return null;

    this.stepsMap.clear();
    this.stepsOrder = [];
    this.turnStartMs = performance.now();
    this.turnMeta = this._getConfig();

    const card = document.createElement('div');
    card.className = 'agent-trace-card level-info';
    if (this.turnMeta.trace_mode === 'minimal') {
      card.classList.add('minimal-mode');
    }

    card.innerHTML = `
      <div class="agent-trace-header" title="${this._isItalian() ? 'Clicca per mostrare/nascondere i passaggi' : 'Click to toggle step timeline'}">
        <div class="agent-trace-left">
          <span class="agent-trace-indicator"><span class="agent-trace-dot"></span></span>
          <i class="fas fa-brain agent-trace-step-icon"></i>
          <div class="agent-trace-title-wrap">
            <span class="agent-trace-title"></span>
            <span class="agent-trace-live-sub"></span>
          </div>
        </div>
        <div class="agent-trace-right">
          <span class="agent-trace-count-badge" style="display:none;"></span>
          <span class="agent-trace-timer">0.0s</span>
          <i class="fas fa-chevron-down agent-trace-chevron"></i>
        </div>
      </div>
      <div class="agent-trace-timeline"></div>
    `;

    const header = card.querySelector('.agent-trace-header');
    header.onclick = (e) => {
      e.stopPropagation();
      if (card.classList.contains('minimal-mode')) return;
      card.classList.toggle('expanded');
    };

    // Place INSIDE .msg.ai .msg-content-wrapper right before .msg-bubble
    // so it aligns with any avatar size and is deleted/regenerated with the message (Fixes B7)
    let inserted = false;
    if (anchorEl) {
      const msgEl = anchorEl.classList && anchorEl.classList.contains('msg')
        ? anchorEl
        : (anchorEl.closest ? anchorEl.closest('.msg') : null);
      if (msgEl) {
        const wrapper = msgEl.querySelector('.msg-content-wrapper');
        const bubble = msgEl.querySelector('.msg-bubble');
        if (wrapper && bubble) {
          wrapper.insertBefore(card, bubble);
          inserted = true;
        } else if (wrapper) {
          wrapper.appendChild(card);
          inserted = true;
        }
      }
    }

    if (!inserted) {
      // Fallback: find the latest .msg.ai in #chat-area
      const aiMsgs = chatArea.querySelectorAll('.msg.ai');
      const lastAi = aiMsgs.length ? aiMsgs[aiMsgs.length - 1] : null;
      if (lastAi) {
        const wrapper = lastAi.querySelector('.msg-content-wrapper');
        const bubble = lastAi.querySelector('.msg-bubble');
        if (wrapper && bubble) {
          wrapper.insertBefore(card, bubble);
          inserted = true;
        }
      }
    }

    if (!inserted) {
      chatArea.appendChild(card);
    }

    this.activeCard = card;
    this._startLiveTimer();
    return card;
  }

  _startLiveTimer() {
    this._stopLiveTimer();
    this.timerInterval = setInterval(() => {
      if (!this.activeCard || !document.body.contains(this.activeCard)) {
        this._stopLiveTimer();
        return;
      }
      const timerEl = this.activeCard.querySelector('.agent-trace-timer');
      if (timerEl) {
        const elapsed = performance.now() - this.turnStartMs;
        timerEl.textContent = `${(elapsed / 1000).toFixed(1)}s`;
      }
    }, 100);
  }

  _stopLiveTimer() {
    if (this.timerInterval) {
      clearInterval(this.timerInterval);
      this.timerInterval = null;
    }
  }

  handleEvent(ev, anchorEl) {
    const payload = (ev && ev.data && typeof ev.data === 'object' && !ev.step && !ev.message) ? ev.data : ev;
    if (!payload) return;

    if (payload.turn && typeof payload.turn === 'object') {
      this.turnMeta = Object.assign({}, this._getConfig(), payload.turn);
    } else {
      this.turnMeta = this._getConfig();
    }

    if (this.turnMeta.trace_mode === 'off') return;

    // Ignore passive/observer events when not streaming and no active card exists
    if (!window.isStreaming && !this.activeCard) return;

    const msg = payload.message || (payload.data ? payload.data.message : '') || '';
    const level = payload.level || (payload.data ? payload.data.level : 'info') || 'info';
    const stepObj = payload.step || (payload.data ? payload.data.step : null);

    if (!msg && !stepObj) return;

    const card = this._ensureCard(anchorEl);
    if (!card) return;

    if (this.turnMeta.trace_mode === 'minimal') {
      card.classList.add('minimal-mode');
    } else {
      card.classList.remove('minimal-mode');
    }

    // Update card border level class
    card.classList.remove('level-info', 'level-tool', 'level-vision', 'level-error');
    if (stepObj && stepObj.kind === 'vision') {
      card.classList.add('level-vision');
    } else if (level === 'error' || (stepObj && stepObj.status === 'error')) {
      card.classList.add('level-error');
      card.classList.add('has-error');
    } else if (level === 'tool' || (stepObj && (stepObj.kind === 'tool' || stepObj.kind === 'command'))) {
      card.classList.add('level-tool');
    } else {
      card.classList.add('level-info');
    }

    // Store / update structured step
    if (stepObj && stepObj.id) {
      if (!this.stepsMap.has(stepObj.id)) {
        this.stepsOrder.push(stepObj.id);
      }
      this.stepsMap.set(stepObj.id, stepObj);
    } else if (msg) {
      const synthId = `legacy_${this.stepsOrder.length || 1}`;
      if (!this.stepsMap.has(synthId)) {
        this.stepsOrder.push(synthId);
      }
      this.stepsMap.set(synthId, {
        id: synthId,
        kind: level === 'tool' ? 'tool' : 'llm',
        level: level,
        label: msg,
        detail: '',
        args_preview: '',
        result_preview: '',
        icon: level === 'tool' ? 'fa-wrench' : (level === 'error' ? 'fa-circle-exclamation' : 'fa-brain'),
        status: level === 'error' ? 'error' : 'running',
        duration_ms: 0,
        substeps: [],
        actions: [],
      });
    }

    // Update live header
    const activeStep = stepObj || this.stepsMap.get(this.stepsOrder[this.stepsOrder.length - 1]);
    const titleEl = card.querySelector('.agent-trace-title');
    const subEl = card.querySelector('.agent-trace-live-sub');
    const stepIconEl = card.querySelector('.agent-trace-step-icon');
    const countBadge = card.querySelector('.agent-trace-count-badge');

    if (activeStep) {
      if (titleEl) titleEl.textContent = activeStep.label || msg;
      if (subEl) {
        const subText = activeStep.detail || activeStep.args_preview || activeStep.result_preview || '';
        subEl.textContent = subText ? `· ${subText}` : '';
      }
      if (stepIconEl && activeStep.icon) {
        stepIconEl.className = `fas ${activeStep.icon} agent-trace-step-icon`;
      }
    } else if (titleEl) {
      titleEl.textContent = msg;
    }

    if (countBadge) {
      const total = this.stepsOrder.length;
      if (total > 1) {
        countBadge.style.display = 'inline-block';
        countBadge.textContent = this._isItalian() ? `Step ${total}` : `Step ${total}`;
      } else {
        countBadge.style.display = 'none';
      }
    }

    // Re-render timeline steps
    if (this.turnMeta.trace_mode !== 'minimal') {
      this._renderTimeline(card);
    }
  }

  _renderTimeline(card, stepsListOverride = null, showArgsOverride = null) {
    const timelineEl = card.querySelector('.agent-trace-timeline');
    if (!timelineEl) return;

    const steps = stepsListOverride || this.stepsOrder.map(id => this.stepsMap.get(id)).filter(Boolean);
    const showArgs = showArgsOverride !== null ? showArgsOverride : (this.turnMeta.trace_show_args !== false);

    timelineEl.innerHTML = '';

    steps.forEach(s => {
      const row = document.createElement('div');
      const status = s.status || 'ok';
      const kind = s.kind || 'llm';
      row.className = `agent-trace-step kind-${kind} status-${status}`;

      const iconClass = status === 'error'
        ? 'fa-xmark'
        : (s.icon || (kind === 'tool' ? 'fa-wrench' : 'fa-check'));

      const durText = s.duration_ms ? this._formatMs(s.duration_ms) : '';
      const argsHtml = (showArgs && s.args_preview)
        ? `<span class="step-args-pill" title="${this._esc(s.args_preview)}">${this._esc(s.args_preview)}</span>`
        : '';

      const outcomeText = s.result_preview || s.detail || '';
      const outcomeHtml = outcomeText
        ? `<div class="step-result">${this._esc(outcomeText)}</div>`
        : '';

      let substepsHtml = '';
      if (Array.isArray(s.substeps) && s.substeps.length > 1) {
        const items = s.substeps.map(sub => `<div>› ${this._esc(sub)}</div>`).join('');
        substepsHtml = `<div class="step-substeps">${items}</div>`;
      }

      let actionsHtml = '';
      if (Array.isArray(s.actions) && s.actions.length > 0) {
        actionsHtml = s.actions.map(act => `
          <div class="step-action-console">
            <div class="step-action-cmd">$ [${this._esc(act.tool_name || 'ACTION')}] ${this._esc(act.command || '')}</div>
            ${act.output ? `<div class="step-action-out">${this._esc(act.output)}</div>` : ''}
          </div>
        `).join('');
      }

      row.innerHTML = `
        <span class="step-node-icon"><i class="fas ${this._esc(iconClass)}"></i></span>
        <div class="step-main">
          <div class="step-top-row">
            <div class="step-title-group">
              <span class="step-label">${this._esc(s.label || '')}</span>
              ${argsHtml}
            </div>
            <span class="step-dur">${durText}</span>
          </div>
          ${outcomeHtml}
          ${substepsHtml}
          ${actionsHtml}
        </div>
      `;

      timelineEl.appendChild(row);
    });
  }

  _buildSummaryTitle(steps, toolsUsed, hasError) {
    const isIt = this._isItalian();
    const count = steps.length;
    if (hasError) {
      return isIt
        ? `Completato con avvisi · ${count} ${count === 1 ? 'passaggio' : 'passaggi'}`
        : `Completed with warnings · ${count} ${count === 1 ? 'step' : 'steps'}`;
    }
    if (toolsUsed && toolsUsed.length > 0) {
      const toolsStr = toolsUsed.slice(0, 3).join(', ') + (toolsUsed.length > 3 ? ` +${toolsUsed.length - 3}` : '');
      return isIt
        ? `${count} ${count === 1 ? 'passaggio' : 'passaggi'} · ${toolsStr}`
        : `${count} ${count === 1 ? 'step' : 'steps'} · ${toolsStr}`;
    }
    if (count <= 1) {
      return isIt ? 'Elaborazione completata' : 'Processing completed';
    }
    return isIt ? `${count} passaggi completati` : `${count} steps completed`;
  }

  finalize(summaryOverride = null) {
    this._stopLiveTimer();
    const card = this.activeCard;
    if (!card) return;
    this.activeCard = null;

    const cfg = Object.assign({}, this._getConfig(), this.turnMeta);
    const afterDone = (summaryOverride && summaryOverride.trace_after_done) || cfg.trace_after_done || 'summary';

    if (afterDone === 'hide' || cfg.trace_mode === 'minimal') {
      card.classList.add('trace-hiding');
      setTimeout(() => {
        if (card.parentNode) card.remove();
      }, 380);
      return;
    }

    // Mark any remaining running steps as ok
    let steps = [];
    if (summaryOverride && Array.isArray(summaryOverride.steps) && summaryOverride.steps.length > 0) {
      steps = summaryOverride.steps;
    } else {
      steps = this.stepsOrder.map(id => {
        const s = this.stepsMap.get(id);
        if (s && s.status === 'running') s.status = 'ok';
        return s;
      }).filter(Boolean);
    }

    const hasError = (summaryOverride && summaryOverride.status === 'error')
      || card.classList.contains('has-error')
      || steps.some(s => s.status === 'error');

    const toolsUsed = (summaryOverride && Array.isArray(summaryOverride.tools_used))
      ? summaryOverride.tools_used
      : Array.from(new Set(
          steps
            .filter(s => s.kind === 'tool' || s.kind === 'command')
            .map(s => s.module_name || (s.label ? s.label.split('·')[0].trim() : ''))
            .filter(Boolean)
        ));

    const totalMs = (summaryOverride && summaryOverride.duration_ms)
      ? summaryOverride.duration_ms
      : Math.max(0, performance.now() - this.turnStartMs);

    card.classList.remove('level-info', 'level-tool', 'level-vision');
    card.classList.add('finished');
    if (hasError) card.classList.add('has-error');

    const indicatorEl = card.querySelector('.agent-trace-indicator');
    if (indicatorEl) {
      indicatorEl.innerHTML = hasError
        ? '<i class="fas fa-circle-exclamation agent-trace-done-icon"></i>'
        : '<i class="fas fa-check agent-trace-done-icon"></i>';
    }

    const stepIconEl = card.querySelector('.agent-trace-step-icon');
    if (stepIconEl) {
      stepIconEl.style.display = 'none';
    }

    const titleEl = card.querySelector('.agent-trace-title');
    if (titleEl) {
      titleEl.textContent = this._buildSummaryTitle(steps, toolsUsed, hasError);
    }

    const subEl = card.querySelector('.agent-trace-live-sub');
    if (subEl) {
      subEl.textContent = '';
    }

    const countBadge = card.querySelector('.agent-trace-count-badge');
    if (countBadge) {
      countBadge.style.display = 'none';
    }

    const timerEl = card.querySelector('.agent-trace-timer');
    if (timerEl) {
      timerEl.textContent = this._formatMs(totalMs);
    }

    this._renderTimeline(card, steps, cfg.trace_show_args !== false);

    if (afterDone === 'expanded') {
      card.classList.add('expanded');
    } else {
      card.classList.remove('expanded');
    }
  }

  /**
   * Renders a finalized trace timeline inside a historical message bubble
   * when restoring chat sessions from SQLite DB.
   */
  renderHistoricalTrace(traceSummary, msgEl) {
    if (!traceSummary || !Array.isArray(traceSummary.steps) || traceSummary.steps.length === 0) return;
    if (!msgEl) return;

    const cfg = this._getConfig();
    if (cfg.trace_mode === 'off' || cfg.trace_mode === 'minimal' || cfg.trace_after_done === 'hide') {
      return;
    }

    // Avoid duplicating if already present
    if (msgEl.querySelector('.agent-trace-card')) return;

    const wrapper = msgEl.querySelector('.msg-content-wrapper');
    const bubble = msgEl.querySelector('.msg-bubble');
    if (!wrapper) return;

    const hasError = traceSummary.status === 'error' || traceSummary.steps.some(s => s.status === 'error');
    const toolsUsed = Array.isArray(traceSummary.tools_used) ? traceSummary.tools_used : [];
    const totalMs = traceSummary.duration_ms || 0;
    const summaryTitle = this._buildSummaryTitle(traceSummary.steps, toolsUsed, hasError);

    const card = document.createElement('div');
    card.className = `agent-trace-card finished${hasError ? ' has-error' : ''}`;
    if (cfg.trace_after_done === 'expanded') {
      card.classList.add('expanded');
    }

    card.innerHTML = `
      <div class="agent-trace-header" title="${this._isItalian() ? 'Clicca per mostrare/nascondere i passaggi' : 'Click to toggle step timeline'}">
        <div class="agent-trace-left">
          <span class="agent-trace-indicator">
            ${hasError ? '<i class="fas fa-circle-exclamation agent-trace-done-icon"></i>' : '<i class="fas fa-check agent-trace-done-icon"></i>'}
          </span>
          <div class="agent-trace-title-wrap">
            <span class="agent-trace-title">${this._esc(summaryTitle)}</span>
          </div>
        </div>
        <div class="agent-trace-right">
          <span class="agent-trace-timer">${this._formatMs(totalMs)}</span>
          <i class="fas fa-chevron-down agent-trace-chevron"></i>
        </div>
      </div>
      <div class="agent-trace-timeline"></div>
    `;

    const header = card.querySelector('.agent-trace-header');
    header.onclick = (e) => {
      e.stopPropagation();
      card.classList.toggle('expanded');
    };

    this._renderTimeline(card, traceSummary.steps, cfg.trace_show_args !== false);

    if (bubble) {
      wrapper.insertBefore(card, bubble);
    } else {
      wrapper.appendChild(card);
    }
  }

  _esc(str) {
    return String(str || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }
}

window.AgentUI = new AgentTraceUI();
