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

  function _findNextPendingStep(plan) {
    const steps = Array.isArray(plan?.steps) ? plan.steps : [];
    for (let i = 0; i < steps.length; i++) {
      const st = String(steps[i]?.status || 'pending').toLowerCase();
      if (st !== 'done' && st !== 'skipped') {
        return { index: Number(steps[i]?.index || i + 1), step: steps[i] };
      }
    }
    return null;
  }

  function _buildExecutionPrompt(plan, singleStepIndex = 0) {
    const stepsLines = (plan.steps || [])
      .map((s, idx) => {
        const mark = s.status === 'done' ? '✓' : (s.status === 'running' ? '▶' : ' ');
        const filesTxt = (Array.isArray(s.files) && s.files.length) ? ` [items: ${s.files.slice(0, 4).join(', ')}]` : '';
        const detailTxt = s.details ? ` — ${s.details}` : '';
        const note = s.notes ? ` (${s.notes})` : '';
        return `  [${mark}] Step ${s.index || idx + 1}: ${s.title}${filesTxt}${detailTxt}${note}`;
      })
      .join('\n');
    const goalLine = plan.goal ? `Goal: ${plan.goal}\n\n` : '';
    const verifLine = plan.verification_plan ? `\nVerification / Completion Criteria:\n${plan.verification_plan}\n` : '';
    const stepNum = Number(singleStepIndex || 0);

    if (stepNum > 0) {
      const targetStep = (plan.steps || []).find((s, i) => Number(s.index || i + 1) === stepNum);
      const stepLabel = targetStep ? `"${targetStep.title}"` : `#${stepNum}`;
      return (
        `Execute ONLY Step ${stepNum} (${stepLabel}) of the active Action Plan "${plan.title || 'Action Plan'}" (ID: ${plan.plan_id}, v${plan.revision || 1}).\n\n` +
        goalLine +
        `Plan Overview:\n${stepsLines}\n` +
        `\nSINGLE-STEP EXECUTION INSTRUCTIONS:\n` +
        `1. Do NOT call \`ACTION_PLANS__create_plan\` again — this plan is already active.\n` +
        `2. Follow the Blueprint specifications in the system prompt and use the tools/capabilities configured in your active Global Preset.\n` +
        `3. Complete ONLY Step ${stepNum}, then call \`ACTION_PLANS__update_step(step_index=${stepNum}, status="done", notes="...")\` and STOP immediately so the user can review the output before running the next step.`
      );
    }

    return (
      `Execute the active Action Plan "${plan.title || 'Action Plan'}" (ID: ${plan.plan_id}, v${plan.revision || 1}) step by step.\n\n` +
      goalLine +
      `Steps:\n${stepsLines}\n` +
      verifLine +
      `\nEXECUTION INSTRUCTIONS:\n` +
      `1. Do NOT call \`ACTION_PLANS__create_plan\` again — this plan is already active.\n` +
      `2. Follow the Plan Blueprint specifications in the system prompt and use the tools/directives of your active Global Preset.\n` +
      `3. Execute each remaining pending/running step in order, and call \`ACTION_PLANS__update_step(step_index=<N>, status="done", notes="...")\` immediately after finishing EACH step.\n` +
      `4. Once all steps are completed and verified, call \`ACTION_PLANS__complete_plan(summary="...")\` and summarize the results (with file:/// links for any files created).`
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

    const singleStepIndex = Number(opts.singleStepIndex || 0);
    const presetTag = presetLabel ? ` (\`${presetLabel}\`)` : '';
    let visibleMsg = '';
    if (singleStepIndex > 0) {
      const targetStep = (plan.steps || []).find((s, i) => Number(s.index || i + 1) === singleStepIndex);
      const stepTitle = targetStep?.title ? ` — *${targetStep.title}*` : '';
      visibleMsg = `⏭️ **Execute Step ${singleStepIndex}${presetTag}:** *${plan.title || plan.plan_id}*${stepTitle}`;
    } else {
      const actionWord = (plan.status === 'awaiting_approval' || plan.status === 'draft')
        ? 'Execute Action Plan'
        : 'Continue Action Plan';
      visibleMsg = `▶️ **${actionWord}${presetTag}:** *${plan.title || plan.plan_id}*`;
    }
    const execPrompt = _buildExecutionPrompt(plan, singleStepIndex);

    if (typeof window.sendInternalMessage === 'function') {
      await window.sendInternalMessage(execPrompt, {
        executePlanId: plan.plan_id,
        executeStepIndex: singleStepIndex,
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
        _broadcastSync(plan);
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
      onExecuteNextStep: async (plan, selectedSteps, chosenPreset) => {
        if (!ns.api || !plan) return;
        ns.widget?.setLaunching?.(plan.plan_id, true, 'execute');
        _broadcastSync(plan);
        let latestPlan = plan;
        try {
          const st = String(plan?.status || '').toLowerCase();
          const isConfirm = st === 'awaiting_approval' || st === 'draft';
          if (isConfirm) {
            const cleanSteps = (selectedSteps || []).map((s) => ({
              title: s.title,
              status: s.status === 'done' ? 'done' : 'pending',
              notes: s.notes || '',
              ...(Array.isArray(s.files) && s.files.length ? { files: s.files } : {}),
              ...(s.details ? { details: s.details } : {}),
            }));
            const res = await ns.api.approvePlan(plan.plan_id, cleanSteps);
            latestPlan = res?.plan || { ...plan, status: 'running', steps: cleanSteps };
            renderPlan(latestPlan);
          }
          const next = _findNextPendingStep(latestPlan);
          if (next) {
            await executePlanInChat(latestPlan, {
              coderPresetId: chosenPreset || '',
              singleStepIndex: next.index,
            });
          }
        } finally {
          ns.widget?.setLaunching?.(plan.plan_id, false);
          renderPlan(latestPlan);
        }
      },
      onToggleStep: async (plan, stepIndex) => {
        if (!ns.api || !plan || !stepIndex) return;
        const res = await ns.api.togglePlanStep(plan.plan_id, stepIndex);
        if (res && res.ok && res.plan) {
          renderPlan(res.plan);
        }
      },
      onRevise: async (plan, feedback) => {
        const cleanFb = String(feedback || '').trim();
        if (!plan || !cleanFb) return;
        ns.widget?.setLaunching?.(plan.plan_id, true, 'revise');
        _broadcastSync(plan);
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
      onExport: async (plan, opts = {}) => exportPlanToDisk(plan, opts),
      onImport: async (opts = {}) => importPlanFromDisk(opts),
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

  function _collectPresetsForSync() {
    const allSouls = Array.isArray(window.sfState?.souls) ? window.sfState.souls : [];
    return allSouls
      .filter((s) => s?.meta?.id)
      .map((s) => ({
        id: String(s.meta.id).trim(),
        name: String(s.meta.name || s.meta.id).trim(),
        icon: String(s.meta.icon || '').trim(),
        model_name: String(s.model?.model_name || '').trim(),
        tags: Array.isArray(s.meta.tags) ? s.meta.tags.map((t) => String(t).toLowerCase()) : [],
      }));
  }

  function _buildSyncSnapshot(explicitPlan) {
    const widgetSnap = (ns.widget && typeof ns.widget.getStateSnapshot === 'function')
      ? ns.widget.getStateSnapshot()
      : {};
    const plan = explicitPlan !== undefined ? explicitPlan : (widgetSnap.plan || null);
    const sid = ns.api ? ns.api.resolveSid() : (plan?.source_id || '');
    const isStreamingNow = Boolean(
      window.isStreaming ||
      (sid && window.HecosChatStatus?.isSessionStreaming?.(sid))
    );
    return {
      plan,
      sessionId: sid,
      isStreaming: isStreamingNow,
      presets: _collectPresetsForSync(),
      activeSoulId: String(window.sfState?.activeSoulId || '').trim(),
      launchingPlanId: String(widgetSnap.launchingPlanId || ''),
      launchingMode: String(widgetSnap.launchingMode || 'execute'),
    };
  }

  function _broadcastSync(explicitPlan) {
    if (ns.detach && typeof ns.detach.broadcastPlanUpdate === 'function') {
      ns.detach.broadcastPlanUpdate(_buildSyncSnapshot(explicitPlan));
    }
  }

  function renderPlan(plan) {
    if (!ns.widget) return;
    ns.widget.renderPlanCard(plan, _handlers());
    _broadcastSync(plan);
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
    _broadcastSync();
  }

  function handleSseEvent(ev) {
    if (!ev || ev.type !== 'action_plan' || !ev.plan) return;
    const st = String(ev.plan.status || '').toLowerCase();
    if (st !== 'completed' && st !== 'cancelled') {
      ns.widget?.setPlanDismissed?.(ev.plan.plan_id, false);
    }
    renderPlan(ev.plan);
  }

  async function refreshForSession(explicitSid = '') {
    if (!ns.api || !ns.widget) return;
    const sid = ns.api.resolveSid(explicitSid);
    if (!sid) return;
    try {
      const plan = await ns.api.fetchActivePlan(sid);
      const st = String(plan?.status || '').toLowerCase();
      const dismissed = Boolean(plan?.plan_id && ns.widget?.isPlanDismissed?.(plan.plan_id));
      const keepVisible = plan && (
        ['awaiting_approval', 'draft', 'running', 'interrupted', 'paused'].includes(st) ||
        (['completed', 'failed'].includes(st) && !dismissed)
      );
      if (keepVisible) {
        renderPlan(plan);
      } else if (!window.isStreaming) {
        ns.widget.renderPlanCard(null, _handlers());
        ns.detach?.broadcastCleared?.(sid);
      }
    } catch (_) { }
  }

  function clear() {
    if (ns.widget) ns.widget.renderPlanCard(null, _handlers());
    const sid = ns.api ? ns.api.resolveSid() : '';
    ns.detach?.broadcastCleared?.(sid);
  }

  async function exportPlanToDisk(plan, opts = {}) {
    if (!ns.api || typeof ns.api.exportPlanNativeDialog !== 'function') return { ok: false };
    const target = plan || _buildSyncSnapshot().plan;
    if (!target) return { ok: false, error: 'No active plan' };
    const res = await ns.api.exportPlanNativeDialog(target, opts || {});
    if (res && res.cancelled) return res;
    if (res && res.ok) {
      if (typeof window.showToast === 'function') {
        window.showToast(`💾 ${_tr('ap_toast_exported', 'Plan exported:')} ${res.filename || target.title}`);
      }
    } else if (typeof window.showToast === 'function') {
      window.showToast(`⚠️ ${_tr('ap_toast_export_failed', 'Export failed:')} ${res?.error || 'error'}`);
    }
    return res;
  }

  async function importPlanFromDisk(opts = {}) {
    if (!ns.api || typeof ns.api.importPlanNativeDialog !== 'function') return { ok: false };
    const sid = ns.api.resolveSid(opts?.sourceId || '');
    const res = await ns.api.importPlanNativeDialog({ ...(opts || {}), sourceId: sid });
    if (res && res.cancelled) return res;
    if (res && res.ok && res.plan) {
      ns.widget?.setPlanDismissed?.(res.plan.plan_id, false);
      renderPlan(res.plan);
      if (typeof window.showToast === 'function') {
        window.showToast(`📂 ${_tr('ap_toast_imported', 'Plan imported:')} ${res.plan.title || res.filename || ''}`);
      }
    } else if (typeof window.showToast === 'function') {
      window.showToast(`⚠️ ${_tr('ap_toast_import_failed', 'Import failed:')} ${res?.error || 'error'}`);
    }
    return res;
  }

  function _initDetachBridge() {
    if (!ns.detach || typeof ns.detach.init !== 'function') return;
    ns.detach.init({
      onModeChanged: () => {
        if (ns.widget && typeof ns.widget.rerenderCurrent === 'function') {
          ns.widget.rerenderCurrent();
        }
      },
      onRequestState: () => _buildSyncSnapshot(),
      onRemoteExecute: async (msg) => {
        const snap = _buildSyncSnapshot();
        const plan = snap.plan;
        if (!plan || (msg.planId && plan.plan_id !== msg.planId)) return;
        const steps = Array.isArray(msg.steps) && msg.steps.length ? msg.steps : plan.steps;
        const chosenPreset = String(msg.coderPresetId || '').trim();
        await _handlers().onExecute(plan, steps, chosenPreset);
      },
      onRemoteRevise: async (msg) => {
        const snap = _buildSyncSnapshot();
        const plan = snap.plan;
        if (!plan || (msg.planId && plan.plan_id !== msg.planId)) return;
        const fb = String(msg.feedback || '').trim();
        if (!fb) return;
        await _handlers().onRevise(plan, fb);
      },
      onRemoteReject: async (msg) => {
        const snap = _buildSyncSnapshot();
        const plan = snap.plan;
        if (!plan || (msg.planId && plan.plan_id !== msg.planId)) return;
        await _handlers().onReject(plan);
      },
      onRemoteSelectPreset: async (msg) => {
        const chosenPreset = String(msg.presetId || '').trim();
        if (!chosenPreset) return;
        await _handlers().onSelectPreset(chosenPreset);
        _broadcastSync();
      },
      onRemoteManualSaved: (msg) => {
        if (msg && msg.plan) {
          renderPlan(msg.plan);
        }
      },
      onRemoteImported: (msg) => {
        if (msg && msg.plan) {
          renderPlan(msg.plan);
        }
      },
      onRemoteNextStep: async (msg) => {
        const snap = _buildSyncSnapshot();
        const plan = snap.plan;
        if (!plan || (msg.planId && plan.plan_id !== msg.planId)) return;
        const steps = Array.isArray(msg.steps) && msg.steps.length ? msg.steps : plan.steps;
        const chosenPreset = String(msg.coderPresetId || '').trim();
        await _handlers().onExecuteNextStep(plan, steps, chosenPreset);
      },
      onRemoteStepToggled: (msg) => {
        if (msg && msg.plan) {
          renderPlan(msg.plan);
        }
      },
    });
  }

  _initDetachBridge();

  window.ActionPlanChat = {
    handleSseEvent,
    refreshForSession,
    onPresetStateUpdated,
    clear,
    renderPlan,
    executePlanInChat,
    revisePlanInChat,
    exportActivePlan: (opts) => exportPlanToDisk(null, opts || {}),
    importPlanFromDisk,
    setFloating: () => ns.detach?.setFloating?.(),
    openPopout: (opts) => {
      const snap = _buildSyncSnapshot();
      if (!snap.plan) return false;
      return ns.detach?.openPopout?.(snap.plan, snap.sessionId, opts || {}) || false;
    },
    dockBack: (opts) => ns.detach?.dockBack?.(opts || {}),
    getDetachMode: () => ns.detach?.getMode?.() || 'docked',
  };

  document.addEventListener('DOMContentLoaded', () => {
    setTimeout(() => refreshForSession(), 750);
  });
})();
