/**
 * MODULE: action_plans_chat/apc_api.js
 * PURPOSE: API calls for Chat Action Plan widget (fetch active plan, approve, reject).
 */

(function () {
  const ns = (window._HecosActionPlanChat = window._HecosActionPlanChat || {});

  function _resolveSid(explicitSid) {
    return (
      explicitSid ||
      window.chatHistoryState?.activeSessionId ||
      localStorage.getItem('hecos_active_session_id') ||
      ''
    );
  }

  async function fetchActivePlan(explicitSid = '') {
    const sid = _resolveSid(explicitSid);
    if (!sid) return null;
    const resp = await fetch(`/api/action-plans?source_id=${encodeURIComponent(sid)}`);
    if (!resp.ok) return null;
    const data = await resp.json();
    return data.active_plan || null;
  }

  async function approvePlan(planId, editedSteps = null) {
    const body = editedSteps ? { steps: editedSteps } : {};
    const resp = await fetch(`/api/action-plans/${encodeURIComponent(planId)}/approve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    return await resp.json();
  }

  async function rejectPlan(planId, reason = 'cancelled by user') {
    const resp = await fetch(`/api/action-plans/${encodeURIComponent(planId)}/reject`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ reason }),
    });
    return await resp.json();
  }

  ns.api = { resolveSid: _resolveSid, fetchActivePlan, approvePlan, rejectPlan };
})();
