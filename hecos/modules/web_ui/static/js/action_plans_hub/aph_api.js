/**
 * MODULE: action_plans_hub/aph_api.js
 * PURPOSE: API client for Core Action Plans & Checkpoints panel in Central Hub -> SISTEMA.
 */

(function () {
  const ns = (window._HecosActionPlansHub = window._HecosActionPlansHub || {});

  async function _jsonFetch(url, opts = {}) {
    const resp = await fetch(url, opts);
    const data = await resp.json().catch(() => ({ ok: false, error: `HTTP ${resp.status}` }));
    if (!resp.ok || data.ok === false) {
      throw new Error(data.error || `HTTP ${resp.status}`);
    }
    return data;
  }

  ns.api = {
    fetchAll: () => _jsonFetch('/api/action-plans'),
    saveConfig: (cfg) => _jsonFetch('/api/action-plans/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(cfg),
    }),
    deletePlan: (planId) => _jsonFetch(`/api/action-plans/${encodeURIComponent(planId)}`, { method: 'DELETE' }),
    purge: (payload) => _jsonFetch('/api/action-plans/checkpoints/purge', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload || { type: 'expired' }),
    }),
    resumeFlow: (flowId, runId) => _jsonFetch(`/api/flows/${encodeURIComponent(flowId)}/resume`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ run_id: runId || '' }),
    }),
  };
})();
