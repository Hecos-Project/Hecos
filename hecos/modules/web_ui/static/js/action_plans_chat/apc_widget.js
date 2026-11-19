/**
 * MODULE: action_plans_chat/apc_widget.js
 * PURPOSE: Render live collapsible Action Plan checklist card in #agent-plan-slot,
 *          with a single primary action button ("Execute Plan" / "Continue Plan")
 *          and a labeled "Run with Coder" preset dropdown synchronized with session state.
 */

(function () {
  const ns = (window._HecosActionPlanChat = window._HecosActionPlanChat || {});
  let _collapsed = false;
  let _lastPlan = null;
  let _lastHandlers = null;
  let _launchingPlanId = '';
  let _launchingMode = 'execute';
  let _reviseOpen = false;
  let _modalOpen = false;
  let _modalEditMode = false;
  let _escBound = false;

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
    const coderSouls = [];
    const otherSouls = [];

    for (const s of allSouls) {
      const id = String(s?.meta?.id || '').trim();
      if (!id) continue;
      const name = String(s?.meta?.name || id).trim();
      const rawModel = String(s?.model?.model_name || '').trim();
      const shortModel = _shortModelName(rawModel);
      const tags = Array.isArray(s?.meta?.tags) ? s.meta.tags.map((t) => String(t).toLowerCase()) : [];
      const isCoder = id.toLowerCase().includes('coder') || tags.includes('coding') || tags.includes('coder');
      const entry = { id, name, rawModel, shortModel };
      if (isCoder) {
        coderSouls.push(entry);
      } else {
        otherSouls.push(entry);
      }
    }

    if (coderSouls.length === 0 && otherSouls.length === 0) {
      coderSouls.push({ id: 'hecos_coder', name: 'Hecos Coder', rawModel: '', shortModel: '' });
    }

    const activeId = String(window.sfState?.activeSoulId || '').trim();
    const allIds = new Set([...coderSouls.map((c) => c.id), ...otherSouls.map((o) => o.id)]);
    const selectedId = (activeId && allIds.has(activeId)) ? activeId : '';

    const fmtLabel = (item, prefix = '') =>
      `${prefix}${item.name}${item.shortModel ? ` (${item.shortModel})` : ''}`;

    const fmtFullTitle = (item, prefix = '') =>
      `${prefix}${item.name}${item.rawModel ? ` — ${item.rawModel}` : ''}`;

    const renderOpt = (item, prefix = '') => {
      const disp = fmtLabel(item, prefix);
      const tip = fmtFullTitle(item, prefix);
      return `<option value="${_esc(item.id)}" data-display-label="${_esc(disp)}" data-full-title="${_esc(tip)}" title="${_esc(tip)}"${item.id === selectedId ? ' selected' : ''}>${_esc(disp)}</option>`;
    };

    const defaultDisp = '⚡ Current Chat Model';
    const defaultTip = '⚡ Current Chat Model — Use the active chat preset/model';
    const defaultOpt = `<option value="" data-display-label="${_esc(defaultDisp)}" data-full-title="${_esc(defaultTip)}" title="${_esc(defaultTip)}"${!selectedId ? ' selected' : ''}>${_esc(defaultDisp)}</option>`;

    let groupsHtml = '';
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
    const slot = document.getElementById('agent-plan-slot');
    if (!slot) return;
    const card = slot.querySelector('#agent-plan-active-card');
    const approveBtn = slot.querySelector('#ap-chat-approve-btn');
    const rejectBtn = slot.querySelector('#ap-chat-reject-btn');
    const reviseToggle = slot.querySelector('#ap-chat-revise-toggle-btn');
    const reviseSend = slot.querySelector('#ap-chat-revise-send-btn');
    const coderGroup = slot.querySelector('#ap-chat-coder-group');
    const coderSelect = slot.querySelector('#ap-chat-coder-preset-select');
    const statusPill = slot.querySelector('.agent-plan-status-pill');

    if (active) {
      if (card) card.classList.add('is-running');
      if (coderGroup) coderGroup.classList.add('is-locked');
      if (coderSelect) coderSelect.disabled = true;
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

  function renderPlanCard(plan, handlers) {
    const slot = document.getElementById('agent-plan-slot');
    if (!slot) return;
    if (!plan || !Array.isArray(plan.steps) || !plan.steps.length) {
      _lastPlan = null;
      _lastHandlers = null;
      _launchingPlanId = '';
      _reviseOpen = false;
      if (_modalOpen) closePlanModal();
      slot.innerHTML = '';
      return;
    }

    const prevPlanId = _lastPlan?.plan_id || '';
    _lastPlan = plan;
    _lastHandlers = handlers || _lastHandlers;
    if (prevPlanId && prevPlanId !== plan.plan_id) {
      _reviseOpen = false;
    }

    const st = String(plan.status || 'running').toLowerCase();
    const isConfirm = st === 'awaiting_approval' || st === 'draft';
    const isCompleted = st === 'completed';
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

    const cardCls = [
      'agent-plan-card',
      isConfirm ? 'is-confirm' : '',
      isRunningActive ? 'is-running' : '',
      isCompleted ? 'is-completed' : '',
      _collapsed ? 'is-collapsed' : '',
    ].filter(Boolean).join(' ');

    const stepsHtml = plan.steps.map((s, idx) => {
      const checkControl = isConfirm
        ? `<input type="checkbox" class="ap-confirm-step-cb" data-idx="${idx}" checked style="margin-top:2px;accent-color:#10b981;">`
        : _stepIcon(s.status);
      const note = s.notes ? `<span style="color:var(--muted);margin-left:6px;">— ${_esc(s.notes)}</span>` : '';
      const filesChips = (Array.isArray(s.files) && s.files.length)
        ? `<div class="ap-step-files">${s.files.slice(0, 5).map(_renderFileChip).join('')}</div>`
        : '';
      const detailLine = s.details
        ? `<div class="ap-step-details" title="${_esc(s.details)}">${_esc(s.details)}</div>`
        : '';
      return `
        <div class="agent-plan-step st-${_esc(s.status || 'pending')}">
          <span style="min-width:16px;text-align:center;">${checkControl}</span>
          <div class="ap-step-body">
            <div><strong>${Number(s.index || idx + 1)}.</strong> ${_esc(s.title)}${note}</div>
            ${filesChips}
            ${detailLine}
          </div>
        </div>
      `;
    }).join('');

    const actionLbl = isConfirm
      ? _esc(_tr('ap_chat_btn_execute', 'Execute Plan'))
      : _esc(_tr('ap_chat_btn_continue', 'Continue Plan'));
    const busyLbl = _launchingMode === 'revise'
      ? _esc(_tr('ap_chat_btn_revising', 'Revising...'))
      : _esc(_tr('ap_chat_btn_starting', 'Starting...'));
    const approveBtnInner = isLaunching
      ? `<i class="fas fa-circle-notch fa-spin"></i> ${busyLbl}`
      : `<i class="fas fa-play"></i> ${actionLbl}`;
    const runCoderTitle = _esc(_tr('ap_chat_lbl_run_with_coder', 'Run with Coder'));
    const viewPlanLbl = _esc(_tr('ap_chat_btn_view_plan', 'View Plan'));
    const reviseLbl = _esc(_tr('ap_chat_btn_revise', 'Revise'));
    const sendRevLbl = _esc(_tr('ap_chat_btn_send_revision', 'Send Revision'));
    const revisePlaceholder = _esc(_tr('ap_chat_revise_placeholder', 'Ask Architect to revise this plan (e.g. add auth, switch DB, change UI)...'));
    const cancelLbl = _esc(_tr('ap_chat_btn_cancel', 'Cancel'));
    const hideTitle = _esc(_tr('ap_chat_btn_hide', 'Hide'));
    const coderPresetOptions = _buildCoderPresetOptionsHtml();
    const pillHtml = isRunningActive
      ? `<i class="fas fa-circle-notch fa-spin" aria-hidden="true"></i> ${_launchingMode === 'revise' ? busyLbl : _esc(_statusLabel('running', plan.plan_mode))}`
      : _esc(_statusLabel(st, plan.plan_mode));
    const revBadgeHtml = (rev > 1 || hasBlueprint)
      ? `<span class="ap-rev-pill" id="ap-chat-rev-badge" title="Implementation Plan revision v${rev}">v${rev}</span>`
      : '';

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
        <div class="agent-plan-coder-group${isLaunching ? ' is-locked' : ''}" id="ap-chat-coder-group" title="Select which Coder / Global Preset executes this Action Plan">
          <label for="ap-chat-coder-preset-select" class="agent-plan-coder-label" title="Run with Coder — Select which Coder or Global Preset will execute this Action Plan">
            <i class="fas fa-laptop-code"></i> ${runCoderTitle}
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

    slot.innerHTML = `
      <div class="${cardCls}" id="agent-plan-active-card" data-plan-id="${_esc(plan.plan_id)}">
        <div class="agent-plan-header" id="ap-chat-toggle-header" title="Click to collapse or expand plan details">
          <div class="agent-plan-title-row">
            <span class="agent-plan-status-pill">${pillHtml}</span>
            ${revBadgeHtml}
            <span>${_esc(plan.title)}</span>
            <span style="font-size:11px;color:var(--muted);">(${doneCount}/${plan.steps.length} · ${pct}%)</span>
          </div>
          <div style="display:flex;align-items:center;gap:8px;flex-shrink:0;">
            <button type="button" class="agent-plan-btn-view" id="ap-chat-view-plan-btn" title="Open full Implementation Plan blueprint (Markdown)">
              <i class="fas fa-file-lines"></i> ${viewPlanLbl}
            </button>
            <i id="ap-chat-chevron" class="fas fa-chevron-${_collapsed ? 'right' : 'down'}" style="font-size:11px;color:var(--muted);"></i>
            ${!isConfirm ? `<button type="button" id="ap-chat-hide-btn" title="${hideTitle}" style="background:none;border:none;color:var(--muted);cursor:pointer;font-size:12px;"><i class="fas fa-times"></i></button>` : ''}
          </div>
        </div>
        <div class="agent-plan-progress-bar"><div class="agent-plan-progress-fill" style="width:${pct}%"></div></div>
        <div class="agent-plan-steps">${stepsHtml}</div>
        ${reviseBarHtml}
        ${actionsHtml}
      </div>
    `;

    const viewBtn = slot.querySelector('#ap-chat-view-plan-btn');
    if (viewBtn) {
      viewBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        _modalEditMode = false;
        openPlanModal(plan);
      });
    }

    const hdr = slot.querySelector('#ap-chat-toggle-header');
    if (hdr) {
      hdr.addEventListener('click', (e) => {
        if (e.target.closest('#ap-chat-hide-btn') || e.target.closest('#ap-chat-view-plan-btn')) return;
        _collapsed = !_collapsed;
        const card = slot.querySelector('#agent-plan-active-card');
        if (card) card.classList.toggle('is-collapsed', _collapsed);
        const chev = slot.querySelector('#ap-chat-chevron');
        if (chev) {
          chev.classList.toggle('fa-chevron-right', _collapsed);
          chev.classList.toggle('fa-chevron-down', !_collapsed);
        }
      });
    }

    const hideBtn = slot.querySelector('#ap-chat-hide-btn');
    if (hideBtn) {
      hideBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        slot.innerHTML = '';
      });
    }

    const collectSelectedSteps = () => {
      const cbs = Array.from(slot.querySelectorAll('.ap-confirm-step-cb'));
      if (!cbs.length) return plan.steps;
      const checked = cbs
        .filter((cb) => cb.checked)
        .map((cb) => plan.steps[Number(cb.dataset.idx)])
        .filter(Boolean);
      return checked.length ? checked : plan.steps;
    };

    const coderSelect = slot.querySelector('#ap-chat-coder-preset-select');
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

    const reviseToggleBtn = slot.querySelector('#ap-chat-revise-toggle-btn');
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

    const reviseCloseBtn = slot.querySelector('#ap-chat-revise-close-btn');
    if (reviseCloseBtn) {
      reviseCloseBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        _reviseOpen = false;
        renderPlanCard(_lastPlan, _lastHandlers);
      });
    }

    const reviseInput = slot.querySelector('#ap-chat-revise-input');
    const reviseSendBtn = slot.querySelector('#ap-chat-revise-send-btn');
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

    const approveBtn = slot.querySelector('#ap-chat-approve-btn');
    if (approveBtn && _lastHandlers?.onExecute) {
      approveBtn.addEventListener('click', () => {
        if (approveBtn.disabled) return;
        setLaunching(plan.plan_id, true, 'execute');
        const chosenPreset = coderSelect?.value || '';
        _lastHandlers.onExecute(plan, collectSelectedSteps(), chosenPreset);
      });
    }

    const rejectBtn = slot.querySelector('#ap-chat-reject-btn');
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

  ns.widget = { renderPlanCard, syncPresetOptions, setLaunching, openPlanModal, closePlanModal };
})();
