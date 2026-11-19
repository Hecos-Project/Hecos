/**
 * MODULE: action_plans_chat/apc_widget.js
 * PURPOSE: Render live collapsible Action Plan checklist card in #agent-plan-slot,
 *          with a single primary action button ("Execute Plan" / "Continue Plan")
 *          and a labeled "Run with Coder" preset dropdown synchronized with session state.
 */

(function () {
  const ns = (window._HecosActionPlanChat = window._HecosActionPlanChat || {});
  const UI_STATE_KEY = 'hecos_action_plan_ui_state';
  const MIN_STEPS_HEIGHT = 48;
  const DEFAULT_ROWS = 5;

  const DISMISSED_PLANS_KEY = 'hecos_ap_dismissed_ids';
  let _collapsed = false;
  let _lastPlan = null;
  let _prevPlanStatus = '';
  let _lastHandlers = null;
  let _launchingPlanId = '';
  let _launchingMode = 'execute';
  let _reviseOpen = false;
  let _modalOpen = false;
  let _modalEditMode = false;
  let _escBound = false;
  let _stepsResizeObserver = null;
  let _isDraggingResize = false;

  function _readDismissedIds() {
    try {
      const raw = JSON.parse(sessionStorage.getItem(DISMISSED_PLANS_KEY) || '[]');
      return Array.isArray(raw) ? raw.map((x) => String(x)) : [];
    } catch (_) {
      return [];
    }
  }

  function isPlanDismissed(planId) {
    const clean = String(planId || '').trim();
    return Boolean(clean && _readDismissedIds().includes(clean));
  }

  function setPlanDismissed(planId, dismissed = true) {
    const clean = String(planId || '').trim();
    if (!clean) return;
    let cur = _readDismissedIds();
    if (dismissed) {
      if (!cur.includes(clean)) cur.push(clean);
      cur = cur.slice(-30);
    } else {
      cur = cur.filter((id) => id !== clean);
    }
    try {
      sessionStorage.setItem(DISMISSED_PLANS_KEY, JSON.stringify(cur));
    } catch (_) {}
  }

  function _clampRows(val) {
    const n = parseInt(val, 10);
    if (!Number.isFinite(n)) return DEFAULT_ROWS;
    return Math.max(1, Math.min(50, n));
  }

  function _maxStepsHeightPx() {
    const vh = Number(window.innerHeight) || 900;
    return Math.max(260, Math.round(vh * 0.70));
  }

  function _clampHeightPx(px) {
    const n = Math.round(Number(px) || 0);
    if (!Number.isFinite(n) || n <= 0) return 0;
    return Math.max(MIN_STEPS_HEIGHT, Math.min(_maxStepsHeightPx(), n));
  }

  function _loadUiState() {
    let raw = {};
    try {
      raw = JSON.parse(localStorage.getItem(UI_STATE_KEY) || '{}') || {};
    } catch (_) {
      raw = {};
    }
    const save = Boolean(raw.save);
    const rows = _clampRows(raw.rows !== undefined ? raw.rows : DEFAULT_ROWS);
    const height = save ? _clampHeightPx(raw.height) : 0;
    return { save, rows, height };
  }

  let _uiState = _loadUiState();
  let _sessionHeightPx = _uiState.save ? _uiState.height : 0;

  function _getDetachMode() {
    return (ns.detach && typeof ns.detach.getMode === 'function') ? ns.detach.getMode() : 'docked';
  }

  function _getCardRoot() {
    if (_getDetachMode() === 'floating') {
      const host = document.getElementById('ap-floating-host');
      if (host) return host;
    }
    return document.getElementById('agent-plan-slot');
  }

  function _saveUiState() {
    let prev = {};
    try {
      prev = JSON.parse(localStorage.getItem(UI_STATE_KEY) || '{}') || {};
    } catch (_) {
      prev = {};
    }
    const payload = {
      save: Boolean(_uiState.save),
      rows: _clampRows(_uiState.rows),
      height: _uiState.save ? _clampHeightPx(_sessionHeightPx) : 0,
    };
    if (payload.save && prev.floatRect && typeof prev.floatRect === 'object') {
      payload.floatRect = prev.floatRect;
    }
    _uiState = payload;
    try {
      localStorage.setItem(UI_STATE_KEY, JSON.stringify(payload));
    } catch (_) {
      // Ignore storage quota / privacy mode errors
    }
    if (payload.save && ns.detach && typeof ns.detach.saveCurrentFloatRect === 'function') {
      ns.detach.saveCurrentFloatRect();
    }
  }

  function _disconnectStepsObserver() {
    if (_stepsResizeObserver) {
      try { _stepsResizeObserver.disconnect(); } catch (_) {}
      _stepsResizeObserver = null;
    }
  }

  function _applyStepsHeightPx(px, persist = true) {
    const root = _getCardRoot();
    const stepsEl = root ? root.querySelector('.agent-plan-steps') : null;
    const clamped = _clampHeightPx(px);
    if (!clamped) return 0;
    _sessionHeightPx = clamped;
    if (stepsEl) {
      stepsEl.classList.add('is-sized');
      stepsEl.style.height = `${clamped}px`;
    }
    if (persist) _saveUiState();
    return clamped;
  }

  function _ensureExpanded() {
    if (!_collapsed) return;
    _collapsed = false;
    const root = _getCardRoot();
    if (!root) return;
    const card = root.querySelector('#agent-plan-active-card');
    if (card) card.classList.remove('is-collapsed');
    const chev = root.querySelector('#ap-chat-chevron');
    if (chev) {
      chev.classList.remove('fa-chevron-right');
      chev.classList.add('fa-chevron-down');
    }
  }

  function adaptStepsHeight(explicitRows) {
    const root = _getCardRoot();
    if (!root) return 0;
    _ensureExpanded();
    const stepsEl = root.querySelector('.agent-plan-steps');
    const rowsInput = root.querySelector('#ap-chat-max-rows');
    const targetRows = _clampRows(
      explicitRows !== undefined
        ? explicitRows
        : (rowsInput ? rowsInput.value : _uiState.rows)
    );
    _uiState.rows = targetRows;
    if (rowsInput && String(rowsInput.value) !== String(targetRows)) {
      rowsInput.value = String(targetRows);
    }

    let targetPx = 0;
    if (stepsEl) {
      const stepEls = Array.from(stepsEl.querySelectorAll('.agent-plan-step'));
      const count = Math.min(targetRows, stepEls.length);
      if (count > 0) {
        let sum = 0;
        for (let i = 0; i < count; i++) {
          sum += stepEls[i].offsetHeight || 0;
        }
        if (sum > 0) {
          // 4px flex gap between items + 10px breathing room/padding
          targetPx = sum + Math.max(0, count - 1) * 4 + 10;
        }
      }
    }
    if (!targetPx) {
      targetPx = targetRows * 34 + 10;
    }
    return _applyStepsHeightPx(targetPx, true);
  }

  function fitAllSteps() {
    const root = _getCardRoot();
    if (!root) return 0;
    _ensureExpanded();
    const stepsEl = root.querySelector('.agent-plan-steps');
    if (!stepsEl) return 0;
    const stepCount = stepsEl.querySelectorAll('.agent-plan-step').length;
    if (!stepCount) return 0;
    let sum = 0;
    stepsEl.querySelectorAll('.agent-plan-step').forEach((el) => {
      sum += el.offsetHeight || 0;
    });
    const targetPx = sum > 0 ? (sum + Math.max(0, stepCount - 1) * 4 + 10) : (stepCount * 34 + 10);
    return _applyStepsHeightPx(targetPx, true);
  }

  function _tr(key, fallbackEn) {
    const val = (window.I18N && window.I18N[key]) || (typeof window.t === 'function' ? window.t(key) : '');
    return (val && val !== key) ? val : fallbackEn;
  }

  function _esc(s) {
    return String(s ?? '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function _stepIcon(st) {
    if (st === 'done') return '<span style="color:#10b981;">✓</span>';
    if (st === 'running') return '<i class="fas fa-circle-notch fa-spin" style="color:#38bdf8;"></i>';
    if (st === 'failed') return '<span style="color:#ef4444;">✗</span>';
    if (st === 'skipped') return '<span style="color:#94a3b8;">−</span>';
    return '<span style="color:#64748b;">○</span>';
  }

  function _statusLabel(st, planMode) {
    const low = String(st || '').toLowerCase();
    if (low === 'awaiting_approval' && String(planMode || '').toLowerCase() === 'plan_only') {
      return _tr('ap_chat_st_ready', 'Plan Ready');
    }
    const map = {
      awaiting_approval: _tr('ap_chat_st_awaiting', 'Awaiting Approval'),
      running: _tr('ap_chat_st_running', 'Active Plan'),
      completed: _tr('ap_chat_st_completed', 'Completed'),
      interrupted: _tr('ap_chat_st_interrupted', 'Interrupted'),
      paused: _tr('ap_chat_st_paused', 'Paused'),
      failed: _tr('ap_chat_st_failed', 'Failed'),
      cancelled: _tr('ap_chat_st_cancelled', 'Cancelled'),
    };
    return map[low] || st || _tr('ap_chat_st_default', 'Plan');
  }

  function _shortModelName(rawModel) {
    const clean = String(rawModel || '').trim();
    if (!clean) return '';
    return clean.split('/').pop();
  }

  function _buildCoderPresetOptionsHtml() {
    const allSouls = Array.isArray(window.sfState?.souls) ? window.sfState.souls : [];
    const planningSouls = [];
    const coderSouls = [];
    const otherSouls = [];

    for (const s of allSouls) {
      const id = String(s?.meta?.id || '').trim();
      if (!id) continue;
      const name = String(s?.meta?.name || id).trim();
      const rawModel = String(s?.model?.model_name || '').trim();
      const shortModel = _shortModelName(rawModel);
      const tags = Array.isArray(s?.meta?.tags) ? s.meta.tags.map((t) => String(t).toLowerCase()) : [];
      const icon = String(s?.meta?.icon || '').trim();
      const isCoder = id.toLowerCase().includes('coder') || tags.includes('coding') || tags.includes('coder');
      const isPlanning = !isCoder && (
        id.toLowerCase().includes('plan') ||
        id.toLowerCase().includes('storyboard') ||
        tags.includes('planning') ||
        tags.includes('storyboard') ||
        tags.includes('image_gen')
      );
      const entry = { id, name, rawModel, shortModel, icon };
      if (isPlanning) {
        planningSouls.push(entry);
      } else if (isCoder) {
        coderSouls.push(entry);
      } else {
        otherSouls.push(entry);
      }
    }

    if (planningSouls.length === 0 && coderSouls.length === 0 && otherSouls.length === 0) {
      coderSouls.push({ id: 'hecos_coder', name: 'Hecos Coder', rawModel: '', shortModel: '', icon: '💻' });
    }

    const activeId = String(window.sfState?.activeSoulId || '').trim();
    const allIds = new Set([
      ...planningSouls.map((p) => p.id),
      ...coderSouls.map((c) => c.id),
      ...otherSouls.map((o) => o.id),
    ]);
    const selectedId = (activeId && allIds.has(activeId)) ? activeId : '';

    const fmtLabel = (item, prefix = '') =>
      `${prefix}${item.name}${item.shortModel ? ` (${item.shortModel})` : ''}`;

    const fmtFullTitle = (item, prefix = '') =>
      `${prefix}${item.name}${item.rawModel ? ` — ${item.rawModel}` : ''}`;

    const renderOpt = (item, fallbackPrefix = '') => {
      const pfx = item.icon ? `${item.icon} ` : fallbackPrefix;
      const disp = fmtLabel(item, pfx);
      const tip = fmtFullTitle(item, pfx);
      return `<option value="${_esc(item.id)}" data-display-label="${_esc(disp)}" data-full-title="${_esc(tip)}" title="${_esc(tip)}"${item.id === selectedId ? ' selected' : ''}>${_esc(disp)}</option>`;
    };

    const defaultDisp = '⚡ Current Chat Model';
    const defaultTip = '⚡ Current Chat Model — Use the active chat preset/model';
    const defaultOpt = `<option value="" data-display-label="${_esc(defaultDisp)}" data-full-title="${_esc(defaultTip)}" title="${_esc(defaultTip)}"${!selectedId ? ' selected' : ''}>${_esc(defaultDisp)}</option>`;

    let groupsHtml = '';
    if (planningSouls.length > 0) {
      groupsHtml += `<optgroup label="Planning &amp; Creative Presets">${planningSouls.map((p) => renderOpt(p, '🗺️ ')).join('')}</optgroup>`;
    }
    if (coderSouls.length > 0) {
      groupsHtml += `<optgroup label="Coder Presets">${coderSouls.map((c) => renderOpt(c, '💻 ')).join('')}</optgroup>`;
    }
    if (otherSouls.length > 0) {
      groupsHtml += `<optgroup label="Other Presets">${otherSouls.map((o) => renderOpt(o, '')).join('')}</optgroup>`;
    }

    return defaultOpt + groupsHtml;
  }

  function _syncSelectVisualDisplay() {
    const sel = document.getElementById('ap-chat-coder-preset-select');
    const disp = document.getElementById('ap-chat-coder-display');
    const wrap = document.getElementById('ap-chat-coder-select-wrap');
    if (!sel) return;
    const opt = sel.options[sel.selectedIndex] || null;
    const displayTxt = opt ? (opt.dataset?.displayLabel || opt.textContent || '').trim() : '⚡ Current Chat Model';
    const tooltipTxt = opt ? (opt.dataset?.fullTitle || opt.title || displayTxt).trim() : displayTxt;
    if (disp) disp.textContent = displayTxt;
    sel.title = tooltipTxt;
    if (wrap) wrap.title = tooltipTxt;
  }

  function syncPresetOptions() {
    const sel = document.getElementById('ap-chat-coder-preset-select');
    if (!sel) return;
    sel.innerHTML = _buildCoderPresetOptionsHtml();
    _syncSelectVisualDisplay();
  }

  function _isChatStreamingNow() {
    if (window.isStreaming) return true;
    const sid = window.chatHistoryState?.activeSessionId || '';
    if (sid && window.HecosChatStatus?.isSessionStreaming?.(sid)) return true;
    return false;
  }

  function _applyLaunchingDom(active) {
    const root = _getCardRoot();
    if (!root) return;
    const card = root.querySelector('#agent-plan-active-card');
    const approveBtn = root.querySelector('#ap-chat-approve-btn');
    const nextStepBtn = root.querySelector('#ap-chat-next-step-btn');
    const rejectBtn = root.querySelector('#ap-chat-reject-btn');
    const reviseToggle = root.querySelector('#ap-chat-revise-toggle-btn');
    const reviseSend = root.querySelector('#ap-chat-revise-send-btn');
    const coderGroup = root.querySelector('#ap-chat-coder-group');
    const coderSelect = root.querySelector('#ap-chat-coder-preset-select');
    const statusPill = root.querySelector('.agent-plan-status-pill');

    if (active) {
      if (card) card.classList.add('is-running');
      if (coderGroup) coderGroup.classList.add('is-locked');
      if (coderSelect) coderSelect.disabled = true;
      if (nextStepBtn) nextStepBtn.disabled = true;
      if (rejectBtn) rejectBtn.disabled = true;
      if (reviseToggle) reviseToggle.disabled = true;
      if (reviseSend) reviseSend.disabled = true;
      if (approveBtn) {
        approveBtn.disabled = true;
        approveBtn.classList.add('is-launching');
        const busyLbl = _launchingMode === 'revise'
          ? _esc(_tr('ap_chat_btn_revising', 'Revising...'))
          : _esc(_tr('ap_chat_btn_starting', 'Starting...'));
        approveBtn.innerHTML = `<i class="fas fa-circle-notch fa-spin"></i> ${busyLbl}`;
      }
      if (statusPill) {
        const pillLbl = _launchingMode === 'revise'
          ? _esc(_tr('ap_chat_btn_revising', 'Revising...'))
          : _esc(_statusLabel('running', _lastPlan?.plan_mode));
        statusPill.innerHTML = `<i class="fas fa-circle-notch fa-spin" aria-hidden="true"></i> ${pillLbl}`;
      }
    }
  }

  function setLaunching(planId, active, mode = 'execute') {
    _launchingPlanId = active ? String(planId || _lastPlan?.plan_id || '') : '';
    _launchingMode = active ? String(mode || 'execute') : 'execute';
    if (active) {
      _applyLaunchingDom(true);
    }
  }

  function _renderFileChip(rawFile) {
    const clean = String(rawFile || '').trim();
    if (!clean) return '';
    let kindCls = 'ap-file-neutral';
    let badge = '';
    let pathText = clean;
    const m = clean.match(/^\[(NEW|MODIFY|DELETE|RENAME|TEST)\]\s*(.*)$/i);
    if (m) {
      const tag = m[1].toUpperCase();
      pathText = m[2] || clean;
      if (tag === 'NEW') kindCls = 'ap-file-new';
      else if (tag === 'MODIFY') kindCls = 'ap-file-modify';
      else if (tag === 'DELETE') kindCls = 'ap-file-delete';
      else kindCls = 'ap-file-info';
      badge = `<span class="ap-file-tag">${_esc(tag)}</span>`;
    }
    return `<span class="ap-file-chip ${kindCls}" title="${_esc(clean)}">${badge}${_esc(pathText)}</span>`;
  }

  function _buildBlueprintMarkdown(plan) {
    if (!plan) return '';
    const existingMd = String(plan.plan_markdown || '').trim();
    if (existingMd) return existingMd;

    const parts = [`# ${plan.title || 'Implementation Plan'}`];
    if (plan.goal) {
      parts.push(`## Goal\n\n${plan.goal}`);
    }
    if (Array.isArray(plan.steps) && plan.steps.length) {
      const stepBlocks = ['## Proposed Changes & Steps'];
      plan.steps.forEach((s, idx) => {
        const lines = [`### ${Number(s.index || idx + 1)}. ${s.title || ''}`];
        if (Array.isArray(s.files) && s.files.length) {
          lines.push(`- **Files:** ${s.files.map((f) => '`' + f + '`').join(', ')}`);
        }
        if (s.details) lines.push(`- **Details:** ${s.details}`);
        if (s.notes) lines.push(`- **Notes:** *${s.notes}*`);
        stepBlocks.push(lines.join('\n'));
      });
      parts.push(stepBlocks.join('\n\n'));
    }
    if (plan.verification_plan) {
      parts.push(`## Verification Plan\n\n${plan.verification_plan}`);
    }
    return parts.join('\n\n');
  }

  function _colorizePlanBadges(html) {
    return String(html || '')
      .replace(/\[NEW\]/g, '<span class="ap-md-badge ap-md-new">NEW</span>')
      .replace(/\[MODIFY\]/g, '<span class="ap-md-badge ap-md-modify">MODIFY</span>')
      .replace(/\[DELETE\]/g, '<span class="ap-md-badge ap-md-delete">DELETE</span>')
      .replace(/\[RENAME\]/g, '<span class="ap-md-badge ap-md-info">RENAME</span>')
      .replace(/\[TEST\]/g, '<span class="ap-md-badge ap-md-test">TEST</span>');
  }

  function _renderMarkdownSafe(md) {
    const src = String(md || '');
    let html = '';
    if (typeof window.renderMarkdown === 'function') {
      html = window.renderMarkdown(src);
    } else if (window.marked && typeof window.marked.parse === 'function') {
      html = window.marked.parse(src);
    } else {
      html = `<pre style="white-space:pre-wrap;margin:0;">${_esc(src)}</pre>`;
    }
    return _colorizePlanBadges(html);
  }

  function closePlanModal() {
    _modalOpen = false;
    _modalEditMode = false;
    const modal = document.getElementById('ap-blueprint-modal');
    if (modal) modal.remove();
  }

  function _ensureEscListener() {
    if (_escBound) return;
    _escBound = true;
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && _modalOpen) {
        closePlanModal();
      }
    });
  }

  function openPlanModal(plan) {
    const target = plan || _lastPlan;
    if (!target) return;
    _ensureEscListener();
    _modalOpen = true;

    let overlay = document.getElementById('ap-blueprint-modal');
    if (!overlay) {
      overlay = document.createElement('div');
      overlay.id = 'ap-blueprint-modal';
      overlay.className = 'ap-modal-overlay';
      document.body.appendChild(overlay);
    }

    const st = String(target.status || 'running').toLowerCase();
    const rev = Number(target.revision || 1);
    const steps = Array.isArray(target.steps) ? target.steps : [];
    const doneCount = steps.filter((s) => s.status === 'done' || s.status === 'skipped').length;
    const pct = steps.length ? Math.round((doneCount / steps.length) * 100) : 0;
    const canModify = ['awaiting_approval', 'draft', 'interrupted', 'paused'].includes(st);
    const canExecute = canModify || (st === 'running' && !_isChatStreamingNow() && doneCount < steps.length);
    const rawMd = _buildBlueprintMarkdown(target);

    const previewLbl = _esc(_tr('ap_chat_modal_preview', 'Preview'));
    const editLbl = _esc(_tr('ap_chat_modal_edit', 'Edit Markdown'));
    const saveLbl = _esc(_tr('ap_chat_modal_save', 'Save Changes'));
    const reviseAiLbl = _esc(_tr('ap_chat_modal_revise_ai', 'Revise with AI'));
    const revisePlaceholder = _esc(_tr('ap_chat_revise_placeholder', 'Ask Architect to revise this plan (e.g. add auth, switch DB, change UI)...'));
    const execLbl = (st === 'awaiting_approval' || st === 'draft')
      ? _esc(_tr('ap_chat_btn_execute', 'Execute Plan'))
      : _esc(_tr('ap_chat_btn_continue', 'Continue Plan'));

    const historyItems = Array.isArray(target.revision_history) && target.revision_history.length
      ? `<div class="ap-modal-rev-history">
           <strong>Revisions:</strong>
           ${target.revision_history.slice(-4).map((h) => `<span class="ap-modal-rev-chip" title="${_esc(h.note || '')}">v${Number(h.revision || 1)}: ${_esc((h.note || '').slice(0, 60))}</span>`).join('')}
         </div>`
      : '';

    const bodyHtml = _modalEditMode
      ? `<div class="ap-modal-edit-wrap">
           <textarea id="ap-modal-md-editor" class="ap-modal-md-editor" spellcheck="false">${_esc(rawMd)}</textarea>
           <div class="ap-modal-edit-bar">
             <button type="button" class="agent-plan-btn-approve" id="ap-modal-save-md-btn">
               <i class="fas fa-save"></i> ${saveLbl}
             </button>
             <button type="button" class="agent-plan-btn-secondary" id="ap-modal-cancel-edit-btn">
               ${previewLbl}
             </button>
           </div>
         </div>`
      : `<div class="ap-modal-markdown" id="ap-modal-md-preview">${_renderMarkdownSafe(rawMd)}</div>`;

    const footerHtml = (canModify || canExecute)
      ? `<div class="ap-modal-footer">
           ${canModify ? `
             <div class="ap-modal-revise-row">
               <input type="text" id="ap-modal-revise-input" class="ap-revise-input" placeholder="${revisePlaceholder}" />
               <button type="button" class="agent-plan-btn-revise" id="ap-modal-revise-send-btn">
                 <i class="fas fa-pen-to-square"></i> ${reviseAiLbl}
               </button>
             </div>` : ''}
           ${canExecute ? `
             <button type="button" class="agent-plan-btn-approve" id="ap-modal-execute-btn">
               <i class="fas fa-play"></i> ${execLbl}
             </button>` : ''}
         </div>`
      : '';

    overlay.innerHTML = `
      <div class="ap-modal-dialog" role="dialog" aria-modal="true" aria-label="${_esc(target.title || 'Implementation Plan')}">
        <div class="ap-modal-header">
          <div class="ap-modal-title-group">
            <span class="agent-plan-status-pill">${_esc(_statusLabel(st, target.plan_mode))}</span>
            <span class="ap-rev-pill">v${rev}</span>
            <h3 class="ap-modal-title">${_esc(target.title || 'Implementation Plan')}</h3>
            <span class="ap-modal-meta">(${doneCount}/${steps.length} · ${pct}%)</span>
          </div>
          <div class="ap-modal-header-actions">
            <button type="button" class="agent-plan-btn-secondary" id="ap-modal-export-btn" title="${_esc(_tr('ap_chat_btn_export_title', 'Export / Save plan to disk (.md default, .html report, .yaml, or .json via native OS dialog · Shift+Click for HTML)'))}">
              <i class="fas fa-file-export"></i> ${_esc(_tr('ap_chat_btn_export', 'Export'))}
            </button>
            ${canModify ? `
              <button type="button" class="agent-plan-btn-secondary" id="ap-modal-toggle-edit-btn">
                <i class="fas ${_modalEditMode ? 'fa-eye' : 'fa-code'}"></i> ${_modalEditMode ? previewLbl : editLbl}
              </button>` : ''}
            <button type="button" class="ap-modal-close-btn" id="ap-modal-close-btn" title="Close (Esc)">
              <i class="fas fa-times"></i>
            </button>
          </div>
        </div>
        ${historyItems}
        <div class="ap-modal-body">${bodyHtml}</div>
        ${footerHtml}
      </div>
    `;

    overlay.onclick = (e) => {
      if (e.target === overlay) closePlanModal();
    };

    const closeBtn = overlay.querySelector('#ap-modal-close-btn');
    if (closeBtn) closeBtn.addEventListener('click', closePlanModal);

    const modalExportBtn = overlay.querySelector('#ap-modal-export-btn');
    if (modalExportBtn) {
      modalExportBtn.addEventListener('click', (e) => {
        const fmt = e && e.shiftKey ? 'html' : 'md';
        if (_lastHandlers?.onExport) {
          _lastHandlers.onExport(_lastPlan || target, { format: fmt });
        } else if (ns.api?.exportPlanNativeDialog) {
          ns.api.exportPlanNativeDialog(_lastPlan || target, { format: fmt });
        }
      });
    }

    const toggleEditBtn = overlay.querySelector('#ap-modal-toggle-edit-btn');
    if (toggleEditBtn) {
      toggleEditBtn.addEventListener('click', () => {
        _modalEditMode = !_modalEditMode;
        openPlanModal(_lastPlan || target);
      });
    }

    const cancelEditBtn = overlay.querySelector('#ap-modal-cancel-edit-btn');
    if (cancelEditBtn) {
      cancelEditBtn.addEventListener('click', () => {
        _modalEditMode = false;
        openPlanModal(_lastPlan || target);
      });
    }

    const saveMdBtn = overlay.querySelector('#ap-modal-save-md-btn');
    if (saveMdBtn && _lastHandlers?.onSaveManualRevision) {
      saveMdBtn.addEventListener('click', async () => {
        const editor = overlay.querySelector('#ap-modal-md-editor');
        const newMd = editor ? editor.value : rawMd;
        saveMdBtn.disabled = true;
        const updated = await _lastHandlers.onSaveManualRevision(_lastPlan || target, {
          plan_markdown: newMd,
          revision_note: 'Manual blueprint edit in Plan Viewer',
        });
        _modalEditMode = false;
        openPlanModal(updated || _lastPlan || target);
      });
    }

    const modalRevInput = overlay.querySelector('#ap-modal-revise-input');
    const modalRevBtn = overlay.querySelector('#ap-modal-revise-send-btn');
    const submitModalRevise = () => {
      const fb = (modalRevInput?.value || '').trim();
      if (!fb || !_lastHandlers?.onRevise) return;
      closePlanModal();
      setLaunching(target.plan_id, true, 'revise');
      _lastHandlers.onRevise(_lastPlan || target, fb);
    };
    if (modalRevBtn) modalRevBtn.addEventListener('click', submitModalRevise);
    if (modalRevInput) {
      modalRevInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
          e.preventDefault();
          submitModalRevise();
        }
      });
    }

    const modalExecBtn = overlay.querySelector('#ap-modal-execute-btn');
    if (modalExecBtn && _lastHandlers?.onExecute) {
      modalExecBtn.addEventListener('click', () => {
        const activePlan = _lastPlan || target;
        const coderSel = document.getElementById('ap-chat-coder-preset-select');
        const chosenPreset = coderSel?.value || '';
        closePlanModal();
        setLaunching(activePlan.plan_id, true, 'execute');
        _lastHandlers.onExecute(activePlan, activePlan.steps || [], chosenPreset);
      });
    }
  }

  function _renderDetachedMiniBar(slot, plan, opts) {
    const {
      mode,
      pillHtml,
      revBadgeHtml,
      doneCount,
      totalSteps,
      pct,
      isConfirm,
      isRunningActive,
      isCompleted,
    } = opts;

    const modeBadgeLbl = mode === 'popout'
      ? _esc(_tr('ap_chat_detached_popout', 'External Window'))
      : _esc(_tr('ap_chat_detached_floating', 'Floating'));
    const modeIcon = mode === 'popout' ? 'fa-up-right-from-square' : 'fa-up-down-left-right';
    const focusLbl = _esc(_tr('ap_chat_btn_focus', 'Focus'));
    const focusTitle = _esc(_tr('ap_chat_btn_focus_title', 'Bring detached plan window to front'));
    const dockLbl = _esc(_tr('ap_chat_btn_dock', 'Dock'));
    const dockTitle = _esc(_tr('ap_chat_btn_dock_title', 'Return plan window back into chat'));
    const popoutLbl = _esc(_tr('ap_chat_btn_popout', 'Pop-out'));
    const popoutTitle = _esc(_tr('ap_chat_btn_popout_title', 'Open plan in a separate window (Shift+Click for new tab)'));

    const barCls = [
      'ap-detached-bar',
      isConfirm ? 'is-confirm' : '',
      isRunningActive ? 'is-running' : '',
      isCompleted ? 'is-completed' : '',
      mode === 'popout' ? 'is-popout' : 'is-floating',
    ].filter(Boolean).join(' ');

    slot.innerHTML = `
      <div class="${barCls}" id="ap-chat-detached-bar" data-plan-id="${_esc(plan.plan_id)}" data-detach-mode="${_esc(mode)}">
        <div class="ap-detached-left">
          <span class="agent-plan-status-pill">${pillHtml}</span>
          ${revBadgeHtml}
          <span class="ap-detached-title" title="${_esc(plan.title)}">${_esc(plan.title)}</span>
          <span class="ap-detached-meta">(${doneCount}/${totalSteps} · ${pct}%)</span>
          <div class="ap-detached-progress" aria-hidden="true">
            <div class="ap-detached-progress-fill" style="width:${pct}%"></div>
          </div>
          <span class="ap-detached-mode-badge">
            <i class="fas ${modeIcon}" aria-hidden="true"></i> ${modeBadgeLbl}
          </span>
        </div>
        <div class="ap-detached-actions">
          <button type="button" class="ap-detached-btn" id="ap-detached-focus-btn" title="${focusTitle}">
            <i class="fas fa-arrow-up-right-from-square"></i> ${focusLbl}
          </button>
          ${mode === 'floating' ? `
            <button type="button" class="ap-detached-btn" id="ap-detached-popout-btn" title="${popoutTitle}">
              <i class="fas fa-up-right-from-square"></i> ${popoutLbl}
            </button>` : ''}
          <button type="button" class="ap-detached-btn is-primary" id="ap-detached-dock-btn" title="${dockTitle}">
            <i class="fas fa-compress"></i> ${dockLbl}
          </button>
        </div>
      </div>
    `;

    const focusBtn = slot.querySelector('#ap-detached-focus-btn');
    if (focusBtn && ns.detach) {
      focusBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        ns.detach.focusDetached();
      });
    }

    const popoutBtn = slot.querySelector('#ap-detached-popout-btn');
    if (popoutBtn && ns.detach) {
      popoutBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        const sid = ns.api ? ns.api.resolveSid() : (plan.source_id || '');
        ns.detach.openPopout(plan, sid, { asTab: Boolean(e.shiftKey) });
      });
    }

    const dockBtn = slot.querySelector('#ap-detached-dock-btn');
    if (dockBtn && ns.detach) {
      dockBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        ns.detach.dockBack({ closePopout: true });
      });
    }
  }

  function renderPlanCard(plan, handlers) {
    const slot = document.getElementById('agent-plan-slot');
    if (!slot) return;
    _disconnectStepsObserver();
    if (!plan || !Array.isArray(plan.steps) || !plan.steps.length) {
      _lastPlan = null;
      _prevPlanStatus = '';
      _lastHandlers = null;
      _launchingPlanId = '';
      _reviseOpen = false;
      if (_modalOpen) closePlanModal();
      if (ns.detach && typeof ns.detach.removeFloatingHost === 'function') {
        ns.detach.removeFloatingHost();
      }
      slot.innerHTML = '';
      return;
    }

    const wasEmpty = !_lastPlan;
    const prevPlanId = _lastPlan?.plan_id || '';
    const prevStatus = _prevPlanStatus;
    _lastPlan = plan;
    _lastHandlers = handlers || _lastHandlers;
    if (prevPlanId && prevPlanId !== plan.plan_id) {
      _reviseOpen = false;
    }
    if (wasEmpty) {
      _uiState = _loadUiState();
      if (_uiState.save && _uiState.height >= MIN_STEPS_HEIGHT) {
        _sessionHeightPx = _uiState.height;
      }
    }

    const detachMode = _getDetachMode();
    const st = String(plan.status || 'running').toLowerCase();
    const isConfirm = st === 'awaiting_approval' || st === 'draft';
    const isCompleted = st === 'completed';
    if (prevPlanId !== plan.plan_id) {
      // Collapse already-completed plans into a compact header bar by default so they remain accessible
      _collapsed = isCompleted;
    } else if (isCompleted && prevStatus !== 'completed') {
      _collapsed = true;
    }
    _prevPlanStatus = st;
    const isLaunching = Boolean(_launchingPlanId && _launchingPlanId === plan.plan_id);
    const streamingNow = _isChatStreamingNow();
    const isRunningActive = isLaunching || (st === 'running' && streamingNow);
    const doneCount = plan.steps.filter((s) => s.status === 'done' || s.status === 'skipped').length;
    const pct = Math.round((doneCount / plan.steps.length) * 100);
    const isResumable = isLaunching || ((st === 'interrupted' || st === 'paused' || (st === 'running' && !streamingNow)) && doneCount < plan.steps.length);
    const showActions = isConfirm || isResumable;
    const canRevise = !isLaunching && (isConfirm || st === 'interrupted' || st === 'paused');
    const rev = Number(plan.revision || 1);
    const hasBlueprint = Boolean(String(plan.plan_markdown || '').trim() || String(plan.goal || '').trim());

    const busyLbl = _launchingMode === 'revise'
      ? _esc(_tr('ap_chat_btn_revising', 'Revising...'))
      : _esc(_tr('ap_chat_btn_starting', 'Starting...'));
    const pillHtml = isRunningActive
      ? `<i class="fas fa-circle-notch fa-spin" aria-hidden="true"></i> ${_launchingMode === 'revise' ? busyLbl : _esc(_statusLabel('running', plan.plan_mode))}`
      : _esc(_statusLabel(st, plan.plan_mode));
    const revBadgeHtml = (rev > 1 || hasBlueprint)
      ? `<span class="ap-rev-pill" id="ap-chat-rev-badge" title="Implementation Plan revision v${rev}">v${rev}</span>`
      : '';

    let mountRoot = slot;
    if (detachMode === 'popout' || detachMode === 'floating') {
      _renderDetachedMiniBar(slot, plan, {
        mode: detachMode,
        pillHtml,
        revBadgeHtml,
        doneCount,
        totalSteps: plan.steps.length,
        pct,
        isConfirm,
        isRunningActive,
        isCompleted,
      });
      if (detachMode === 'popout') {
        if (ns.detach && typeof ns.detach.removeFloatingHost === 'function') {
          ns.detach.removeFloatingHost();
        }
        if (_modalOpen && !_modalEditMode) {
          openPlanModal(plan);
        }
        return;
      }
      mountRoot = ns.detach.ensureFloatingHost();
    } else if (ns.detach && typeof ns.detach.removeFloatingHost === 'function') {
      ns.detach.removeFloatingHost();
    }

    const cardCls = [
      'agent-plan-card',
      isConfirm ? 'is-confirm' : '',
      isRunningActive ? 'is-running' : '',
      isCompleted ? 'is-completed' : '',
      detachMode === 'floating' ? 'is-floating-card' : '',
      _collapsed ? 'is-collapsed' : '',
    ].filter(Boolean).join(' ');

    const stepToggleTitle = _esc(_tr('ap_chat_step_toggle_title', 'Click to mark step done or pending manually'));
    const stepsHtml = plan.steps.map((s, idx) => {
      const stepNum = Number(s.index || idx + 1);
      const isStepDone = String(s.status || '').toLowerCase() === 'done';
      const checkControl = isConfirm
        ? `<input type="checkbox" class="ap-confirm-step-cb" data-idx="${idx}" checked style="margin-top:2px;accent-color:#10b981;">`
        : `<button type="button" class="ap-step-toggle-btn" data-step-index="${stepNum}" title="${stepToggleTitle}">${_stepIcon(s.status)}</button>`;
      const manualDoneBtn = isConfirm
        ? `<button type="button" class="ap-step-manual-done-btn${isStepDone ? ' is-done' : ''}" data-step-index="${stepNum}" title="${stepToggleTitle}" aria-label="${stepToggleTitle}">${isStepDone ? '✓' : '○'}</button>`
        : '';
      const note = s.notes ? `<span style="color:var(--muted);margin-left:6px;">— ${_esc(s.notes)}</span>` : '';
      const filesChips = (Array.isArray(s.files) && s.files.length)
        ? `<div class="ap-step-files">${s.files.slice(0, 5).map(_renderFileChip).join('')}</div>`
        : '';
      const detailLine = s.details
        ? `<div class="ap-step-details" title="${_esc(s.details)}">${_esc(s.details)}</div>`
        : '';
      return `
        <div class="agent-plan-step st-${_esc(s.status || 'pending')}">
          <span style="min-width:18px;text-align:center;">${checkControl}</span>
          <div class="ap-step-body">
            <div><strong>${stepNum}.</strong> ${_esc(s.title)}${note}</div>
            ${filesChips}
            ${detailLine}
          </div>
          ${manualDoneBtn}
        </div>
      `;
    }).join('');

    const actionLbl = isConfirm
      ? _esc(_tr('ap_chat_btn_execute', 'Execute Plan'))
      : _esc(_tr('ap_chat_btn_continue', 'Continue Plan'));
    const nextStepLbl = _esc(_tr('ap_chat_btn_next_step', 'Next Step'));
    const nextStepTitle = _esc(_tr('ap_chat_btn_next_step_title', 'Execute only the next pending step and pause for review'));
    const approveBtnInner = isLaunching
      ? `<i class="fas fa-circle-notch fa-spin"></i> ${busyLbl}`
      : `<i class="fas fa-play"></i> ${actionLbl}`;
    const runCoderTitle = _esc(_tr('ap_chat_lbl_run_with_coder', 'Run with Preset'));
    const viewPlanLbl = _esc(_tr('ap_chat_btn_view_plan', 'View Plan'));
    const reviseLbl = _esc(_tr('ap_chat_btn_revise', 'Revise'));
    const sendRevLbl = _esc(_tr('ap_chat_btn_send_revision', 'Send Revision'));
    const revisePlaceholder = _esc(_tr('ap_chat_revise_placeholder', 'Ask Architect to revise this plan (e.g. add auth, switch DB, change UI)...'));
    const cancelLbl = _esc(_tr('ap_chat_btn_cancel', 'Cancel'));
    const hideTitle = _esc(_tr('ap_chat_btn_hide', 'Hide'));
    const saveUiLbl = _esc(_tr('ap_chat_save_ui', 'Save UI'));
    const saveUiTitle = _esc(_tr('ap_chat_save_ui_title', 'Remember plan panel height and visible rows across sessions'));
    const maxRowsLbl = _esc(_tr('ap_chat_max_rows', 'Rows:'));
    const adaptLbl = _esc(_tr('ap_chat_btn_adapt', 'Adapt'));
    const adaptTitle = _esc(_tr('ap_chat_btn_adapt_title', 'Adapt plan height to the configured number of step rows'));
    const resizeTitle = _esc(_tr('ap_chat_resize_title', 'Drag to resize plan height · Double-click to fit all steps'));
    const floatTitle = _esc(_tr('ap_chat_btn_float_title', 'Detach plan into a draggable floating window inside chat'));
    const popoutTitle = _esc(_tr('ap_chat_btn_popout_title', 'Open plan in a separate window (Shift+Click for new tab)'));
    const dockTitle = _esc(_tr('ap_chat_btn_dock_title', 'Return plan window back into chat'));
    const coderPresetOptions = _buildCoderPresetOptionsHtml();
    const appliedHeight = _clampHeightPx(_sessionHeightPx);
    const stepsCls = appliedHeight ? 'agent-plan-steps is-sized' : 'agent-plan-steps';
    const stepsStyleAttr = appliedHeight ? ` style="height:${appliedHeight}px;"` : '';

    const exportTitle = _esc(_tr('ap_chat_btn_export_title', 'Export / Save plan to disk (.md default, .html report, .yaml, or .json via native OS dialog · Shift+Click for HTML)'));
    const importTitle = _esc(_tr('ap_chat_btn_import_title', 'Import a saved Action Plan (.md, .html, .yaml, .yml, or .json via native OS dialog)'));
    const ioButtonsHtml = `
      <button type="button" class="ap-icon-action-btn" id="ap-chat-export-btn" title="${exportTitle}" aria-label="${exportTitle}">
        <i class="fas fa-file-export"></i>
      </button>
      <button type="button" class="ap-icon-action-btn" id="ap-chat-import-btn" title="${importTitle}" aria-label="${importTitle}">
        <i class="fas fa-file-import"></i>
      </button>
    `;

    const detachButtonsHtml = ns.detach ? `
      ${detachMode === 'floating' ? `
        <button type="button" class="ap-icon-action-btn is-dock" id="ap-chat-dock-btn" title="${dockTitle}" aria-label="${dockTitle}">
          <i class="fas fa-compress"></i>
        </button>` : `
        <button type="button" class="ap-icon-action-btn" id="ap-chat-float-btn" title="${floatTitle}" aria-label="${floatTitle}">
          <i class="fas fa-up-down-left-right"></i>
        </button>`}
      <button type="button" class="ap-icon-action-btn" id="ap-chat-popout-btn" title="${popoutTitle}" aria-label="${popoutTitle}">
        <i class="fas fa-up-right-from-square"></i>
      </button>
    ` : '';

    const reviseBarHtml = (_reviseOpen && canRevise) ? `
      <div class="agent-plan-revise-bar" id="ap-chat-revise-bar">
        <input type="text" id="ap-chat-revise-input" class="ap-revise-input" placeholder="${revisePlaceholder}" />
        <button type="button" class="agent-plan-btn-revise" id="ap-chat-revise-send-btn">
          <i class="fas fa-paper-plane"></i> ${sendRevLbl}
        </button>
        <button type="button" class="ap-revise-close-btn" id="ap-chat-revise-close-btn" title="Close">
          <i class="fas fa-times"></i>
        </button>
      </div>
    ` : '';

    const actionsHtml = showActions ? `
      <div class="agent-plan-actions">
        <button type="button" class="agent-plan-btn-approve${isLaunching ? ' is-launching' : ''}" id="ap-chat-approve-btn" title="Execute or continue the active plan using the selected model/preset"${isLaunching ? ' disabled' : ''}>
          ${approveBtnInner}
        </button>
        <button type="button" class="agent-plan-btn-next-step" id="ap-chat-next-step-btn" title="${nextStepTitle}"${isLaunching ? ' disabled' : ''}>
          <i class="fas fa-forward-step"></i> ${nextStepLbl}
        </button>
        <div class="agent-plan-coder-group${isLaunching ? ' is-locked' : ''}" id="ap-chat-coder-group" title="Select which Global Preset executes this Action Plan">
          <label for="ap-chat-coder-preset-select" class="agent-plan-coder-label" title="${runCoderTitle} — Select which Global Preset will execute this Action Plan">
            <i class="fas fa-sliders"></i> ${runCoderTitle}
          </label>
          <div class="agent-plan-coder-select-wrap" id="ap-chat-coder-select-wrap" title="">
            <span class="agent-plan-coder-display" id="ap-chat-coder-display"></span>
            <i class="fas fa-chevron-down agent-plan-coder-caret" aria-hidden="true"></i>
            <select id="ap-chat-coder-preset-select" class="agent-plan-coder-select" aria-label="${runCoderTitle}" title=""${isLaunching ? ' disabled' : ''}>
              ${coderPresetOptions}
            </select>
          </div>
        </div>
        ${canRevise ? `
          <button type="button" class="agent-plan-btn-revise${_reviseOpen ? ' is-active' : ''}" id="ap-chat-revise-toggle-btn" title="Request Architect changes to this plan before executing"${isLaunching ? ' disabled' : ''}>
            <i class="fas fa-pen-to-square"></i> ${reviseLbl}
          </button>` : ''}
        <button type="button" class="agent-plan-btn-reject" id="ap-chat-reject-btn"${isLaunching ? ' disabled' : ''}>
          <i class="fas fa-times"></i> ${cancelLbl}
        </button>
      </div>
    ` : '';

    const cornerResizeHtml = detachMode === 'floating'
      ? `<span class="ap-float-corner-resize" id="ap-float-corner-resize" title="${resizeTitle}" aria-hidden="true"></span>`
      : '';

    mountRoot.innerHTML = `
      <div class="${cardCls}" id="agent-plan-active-card" data-plan-id="${_esc(plan.plan_id)}">
        <div class="agent-plan-header" id="ap-chat-toggle-header" title="${detachMode === 'floating' ? 'Drag to move · Click to collapse or expand' : 'Click to collapse or expand plan details'}">
          <div class="agent-plan-title-row">
            <span class="agent-plan-status-pill">${pillHtml}</span>
            ${revBadgeHtml}
            <span>${_esc(plan.title)}</span>
            <span style="font-size:11px;color:var(--muted);">(${doneCount}/${plan.steps.length} · ${pct}%)</span>
          </div>
          <div class="ap-header-right-controls">
            <div class="ap-header-size-controls">
              <label class="ap-ctrl-label" title="${saveUiTitle}">
                <input type="checkbox" id="ap-chat-remember-size"${_uiState.save ? ' checked' : ''}> ${saveUiLbl}
              </label>
              <div class="ap-max-rows-box">
                <span>${maxRowsLbl}</span>
                <input type="number" id="ap-chat-max-rows" class="ap-dark-input" min="1" max="50" value="${_clampRows(_uiState.rows)}" aria-label="${maxRowsLbl}" title="${adaptTitle}">
                <button type="button" id="ap-chat-adapt-btn" title="${adaptTitle}">${adaptLbl}</button>
              </div>
            </div>
            <button type="button" class="agent-plan-btn-view" id="ap-chat-view-plan-btn" title="Open full Implementation Plan blueprint (Markdown)">
              <i class="fas fa-file-lines"></i> ${viewPlanLbl}
            </button>
            ${ioButtonsHtml}
            ${detachButtonsHtml}
            <i id="ap-chat-chevron" class="fas fa-chevron-${_collapsed ? 'right' : 'down'}" style="font-size:11px;color:var(--muted);"></i>
            ${!isConfirm ? `<button type="button" id="ap-chat-hide-btn" title="${hideTitle}" style="background:none;border:none;color:var(--muted);cursor:pointer;font-size:12px;"><i class="fas fa-times"></i></button>` : ''}
          </div>
        </div>
        <div class="agent-plan-progress-bar"><div class="agent-plan-progress-fill" style="width:${pct}%"></div></div>
        <div class="${stepsCls}"${stepsStyleAttr}>${stepsHtml}</div>
        ${reviseBarHtml}
        ${actionsHtml}
        <div class="ap-resize-handle" id="ap-chat-resize-handle" role="separator" aria-orientation="horizontal" title="${resizeTitle}">
          <span class="ap-resize-grip" aria-hidden="true"></span>
        </div>
        ${cornerResizeHtml}
      </div>
    `;

    const sizeControls = mountRoot.querySelector('.ap-header-size-controls');
    if (sizeControls) {
      sizeControls.addEventListener('click', (e) => e.stopPropagation());
    }

    const rememberCb = mountRoot.querySelector('#ap-chat-remember-size');
    if (rememberCb) {
      rememberCb.addEventListener('change', (e) => {
        e.stopPropagation();
        _uiState.save = Boolean(rememberCb.checked);
        if (_uiState.save && !_sessionHeightPx) {
          const stepsElNow = mountRoot.querySelector('.agent-plan-steps');
          const curH = stepsElNow ? Math.round(stepsElNow.getBoundingClientRect().height || stepsElNow.offsetHeight || 0) : 0;
          if (curH >= MIN_STEPS_HEIGHT) {
            _sessionHeightPx = _clampHeightPx(curH);
          }
        }
        _saveUiState();
      });
    }

    const rowsInput = mountRoot.querySelector('#ap-chat-max-rows');
    if (rowsInput) {
      rowsInput.addEventListener('change', (e) => {
        e.stopPropagation();
        adaptStepsHeight(rowsInput.value);
      });
      rowsInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
          e.preventDefault();
          e.stopPropagation();
          adaptStepsHeight(rowsInput.value);
        }
      });
    }

    const adaptBtn = mountRoot.querySelector('#ap-chat-adapt-btn');
    if (adaptBtn) {
      adaptBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        adaptStepsHeight(rowsInput ? rowsInput.value : _uiState.rows);
      });
    }

    const exportBtn = mountRoot.querySelector('#ap-chat-export-btn');
    if (exportBtn) {
      exportBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        const fmt = e.shiftKey ? 'html' : 'md';
        if (_lastHandlers?.onExport) {
          _lastHandlers.onExport(plan, { format: fmt });
        } else if (ns.api?.exportPlanNativeDialog) {
          ns.api.exportPlanNativeDialog(plan, { format: fmt });
        }
      });
    }

    const importBtn = mountRoot.querySelector('#ap-chat-import-btn');
    if (importBtn) {
      importBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        if (_lastHandlers?.onImport) {
          _lastHandlers.onImport({});
        } else if (ns.api?.importPlanNativeDialog) {
          ns.api.importPlanNativeDialog({}).then((res) => {
            if (res && res.ok && !res.cancelled && res.plan) {
              renderPlanCard(res.plan, _lastHandlers);
            }
          });
        }
      });
    }

    const floatBtn = mountRoot.querySelector('#ap-chat-float-btn');
    if (floatBtn && ns.detach) {
      floatBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        ns.detach.setFloating();
      });
    }

    const dockHeaderBtn = mountRoot.querySelector('#ap-chat-dock-btn');
    if (dockHeaderBtn && ns.detach) {
      dockHeaderBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        ns.detach.dockBack({ closePopout: false });
      });
    }

    const popoutHeaderBtn = mountRoot.querySelector('#ap-chat-popout-btn');
    if (popoutHeaderBtn && ns.detach) {
      popoutHeaderBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        const sid = ns.api ? ns.api.resolveSid() : (plan.source_id || '');
        ns.detach.openPopout(plan, sid, { asTab: Boolean(e.shiftKey) });
      });
    }

    const cardEl = mountRoot.querySelector('#agent-plan-active-card');
    const stepsEl = mountRoot.querySelector('.agent-plan-steps');
    const resizeHandle = mountRoot.querySelector('#ap-chat-resize-handle');
    if (resizeHandle && stepsEl) {
      resizeHandle.addEventListener('pointerdown', (e) => {
        if (e.button !== undefined && e.button !== 0) return;
        e.preventDefault();
        e.stopPropagation();
        _ensureExpanded();
        const startY = e.clientY;
        const startH = Math.round(stepsEl.getBoundingClientRect().height || stepsEl.offsetHeight || 140);
        _isDraggingResize = true;
        if (cardEl) cardEl.classList.add('is-resizing');
        resizeHandle.classList.add('is-active');
        const prevUserSelect = document.body.style.userSelect;
        const prevCursor = document.body.style.cursor;
        document.body.style.userSelect = 'none';
        document.body.style.cursor = 'ns-resize';

        const onMove = (ev) => {
          const deltaY = ev.clientY - startY;
          const nextH = _clampHeightPx(startH + deltaY) || MIN_STEPS_HEIGHT;
          _sessionHeightPx = nextH;
          stepsEl.classList.add('is-sized');
          stepsEl.style.height = `${nextH}px`;
        };
        const onUp = () => {
          _isDraggingResize = false;
          document.removeEventListener('pointermove', onMove);
          document.removeEventListener('pointerup', onUp);
          document.removeEventListener('pointercancel', onUp);
          if (cardEl) cardEl.classList.remove('is-resizing');
          resizeHandle.classList.remove('is-active');
          document.body.style.userSelect = prevUserSelect;
          document.body.style.cursor = prevCursor;
          _saveUiState();
        };
        document.addEventListener('pointermove', onMove);
        document.addEventListener('pointerup', onUp);
        document.addEventListener('pointercancel', onUp);
      });

      resizeHandle.addEventListener('dblclick', (e) => {
        e.preventDefault();
        e.stopPropagation();
        fitAllSteps();
      });
    }

    if (detachMode === 'floating' && ns.detach && cardEl) {
      ns.detach.attachFloatingInteractions(mountRoot, cardEl, stepsEl, (nextH, persist) => {
        _applyStepsHeightPx(nextH, persist);
      });
    }

    if (stepsEl && typeof ResizeObserver !== 'undefined') {
      _stepsResizeObserver = new ResizeObserver(() => {
        if (_isDraggingResize || _collapsed) return;
        const inlineH = parseFloat(stepsEl.style.height);
        if (!Number.isFinite(inlineH) || inlineH < MIN_STEPS_HEIGHT) return;
        const clamped = _clampHeightPx(inlineH);
        if (clamped && clamped !== _sessionHeightPx) {
          _sessionHeightPx = clamped;
          stepsEl.classList.add('is-sized');
          _saveUiState();
        }
      });
      _stepsResizeObserver.observe(stepsEl);
    }

    const viewBtn = mountRoot.querySelector('#ap-chat-view-plan-btn');
    if (viewBtn) {
      viewBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        _modalEditMode = false;
        openPlanModal(plan);
      });
    }

    const hdr = mountRoot.querySelector('#ap-chat-toggle-header');
    if (hdr) {
      hdr.addEventListener('click', (e) => {
        if (mountRoot.dataset && mountRoot.dataset.justDragged === '1') return;
        if (
          e.target.closest('#ap-chat-hide-btn') ||
          e.target.closest('#ap-chat-view-plan-btn') ||
          e.target.closest('.ap-header-size-controls') ||
          e.target.closest('.ap-icon-action-btn')
        ) return;
        _collapsed = !_collapsed;
        if (cardEl) cardEl.classList.toggle('is-collapsed', _collapsed);
        const chev = mountRoot.querySelector('#ap-chat-chevron');
        if (chev) {
          chev.classList.toggle('fa-chevron-right', _collapsed);
          chev.classList.toggle('fa-chevron-down', !_collapsed);
        }
      });
    }

    const hideBtn = mountRoot.querySelector('#ap-chat-hide-btn');
    if (hideBtn) {
      hideBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        setPlanDismissed(plan.plan_id, true);
        _disconnectStepsObserver();
        if (ns.detach && typeof ns.detach.removeFloatingHost === 'function') {
          ns.detach.removeFloatingHost();
        }
        slot.innerHTML = '';
      });
    }

    const collectSelectedSteps = () => {
      const cbs = Array.from(mountRoot.querySelectorAll('.ap-confirm-step-cb'));
      if (!cbs.length) return plan.steps;
      const checked = cbs
        .filter((cb) => cb.checked)
        .map((cb) => plan.steps[Number(cb.dataset.idx)])
        .filter(Boolean);
      return checked.length ? checked : plan.steps;
    };

    const coderSelect = mountRoot.querySelector('#ap-chat-coder-preset-select');
    if (coderSelect) {
      _syncSelectVisualDisplay();
      coderSelect.addEventListener('change', async (e) => {
        e.stopPropagation();
        _syncSelectVisualDisplay();
        const chosenPreset = coderSelect.value || '';
        if (_lastHandlers?.onSelectPreset) {
          await _lastHandlers.onSelectPreset(chosenPreset);
        }
      });
    }

    const reviseToggleBtn = mountRoot.querySelector('#ap-chat-revise-toggle-btn');
    if (reviseToggleBtn) {
      reviseToggleBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        _reviseOpen = !_reviseOpen;
        renderPlanCard(_lastPlan, _lastHandlers);
        if (_reviseOpen) {
          const inp = document.getElementById('ap-chat-revise-input');
          if (inp) inp.focus();
        }
      });
    }

    const reviseCloseBtn = mountRoot.querySelector('#ap-chat-revise-close-btn');
    if (reviseCloseBtn) {
      reviseCloseBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        _reviseOpen = false;
        renderPlanCard(_lastPlan, _lastHandlers);
      });
    }

    const reviseInput = mountRoot.querySelector('#ap-chat-revise-input');
    const reviseSendBtn = mountRoot.querySelector('#ap-chat-revise-send-btn');
    const triggerInlineRevise = () => {
      const fb = (reviseInput?.value || '').trim();
      if (!fb || !_lastHandlers?.onRevise) return;
      _reviseOpen = false;
      setLaunching(plan.plan_id, true, 'revise');
      _lastHandlers.onRevise(plan, fb);
    };
    if (reviseSendBtn) {
      reviseSendBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        triggerInlineRevise();
      });
    }
    if (reviseInput) {
      reviseInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
          e.preventDefault();
          triggerInlineRevise();
        } else if (e.key === 'Escape') {
          e.preventDefault();
          _reviseOpen = false;
          renderPlanCard(_lastPlan, _lastHandlers);
        }
      });
    }

    const approveBtn = mountRoot.querySelector('#ap-chat-approve-btn');
    if (approveBtn && _lastHandlers?.onExecute) {
      approveBtn.addEventListener('click', () => {
        if (approveBtn.disabled) return;
        setLaunching(plan.plan_id, true, 'execute');
        const chosenPreset = coderSelect?.value || '';
        _lastHandlers.onExecute(plan, collectSelectedSteps(), chosenPreset);
      });
    }

    const nextStepBtn = mountRoot.querySelector('#ap-chat-next-step-btn');
    if (nextStepBtn && _lastHandlers?.onExecuteNextStep) {
      nextStepBtn.addEventListener('click', () => {
        if (nextStepBtn.disabled) return;
        setLaunching(plan.plan_id, true, 'execute');
        const chosenPreset = coderSelect?.value || '';
        _lastHandlers.onExecuteNextStep(plan, collectSelectedSteps(), chosenPreset);
      });
    }

    mountRoot.querySelectorAll('.ap-step-toggle-btn, .ap-step-manual-done-btn').forEach((btn) => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const stepIdx = Number(btn.dataset.stepIndex || 0);
        if (!stepIdx) return;
        if (_lastHandlers?.onToggleStep) {
          _lastHandlers.onToggleStep(plan, stepIdx);
        } else if (ns.api?.togglePlanStep) {
          ns.api.togglePlanStep(plan.plan_id, stepIdx).then((res) => {
            if (res && res.ok && res.plan) renderPlanCard(res.plan, _lastHandlers);
          });
        }
      });
    });

    const rejectBtn = mountRoot.querySelector('#ap-chat-reject-btn');
    if (rejectBtn && _lastHandlers?.onReject) {
      rejectBtn.addEventListener('click', () => {
        if (rejectBtn.disabled) return;
        rejectBtn.disabled = true;
        _lastHandlers.onReject(plan);
      });
    }

    if (_modalOpen && !_modalEditMode) {
      openPlanModal(plan);
    }
  }

  function rerenderCurrent() {
    if (_lastPlan) {
      renderPlanCard(_lastPlan, _lastHandlers);
    }
  }

  function getStateSnapshot() {
    return {
      plan: _lastPlan,
      launchingPlanId: _launchingPlanId,
      launchingMode: _launchingMode,
    };
  }

  ns.widget = {
    renderPlanCard,
    rerenderCurrent,
    getStateSnapshot,
    syncPresetOptions,
    setLaunching,
    openPlanModal,
    closePlanModal,
    adaptHeight: adaptStepsHeight,
    fitAllSteps,
    isPlanDismissed,
    setPlanDismissed,
  };
})();
