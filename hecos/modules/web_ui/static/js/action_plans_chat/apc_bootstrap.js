/**
 * MODULE: action_plans_chat/apc_bootstrap.js
 * PURPOSE: Connects chat SSE streams & session navigation to the Action Plan widget.
 */

(function () {
  const ns = (window._HecosActionPlanChat = window._HecosActionPlanChat || {});

  function _tr(key, fallbackEn) {
    const val = (window.I18N && window.I18N[key]) || (typeof window.t === 'function' ? window.t(key) : '');
    return (val && val !== key) ? val : fallbackEn;
  }

  function _handlers() {
    return {
      onApprove: async (plan, selectedSteps) => {
        if (!ns.api) return;
        const cleanSteps = (selectedSteps || []).map((s) => ({ title: s.title, status: 'pending' }));
        await ns.api.approvePlan(plan.plan_id, cleanSteps);
      },
      onReject: async (plan) => {
        if (!ns.api) return;
        await ns.api.rejectPlan(plan.plan_id, _tr('ap_chat_rejected_reason', 'Cancelled by user in chat'));
      },
    };
  }

  function renderPlan(plan) {
    if (!ns.widget) return;
    ns.widget.renderPlanCard(plan, _handlers());
  }

  function handleSseEvent(ev) {
    if (!ev || ev.type !== 'action_plan' || !ev.plan) return;
    renderPlan(ev.plan);
  }

  async function refreshForSession(explicitSid = '') {
    if (!ns.api || !ns.widget) return;
    try {
      const plan = await ns.api.fetchActivePlan(explicitSid);
      const st = String(plan?.status || '').toLowerCase();
      if (plan && ['awaiting_approval', 'running', 'interrupted', 'paused'].includes(st)) {
        renderPlan(plan);
      } else if (!window.isStreaming) {
        ns.widget.renderPlanCard(null, _handlers());
      }
    } catch (_) {}
  }

  function clear() {
    if (ns.widget) ns.widget.renderPlanCard(null, _handlers());
  }

  window.ActionPlanChat = { handleSseEvent, refreshForSession, clear, renderPlan };

  document.addEventListener('DOMContentLoaded', () => {
    setTimeout(() => refreshForSession(), 750);
  });
})();
