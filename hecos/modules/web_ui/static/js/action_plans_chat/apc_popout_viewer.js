/**
 * MODULE: action_plans_chat/apc_popout_viewer.js
 * PURPOSE: Standalone Pop-out Window / New-Tab Action Plan Viewer synchronized live
 *          with Hecos Chat via BroadcastChannel ('hecos_action_plan_sync') + REST fallback.
 */

(function () {
  const CHANNEL_NAME = 'hecos_action_plan_sync';
  const params = window.HECOS_VIEWER_PARAMS || {};
  const qs = new URLSearchParams(window.location.search || '');

  let _planId = String(params.planId || qs.get('plan_id') || '').trim();
  let _sessionId = String(params.sessionId || qs.get('sid') || '').trim();
  let _plan = null;
  let _isStreaming = false;
  let _launchingPlanId = '';
  let _launchingMode = 'execute';
  let _presets = [];
  let _activeSoulId = '';
  let _selectedPresetId = '';
  let _syncedWithChat = false;
  let _viewTab = 'split'; // 'split' | 'steps' | 'blueprint' (stacks vertically below 860px)
  let _editMode = false;
  let _editDraftMd = '';
  let _checkedIdxSet = null; // null => all checked
  let _channel = null;
  let _closedNotified = false;
  let _toastTimer = null;

  function _tr(key, fallbackEn) {
    const val = (window.I18N && window.I18N[key]) || '';
    return (val && val !== key) ? val : fallbackEn;
  }

  function _esc(s) {
    return String(s ?? '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function _showBannerToast(msg) {
    let el = document.getElementById('ap-viewer-toast');
    if (!el) {
      el = document.createElement('div');
      el.id = 'ap-viewer-toast';
      el.className = 'ap-viewer-toast';
      document.body.appendChild(el);
    }
    el.textContent = String(msg || '');
    el.classList.add('is-visible');
    clearTimeout(_toastTimer);
    _toastTimer = setTimeout(() => el.classList.remove('is-visible'), 2600);
  }

  function _post(msg) {
    if (!_channel) return;
    try {
      _channel.postMessage(msg);
    } catch (_) {}
  }

  function _notifyClosedOnce() {
    if (_closedNotified) return;
    _closedNotified = true;
    _post({
      type: 'viewer_closed',
      planId: _plan?.plan_id || _planId,
      sessionId: _plan?.source_id || _sessionId,
      ts: Date.now(),
    });
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
    if (plan.goal) parts.push(`## Goal\n\n${plan.goal}`);
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
    if (window.marked && typeof window.marked.parse === 'function') {
      html = window.marked.parse(src);
    } else {
      html = `<pre style="white-space:pre-wrap;margin:0;">${_esc(src)}</pre>`;
    }
    return _colorizePlanBadges(html);
  }

  function _shortModelName(rawModel) {
    const clean = String(rawModel || '').trim();
    return clean ? clean.split('/').pop() : '';
  }

  function _buildPresetOptionsHtml() {
    const planningSouls = [];
    const coderSouls = [];
    const otherSouls = [];
    for (const p of _presets) {
      const id = String(p?.id || '').trim();
      if (!id) continue;
      const name = String(p?.name || id).trim();
      const rawModel = String(p?.model_name || '').trim();
      const shortModel = _shortModelName(rawModel);
      const tags = Array.isArray(p?.tags) ? p.tags : [];
      const icon = String(p?.icon || '').trim();
      const isCoder = id.toLowerCase().includes('coder') || tags.includes('coding') || tags.includes('coder');
      const isPlanning = !isCoder && (
        id.toLowerCase().includes('plan') ||
        id.toLowerCase().includes('storyboard') ||
        tags.includes('planning') ||
        tags.includes('storyboard') ||
        tags.includes('image_gen')
      );
      const entry = { id, name, rawModel, shortModel, icon };
      if (isPlanning) planningSouls.push(entry);
      else if (isCoder) coderSouls.push(entry);
      else otherSouls.push(entry);
    }
    const allIds = new Set([
      ...planningSouls.map((p) => p.id),
      ...coderSouls.map((c) => c.id),
      ...otherSouls.map((o) => o.id),
    ]);
    const effectiveSelected = (_selectedPresetId && allIds.has(_selectedPresetId))
      ? _selectedPresetId
      : ((_activeSoulId && allIds.has(_activeSoulId)) ? _activeSoulId : '');

    const renderOpt = (item, fallbackPrefix = '') => {
      const pfx = item.icon ? `${item.icon} ` : fallbackPrefix;
      const disp = `${pfx}${item.name}${item.shortModel ? ` (${item.shortModel})` : ''}`;
      return `<option value="${_esc(item.id)}"${item.id === effectiveSelected ? ' selected' : ''}>${_esc(disp)}</option>`;
    };

    let html = `<option value=""${!effectiveSelected ? ' selected' : ''}>⚡ Current Chat Model</option>`;
    if (planningSouls.length) {
      html += `<optgroup label="Planning &amp; Creative Presets">${planningSouls.map((p) => renderOpt(p, '🗺️ ')).join('')}</optgroup>`;
    }
    if (coderSouls.length) {
      html += `<optgroup label="Coder Presets">${coderSouls.map((c) => renderOpt(c, '💻 ')).join('')}</optgroup>`;
    }
    if (otherSouls.length) {
      html += `<optgroup label="Other Presets">${otherSouls.map((o) => renderOpt(o, '')).join('')}</optgroup>`;
    }
    return html;
  }

  async function _fetchPresetsFallback() {
    if (_presets.length) return;
    try {
      const r = await fetch('/api/souls');
      if (!r.ok) return;
      const data = await r.json();
      const souls = Array.isArray(data?.souls) ? data.souls : (Array.isArray(data?.presets) ? data.presets : []);
      if (souls.length) {
        _presets = souls
          .filter((s) => s?.meta?.id)
          .map((s) => ({
            id: String(s.meta.id).trim(),
            name: String(s.meta.name || s.meta.id).trim(),
            model_name: String(s.model?.model_name || '').trim(),
            tags: Array.isArray(s.meta.tags) ? s.meta.tags.map((t) => String(t).toLowerCase()) : [],
          }));
        if (data.active_soul_id && !_activeSoulId) {
          _activeSoulId = String(data.active_soul_id).trim();
        }
        render();
      }
    } catch (_) {}
  }

  async function _fetchPlanFromRest() {
    if (_editMode) return;
    try {
      let url = '';
      if (_planId) {
        url = `/api/action-plans/${encodeURIComponent(_planId)}`;
      } else if (_sessionId) {
        url = `/api/action-plans?source_id=${encodeURIComponent(_sessionId)}`;
      } else {
        return;
      }
      const r = await fetch(url);
      if (!r.ok) return;
      const data = await r.json();
      const fetched = data?.plan || data?.active_plan || null;
      if (fetched && Array.isArray(fetched.steps) && fetched.steps.length) {
        const prevSig = JSON.stringify(_plan || {});
        const nextSig = JSON.stringify(fetched);
        if (prevSig !== nextSig) {
          _plan = fetched;
          _planId = fetched.plan_id || _planId;
          _sessionId = fetched.source_id || _sessionId;
          render();
        }
      }
    } catch (_) {}
  }

  function _collectSelectedSteps() {
    const steps = Array.isArray(_plan?.steps) ? _plan.steps : [];
    if (!_checkedIdxSet) return steps;
    const picked = steps.filter((_, idx) => _checkedIdxSet.has(idx));
    return picked.length ? picked : steps;
  }

  function _getApi() {
    return window._HecosActionPlanChat?.api || null;
  }

  async function _handleExportClick(e) {
    const api = _getApi();
    if (!api || !_plan) return;
    const res = await api.exportPlanNativeDialog(_plan, { format: e?.shiftKey ? 'html' : 'md' });
    if (res && res.cancelled) return;
    if (res && res.ok) {
      _showBannerToast(`${_tr('ap_toast_exported', 'Plan exported:')} ${res.filename || _plan.title}`);
    } else {
      _showBannerToast(`${_tr('ap_toast_export_failed', 'Export failed:')} ${res?.error || 'error'}`);
    }
  }

  async function _handleImportClick() {
    const api = _getApi();
    if (!api) return;
    const res = await api.importPlanNativeDialog({ sourceId: _sessionId });
    if (res && res.cancelled) return;
    if (res && res.ok && res.plan) {
      _plan = res.plan;
      _planId = res.plan.plan_id || _planId;
      _sessionId = res.plan.source_id || _sessionId;
      _checkedIdxSet = null;
      _editMode = false;
      _post({ type: 'action_imported', plan: res.plan, ts: Date.now() });
      _showBannerToast(`${_tr('ap_toast_imported', 'Plan imported:')} ${res.plan.title || res.filename || ''}`);
      render();
    } else {
      _showBannerToast(`${_tr('ap_toast_import_failed', 'Import failed:')} ${res?.error || 'error'}`);
    }
  }

  function render() {
    const root = document.getElementById('ap-viewer-root');
    if (!root) return;

    const dockLbl = _esc(_tr('ap_chat_btn_dock', 'Dock'));
    const dockTitle = _esc(_tr('ap_chat_btn_dock_title', 'Return plan window back into chat'));
    const exportLbl = _esc(_tr('ap_chat_btn_export', 'Export'));
    const exportTitle = _esc(_tr('ap_chat_btn_export_title', 'Export / Save plan to disk (.md default, .html report, .yaml, or .json via native OS dialog · Shift+Click for HTML)'));
    const importLbl = _esc(_tr('ap_chat_btn_import', 'Import Plan'));
    const importTitle = _esc(_tr('ap_chat_btn_import_title', 'Import a saved Action Plan (.md, .html, .yaml, .yml, or .json via native OS dialog)'));
    const syncLbl = _syncedWithChat
      ? _esc(_tr('ap_viewer_synced', 'Synced with Chat'))
      : _esc(_tr('ap_viewer_standalone', 'Standalone'));
    const splitLbl = _esc(_tr('ap_viewer_tab_split', 'Split'));
    const stepsLbl = _esc(_tr('ap_viewer_tab_steps', 'Checklist'));
    const bpLbl = _esc(_tr('ap_viewer_tab_blueprint', 'Blueprint'));
    const openTabLbl = _esc(_tr('ap_viewer_open_tab', 'New Tab'));

    if (!_plan || !Array.isArray(_plan.steps) || !_plan.steps.length) {
      document.title = 'Hecos — Action Plan Viewer';
      root.innerHTML = `
        <header class="ap-viewer-topbar">
          <div class="ap-viewer-brand">
            <img src="/assets/Hecos_Logo_SQR_NBG_LogoOnly.png" alt="Hecos" class="ap-viewer-logo" onerror="this.style.display='none'">
            <strong>Action Plan Viewer</strong>
            <span class="ap-viewer-sync-pill ${_syncedWithChat ? 'is-synced' : ''}">
              <span class="ap-viewer-sync-dot"></span> ${syncLbl}
            </span>
          </div>
          <div class="ap-viewer-top-actions">
            <button type="button" class="ap-detached-btn" id="ap-viewer-import-btn" title="${importTitle}">
              <i class="fas fa-file-import"></i> ${importLbl}
            </button>
            <button type="button" class="ap-detached-btn is-primary" id="ap-viewer-dock-btn" title="${dockTitle}">
              <i class="fas fa-compress"></i> ${dockLbl}
            </button>
          </div>
        </header>
        <div class="ap-viewer-empty">
          <i class="fas fa-clipboard-list" style="font-size:28px;opacity:0.45;"></i>
          <p>${_esc(_tr('ap_viewer_empty', 'No active Action Plan for this session.'))}</p>
        </div>
      `;
      const emptyImportBtn = root.querySelector('#ap-viewer-import-btn');
      if (emptyImportBtn) emptyImportBtn.addEventListener('click', _handleImportClick);
      const dockBtn = root.querySelector('#ap-viewer-dock-btn');
      if (dockBtn) {
        dockBtn.addEventListener('click', () => {
          _notifyClosedOnce();
          window.close();
        });
      }
      return;
    }

    const plan = _plan;
    document.title = `${plan.title || 'Action Plan'} — Hecos`;

    const st = String(plan.status || 'running').toLowerCase();
    const isConfirm = st === 'awaiting_approval' || st === 'draft';
    const isCompleted = st === 'completed';
    const isLaunching = Boolean(_launchingPlanId && _launchingPlanId === plan.plan_id);
    const isRunningActive = isLaunching || (st === 'running' && _isStreaming);
    const steps = plan.steps;
    const doneCount = steps.filter((s) => s.status === 'done' || s.status === 'skipped').length;
    const pct = Math.round((doneCount / steps.length) * 100);
    const isResumable = isLaunching || ((st === 'interrupted' || st === 'paused' || (st === 'running' && !_isStreaming)) && doneCount < steps.length);
    const showActions = isConfirm || isResumable;
    const canModify = !isLaunching && (isConfirm || st === 'interrupted' || st === 'paused');
    const rev = Number(plan.revision || 1);

    const busyLbl = _launchingMode === 'revise'
      ? _esc(_tr('ap_chat_btn_revising', 'Revising...'))
      : _esc(_tr('ap_chat_btn_starting', 'Starting...'));
    const pillHtml = isRunningActive
      ? `<i class="fas fa-circle-notch fa-spin" aria-hidden="true"></i> ${_launchingMode === 'revise' ? busyLbl : _esc(_statusLabel('running', plan.plan_mode))}`
      : _esc(_statusLabel(st, plan.plan_mode));
    const actionLbl = isConfirm
      ? _esc(_tr('ap_chat_btn_execute', 'Execute Plan'))
      : _esc(_tr('ap_chat_btn_continue', 'Continue Plan'));
    const approveInner = isLaunching
      ? `<i class="fas fa-circle-notch fa-spin"></i> ${busyLbl}`
      : `<i class="fas fa-play"></i> ${actionLbl}`;
    const runCoderLbl = _esc(_tr('ap_chat_lbl_run_with_coder', 'Run with Preset'));
    const reviseAiLbl = _esc(_tr('ap_chat_modal_revise_ai', 'Revise with AI'));
    const revisePlaceholder = _esc(_tr('ap_chat_revise_placeholder', 'Ask Architect to revise this plan (e.g. add auth, switch DB, change UI)...'));
    const cancelLbl = _esc(_tr('ap_chat_btn_cancel', 'Cancel'));
    const previewLbl = _esc(_tr('ap_chat_modal_preview', 'Preview'));
    const editLbl = _esc(_tr('ap_chat_modal_edit', 'Edit Markdown'));
    const saveLbl = _esc(_tr('ap_chat_modal_save', 'Save Changes'));

    const rawMd = _editMode ? _editDraftMd : _buildBlueprintMarkdown(plan);

    const stepToggleTitle = _esc(_tr('ap_chat_step_toggle_title', 'Click to mark step done or pending manually'));
    const nextStepLbl = _esc(_tr('ap_chat_btn_next_step', 'Next Step'));
    const nextStepTitle = _esc(_tr('ap_chat_btn_next_step_title', 'Execute only the next pending step and pause for review'));

    const stepsHtml = steps.map((s, idx) => {
      const stepNum = Number(s.index || idx + 1);
      const isStepDone = String(s.status || '').toLowerCase() === 'done';
      const checked = !_checkedIdxSet || _checkedIdxSet.has(idx);
      const checkControl = isConfirm
        ? `<input type="checkbox" class="ap-confirm-step-cb" data-idx="${idx}"${checked ? ' checked' : ''} style="margin-top:2px;accent-color:#10b981;">`
        : `<button type="button" class="ap-step-toggle-btn" data-step-index="${stepNum}" title="${stepToggleTitle}">${_stepIcon(s.status)}</button>`;
      const manualDoneBtn = isConfirm
        ? `<button type="button" class="ap-step-manual-done-btn${isStepDone ? ' is-done' : ''}" data-step-index="${stepNum}" title="${stepToggleTitle}" aria-label="${stepToggleTitle}">${isStepDone ? '✓' : '○'}</button>`
        : '';
      const note = s.notes ? `<span style="color:#94a3b8;margin-left:6px;">— ${_esc(s.notes)}</span>` : '';
      const filesChips = (Array.isArray(s.files) && s.files.length)
        ? `<div class="ap-step-files">${s.files.slice(0, 6).map(_renderFileChip).join('')}</div>`
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

    const historyHtml = (Array.isArray(plan.revision_history) && plan.revision_history.length)
      ? `<div class="ap-modal-rev-history">
           <strong>Revisions:</strong>
           ${plan.revision_history.slice(-5).map((h) => `<span class="ap-modal-rev-chip" title="${_esc(h.note || '')}">v${Number(h.revision || 1)}: ${_esc((h.note || '').slice(0, 56))}</span>`).join('')}
         </div>`
      : '';

    const blueprintContentHtml = _editMode
      ? `<div class="ap-modal-edit-wrap">
           <textarea id="ap-viewer-md-editor" class="ap-modal-md-editor" spellcheck="false">${_esc(rawMd)}</textarea>
           <div class="ap-modal-edit-bar">
             <button type="button" class="agent-plan-btn-approve" id="ap-viewer-save-md-btn">
               <i class="fas fa-save"></i> ${saveLbl}
             </button>
             <button type="button" class="agent-plan-btn-secondary" id="ap-viewer-cancel-edit-btn">
               ${previewLbl}
             </button>
           </div>
         </div>`
      : `<div class="ap-modal-markdown" id="ap-viewer-md-preview">${_renderMarkdownSafe(rawMd)}</div>`;

    const showChecklist = _viewTab === 'split' || _viewTab === 'steps';
    const showBlueprint = _viewTab === 'split' || _viewTab === 'blueprint';
    const isPopupWin = Boolean(window.opener);

    const footerHtml = showActions ? `
      <footer class="ap-viewer-footer">
        <div class="ap-viewer-footer-row">
          <button type="button" class="agent-plan-btn-approve${isLaunching ? ' is-launching' : ''}" id="ap-viewer-execute-btn"${isLaunching ? ' disabled' : ''}>
            ${approveInner}
          </button>
          <button type="button" class="agent-plan-btn-next-step" id="ap-viewer-next-step-btn" title="${nextStepTitle}"${isLaunching ? ' disabled' : ''}>
            <i class="fas fa-forward-step"></i> ${nextStepLbl}
          </button>
          <div class="agent-plan-coder-group${isLaunching ? ' is-locked' : ''}" title="Select Global Preset for execution">
            <label for="ap-viewer-preset-select" class="agent-plan-coder-label">
              <i class="fas fa-sliders"></i> ${runCoderLbl}
            </label>
            <select id="ap-viewer-preset-select" class="ap-viewer-preset-select"${isLaunching ? ' disabled' : ''}>
              ${_buildPresetOptionsHtml()}
            </select>
          </div>
          ${canModify ? `
            <div class="ap-viewer-revise-inline">
              <input type="text" id="ap-viewer-revise-input" class="ap-revise-input" placeholder="${revisePlaceholder}" />
              <button type="button" class="agent-plan-btn-revise" id="ap-viewer-revise-btn"${isLaunching ? ' disabled' : ''}>
                <i class="fas fa-pen-to-square"></i> ${reviseAiLbl}
              </button>
            </div>` : ''}
          <button type="button" class="agent-plan-btn-reject" id="ap-viewer-reject-btn"${isLaunching ? ' disabled' : ''}>
            <i class="fas fa-times"></i> ${cancelLbl}
          </button>
        </div>
      </footer>
    ` : '';

    root.className = [
      'ap-viewer-shell',
      isConfirm ? 'is-confirm' : '',
      isRunningActive ? 'is-running' : '',
      isCompleted ? 'is-completed' : '',
    ].filter(Boolean).join(' ');

    root.innerHTML = `
      <header class="ap-viewer-topbar" id="ap-viewer-topbar">
        <div class="ap-viewer-brand">
          <img src="/assets/Hecos_Logo_SQR_NBG_LogoOnly.png" alt="Hecos" class="ap-viewer-logo" onerror="this.style.display='none'">
          <span class="agent-plan-status-pill">${pillHtml}</span>
          <span class="ap-rev-pill">v${rev}</span>
          <h1 class="ap-viewer-title" title="${_esc(plan.title)}">${_esc(plan.title || 'Implementation Plan')}</h1>
          <span class="ap-viewer-meta">(${doneCount}/${steps.length} · ${pct}%)</span>
        </div>
        <div class="ap-viewer-top-actions">
          <span class="ap-viewer-sync-pill ${_syncedWithChat ? 'is-synced' : ''}">
            <span class="ap-viewer-sync-dot"></span> ${syncLbl}
          </span>
          <div class="ap-viewer-tabs" role="tablist">
            <button type="button" class="ap-viewer-tab${_viewTab === 'split' ? ' is-active' : ''}" data-tab="split">${splitLbl}</button>
            <button type="button" class="ap-viewer-tab${_viewTab === 'steps' ? ' is-active' : ''}" data-tab="steps">${stepsLbl}</button>
            <button type="button" class="ap-viewer-tab${_viewTab === 'blueprint' ? ' is-active' : ''}" data-tab="blueprint">${bpLbl}</button>
          </div>
          <button type="button" class="ap-detached-btn" id="ap-viewer-export-btn" title="${exportTitle}">
            <i class="fas fa-file-export"></i> ${exportLbl}
          </button>
          <button type="button" class="ap-detached-btn" id="ap-viewer-import-btn" title="${importTitle}">
            <i class="fas fa-file-import"></i> ${importLbl}
          </button>
          ${isPopupWin ? `
            <a href="${_esc(window.location.href)}" target="_blank" rel="noopener" class="ap-detached-btn" id="ap-viewer-open-tab-link" title="${openTabLbl}">
              <i class="fas fa-arrow-up-right-from-square"></i> ${openTabLbl}
            </a>` : ''}
          <button type="button" class="ap-detached-btn is-primary" id="ap-viewer-dock-btn" title="${dockTitle}">
            <i class="fas fa-compress"></i> ${dockLbl}
          </button>
        </div>
      </header>
      <div class="agent-plan-progress-bar ap-viewer-progress">
        <div class="agent-plan-progress-fill" style="width:${pct}%"></div>
      </div>
      ${historyHtml}
      <main class="ap-viewer-workspace mode-${_viewTab}">
        ${showChecklist ? `
          <section class="ap-viewer-pane ap-viewer-steps-pane">
            <div class="ap-viewer-pane-header">
              <span><i class="fas fa-list-check"></i> ${stepsLbl}</span>
              <span class="ap-viewer-pane-sub">${doneCount}/${steps.length}</span>
            </div>
            <div class="ap-viewer-steps-list">${stepsHtml}</div>
          </section>` : ''}
        ${showBlueprint ? `
          <section class="ap-viewer-pane ap-viewer-blueprint-pane">
            <div class="ap-viewer-pane-header">
              <span><i class="fas fa-file-lines"></i> ${bpLbl}</span>
              ${canModify ? `
                <button type="button" class="agent-plan-btn-secondary" id="ap-viewer-toggle-edit-btn">
                  <i class="fas ${_editMode ? 'fa-eye' : 'fa-code'}"></i> ${_editMode ? previewLbl : editLbl}
                </button>` : ''}
            </div>
            <div class="ap-viewer-blueprint-scroll">${blueprintContentHtml}</div>
          </section>` : ''}
      </main>
      ${footerHtml}
    `;

    // Bind tabs
    root.querySelectorAll('.ap-viewer-tab').forEach((btn) => {
      btn.addEventListener('click', () => {
        _viewTab = btn.dataset.tab || 'split';
        render();
      });
    });

    // Bind export / import
    const exportBtn = root.querySelector('#ap-viewer-export-btn');
    if (exportBtn) exportBtn.addEventListener('click', _handleExportClick);
    const importBtn = root.querySelector('#ap-viewer-import-btn');
    if (importBtn) importBtn.addEventListener('click', _handleImportClick);

    // Bind dock back to chat
    const dockBtn = root.querySelector('#ap-viewer-dock-btn');
    if (dockBtn) {
      dockBtn.addEventListener('click', () => {
        _notifyClosedOnce();
        window.close();
      });
    }

    // Bind step checkboxes
    root.querySelectorAll('.ap-confirm-step-cb').forEach((cb) => {
      cb.addEventListener('change', () => {
        const allCbs = Array.from(root.querySelectorAll('.ap-confirm-step-cb'));
        _checkedIdxSet = new Set(allCbs.filter((c) => c.checked).map((c) => Number(c.dataset.idx)));
      });
    });

    // Bind blueprint edit / save
    const toggleEditBtn = root.querySelector('#ap-viewer-toggle-edit-btn');
    if (toggleEditBtn) {
      toggleEditBtn.addEventListener('click', () => {
        if (!_editMode) {
          _editDraftMd = _buildBlueprintMarkdown(plan);
          _editMode = true;
        } else {
          _editMode = false;
        }
        render();
      });
    }

    const cancelEditBtn = root.querySelector('#ap-viewer-cancel-edit-btn');
    if (cancelEditBtn) {
      cancelEditBtn.addEventListener('click', () => {
        _editMode = false;
        render();
      });
    }

    const saveMdBtn = root.querySelector('#ap-viewer-save-md-btn');
    if (saveMdBtn) {
      saveMdBtn.addEventListener('click', async () => {
        const editor = root.querySelector('#ap-viewer-md-editor');
        const newMd = editor ? editor.value : _editDraftMd;
        saveMdBtn.disabled = true;
        try {
          const r = await fetch(`/api/action-plans/${encodeURIComponent(plan.plan_id)}/revise`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              plan_markdown: newMd,
              revision_note: 'Manual blueprint edit in Pop-out Viewer',
            }),
          });
          const data = await r.json();
          if (data && data.ok && data.plan) {
            _plan = data.plan;
            _editMode = false;
            _post({ type: 'action_manual_saved', plan: data.plan, ts: Date.now() });
            _showBannerToast(_tr('ap_chat_modal_saved', 'Implementation Plan saved.'));
            render();
          }
        } catch (_) {
          saveMdBtn.disabled = false;
        }
      });
    }

    // Bind preset select
    const presetSel = root.querySelector('#ap-viewer-preset-select');
    if (presetSel) {
      presetSel.addEventListener('change', () => {
        _selectedPresetId = presetSel.value || '';
        if (_selectedPresetId) {
          _post({ type: 'action_select_preset', presetId: _selectedPresetId, ts: Date.now() });
        }
      });
    }

    // Bind manual step toggles
    root.querySelectorAll('.ap-step-toggle-btn, .ap-step-manual-done-btn').forEach((btn) => {
      btn.addEventListener('click', async (e) => {
        e.stopPropagation();
        const stepIdx = Number(btn.dataset.stepIndex || 0);
        const api = _getApi();
        if (!stepIdx || !api || typeof api.togglePlanStep !== 'function') return;
        const res = await api.togglePlanStep(plan.plan_id, stepIdx);
        if (res && res.ok && res.plan) {
          _plan = res.plan;
          _post({ type: 'action_step_toggled', plan: res.plan, ts: Date.now() });
          render();
        }
      });
    });

    // Bind Next Step (single step execution)
    const nextStepBtn = root.querySelector('#ap-viewer-next-step-btn');
    if (nextStepBtn) {
      nextStepBtn.addEventListener('click', () => {
        if (nextStepBtn.disabled) return;
        const chosenPreset = presetSel ? (presetSel.value || '') : '';
        const selectedSteps = _collectSelectedSteps();
        if (!_syncedWithChat) {
          _showBannerToast('Open Hecos Chat tab to run single steps.');
          return;
        }
        _launchingPlanId = plan.plan_id;
        _launchingMode = 'execute';
        render();
        _post({
          type: 'action_next_step',
          planId: plan.plan_id,
          steps: selectedSteps,
          coderPresetId: chosenPreset,
          ts: Date.now(),
        });
      });
    }

    // Bind Execute Plan
    const execBtn = root.querySelector('#ap-viewer-execute-btn');
    if (execBtn) {
      execBtn.addEventListener('click', async () => {
        if (execBtn.disabled) return;
        const chosenPreset = presetSel ? (presetSel.value || '') : '';
        const selectedSteps = _collectSelectedSteps();
        _launchingPlanId = plan.plan_id;
        _launchingMode = 'execute';
        render();
        if (_syncedWithChat) {
          _post({
            type: 'action_execute',
            planId: plan.plan_id,
            steps: selectedSteps,
            coderPresetId: chosenPreset,
            ts: Date.now(),
          });
        } else {
          // Standalone fallback: approve on backend directly
          try {
            const r = await fetch(`/api/action-plans/${encodeURIComponent(plan.plan_id)}/approve`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ steps: selectedSteps }),
            });
            const data = await r.json();
            if (data?.plan) _plan = data.plan;
          } catch (_) {}
          _launchingPlanId = '';
          render();
        }
      });
    }

    // Bind Revise with AI
    const revInput = root.querySelector('#ap-viewer-revise-input');
    const revBtn = root.querySelector('#ap-viewer-revise-btn');
    const triggerRevise = () => {
      const fb = (revInput?.value || '').trim();
      if (!fb) return;
      if (!_syncedWithChat) {
        _showBannerToast('Open Hecos Chat tab to send AI revisions.');
        return;
      }
      _launchingPlanId = plan.plan_id;
      _launchingMode = 'revise';
      render();
      _post({
        type: 'action_revise',
        planId: plan.plan_id,
        feedback: fb,
        ts: Date.now(),
      });
    };
    if (revBtn) revBtn.addEventListener('click', triggerRevise);
    if (revInput) {
      revInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
          e.preventDefault();
          triggerRevise();
        }
      });
    }

    // Bind Cancel / Reject
    const rejectBtn = root.querySelector('#ap-viewer-reject-btn');
    if (rejectBtn) {
      rejectBtn.addEventListener('click', async () => {
        if (rejectBtn.disabled) return;
        rejectBtn.disabled = true;
        if (_syncedWithChat) {
          _post({ type: 'action_reject', planId: plan.plan_id, ts: Date.now() });
        } else {
          try {
            await fetch(`/api/action-plans/${encodeURIComponent(plan.plan_id)}/reject`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ reason: _tr('ap_chat_rejected_reason', 'Cancelled by user in chat') }),
            });
          } catch (_) {}
          _plan = null;
          render();
        }
      });
    }
  }

  function _initChannel() {
    if (typeof BroadcastChannel === 'undefined') return;
    try {
      _channel = new BroadcastChannel(CHANNEL_NAME);
      _channel.addEventListener('message', (ev) => {
        const msg = ev?.data;
        if (!msg || typeof msg !== 'object') return;

        switch (msg.type) {
          case 'plan_update': {
            _syncedWithChat = true;
            if (Array.isArray(msg.presets) && msg.presets.length) {
              _presets = msg.presets;
            }
            if (msg.activeSoulId !== undefined) {
              _activeSoulId = String(msg.activeSoulId || '');
            }
            _isStreaming = Boolean(msg.isStreaming);
            _launchingPlanId = String(msg.launchingPlanId || '');
            _launchingMode = String(msg.launchingMode || 'execute');
            if (msg.sessionId) _sessionId = String(msg.sessionId);
            if (msg.plan) {
              const prevId = _plan?.plan_id || '';
              _plan = msg.plan;
              _planId = msg.plan.plan_id || _planId;
              if (prevId && prevId !== _planId) {
                _checkedIdxSet = null;
                _editMode = false;
              }
            }
            if (!_editMode) render();
            break;
          }
          case 'plan_cleared': {
            if (!msg.sessionId || !_sessionId || msg.sessionId === _sessionId) {
              _plan = null;
              _launchingPlanId = '';
              _editMode = false;
              render();
            }
            break;
          }
          case 'dock_close': {
            _closedNotified = true;
            window.close();
            break;
          }
          case 'focus_viewer': {
            try { window.focus(); } catch (_) {}
            const tb = document.getElementById('ap-viewer-topbar');
            if (tb) {
              tb.classList.remove('is-focus-pulse');
              void tb.offsetWidth;
              tb.classList.add('is-focus-pulse');
              setTimeout(() => tb.classList.remove('is-focus-pulse'), 750);
            }
            break;
          }
          default:
            break;
        }
      });
    } catch (_) {
      _channel = null;
    }
  }

  function bootstrap() {
    _initChannel();
    render();

    // Announce to chat immediately so chat minimizes to compact bar & pushes full state
    _post({
      type: 'viewer_hello',
      planId: _planId,
      sessionId: _sessionId,
      ts: Date.now(),
    });

    // Hydrate directly from REST as fast fallback
    _fetchPlanFromRest();
    _fetchPresetsFallback();

    // Keep heartbeat alive for multi-tab auto-dock detection
    setInterval(() => {
      _post({
        type: 'viewer_heartbeat',
        planId: _plan?.plan_id || _planId,
        sessionId: _plan?.source_id || _sessionId,
        ts: Date.now(),
      });
    }, 2500);

    // Lightweight REST fallback poll (skipped while user is editing Markdown)
    setInterval(_fetchPlanFromRest, 3000);

    window.addEventListener('beforeunload', _notifyClosedOnce);
    window.addEventListener('pagehide', _notifyClosedOnce);
  }

  document.addEventListener('DOMContentLoaded', bootstrap);
})();
