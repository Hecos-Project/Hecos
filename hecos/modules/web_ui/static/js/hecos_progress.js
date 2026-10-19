/**
 * hecos_progress.js
 * Unified Progress Bar UI component and SSE event coordinator for Hecos WebUI.
 */
(function() {
  'use strict';

  // Translation helper
  function _t(en, it, es) {
    if (typeof window._t === 'function') return window._t(en, it, es);
    const lang = (localStorage.getItem('hecos_language') || 'it').toLowerCase();
    if (lang.startsWith('it')) return it;
    if (lang.startsWith('es')) return es || it;
    return en;
  }

  function formatBytes(bytes) {
    if (!bytes || bytes <= 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  }

  function formatEta(seconds) {
    if (seconds == null || isNaN(seconds) || seconds < 0) return '';
    if (seconds === 0) return _t('Finishing…', 'Quasi finito…', 'Terminando…');
    if (seconds < 60) return `~${Math.round(seconds)}s`;
    const m = Math.floor(seconds / 60);
    const s = Math.round(seconds % 60);
    return `~${m}m ${s}s`;
  }

  // Registry of active bound widgets by task ID or container
  const _instances = new Map();

  class ProgressWidget {
    constructor(container, options = {}) {
      this.container = typeof container === 'string' ? document.getElementById(container) : container;
      this.options = Object.assign({
        variant: 'card', // 'card', 'inline', 'modal'
        taskId: null,
        title: '',
        source: 'SYSTEM',
        showCancel: true,
        showLog: true,
        onCancel: null,
        onDone: null,
      }, options);

      this.data = {
        id: this.options.taskId,
        title: this.options.title || '',
        state: 'pending',
        percent: 0,
        message: '',
        log: '',
        bytes_done: 0,
        bytes_total: 0,
        speed_bps: 0,
        eta_s: null,
        phases: [],
        phase: null,
        cancellable: this.options.showCancel
      };

      if (this.container) {
        this.render();
      }
    }

    render() {
      if (!this.container) return;

      const isInline = this.options.variant === 'inline';
      this.container.className = `hp-widget hp-widget-${this.options.variant} hp-state-${this.data.state}`;

      // Pick icon based on state
      let iconHtml = '<i class="fas fa-spinner fa-spin hp-icon"></i>';
      if (this.data.state === 'done') {
        iconHtml = '<i class="fas fa-check-circle hp-icon" style="color:var(--accent,#6366f1);"></i>';
      } else if (this.data.state === 'error') {
        iconHtml = '<i class="fas fa-times-circle hp-icon" style="color:#ef4444;"></i>';
      } else if (this.data.state === 'cancelled') {
        iconHtml = '<i class="fas fa-ban hp-icon" style="color:#f59e0b;"></i>';
      } else if (this.data.source === 'HPM' || this.data.source === 'EDM') {
        iconHtml = '<i class="fas fa-download hp-icon"></i>';
      }

      // Phases stepper html
      let phasesHtml = '';
      if (!isInline && this.data.phases && this.data.phases.length > 1) {
        const curIdx = this.data.phase ? (this.data.phase.index - 1) : 0;
        phasesHtml = `
          <div class="hp-phases-stepper">
            ${this.data.phases.map((p, idx) => {
              let cls = '';
              let symbol = idx + 1;
              if (idx < curIdx || (this.data.state === 'done')) {
                cls = 'completed';
                symbol = '✓';
              } else if (idx === curIdx && this.data.state === 'running') {
                cls = 'active';
                symbol = '●';
              }
              return `<span class="hp-phase-pill ${cls}"><b>${symbol}</b> ${p.label || p.key}</span>`;
            }).join('')}
          </div>
        `;
      }

      // Cancel button
      let cancelBtnHtml = '';
      if (this.options.showCancel && this.data.cancellable && (this.data.state === 'running' || this.data.state === 'pending')) {
        const lblCancel = _t('Cancel', 'Annulla', 'Cancelar');
        cancelBtnHtml = `
          <button type="button" class="hp-cancel-btn" title="${lblCancel}">
            <i class="fas fa-times"></i> ${lblCancel}
          </button>
        `;
      }

      // Metrics html (Bytes, Speed, ETA)
      let metricsHtml = '';
      if (!isInline) {
        let byteStr = '';
        if (this.data.bytes_total > 0) {
          byteStr = `<span>${formatBytes(this.data.bytes_done)} / ${formatBytes(this.data.bytes_total)}</span>`;
        }
        let speedStr = '';
        if (this.data.speed_bps > 0) {
          speedStr = `<span>${formatBytes(this.data.speed_bps)}/s</span>`;
        }
        let etaStr = '';
        if (this.data.eta_s != null && this.data.state === 'running') {
          etaStr = `<span>${formatEta(this.data.eta_s)}</span>`;
        }

        metricsHtml = `
          <div class="hp-meta-row">
            <div style="flex:1; min-width:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; padding-right:8px;">
              ${this.data.message || ''}
            </div>
            <div class="hp-speed-eta">
              ${byteStr}
              ${speedStr}
              ${etaStr}
            </div>
          </div>
        `;
      }

      // Secondary log row
      let logHtml = '';
      if (!isInline && this.options.showLog && this.data.log) {
        logHtml = `<div class="hp-log-line" title="${this.data.log}">› ${this.data.log}</div>`;
      }

      const pctDisplay = Math.min(100, Math.max(0, Math.round(this.data.percent || 0)));

      this.container.innerHTML = `
        <div class="hp-header">
          <div class="hp-title-wrap">
            ${iconHtml}
            <div class="hp-title">${this.data.title || this.options.title || 'In corso…'}</div>
          </div>
          <div style="display:flex; align-items:center; gap:8px;">
            ${cancelBtnHtml}
            <div class="hp-pct">${pctDisplay}%</div>
          </div>
        </div>

        ${phasesHtml}

        <div class="hp-track">
          <div class="hp-fill" style="width: ${pctDisplay}%;"></div>
        </div>

        ${metricsHtml}
        ${logHtml}
      `;

      // Attach cancel click handler
      const cancelBtn = this.container.querySelector('.hp-cancel-btn');
      if (cancelBtn) {
        cancelBtn.onclick = (e) => {
          e.preventDefault();
          e.stopPropagation();
          cancelBtn.disabled = true;
          cancelBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> ' + _t('Cancelling…', 'Annullamento…', 'Cancelando…');
          if (this.options.onCancel) {
            this.options.onCancel(this.data.id);
          } else if (this.data.id) {
            window.HecosProgress.cancel(this.data.id);
          }
        };
      }
    }

    update(payload) {
      if (!payload) return;
      Object.assign(this.data, payload);
      this.render();

      if (this.data.state === 'done' && typeof this.options.onDone === 'function') {
        this.options.onDone(this.data);
      }
    }
  }

  // ── Global API ─────────────────────────────────────────────────────────────
  window.HecosProgress = {
    attach(container, options = {}) {
      const widget = new ProgressWidget(container, options);
      if (options.taskId) {
        _instances.set(options.taskId, widget);
      }
      return widget;
    },

    createModal(options = {}) {
      // Remove any existing backdrop
      const old = document.getElementById('hecos-progress-modal-backdrop');
      if (old) old.remove();

      const backdrop = document.createElement('div');
      backdrop.id = 'hecos-progress-modal-backdrop';
      backdrop.className = 'hp-modal-backdrop';

      const content = document.createElement('div');
      content.className = 'hp-modal-content';
      backdrop.appendChild(content);

      document.body.appendChild(backdrop);

      const modalWidget = new ProgressWidget(content, Object.assign({}, options, { variant: 'card' }));
      if (options.taskId) {
        _instances.set(options.taskId, modalWidget);
      }

      modalWidget.close = function() {
        backdrop.style.opacity = '0';
        backdrop.style.transition = 'opacity 0.2s ease';
        setTimeout(() => backdrop.remove(), 200);
      };

      // Double click to dismiss
      backdrop.ondblclick = function(e) {
        if (e.target === backdrop) modalWidget.close();
      };

      return modalWidget;
    },

    cancel(taskId) {
      if (!taskId) return;
      return fetch(`/api/progress/${encodeURIComponent(taskId)}/cancel`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason: _t("Cancelled by user", "Annullato dall'utente", "Cancelado por el usuario") })
      }).then(r => r.json()).catch(err => {
        console.warn('[HecosProgress] Cancel error:', err);
      });
    },

    handleSSE(eventData) {
      if (!eventData || !eventData.id) return;
      const widget = _instances.get(eventData.id);
      if (widget) {
        widget.update(eventData);
      }
      // Also broadcast DOM event for arbitrary page listeners
      document.dispatchEvent(new CustomEvent('hecos:progress', { detail: eventData }));
    }
  };

  // Wire SSE Handler into Hecos central SSE bus
  window._hecosSSEHandlers = window._hecosSSEHandlers || {};
  window._hecosSSEHandlers['progress'] = function(ev) {
    const payload = ev.data || ev;
    window.HecosProgress.handleSSE(payload);
  };
})();
