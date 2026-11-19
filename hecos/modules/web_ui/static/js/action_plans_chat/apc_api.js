/**
 * MODULE: action_plans_chat/apc_api.js
 * PURPOSE: API calls and native OS filesystem Save/Open dialog helpers for Hecos Action Plans
 *          (shared by both Chat widget and Pop-out Viewer).
 */

(function () {
  const ns = (window._HecosActionPlanChat = window._HecosActionPlanChat || {});
  const LAST_DIR_KEY = 'hecos_action_plan_last_dir';

  function _resolveSid(explicitSid) {
    return (
      explicitSid ||
      window.chatHistoryState?.activeSessionId ||
      localStorage.getItem('hecos_active_session_id') ||
      ''
    );
  }

  function _normalizeFmt(fmt) {
    const clean = String(fmt || 'md').trim().toLowerCase().replace(/^\./, '');
    if (clean === 'html' || clean === 'htm') return 'html';
    if (clean === 'yaml' || clean === 'yml') return 'yaml';
    if (clean === 'json') return 'json';
    return 'md';
  }

  function _formatFromName(name, fallback = 'md') {
    const low = String(name || '').toLowerCase();
    if (low.endsWith('.html') || low.endsWith('.htm')) return 'html';
    if (low.endsWith('.yaml') || low.endsWith('.yml')) return 'yaml';
    if (low.endsWith('.json')) return 'json';
    if (low.endsWith('.md') || low.endsWith('.markdown')) return 'md';
    return _normalizeFmt(fallback);
  }

  function _suggestFilename(plan, fmt = 'md') {
    const raw = String(plan?.title || 'action_plan').trim().toLowerCase();
    const slug = raw.replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '').slice(0, 60) || 'action_plan';
    const eff = _normalizeFmt(fmt);
    if (eff === 'html') return `${slug}.html`;
    if (eff === 'yaml') return `${slug}.yaml`;
    if (eff === 'json') return `${slug}.hecos-plan.json`;
    return `${slug}.md`;
  }

  function _fallbackSerializePlan(plan, fmt = 'json') {
    if (String(fmt || 'json').toLowerCase() === 'md') {
      const existingMd = String(plan?.plan_markdown || '').trim();
      if (existingMd) return existingMd + '\n';
      const lines = [`# ${plan?.title || 'Implementation Plan'}`];
      if (plan?.goal) lines.push('', '## Goal', '', plan.goal);
      if (Array.isArray(plan?.steps) && plan.steps.length) {
        lines.push('', '## Execution Checklist', '');
        plan.steps.forEach((s, i) => {
          const mark = s.status === 'done' ? 'x' : ' ';
          lines.push(`- [${mark}] Step ${s.index || i + 1}: ${s.title || ''}`);
        });
      }
      if (plan?.verification_plan) lines.push('', '## Verification Plan', '', plan.verification_plan);
      return lines.join('\n') + '\n';
    }
    return JSON.stringify({
      schema: 'hecos.action_plan.v1',
      exported_at: new Date().toISOString(),
      plan: {
        plan_id: plan?.plan_id || '',
        title: plan?.title || 'Implementation Plan',
        goal: plan?.goal || '',
        plan_markdown: plan?.plan_markdown || '',
        verification_plan: plan?.verification_plan || '',
        revision: Number(plan?.revision || 1),
        revision_history: Array.isArray(plan?.revision_history) ? plan.revision_history : [],
        status: plan?.status || 'awaiting_approval',
        plan_mode: plan?.plan_mode || 'plan_only',
        steps: Array.isArray(plan?.steps) ? plan.steps : [],
        metadata: plan?.metadata || {},
      },
    }, null, 2) + '\n';
  }

  function _rememberDir(dirPath) {
    const clean = String(dirPath || '').trim();
    if (!clean) return;
    try {
      localStorage.setItem(LAST_DIR_KEY, clean);
    } catch (_) {}
  }

  function _getRememberedDir() {
    try {
      return localStorage.getItem(LAST_DIR_KEY) || '';
    } catch (_) {
      return '';
    }
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

  async function savePlanRevision(planId, payload = {}) {
    const resp = await fetch(`/api/action-plans/${encodeURIComponent(planId)}/revise`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload || {}),
    });
    return await resp.json();
  }

  async function togglePlanStep(planId, stepIndex, explicitStatus = '') {
    const body = explicitStatus ? { status: explicitStatus } : {};
    const resp = await fetch(
      `/api/action-plans/${encodeURIComponent(planId)}/steps/${encodeURIComponent(stepIndex)}/toggle`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      }
    );
    return await resp.json();
  }

  async function fetchExportPayload(planId, fmt = 'json') {
    const resp = await fetch(
      `/api/action-plans/${encodeURIComponent(planId)}/export?format=${encodeURIComponent(fmt)}&inline=1`
    );
    if (!resp.ok) return null;
    return await resp.json();
  }

  async function importPlanFromContent(content, filename, explicitSid = '', resetProgress = false) {
    const sid = _resolveSid(explicitSid);
    const resp = await fetch('/api/action-plans/import', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        content,
        filename: filename || 'imported_plan.json',
        source_id: sid,
        reset_progress: Boolean(resetProgress),
      }),
    });
    return await resp.json();
  }

  async function exportPlanNativeDialog(plan, opts = {}) {
    if (!plan || !plan.plan_id) {
      return { ok: false, error: 'No active plan to export' };
    }
    const prefFmt = _normalizeFmt(opts.format || 'md');
    const suggestedName = _suggestFilename(plan, prefFmt);

    // Tier 1: Browser Native OS File System Access Save Dialog (instant, modal, works local & remote)
    if (typeof window.showSaveFilePicker === 'function') {
      try {
        const typeDefs = {
          md: { description: 'Markdown Blueprint (.md)', accept: { 'text/markdown': ['.md'] } },
          html: { description: 'Interactive HTML Report (.html)', accept: { 'text/html': ['.html'] } },
          yaml: { description: 'Structured YAML Plan (.yaml)', accept: { 'application/x-yaml': ['.yaml', '.yml'], 'text/plain': ['.yaml', '.yml'] } },
          json: { description: 'Hecos Action Plan JSON (.json)', accept: { 'application/json': ['.json'] } },
        };
        const ordered = [prefFmt, ...['md', 'html', 'yaml', 'json'].filter((k) => k !== prefFmt)];
        const types = ordered.map((k) => typeDefs[k]);
        const handle = await window.showSaveFilePicker({
          id: 'hecos_action_plans',
          suggestedName,
          types,
        });
        const chosenName = String(handle?.name || suggestedName);
        const effFmt = _formatFromName(chosenName, prefFmt);
        let content = '';
        try {
          const payload = await fetchExportPayload(plan.plan_id, effFmt);
          if (payload && payload.ok && typeof payload.content === 'string') {
            content = payload.content;
          }
        } catch (_) {}
        if (!content) {
          content = _fallbackSerializePlan(plan, effFmt === 'json' ? 'json' : 'md');
        }
        const writable = await handle.createWritable();
        await writable.write(content);
        await writable.close();
        return { ok: true, cancelled: false, filename: chosenName, format: effFmt, via: 'browser_native' };
      } catch (err) {
        if (err && (err.name === 'AbortError' || err.code === 20)) {
          return { ok: true, cancelled: true };
        }
        // Non-abort error (e.g. SecurityError in non-secure context): fall through to OS native endpoint
      }
    }

    // Tier 2: Hecos Backend Native OS SaveFileDialog (Windows Forms / tkinter — works on Firefox & LAN HTTP)
    try {
      const resp = await fetch(`/api/action-plans/${encodeURIComponent(plan.plan_id)}/export-native`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          format: prefFmt,
          initialdir: _getRememberedDir(),
        }),
      });
      if (resp.ok) {
        const data = await resp.json();
        if (data && data.ok) {
          if (data.directory) _rememberDir(data.directory);
          return { ...data, via: 'os_native' };
        }
      }
    } catch (_) {}

    // Tier 3: Universal browser download fallback
    try {
      let content = '';
      let dlName = suggestedName;
      let mime = prefFmt === 'html'
        ? 'text/html;charset=utf-8'
        : (prefFmt === 'yaml'
          ? 'application/x-yaml;charset=utf-8'
          : (prefFmt === 'json' ? 'application/json;charset=utf-8' : 'text/markdown;charset=utf-8'));
      try {
        const payload = await fetchExportPayload(plan.plan_id, prefFmt);
        if (payload && payload.ok && typeof payload.content === 'string') {
          content = payload.content;
          dlName = payload.filename || dlName;
          mime = payload.mime || mime;
        }
      } catch (_) {}
      if (!content) content = _fallbackSerializePlan(plan, prefFmt === 'json' ? 'json' : 'md');
      const blob = new Blob([content], { type: mime });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = dlName;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      return { ok: true, cancelled: false, filename: dlName, format: prefFmt, via: 'download' };
    } catch (err) {
      return { ok: false, error: String(err?.message || err || 'Export failed') };
    }
  }

  function _pickFileWithInputFallback(explicitSid, resetProgress) {
    return new Promise((resolve) => {
      const input = document.createElement('input');
      input.type = 'file';
      input.accept = '.md,.html,.htm,.yaml,.yml,.json,.hecos-plan.json,text/markdown,text/html,application/x-yaml,application/json';
      input.style.display = 'none';
      document.body.appendChild(input);

      let settled = false;
      const done = (val) => {
        if (settled) return;
        settled = true;
        input.remove();
        resolve(val);
      };

      input.addEventListener('cancel', () => done({ ok: true, cancelled: true }));
      input.addEventListener('change', async () => {
        const file = input.files && input.files[0];
        if (!file) return done({ ok: true, cancelled: true });
        try {
          const text = await file.text();
          const res = await importPlanFromContent(text, file.name, explicitSid, resetProgress);
          done({ ...res, filename: file.name, via: 'file_input' });
        } catch (err) {
          done({ ok: false, error: String(err?.message || err || 'Import failed') });
        }
      });

      input.click();
    });
  }

  async function importPlanNativeDialog(opts = {}) {
    const explicitSid = opts.sourceId || '';
    const resetProgress = Boolean(opts.resetProgress);
    const sid = _resolveSid(explicitSid);

    // Tier 1: Browser Native OS Open File Dialog (File System Access API)
    if (typeof window.showOpenFilePicker === 'function') {
      try {
        const handles = await window.showOpenFilePicker({
          id: 'hecos_action_plans',
          multiple: false,
          types: [
            {
              description: 'Hecos Action Plans (.md, .html, .yaml, .json)',
              accept: {
                'text/markdown': ['.md'],
                'text/html': ['.html', '.htm'],
                'application/x-yaml': ['.yaml', '.yml'],
                'application/json': ['.json'],
                'text/plain': ['.md', '.yaml', '.yml', '.json'],
              },
            },
          ],
        });
        const handle = Array.isArray(handles) ? handles[0] : null;
        if (!handle) return { ok: true, cancelled: true };
        const file = await handle.getFile();
        const text = await file.text();
        const res = await importPlanFromContent(text, file.name, sid, resetProgress);
        return { ...res, filename: file.name, via: 'browser_native' };
      } catch (err) {
        if (err && (err.name === 'AbortError' || err.code === 20)) {
          return { ok: true, cancelled: true };
        }
        // Non-abort error: fall through to server-side OS native dialog
      }
    }

    // Tier 2: Hecos Backend Native OS OpenFileDialog (Windows Forms / tkinter)
    try {
      const resp = await fetch('/api/action-plans/import-native', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          source_id: sid,
          initialdir: _getRememberedDir(),
          reset_progress: resetProgress,
        }),
      });
      const data = await resp.json();
      if (resp.ok && data && data.ok) {
        if (data.directory) _rememberDir(data.directory);
        return { ...data, via: 'os_native' };
      }
      if (resp.status === 400 && data && data.error) {
        return data;
      }
    } catch (_) {}

    // Tier 3: Standard native browser <input type="file">
    return await _pickFileWithInputFallback(sid, resetProgress);
  }

  ns.api = {
    resolveSid: _resolveSid,
    fetchActivePlan,
    approvePlan,
    rejectPlan,
    savePlanRevision,
    togglePlanStep,
    fetchExportPayload,
    importPlanFromContent,
    exportPlanNativeDialog,
    importPlanNativeDialog,
  };
})();
