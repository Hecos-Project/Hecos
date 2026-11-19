/**
 * MODULE: action_plans_chat/apc_bootstrap.js
 * PURPOSE: Connects chat SSE streams, session navigation, and 1-click Plan Execution
 *          ("Execute Plan" / "Continue Plan" + "Run with Coder" preset selector)
 *          to the Action Plan widget.
 */

(function () {
  const ns = (window._HecosActionPlanChat = window._HecosActionPlanChat || {});

  function _tr(key, fallbackEn) {
    const val = (window.I18N && window.I18N[key]) || (typeof window.t === 'function' ? window.t(key) : '');
    return (val && val !== key) ? val : fallbackEn;
  }

  function _buildExecutionPrompt(plan) {
    const stepsLines = (plan.steps || [])
      .map((s, idx) => {
        const mark = s.status === 'done' ? '✓' : (s.status === 'running' ? '▶' : ' ');
        const filesTxt = (Array.isArray(s.files) && s.files.length) ? ` [files: ${s.files.slice(0, 4).join(', ')}]` : '';
        const detailTxt = s.details ? ` — ${s.details}` : '';
        const note = s.notes ? ` (${s.notes})` : '';
        return `  [${mark}] Step ${s.index || idx + 1}: ${s.title}${filesTxt}${detailTxt}${note}`;
      })
      .join('\n');
    const goalLine = plan.goal ? `Goal: ${plan.goal}\n\n` : '';
    const verifLine = plan.verification_plan ? `\nVerification Plan:\n${plan.verification_plan}\n` : '';
    return (
      `Execute the active Implementation Plan "${plan.title || 'Execution Plan'}" (ID: ${plan.plan_id}, v${plan.revision || 1}) step by step.\n\n` +
      goalLine +
      `Steps:\n${stepsLines}\n` +
      verifLine +
      `\nEXECUTION INSTRUCTIONS:\n` +
      `1. Do NOT call \`ACTION_PLANS__create_plan\` again — this plan is already active.\n` +
      `2. Follow the Architectural Blueprint specifications in the system prompt (file paths, schemas, routes, UI, and tests).\n` +
      `3. First check existing workspace files on disk (do not rewrite files already completed unless broken), and mark any already-completed step with \`ACTION_PLANS__update_step(step_index=<N>, status="done")\`.\n` +
      `4. Execute each remaining pending/running step in order using real \`EXECUTOR__*\` tools, and call \`ACTION_PLANS__update_step(step_index=<N>, status="done", notes="...")\` immediately after finishing EACH step.\n` +
      `5. Once all steps are verified on disk, call \`ACTION_PLANS__complete_plan(summary="...")\` and summarize the created/modified file:/// links.`
    );
  }

  async function _switchSessionPresetIfNeeded(presetId) {
    const cleanId = String(presetId || '').trim();
    const currentId = String(window.sfState?.activeSoulId || '').trim();
    if (!cleanId || cleanId === currentId) {
      return { switched: false, presetId: currentId, presetName: '' };
    }

    const found = (window.sfState?.souls || []).find((s) => s?.meta?.id === cleanId);
    const presetName = found?.meta?.name || cleanId;

    try {
      if (typeof window.sfSelectSessionSoul === 'function') {
        await window.sfSelectSessionSoul(cleanId);
      } else {
        const sid = ns.api ? ns.api.resolveSid() : '';
        await fetch('/api/souls/activate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ soul_id: cleanId, session_id: sid || 'global' }),
        });
      }
      if (typeof window.showToast === 'function') {
        window.showToast(`💻 Preset switched to ${presetName}`);
      }
      return { switched: true, presetId: cleanId, presetName };
    } catch (e) {
      console.warn('[ActionPlanChat] Preset switch error:', e);
      return { switched: false, presetId: cleanId, presetName };
    }
  }

  async function executePlanInChat(plan, opts = {}) {
    if (!plan || window.isStreaming) return;
    if (window.hecosPlanFirstMode && typeof window.setPlanFirstMode === 'function') {
      window.setPlanFirstMode(false, true);
    }
    const chosenPreset = String(opts.coderPresetId || '').trim();
    const currentActiveId = String(window.sfState?.activeSoulId || '').trim();
    const needsSwitch = !!(chosenPreset && chosenPreset !== currentActiveId);

    let presetLabel = '';
    if (needsSwitch) {
      const sw = await _switchSessionPresetIfNeeded(chosenPreset);
      presetLabel = sw.presetName || chosenPreset;
    } else if (chosenPreset || currentActiveId) {
      const effId = chosenPreset || currentActiveId;
      const found = (window.sfState?.souls || []).find((s) => s?.meta?.id === effId);
      presetLabel = found?.meta?.name || effId;
    }

    const actionWord = (plan.status === 'awaiting_approval' || plan.status === 'draft')
      ? 'Execute Action Plan'
      : 'Continue Action Plan';
    const presetTag = presetLabel ? ` (\`${presetLabel}\`)` : '';
    const visibleMsg = `▶️ **${actionWord}${presetTag}:** *${plan.title || plan.plan_id}*`;
    const execPrompt = _buildExecutionPrompt(plan);

    if (typeof window.sendInternalMessage === 'function') {
      await window.sendInternalMessage(execPrompt, {
        executePlanId: plan.plan_id,
        coderPresetId: needsSwitch ? chosenPreset : '',
        visibleUserBubble: visibleMsg,
      });
    }
  }

  async function revisePlanInChat(plan, feedback) {
    const cleanFb = String(feedback || '').trim();
    if (!plan || !cleanFb || window.isStreaming) return;
    const revPrompt =
      `Revise the active Implementation Plan "${plan.title || 'Implementation Plan'}" (ID: ${plan.plan_id}, v${plan.revision || 1}) ` +
      `according to the user's feedback below.\n\n` +
      `USER FEEDBACK:\n${cleanFb}\n\n` +
      `Call \`ACTION_PLANS__revise_plan(plan_id="${plan.plan_id}", revision_note=..., title=..., goal=..., plan_markdown=..., steps=..., verification_plan=...)\` ` +
      `with the full updated Implementation Plan and stop without editing files on disk.`;
    const visibleMsg = `✏️ **Revise Plan (*${plan.title || plan.plan_id}*):** ${cleanFb}`;

    if (typeof window.sendInternalMessage === 'function') {
      await window.sendInternalMessage(revPrompt, {
        planOnly: true,
        revisePlanId: plan.plan_id,
        visibleUserBubble: visibleMsg,
      });
    }
  }

  function _handlers() {
    return {
      onSelectPreset: async (chosenPreset) => {
        if (!chosenPreset) return;
        await _switchSessionPresetIfNeeded(chosenPreset);
      },
      onExecute: async (plan, selectedSteps, chosenPreset) => {
        if (!ns.api) return;
        ns.widget?.setLaunching?.(plan.plan_id, true, 'execute');
        let latestPlan = plan;
        try {
          const st = String(plan?.status || '').toLowerCase();
          const isConfirm = st === 'awaiting_approval' || st === 'draft';
          const cleanSteps = isConfirm
            ? (selectedSteps || []).map((s) => ({
              title: s.title,
              status: s.status === 'done' ? 'done' : 'pending',
              notes: s.notes || '',
              ...(Array.isArray(s.files) && s.files.length ? { files: s.files } : {}),
              ...(s.details ? { details: s.details } : {}),
            }))
            : null;
          const res = await ns.api.approvePlan(plan.plan_id, cleanSteps);
          latestPlan = res?.plan || { ...plan, status: 'running', ...(cleanSteps ? { steps: cleanSteps } : {}) };
          renderPlan(latestPlan);
          if (!res?.resumed_gate) {
            await executePlanInChat(latestPlan, { coderPresetId: chosenPreset || '' });
          }
        } finally {
          ns.widget?.setLaunching?.(plan.plan_id, false);
          renderPlan(latestPlan);
        }
      },
      onRevise: async (plan, feedback) => {
        const cleanFb = String(feedback || '').trim();
        if (!plan || !cleanFb) return;
        ns.widget?.setLaunching?.(plan.plan_id, true, 'revise');
        try {
          await revisePlanInChat(plan, cleanFb);
        } finally {
          ns.widget?.setLaunching?.(plan.plan_id, false);
          renderPlan(plan);
        }
      },
      onSaveManualRevision: async (plan, payload) => {
        if (!ns.api || !plan) return null;
        const res = await ns.api.savePlanRevision(plan.plan_id, payload || {});
        if (res && res.ok && res.plan) {
          renderPlan(res.plan);
          if (typeof window.showToast === 'function') {
            window.showToast(`💾 ${_tr('ap_chat_modal_saved', 'Implementation Plan saved.')}`);
          }
          return res.plan;
        }
        return null;
      },
      onReject: async (plan) => {
        if (!ns.api) return;
        await ns.api.rejectPlan(plan.plan_id, _tr('ap_chat_rejected_reason', 'Cancelled by user in chat'));
        if (window.AgentResume && typeof window.AgentResume.dismissActive === 'function') {
          try {
            await window.AgentResume.dismissActive(plan.source_id || '');
          } catch (_) { }
        }
        clear();
        if (window.AgentResume && typeof window.AgentResume.refreshBanner === 'function') {
          window.AgentResume.refreshBanner(plan.source_id || '');
        }
      },
    };
  }

  function renderPlan(plan) {
    if (!ns.widget) return;
    ns.widget.renderPlanCard(plan, _handlers());
    const st = String(plan?.status || '').toLowerCase();
    const isActive = !!(plan && Array.isArray(plan.steps) && plan.steps.length &&
      ['awaiting_approval', 'draft', 'running', 'interrupted', 'paused'].includes(st));
    if (isActive) {
      const resumeSlot = document.getElementById('agent-resume-slot');
      if (resumeSlot) resumeSlot.innerHTML = '';
    } else if (plan && ['completed', 'cancelled', 'failed'].includes(st)) {
      if (window.AgentResume && typeof window.AgentResume.refreshBanner === 'function') {
        window.AgentResume.refreshBanner(plan.source_id || '');
      }
    }
  }

  function onPresetStateUpdated() {
    if (ns.widget && typeof ns.widget.syncPresetOptions === 'function') {
      ns.widget.syncPresetOptions();
    }
  }

  function handleSseEvent(ev) {
    if (!ev || ev.type !== 'action_plan' || !ev.plan) return;
    renderPlan(ev.plan);
  }

  async function refreshForSession(explicitSid = '') {
    if (!ns.api || !ns.widget) return;
    const sid = ns.api.resolveSid(explicitSid);
    if (!sid) return;
    try {
      const plan = await ns.api.fetchActivePlan(sid);
      const st = String(plan?.status || '').toLowerCase();
      if (plan && ['awaiting_approval', 'draft', 'running', 'interrupted', 'paused'].includes(st)) {
        renderPlan(plan);
      } else if (!window.isStreaming) {
        ns.widget.renderPlanCard(null, _handlers());
      }
    } catch (_) { }
  }

  function clear() {
    if (ns.widget) ns.widget.renderPlanCard(null, _handlers());
  }

  window.ActionPlanChat = {
    handleSseEvent,
    refreshForSession,
    onPresetStateUpdated,
    clear,
    renderPlan,
    executePlanInChat,
    revisePlanInChat,
  };

  document.addEventListener('DOMContentLoaded', () => {
    setTimeout(() => refreshForSession(), 750);
  });
})();
