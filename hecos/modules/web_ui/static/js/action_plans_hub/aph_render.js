/**
 * MODULE: action_plans_hub/aph_render.js
 * PURPOSE: Renders configuration controls and live Plan/Checkpoint tables in Central Hub -> SYSTEM.
 */

(function () {
  const ns = (window._HecosActionPlansHub = window._HecosActionPlansHub || {});

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

  function _fmtDate(ts) {
    const n = Number(ts || 0);
    if (!n) return '—';
    return new Date(n * 1000).toLocaleString();
  }

  function _badge(status) {
    const st = String(status || '').toLowerCase();
    const map = {
      completed: '#10b981',
      done: '#10b981',
      running: '#38bdf8',
      awaiting_approval: '#f59e0b',
      interrupted: '#f59e0b',
      failed: '#ef4444',
      cancelled: '#94a3b8',
      dismissed: '#94a3b8',
    };
    const color = map[st] || '#94a3b8';
    return `<span style="display:inline-block;padding:2px 8px;border-radius:999px;font-size:10.5px;font-weight:700;background:${color}22;border:1px solid ${color}66;color:${color};text-transform:uppercase;">${_esc(st)}</span>`;
  }

  function populateConfig(cfg) {
    const c = cfg || {};
    const setCk = (id, val) => { const el = document.getElementById(id); if (el) el.checked = !!val; };
    const setVal = (id, val) => { const el = document.getElementById(id); if (el) el.value = val; };

    setVal('ap-plan-mode', c.plan_mode || 'auto');
    setVal('ap-min-steps', c.auto_plan_min_steps_hint ?? 3);
    setCk('ap-expose-presets', c.expose_tools_in_custom_presets !== false);
    setVal('ap-approval-timeout', c.approval_timeout_seconds ?? 300);

    setCk('ap-ckpt-enabled', c.checkpoint_enabled !== false);
    setCk('ap-resume-banner', c.resume_banner_enabled !== false);
    setVal('ap-resume-extra-steps', c.resume_extra_steps ?? 10);
    setVal('ap-retention-days', c.retention_days ?? 14);
    setCk('ap-flows-ckpt', c.flows_checkpoint_enabled !== false);
  }

  function readConfigFromForm() {
    const getCk = (id, defVal) => {
      const el = document.getElementById(id);
      return el ? !!el.checked : defVal;
    };
    const getNum = (id, defVal) => {
      const el = document.getElementById(id);
      const n = el ? parseInt(el.value, 10) : NaN;
      return Number.isFinite(n) ? n : defVal;
    };
    const modeEl = document.getElementById('ap-plan-mode');
    return {
      plan_mode: modeEl ? modeEl.value : 'auto',
      auto_plan_min_steps_hint: getNum('ap-min-steps', 3),
      expose_tools_in_custom_presets: getCk('ap-expose-presets', true),
      approval_timeout_seconds: getNum('ap-approval-timeout', 300),
      checkpoint_enabled: getCk('ap-ckpt-enabled', true),
      resume_banner_enabled: getCk('ap-resume-banner', true),
      resume_extra_steps: getNum('ap-resume-extra-steps', 10),
      retention_days: getNum('ap-retention-days', 14),
      flows_checkpoint_enabled: getCk('ap-flows-ckpt', true),
    };
  }

  function renderTables(data, handlers) {
    const plansEl = document.getElementById('ap-plans-list');
    const agentEl = document.getElementById('ap-agent-ckpts-list');
    const flowEl = document.getElementById('ap-flow-ckpts-list');
    const stepsUnit = _tr('ap_unit_steps', 'steps');
    const nodesUnit = _tr('ap_unit_nodes', 'nodes');

    if (plansEl) {
      const plans = data.plans || [];
      const delTitle = _tr('ap_btn_delete_plan', 'Delete plan');
      const viewTitle = _tr('ap_btn_view_plan', 'Open in Plan Viewer');
      const expTitle = _tr('ap_btn_export_plan', 'Download Markdown (.md)');
      plansEl.innerHTML = plans.length ? plans.map((p) => {
        const steps = p.steps || [];
        const done = steps.filter((s) => s.status === 'done' || s.status === 'skipped').length;
        const pidEsc = _esc(p.plan_id);
        const sidEsc = _esc(p.source_id || '');
        const viewerHref = `/action-plan-viewer?plan_id=${encodeURIComponent(p.plan_id || '')}&sid=${encodeURIComponent(p.source_id || '')}`;
        const exportHref = `/api/action-plans/${encodeURIComponent(p.plan_id || '')}/export?format=md`;
        const mediaTag = p.media_file ? ` · <code>media/action_plans/${_esc(p.media_file)}</code>` : '';
        return `
          <div style="display:flex;justify-content:space-between;align-items:center;gap:10px;padding:10px 12px;border:1px solid var(--border-color);border-radius:8px;background:var(--bg3, rgba(255,255,255,0.02));">
            <div style="min-width:0;flex:1;">
              <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
                ${_badge(p.status)}
                <strong style="font-size:13px;">${_esc(p.title)}</strong>
                <span style="font-size:11px;color:var(--muted);">${done}/${steps.length} ${_esc(stepsUnit)} · ${_esc(p.scope || 'agent')}</span>
              </div>
              <div style="font-size:11px;color:var(--muted);margin-top:3px;word-break:break-word;">ID: ${pidEsc} · ${_fmtDate(p.updated_at)}${mediaTag}</div>
            </div>
            <div style="display:flex;gap:6px;flex-shrink:0;">
              <a href="${viewerHref}" target="_blank" rel="noopener" class="btn btn-xs btn-outline" data-ap-view-plan="${pidEsc}" data-ap-view-sid="${sidEsc}" title="${_esc(viewTitle)}"><i class="fas fa-up-right-from-square"></i></a>
              <a href="${exportHref}" class="btn btn-xs btn-outline" title="${_esc(expTitle)}"><i class="fas fa-file-export"></i></a>
              <button type="button" class="btn btn-xs btn-outline" data-ap-del-plan="${pidEsc}" title="${_esc(delTitle)}"><i class="fas fa-trash"></i></button>
            </div>
          </div>
        `;
      }).join('') : `<div style="font-size:12px;color:var(--muted);">${_esc(_tr('ap_empty_plans', 'No Action Plans recorded.'))}</div>`;

      plansEl.querySelectorAll('[data-ap-del-plan]').forEach((btn) => {
        btn.addEventListener('click', () => handlers?.onDeletePlan?.(btn.dataset.apDelPlan));
      });
    }

    if (agentEl) {
      const ckpts = data.agent_checkpoints || [];
      const delTitle = _tr('ap_btn_delete_ckpt', 'Delete checkpoint');
      agentEl.innerHTML = ckpts.length ? ckpts.map((c) => `
        <div style="display:flex;justify-content:space-between;align-items:center;gap:10px;padding:10px 12px;border:1px solid var(--border-color);border-radius:8px;background:var(--bg3, rgba(255,255,255,0.02));">
          <div style="min-width:0;flex:1;">
            <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
              ${_badge(c.status)}
              <span style="font-size:12.5px;font-weight:600;">${_esc(_tr('ar_unit_iteration', 'Iteration'))} ${Number(c.iteration || 0)}/${Number(c.max_iterations || 25)}</span>
              ${c.model_label ? `<span style="font-size:11px;color:var(--muted);">· ${_esc(c.model_label)}</span>` : ''}
              ${c.reason ? `<span style="font-size:11px;color:var(--muted);">· ${_esc(c.reason)}</span>` : ''}
            </div>
            <div style="font-size:11.5px;color:var(--muted);margin-top:3px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${_esc(c.user_preview || c.session_id)}</div>
            <div style="font-size:10.5px;color:var(--muted);margin-top:2px;">Session: ${_esc(c.session_id)} · ${_fmtDate(c.updated_at)}</div>
          </div>
          <button type="button" class="btn btn-xs btn-outline" data-ap-del-agent="${_esc(c.session_id)}" title="${_esc(delTitle)}"><i class="fas fa-trash"></i></button>
        </div>
      `).join('') : `<div style="font-size:12px;color:var(--muted);">${_esc(_tr('ap_empty_agent_ckpts', 'No Agent Checkpoints saved.'))}</div>`;

      agentEl.querySelectorAll('[data-ap-del-agent]').forEach((btn) => {
        btn.addEventListener('click', () => handlers?.onDeleteAgentCkpt?.(btn.dataset.apDelAgent));
      });
    }

    if (flowEl) {
      const fckpts = data.flow_checkpoints || [];
      const resumeLbl = _tr('ap_btn_resume', 'Resume');
      const delTitle = _tr('ap_btn_delete_ckpt', 'Delete checkpoint');
      flowEl.innerHTML = fckpts.length ? fckpts.map((f) => {
        const resumable = f.status === 'running' || f.status === 'interrupted';
        return `
          <div style="display:flex;justify-content:space-between;align-items:center;gap:10px;padding:10px 12px;border:1px solid var(--border-color);border-radius:8px;background:var(--bg3, rgba(255,255,255,0.02));">
            <div style="min-width:0;flex:1;">
              <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
                ${_badge(f.status)}
                <strong style="font-size:12.5px;">${_esc(f.flow_name || f.flow_id)}</strong>
                <span style="font-size:11px;color:var(--muted);">${Number(f.completed_count || 0)}/${Number(f.total_steps || 0)} ${_esc(nodesUnit)}</span>
              </div>
              <div style="font-size:11px;color:var(--muted);margin-top:3px;">Run: ${_esc(f.run_id)} · ${_fmtDate(f.updated_at)}${f.error_msg ? ` · ${_esc(f.error_msg)}` : ''}</div>
            </div>
            <div style="display:flex;gap:6px;">
              ${resumable ? `<button type="button" class="btn btn-xs btn-primary" data-ap-resume-flow="${_esc(f.flow_id)}" data-ap-resume-run="${_esc(f.run_id)}"><i class="fas fa-play"></i> ${_esc(resumeLbl)}</button>` : ''}
              <button type="button" class="btn btn-xs btn-outline" data-ap-del-flow="${_esc(f.run_id)}" title="${_esc(delTitle)}"><i class="fas fa-trash"></i></button>
            </div>
          </div>
        `;
      }).join('') : `<div style="font-size:12px;color:var(--muted);">${_esc(_tr('ap_empty_flow_ckpts', 'No Flow Checkpoints saved.'))}</div>`;

      flowEl.querySelectorAll('[data-ap-resume-flow]').forEach((btn) => {
        btn.addEventListener('click', () => handlers?.onResumeFlow?.(btn.dataset.apResumeFlow, btn.dataset.apResumeRun));
      });
      flowEl.querySelectorAll('[data-ap-del-flow]').forEach((btn) => {
        btn.addEventListener('click', () => handlers?.onDeleteFlowCkpt?.(btn.dataset.apDelFlow));
      });
    }
  }

  ns.render = { populateConfig, readConfigFromForm, renderTables };
})();
