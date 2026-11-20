/**
 * MODULE: workspace_console.js
 * PURPOSE: Shared Workspace Runner constants, cross-tab event bus, inline/panel console rendering,
 *          live log polling, execution, and process termination helpers.
 */

(function () {
  const RUNNABLE_EXTS = new Set(['py', 'bat', 'cmd', 'sh']);
  const TESTABLE_EXTS = new Set(['py']);
  const VIEWABLE_EXTS = new Set([
    'py', 'js', 'mjs', 'cjs', 'ts', 'jsx', 'tsx', 'css', 'scss', 'html', 'htm',
    'json', 'yaml', 'yml', 'toml', 'sh', 'bat', 'cmd', 'ps1',
    'sql', 'txt', 'md', 'csv', 'log', 'ini', 'cfg', 'conf', 'xml', 'env',
  ]);
  const EDITABLE_EXTS = new Set([
    'py', 'js', 'mjs', 'cjs', 'ts', 'tsx', 'jsx', 'json', 'yaml', 'yml', 'toml',
    'html', 'htm', 'css', 'scss', 'sh', 'bat', 'cmd', 'ps1',
    'md', 'txt', 'ini', 'cfg', 'conf', 'log', 'sql', 'xml', 'csv', 'env',
  ]);

  const _activePollers = new Map(); // key -> intervalId
  const _WS_BUS_CHANNEL = 'hecos_workspace_bus';
  const _WS_BUS_STORAGE_KEY = 'hecos_workspace_bus_event';
  const _wsTabId = 'wr_' + Math.random().toString(36).slice(2) + '_' + Date.now().toString(36);
  const _seenBusMsgs = new Set();
  let _wsSeq = 0;
  let _wsChannel = null;

  function _wrTr(key, fallbackEn) {
    const val = (window.I18N && window.I18N[key]) || (typeof window.t === 'function' ? window.t(key) : '');
    return (val && val !== key) ? val : fallbackEn;
  }

  const state = {
    isStandaloneMounted: false,
    workspaceRootDir: 'C:/Hecos/hecos/media/workspace',
    standaloneWinRef: null,
  };

  const hooks = {
    closeModal: () => {},
    refreshModal: () => {},
    updateTopbarBadge: () => {},
  };

  function registerUiHooks(partial) {
    Object.assign(hooks, partial || {});
  }

  function _deliverPromptInCurrentTab(prompt, autoSend) {
    const input = document.getElementById('user-input');
    if (!input) return false;
    input.value = prompt;
    input.dispatchEvent(new Event('input', { bubbles: true }));
    hooks.closeModal?.();
    input.focus();
    if (autoSend !== false && typeof window.sendMessage === 'function') {
      window.sendMessage();
    }
    return true;
  }

  function _handleWorkspaceBusMessage(msg) {
    if (!msg || typeof msg !== 'object' || msg.tabId === _wsTabId) return;
    const msgKey = `${msg.tabId || ''}:${msg.seq || ''}`;
    if (msgKey !== ':') {
      if (_seenBusMsgs.has(msgKey)) return;
      _seenBusMsgs.add(msgKey);
      if (_seenBusMsgs.size > 40) {
        const first = _seenBusMsgs.values().next().value;
        _seenBusMsgs.delete(first);
      }
    }
    if (msg.type === 'wr_standalone_opened' && !state.isStandaloneMounted) {
      hooks.closeModal();
    } else if (msg.type === 'wr_runs_changed') {
      hooks.updateTopbarBadge();
    } else if (msg.type === 'wr_files_changed') {
      hooks.onFilesChanged?.(msg);
      hooks.updateTopbarBadge();
    } else if (msg.type === 'wr_coding_visibility') {
      hooks.setCodingVisibility?.(Boolean(msg.enabled));
    } else if (msg.type === 'wr_send_to_chat' && msg.prompt) {
      _deliverPromptInCurrentTab(msg.prompt, msg.autoSend !== false);
    }
  }

  try {
    if (typeof BroadcastChannel !== 'undefined') {
      _wsChannel = new BroadcastChannel(_WS_BUS_CHANNEL);
      _wsChannel.onmessage = (ev) => _handleWorkspaceBusMessage(ev && ev.data);
    }
  } catch (e) {}

  window.addEventListener('storage', (ev) => {
    if (ev.key !== _WS_BUS_STORAGE_KEY || !ev.newValue) return;
    try {
      _handleWorkspaceBusMessage(JSON.parse(ev.newValue));
    } catch (e) {}
  });

  function emitWorkspaceBusEvent(type, extra = {}) {
    const msg = { ...extra, type, tabId: _wsTabId, seq: ++_wsSeq, ts: Date.now() };
    try {
      if (_wsChannel) _wsChannel.postMessage(msg);
    } catch (e) {}
    try {
      localStorage.setItem(_WS_BUS_STORAGE_KEY, JSON.stringify(msg));
    } catch (e) {}
  }

  let _filesNotifyTimer = null;
  function notifyFilesChanged(source = 'ui') {
    if (_filesNotifyTimer) clearTimeout(_filesNotifyTimer);
    _filesNotifyTimer = setTimeout(() => {
      _filesNotifyTimer = null;
      emitWorkspaceBusEvent('wr_files_changed', { source });
      hooks.onFilesChanged?.({ source });
    }, 220);
  }

  function sendPromptToCoder(prompt, { autoSend = true, triggerBtn = null } = {}) {
    const clean = String(prompt || '').trim();
    if (!clean) return false;
    if (_deliverPromptInCurrentTab(clean, autoSend)) {
      return true;
    }
    // Standalone /workspace tab: bridge prompt back to the active Chat tab and copy to clipboard.
    emitWorkspaceBusEvent('wr_send_to_chat', { prompt: clean, autoSend });
    try { navigator.clipboard?.writeText(clean); } catch (e) {}
    try {
      if (window.opener && !window.opener.closed) window.opener.focus();
    } catch (e) {}
    if (triggerBtn) {
      const origHtml = triggerBtn.innerHTML;
      triggerBtn.innerHTML = `<i class="fas fa-check"></i> ${escHtml(_wrTr('wr_sent_to_chat', 'Sent to Chat'))}`;
      setTimeout(() => {
        if (document.body.contains(triggerBtn)) triggerBtn.innerHTML = origHtml;
      }, 2200);
    }
    window.showToast?.(_wrTr('wr_toast_debug_sent', 'Diagnostics sent to Coder Chat and copied to clipboard.'), 'info');
    return true;
  }

  function buildFixWithCoderPrompt(runState, rawOutput) {
    const rs = runState || {};
    const targetPath = rs.path || '';
    const projectName = targetPath.split(/[\\/]/).filter(Boolean).pop() || 'project';
    const probe = rs.http_probe;
    const diags = Array.isArray(rs.web_diagnostics) ? rs.web_diagnostics : [];

    const diagLines = [];
    if (rs.command) diagLines.push(`- Command: \`${rs.command}\``);
    if (rs.status) {
      const exitStr = (rs.exit_code !== undefined && rs.exit_code !== null) ? ` (exit=${rs.exit_code})` : '';
      diagLines.push(`- Status: ${rs.status}${exitStr}`);
    }
    if (probe && probe.ok === false) {
      diagLines.push(`- Health-check failed: ${probe.url || ''} -> ${probe.summary || probe.error || 'HTTP Error'}`);
    }
    if (diags.length) {
      diagLines.push(`- Web diagnostics: ${diags.join(' | ')}`);
    }

    const cleanOut = String(rawOutput || rs.output || rs.error || '').trim();
    const tailLines = cleanOut ? cleanOut.split(/\r?\n/).slice(-45).join('\n').slice(-2200) : '';
    const logBlock = tailLines ? `\nOutput/log excerpt:\n\`\`\`\n${tailLines}\n\`\`\`\n` : '';

    return (
      `I ran/tested \`${projectName}\` (path: \`${targetPath}\`) and hit an error:\n\n` +
      `Diagnostics:\n${diagLines.join('\n')}\n` +
      logBlock +
      `\nFix the real issue on disk:\n` +
      `1. Use \`EXECUTOR__read_file\` on the relevant files to inspect the root cause (or missing files).\n` +
      `2. Apply the fix with \`EXECUTOR__patch_file\` / \`EXECUTOR__write_file\` (one concise file per turn).\n` +
      `3. Verify by running \`EXECUTOR__run_project_test\` (if tests exist) and starting/probing the app with \`EXECUTOR__start_app\` and \`EXECUTOR__probe_url\`.`
    );
  }

  function askAiToFixRun(slot, fallbackPath, triggerBtn) {
    const rs = (slot && slot._wrLastRunState) ? slot._wrLastRunState : { path: fallbackPath || '' };
    const effective = { ...rs, path: rs.path || fallbackPath || '' };
    if (!effective.path) return false;
    const prompt = buildFixWithCoderPrompt(effective, slot ? slot._wrRawOutput : '');
    return sendPromptToCoder(prompt, { autoSend: true, triggerBtn });
  }

  function escHtml(str) {
    return String(str ?? '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function formatDuration(ms) {
    const n = Number(ms || 0);
    if (n < 1000) return `${n}ms`;
    return `${(n / 1000).toFixed(1)}s`;
  }

  function formatBytes(bytes) {
    const n = Number(bytes || 0);
    if (!n || n <= 0) return '';
    if (n < 1024) return `${n} B`;
    if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
    return `${(n / (1024 * 1024)).toFixed(2)} MB`;
  }

  function getBadgeStyle(status) {
    switch ((status || '').toLowerCase()) {
      case 'running':
        return { label: 'RUNNING', cls: 'wr-pill-running' };
      case 'passed':
        return { label: 'TESTS PASSED', cls: 'wr-pill-ok' };
      case 'failed':
        return { label: 'TESTS FAILED', cls: 'wr-pill-err' };
      case 'no_tests':
        return { label: 'NO TESTS', cls: 'wr-pill-warn' };
      case 'stopped':
        return { label: 'STOPPED', cls: 'wr-pill-muted' };
      case 'timeout':
        return { label: 'TIMEOUT', cls: 'wr-pill-err' };
      case 'exited':
        return { label: 'EXITED', cls: 'wr-pill-ok' };
      default:
        return { label: (status || 'DONE').toUpperCase(), cls: 'wr-pill-muted' };
    }
  }

  function renderUrlButtons(urls) {
    if (!Array.isArray(urls) || !urls.length) return '';
    return urls.map((u) => `
      <a href="${escHtml(u)}" target="_blank" rel="noopener noreferrer" class="wr-btn wr-btn-url" title="Open local web app in browser">
        <i class="fas fa-external-link-alt"></i> Open App
      </a>
    `).join('');
  }

  function clearPoller(key) {
    if (_activePollers.has(key)) {
      clearInterval(_activePollers.get(key));
      _activePollers.delete(key);
    }
  }

  function ensureConsoleSlot(anchorEl) {
    const wrap = anchorEl.closest('.chat-file-card-wrap') || anchorEl.closest('.chat-file-card')?.parentElement;
    if (!wrap) return null;
    let slot = wrap.querySelector(':scope > .wr-card-console');
    if (!slot) {
      slot = document.createElement('div');
      slot.className = 'wr-card-console';
      wrap.appendChild(slot);
    }
    return slot;
  }

  function applyConsoleFilter(slot) {
    const pre = slot.querySelector('.wr-console-pre');
    if (!pre) return;
    const raw = slot._wrRawOutput || '';
    const q = (slot._wrFilter || '').trim().toLowerCase();
    if (!q) {
      pre.textContent = raw;
    } else {
      const lines = raw.split(/\r?\n/);
      const matched = lines.filter((line) => line.toLowerCase().includes(q));
      pre.textContent = matched.length ? matched.join('\n') : `(no lines matching "${slot._wrFilter.trim()}")`;
    }
    if (slot._wrAutoScroll !== false) {
      pre.scrollTop = pre.scrollHeight;
    }
  }

  function renderConsole(slot, runState) {
    if (!slot) return;
    const isErrExit = runState.status === 'exited' && runState.exit_code !== 0 && runState.exit_code !== undefined && runState.exit_code !== null;
    const pill = isErrExit
      ? { label: `EXIT ${runState.exit_code}`, cls: 'wr-pill-err' }
      : (runState.status === 'exited'
          ? { label: `EXIT ${runState.exit_code ?? 0}`, cls: 'wr-pill-ok' }
          : getBadgeStyle(runState.status));

    const metaParts = [];
    if (runState.command) metaParts.push(runState.command);
    if (runState.pid && runState.status === 'running') metaParts.push(`PID ${runState.pid}`);
    if (runState.duration_ms !== undefined && runState.status !== 'running') {
      metaParts.push(formatDuration(runState.duration_ms));
    }
    if (runState.total_bytes) {
      const byteStr = formatBytes(runState.total_bytes);
      metaParts.push(runState.truncated ? `${byteStr} (tail)` : byteStr);
    }

    const rawLogBtns = runState.run_id
      ? `<a href="/api/workspace/runs/${encodeURIComponent(runState.run_id)}/logs/raw" target="_blank" rel="noopener noreferrer" class="wr-btn wr-btn-view wr-btn-xs" title="Open full uncompressed app log in new tab"><i class="fas fa-external-link-alt"></i> Full Log</a>` +
        `<a href="/api/workspace/runs/${encodeURIComponent(runState.run_id)}/logs/raw?download=1" class="wr-btn wr-btn-dl wr-btn-xs" title="Download complete raw .log file"><i class="fas fa-download"></i></a>`
      : '';

    const stopBtn = runState.status === 'running' && runState.run_id
      ? `<button type="button" class="wr-btn wr-btn-stop wr-action-btn" data-wr-action="stop" data-wr-run-id="${escHtml(runState.run_id)}" title="Stop running process">
           <i class="fas fa-stop"></i> Stop
         </button>`
      : '';

    const genTestBtn = runState.no_tests_found && runState.path
      ? `<button type="button" class="wr-btn wr-btn-ai wr-action-btn" data-wr-action="gen-tests" data-wr-path="${escHtml(runState.path)}" title="Ask AI to generate unit tests">
           <i class="fas fa-magic"></i> Generate &amp; Run Tests with AI
         </button>`
      : '';

    const closeBtn = slot.dataset.wrSticky === '1'
      ? ''
      : `<button type="button" class="wr-btn wr-btn-close wr-action-btn" data-wr-action="close-console" title="Hide output">
           <i class="fas fa-times"></i>
         </button>`;

    const probe = runState.http_probe;
    const probeFailed = Boolean(probe && probe.ok === false);
    const statusLow = String(runState.status || '').toLowerCase();
    const hasProcessError = isErrExit || statusLow === 'failed' || statusLow === 'timeout' || statusLow === 'error';
    const targetPath = runState.path || slot._wrLastRunState?.path || '';
    const effectiveState = { ...runState, path: targetPath };
    slot._wrLastRunState = effectiveState;

    const fixBtnHtml = (!probeFailed && hasProcessError && targetPath)
      ? `<button type="button" class="wr-btn wr-btn-ai wr-action-btn" data-wr-action="fix-ai" data-wr-path="${escHtml(targetPath)}" title="${escHtml(_wrTr('wr_btn_fix_coder_title', 'Send error and logs to Hecos Coder for automatic fixing'))}">` +
        `<i class="fas fa-wrench"></i> ${escHtml(_wrTr('wr_btn_fix_coder', 'Fix with Coder'))}</button>`
      : '';

    const diags = Array.isArray(runState.web_diagnostics) ? runState.web_diagnostics : [];
    const probeHtml = probeFailed
      ? `<div class="wr-probe-alert">` +
        `<div class="wr-probe-alert-head">` +
          `<div><i class="fas fa-exclamation-triangle"></i> <strong>Health-check failed:</strong> ${escHtml(probe.url || '')} → ${escHtml(probe.summary || probe.error || 'HTTP Error')}</div>` +
          (targetPath
            ? `<button type="button" class="wr-btn wr-btn-ai wr-btn-xs wr-action-btn" data-wr-action="fix-ai" data-wr-path="${escHtml(targetPath)}" title="${escHtml(_wrTr('wr_btn_send_coder_fix_title', 'Send diagnostics and logs to Hecos Coder to fix the project'))}"><i class="fas fa-wrench"></i> ${escHtml(_wrTr('wr_btn_send_coder_fix', 'Send to Coder / Fix'))}</button>`
            : '') +
        `</div>` +
        (diags.length ? `<div style="margin-top:4px;color:#fde68a;">${diags.map((d) => escHtml(d)).join('<br>')}</div>` : '') +
        `</div>`
      : '';

    const bodyText = runState.output !== undefined && runState.output !== ''
      ? runState.output
      : (runState.error || '(waiting for output...)');
    slot._wrRawOutput = bodyText;
    if (slot._wrAutoScroll === undefined) slot._wrAutoScroll = true;

    const controlsHtml = `${renderUrlButtons(runState.detected_urls)}${fixBtnHtml}${rawLogBtns}${stopBtn}${genTestBtn}${closeBtn}`;
    const existingPre = slot.querySelector('.wr-console-pre');
    if (existingPre) {
      const pillEl = slot.querySelector('.wr-console-meta .wr-status-pill');
      const cmdEl = slot.querySelector('.wr-console-meta .wr-console-cmd');
      const ctrlEl = slot.querySelector('.wr-console-controls');
      if (pillEl) {
        pillEl.className = `wr-status-pill ${pill.cls}`;
        pillEl.textContent = pill.label;
      }
      if (cmdEl) {
        cmdEl.title = metaParts.join(' | ');
        cmdEl.textContent = metaParts.join(' · ') || runState.title || 'Execution';
      }
      if (ctrlEl && slot._wrLastControlsHtml !== controlsHtml) {
        ctrlEl.innerHTML = controlsHtml;
        slot._wrLastControlsHtml = controlsHtml;
      }
      if (slot._wrLastProbeHtml !== probeHtml) {
        const prevAlert = slot.querySelector('.wr-probe-alert');
        if (prevAlert) prevAlert.remove();
        if (probeHtml) existingPre.insertAdjacentHTML('beforebegin', probeHtml);
        slot._wrLastProbeHtml = probeHtml;
      }
      slot.style.display = 'block';
      applyConsoleFilter(slot);
      return;
    }

    slot._wrLastControlsHtml = controlsHtml;
    slot._wrLastProbeHtml = probeHtml;

    slot.innerHTML = `
      <div class="wr-console-bar">
        <div class="wr-console-meta">
          <span class="wr-status-pill ${pill.cls}">${escHtml(pill.label)}</span>
          <span class="wr-console-cmd" title="${escHtml(metaParts.join(' | '))}">${escHtml(metaParts.join(' · ') || runState.title || 'Execution')}</span>
        </div>
        <div class="wr-console-controls">
          ${controlsHtml}
        </div>
      </div>
      <div class="wr-console-tools">
        <div class="wr-console-filter-wrap">
          <i class="fas fa-search"></i>
          <input type="text" class="wr-console-filter" placeholder="Filter console output..." value="${escHtml(slot._wrFilter || '')}" title="Filter log lines in real time">
        </div>
        <label class="wr-console-autoscroll" title="Automatically scroll to newest log lines">
          <input type="checkbox" class="wr-console-autoscroll-cb" ${slot._wrAutoScroll ? 'checked' : ''}> Auto-scroll
        </label>
      </div>
      ${probeHtml}
      <pre class="wr-console-pre"></pre>
    `;
    const filterInput = slot.querySelector('.wr-console-filter');
    if (filterInput) {
      filterInput.addEventListener('input', () => {
        slot._wrFilter = filterInput.value;
        applyConsoleFilter(slot);
      });
    }
    const autoCb = slot.querySelector('.wr-console-autoscroll-cb');
    if (autoCb) {
      autoCb.addEventListener('change', () => {
        slot._wrAutoScroll = autoCb.checked;
        if (autoCb.checked) applyConsoleFilter(slot);
      });
    }
    slot.style.display = 'block';
    applyConsoleFilter(slot);
  }

  async function startLogPolling(slot, key, initialState) {
    clearPoller(key);
    let offset = Number(initialState.offset || 0);
    let accOutput = initialState.output || '';
    let urls = Array.isArray(initialState.detected_urls) ? [...initialState.detected_urls] : [];
    let totalBytes = Number(initialState.total_bytes || 0);
    let truncated = Boolean(initialState.truncated);
    const runId = initialState.run_id;

    const timer = setInterval(async () => {
      if (!document.body.contains(slot)) {
        clearPoller(key);
        return;
      }
      try {
        const resp = await fetch(`/api/workspace/runs/${encodeURIComponent(runId)}/logs?offset=${offset}`);
        const data = await resp.json();
        if (!data.ok) {
          clearPoller(key);
          return;
        }
        if (data.chunk) {
          accOutput += data.chunk;
          if (accOutput.length > 120000) {
            accOutput = accOutput.slice(-120000);
            truncated = true;
          }
        }
        offset = Number(data.offset ?? offset);
        if (data.total_bytes !== undefined) totalBytes = Number(data.total_bytes || 0);
        if (data.truncated) truncated = true;
        if (Array.isArray(data.detected_urls) && data.detected_urls.length) {
          urls = data.detected_urls;
        }
        renderConsole(slot, {
          ...initialState,
          status: data.status,
          exit_code: data.exit_code,
          duration_ms: data.duration_ms,
          total_bytes: totalBytes,
          truncated,
          detected_urls: urls,
          ...(data.http_probe !== undefined ? { http_probe: data.http_probe } : {}),
          ...(data.web_diagnostics !== undefined ? { web_diagnostics: data.web_diagnostics } : {}),
          output: accOutput || (data.status === 'running' ? '(running... waiting for stdout)' : '(no output)'),
        });
        if (data.status !== 'running') {
          clearPoller(key);
          hooks.updateTopbarBadge();
        }
      } catch (err) {
        console.warn('[WorkspaceRunner] log poll error:', err);
      }
    }, 1000);

    _activePollers.set(key, timer);
    hooks.updateTopbarBadge();
  }

  async function executeIntoSlot(slot, path, mode, triggerBtn) {
    if (!slot || !path) return;
    const pollerKey = slot.dataset.wrKey || ('slot_' + Math.random().toString(36).slice(2, 10));
    slot.dataset.wrKey = pollerKey;
    clearPoller(pollerKey);

    const prevHtml = triggerBtn ? triggerBtn.innerHTML : null;
    if (triggerBtn) {
      triggerBtn.disabled = true;
      triggerBtn.innerHTML = `<i class="fas fa-spinner fa-spin"></i> ${mode === 'test' ? 'Testing...' : 'Running...'}`;
    }

    renderConsole(slot, {
      status: 'running',
      command: `${mode === 'test' ? 'Test' : 'Run'}: ${path.split(/[\\/]/).pop()}`,
      output: 'Launching process in Hecos workspace...',
    });

    try {
      const resp = await fetch('/api/workspace/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path, mode, wait_seconds: 1.5 }),
      });
      const data = await resp.json();
      renderConsole(slot, {
        ...data,
        path,
        title: path.split(/[\\/]/).pop(),
      });

      if (data.status === 'running' && data.run_id) {
        startLogPolling(slot, pollerKey, { ...data, path });
      } else {
        hooks.updateTopbarBadge();
      }
    } catch (err) {
      renderConsole(slot, {
        status: 'error',
        path,
        error: `Request failed: ${err.message || err}`,
      });
    } finally {
      if (triggerBtn && prevHtml !== null) {
        triggerBtn.disabled = false;
        triggerBtn.innerHTML = prevHtml;
      }
    }
  }

  async function stopManagedRun(runId, slot) {
    if (!runId) return;
    try {
      const resp = await fetch(`/api/workspace/runs/${encodeURIComponent(runId)}/stop`, { method: 'POST' });
      const res = await resp.json().catch(() => ({}));
      const isOrphan = String(runId).startsWith('os_');
      if (slot && slot.dataset.wrKey && !isOrphan) {
        clearPoller(slot.dataset.wrKey);
        const logResp = await fetch(`/api/workspace/runs/${encodeURIComponent(runId)}/logs?offset=0`);
        const logData = await logResp.json();
        if (logData.ok) {
          renderConsole(slot, {
            run_id: runId,
            path: logData.path,
            status: logData.status,
            exit_code: logData.exit_code,
            duration_ms: logData.duration_ms,
            detected_urls: logData.detected_urls,
            output: logData.chunk || '(process stopped)',
          });
        }
      }
      if (res.ok && res.message && window.showToast) {
        window.showToast(res.message, false);
      }
      hooks.updateTopbarBadge();
      if (document.getElementById('wr-modal-backdrop')?.classList.contains('open')) {
        hooks.refreshModal();
      }
    } catch (err) {
      console.error('[WorkspaceRunner] Failed to stop run:', err);
    }
  }

  async function stopProjectProcesses(targetPath) {
    if (!targetPath) return null;
    try {
      const resp = await fetch('/api/workspace/processes/stop', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: targetPath }),
      });
      const res = await resp.json();
      if (window.showToast) {
        const count = Number(res.stopped_count || 0);
        window.showToast(
          res.ok
            ? _wrTr('wr_toast_stopped_procs', 'Stopped {count} process(es).').replace('{count}', String(count))
            : (res.error || 'Stop failed'),
          !res.ok
        );
      }
      hooks.updateTopbarBadge();
      return res;
    } catch (err) {
      window.showToast?.(`Stop error: ${err.message || err}`, true);
      return null;
    }
  }

  async function stopAllWorkspaceProcesses() {
    try {
      const resp = await fetch('/api/workspace/processes/stop', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ stop_all: true }),
      });
      const res = await resp.json();
      if (window.showToast) {
        const count = Number(res.stopped_count || 0);
        window.showToast(
          res.ok
            ? _wrTr('wr_toast_stopped_all', 'Stopped all active workspace processes ({count}).').replace('{count}', String(count))
            : (res.error || 'Stop all failed'),
          !res.ok
        );
      }
      hooks.updateTopbarBadge();
      return res;
    } catch (err) {
      window.showToast?.(`Stop all error: ${err.message || err}`, true);
      return null;
    }
  }

  async function deleteWorkspaceProject(targetPath, displayName = '') {
    if (!targetPath) return null;
    const label = displayName || targetPath.split(/[\\/]/).filter(Boolean).pop() || targetPath;
    const msg = _wrTr(
      'wr_confirm_delete_project',
      'Stop any running processes inside "{name}" and permanently delete it?'
    ).replace('{name}', label);
    if (!window.confirm(msg)) return { cancelled: true };

    try {
      const resp = await fetch('/api/workspace/projects/delete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: targetPath }),
      });
      const res = await resp.json();
      if (window.showToast) {
        const stoppedN = Array.isArray(res.stopped_pids) ? res.stopped_pids.length : 0;
        const okMsg = stoppedN > 0
          ? _wrTr('wr_toast_deleted_unlocked', 'Deleted "{name}" after stopping {count} locked process(es).')
              .replace('{name}', label)
              .replace('{count}', String(stoppedN))
          : _wrTr('wr_toast_deleted', 'Deleted "{name}".').replace('{name}', label);
        window.showToast(res.ok ? okMsg : (res.error || 'Delete failed'), !res.ok);
      }
      hooks.updateTopbarBadge();
      notifyFilesChanged('delete_project');
      return res;
    } catch (err) {
      window.showToast?.(`Delete error: ${err.message || err}`, true);
      return null;
    }
  }

  async function openWorkspaceCli(mode = 'shell', targetPath = '') {
    try {
      const resp = await fetch('/api/workspace/cli/open', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode, path: targetPath }),
      });
      const res = await resp.json();
      if (window.showToast) {
        if (!res.ok) {
          window.showToast(res.error || 'Could not launch CLI window', true);
        } else if (mode === 'aider') {
          window.showToast(
            _wrTr('wr_toast_opened_aider_cli', 'Opened Interactive Aider CLI ({model}).').replace('{model}', String(res.model || 'active model'))
          );
        } else if (mode === 'trace') {
          window.showToast(_wrTr('wr_toast_opened_trace_cli', 'Opened Live Coding Action Trace window.'));
        } else {
          window.showToast(
            _wrTr('wr_toast_opened_shell_cli', 'Opened Coding Shell in {cwd}.').replace('{cwd}', String(res.cwd || 'workspace'))
          );
        }
      }
      return res;
    } catch (err) {
      window.showToast?.(`CLI launch error: ${err.message || err}`, true);
      return null;
    }
  }

  async function loadLogsIntoConsole(consoleEl, pollerKey, runId) {
    if (!consoleEl || !runId) return;
    const resp = await fetch(`/api/workspace/runs/${encodeURIComponent(runId)}/logs?offset=0&tail_bytes=131072`);
    const logData = await resp.json();
    if (logData.ok) {
      renderConsole(consoleEl, {
        ...logData,
        output: logData.chunk || '(no log output yet)',
      });
      if (logData.status === 'running') {
        consoleEl.dataset.wrKey = pollerKey;
        startLogPolling(consoleEl, pollerKey, { ...logData, output: logData.chunk || '' });
      }
    }
  }

  window._HecosWorkspaceShared = {
    RUNNABLE_EXTS,
    TESTABLE_EXTS,
    VIEWABLE_EXTS,
    EDITABLE_EXTS,
    state,
    hooks,
    registerUiHooks,
    emitWorkspaceBusEvent,
    escHtml,
    formatDuration,
    getBadgeStyle,
    renderUrlButtons,
    clearPoller,
    ensureConsoleSlot,
    renderConsole,
    startLogPolling,
    executeIntoSlot,
    stopManagedRun,
    stopProjectProcesses,
    stopAllWorkspaceProcesses,
    deleteWorkspaceProject,
    openWorkspaceCli,
    loadLogsIntoConsole,
    notifyFilesChanged,
    sendPromptToCoder,
    buildFixWithCoderPrompt,
    askAiToFixRun,
  };
})();
