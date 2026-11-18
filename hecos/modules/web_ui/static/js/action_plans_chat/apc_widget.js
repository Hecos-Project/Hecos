/**
 * MODULE: action_plans_chat/apc_widget.js
 * PURPOSE: Render live collapsible Action Plan checklist card in #agent-plan-slot.
 */

(function () {
  const ns = (window._HecosActionPlanChat = window._HecosActionPlanChat || {});
  let _collapsed = false;

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

  function _statusLabel(st) {
    const low = String(st || '').toLowerCase();
    const map = {
      awaiting_approval: _tr('ap_chat_st_awaiting', 'Awaiting Approval'),
      running: _tr('ap_chat_st_running', 'Active Plan'),
      completed: _tr('ap_chat_st_completed', 'Completed'),
      interrupted: _tr('ap_chat_st_interrupted', 'Interrupted'),
      failed: _tr('ap_chat_st_failed', 'Failed'),
      cancelled: _tr('ap_chat_st_cancelled', 'Cancelled'),
    };
    return map[low] || st || _tr('ap_chat_st_default', 'Plan');
  }

  function renderPlanCard(plan, handlers) {
    const slot = document.getElementById('agent-plan-slot');
    if (!slot) return;
    if (!plan || !Array.isArray(plan.steps) || !plan.steps.length) {
      slot.innerHTML = '';
      return;
    }

    const st = String(plan.status || 'running').toLowerCase();
    const isConfirm = st === 'awaiting_approval';
    const isCompleted = st === 'completed';
    const doneCount = plan.steps.filter((s) => s.status === 'done' || s.status === 'skipped').length;
    const pct = Math.round((doneCount / plan.steps.length) * 100);

    const cardCls = [
      'agent-plan-card',
      isConfirm ? 'is-confirm' : '',
      isCompleted ? 'is-completed' : '',
      (_collapsed && !isConfirm) ? 'is-collapsed' : '',
    ].filter(Boolean).join(' ');

    const stepsHtml = plan.steps.map((s, idx) => {
      const checkControl = isConfirm
        ? `<input type="checkbox" class="ap-confirm-step-cb" data-idx="${idx}" checked style="margin-top:2px;accent-color:#10b981;">`
        : _stepIcon(s.status);
      const note = s.notes ? `<span style="color:var(--muted);margin-left:6px;">— ${_esc(s.notes)}</span>` : '';
      return `
        <div class="agent-plan-step st-${_esc(s.status || 'pending')}">
          <span style="min-width:16px;text-align:center;">${checkControl}</span>
          <span><strong>${Number(s.index || idx + 1)}.</strong> ${_esc(s.title)}${note}</span>
        </div>
      `;
    }).join('');

    const approveLbl = _esc(_tr('ap_chat_btn_approve', 'Approve & Start'));
    const cancelLbl = _esc(_tr('ap_chat_btn_cancel', 'Cancel'));
    const hideTitle = _esc(_tr('ap_chat_btn_hide', 'Hide'));

    const actionsHtml = isConfirm ? `
      <div class="agent-plan-actions">
        <button type="button" class="agent-plan-btn-approve" id="ap-chat-approve-btn">
          <i class="fas fa-check"></i> ${approveLbl}
        </button>
        <button type="button" class="agent-plan-btn-reject" id="ap-chat-reject-btn">
          <i class="fas fa-times"></i> ${cancelLbl}
        </button>
      </div>
    ` : '';

    slot.innerHTML = `
      <div class="${cardCls}" id="agent-plan-active-card" data-plan-id="${_esc(plan.plan_id)}">
        <div class="agent-plan-header" id="ap-chat-toggle-header">
          <div class="agent-plan-title-row">
            <span class="agent-plan-status-pill">${_esc(_statusLabel(st))}</span>
            <span>${_esc(plan.title)}</span>
            <span style="font-size:11px;color:var(--muted);">(${doneCount}/${plan.steps.length} · ${pct}%)</span>
          </div>
          <div style="display:flex;align-items:center;gap:8px;">
            <i class="fas fa-chevron-${(_collapsed && !isConfirm) ? 'right' : 'down'}" style="font-size:11px;color:var(--muted);"></i>
            ${!isConfirm ? `<button type="button" id="ap-chat-hide-btn" title="${hideTitle}" style="background:none;border:none;color:var(--muted);cursor:pointer;font-size:12px;"><i class="fas fa-times"></i></button>` : ''}
          </div>
        </div>
        <div class="agent-plan-progress-bar"><div class="agent-plan-progress-fill" style="width:${pct}%"></div></div>
        <div class="agent-plan-steps">${stepsHtml}</div>
        ${actionsHtml}
      </div>
    `;

    const hdr = slot.querySelector('#ap-chat-toggle-header');
    if (hdr) {
      hdr.addEventListener('click', (e) => {
        if (e.target.closest('#ap-chat-hide-btn')) return;
        _collapsed = !_collapsed;
        const card = slot.querySelector('#agent-plan-active-card');
        if (card) card.classList.toggle('is-collapsed', _collapsed && !isConfirm);
      });
    }

    const hideBtn = slot.querySelector('#ap-chat-hide-btn');
    if (hideBtn) {
      hideBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        slot.innerHTML = '';
      });
    }

    const approveBtn = slot.querySelector('#ap-chat-approve-btn');
    if (approveBtn && handlers?.onApprove) {
      approveBtn.addEventListener('click', () => {
        approveBtn.disabled = true;
        const checked = Array.from(slot.querySelectorAll('.ap-confirm-step-cb'))
          .filter((cb) => cb.checked)
          .map((cb) => plan.steps[Number(cb.dataset.idx)])
          .filter(Boolean);
        handlers.onApprove(plan, checked.length ? checked : plan.steps);
      });
    }

    const rejectBtn = slot.querySelector('#ap-chat-reject-btn');
    if (rejectBtn && handlers?.onReject) {
      rejectBtn.addEventListener('click', () => {
        rejectBtn.disabled = true;
        handlers.onReject(plan);
      });
    }
  }

  ns.widget = { renderPlanCard };
})();
