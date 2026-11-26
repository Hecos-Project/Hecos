/**
 * MODULE: action_plans_hub/aph_bootstrap.js
 * PURPOSE: Event binding & refresh orchestrator for Central Hub -> SYSTEM -> Action Plans.
 */

(function () {
  const ns = (window._HecosActionPlansHub = window._HecosActionPlansHub || {});

  function _tr(key, fallbackEn) {
    const val = (window.I18N && window.I18N[key]) || (typeof window.t === 'function' ? window.t(key) : '');
    return (val && val !== key) ? val : fallbackEn;
  }

  function _toast(msg, isErr = false) {
    if (typeof window.showToast === 'function') window.showToast(msg, isErr);
  }

  async function refresh() {
    if (!ns.api || !ns.render) return;
    try {
      const data = await ns.api.fetchAll();
      ns.render.populateConfig(data.config || {});
      ns.render.renderTables(data, {
        onDeletePlan: async (planId) => {
          await ns.api.deletePlan(planId);
          _toast(_tr('ap_toast_plan_deleted', 'Plan deleted.'), false);
          await refresh();
        },
        onDeleteAgentCkpt: async (sid) => {
          await ns.api.purge({ type: 'agent', id: sid });
          _toast(_tr('ap_toast_session_ckpt_deleted', 'Session checkpoint deleted.'), false);
          await refresh();
        },
        onDeleteFlowCkpt: async (runId) => {
          await ns.api.purge({ type: 'flow', id: runId });
          _toast(_tr('ap_toast_flow_ckpt_deleted', 'Flow checkpoint deleted.'), false);
          await refresh();
        },
        onResumeFlow: async (flowId, runId) => {
          const res = await ns.api.resumeFlow(flowId, runId);
          _toast(`${_tr('ap_toast_flow_resumed', 'Flow resumed cleanly.')} (${flowId} · ${res.run_id})`, false);
          await refresh();
        },
      });
    } catch (err) {
      _toast(`Action Plans: ${err.message || err}`, true);
    }
  }

  async function save() {
    if (!ns.api || !ns.render) return;
    try {
      const payload = ns.render.readConfigFromForm();
      const res = await ns.api.saveConfig(payload);
      window.cfg = window.cfg || {};
      window.cfg.plugins = window.cfg.plugins || {};
      window.cfg.plugins.ACTION_PLANS = Object.assign({}, window.cfg.plugins.ACTION_PLANS || {}, res.config);
      _toast(_tr('ap_toast_cfg_saved', 'Action Plans & Checkpoints settings saved.'), false);
    } catch (err) {
      _toast(`${_tr('ap_toast_cfg_error', 'Error saving Action Plans settings:')} ${err.message || err}`, true);
    }
  }

  async function purgeExpired() {
    if (!ns.api || !ns.render) return;
    try {
      const cfg = ns.render.readConfigFromForm();
      const res = await ns.api.purge({ type: 'expired', retention_days: cfg.retention_days });
      const rem = res.removed || {};
      const tot = Number(rem.plans || 0) + Number(rem.agent_checkpoints || 0) + Number(rem.flow_checkpoints || 0);
      const tpl = _tr('ap_toast_purge_done', 'Cleanup completed (removed {count} items).');
      _toast(tpl.replace('{count}', String(tot)), false);
      await refresh();
    } catch (err) {
      _toast(`${_tr('ap_toast_purge_error', 'Cleanup error:')} ${err.message || err}`, true);
    }
  }

  function bindEvents() {
    const panel = document.getElementById('tab-action-plans');
    if (!panel || panel.dataset.apBound === 'true') return;
    panel.dataset.apBound = 'true';

    panel.querySelectorAll('input, select, textarea').forEach((el) => {
      el.addEventListener('change', () => { save(); });
    });
    const tplBtn = document.getElementById('ap-directive-template-btn');
    if (tplBtn) {
      tplBtn.addEventListener('click', () => {
        const dirEl = document.getElementById('ap-planning-directive');
        if (dirEl) {
          dirEl.value =
            'For complex multi-step tasks (>= {min_steps} steps: software projects, refactors, audits, or workflows): ' +
            'create a concise checklist FIRST via `ACTION_PLANS__create_plan(title=..., steps=[...])`, ' +
            'update progress with `ACTION_PLANS__update_step(step_index=..., status=\'done\'|\'running\'|\'failed\', notes=...)`, ' +
            'and finalize with `ACTION_PLANS__complete_plan(...)`. Skip planning for simple chat, questions, or direct image requests.';
          save();
        }
      });
    }
    const clrBtn = document.getElementById('ap-directive-clear-btn');
    if (clrBtn) {
      clrBtn.addEventListener('click', () => {
        const dirEl = document.getElementById('ap-planning-directive');
        if (dirEl) {
          dirEl.value = '';
          save();
        }
      });
    }
    const saveDirBtn = document.getElementById('ap-directive-save-btn');
    if (saveDirBtn) saveDirBtn.addEventListener('click', () => { save(); });
    const refBtn = document.getElementById('ap-refresh-btn');
    if (refBtn) refBtn.addEventListener('click', refresh);
    const purgeBtn = document.getElementById('ap-purge-btn');
    if (purgeBtn) purgeBtn.addEventListener('click', purgeExpired);
    const openFolderBtn = document.getElementById('ap-open-folder-btn');
    if (openFolderBtn) {
      openFolderBtn.addEventListener('click', async () => {
        try {
          const res = await ns.api.openFolder();
          _toast(`${_tr('ap_toast_folder_opened', 'Opened plans folder:')} ${res.path || 'media/action_plans'}`, false);
        } catch (err) {
          _toast(`Action Plans: ${err.message || err}`, true);
        }
      });
    }
  }

  window.ActionPlansHub = { refresh, save, purgeExpired, bindEvents };
  bindEvents();
  refresh();
})();
