/**
 * MODULE: workspace_runner.js
 * PURPOSE: Execute, test, view, and monitor workspace scripts/apps directly from
 *          chat file cards and the persistent Workspace Runner modal.
 */

(function () {
  const RUNNABLE_EXTS = new Set(['py', 'bat', 'cmd', 'sh']);
  const TESTABLE_EXTS = new Set(['py']);
  const VIEWABLE_EXTS = new Set([
    'py', 'js', 'mjs', 'cjs', 'ts', 'jsx', 'tsx', 'css', 'scss', 'html', 'htm',
    'json', 'yaml', 'yml', 'toml', 'sh', 'bat', 'cmd', 'ps1',
    'sql', 'txt', 'md', 'csv', 'log', 'ini', 'cfg', 'conf', 'xml', 'env'
  ]);
  const EDITABLE_EXTS = new Set([
    'py', 'js', 'mjs', 'cjs', 'ts', 'tsx', 'jsx', 'json', 'yaml', 'yml', 'toml',
    'html', 'htm', 'css', 'scss', 'sh', 'bat', 'cmd', 'ps1',
    'md', 'txt', 'ini', 'cfg', 'conf', 'log', 'sql', 'xml', 'csv', 'env'
  ]);

  const _activePollers = new Map(); // key -> intervalId
  let _modalActiveTab = 'projects';
  let _modalPoller = null;
  let _badgePoller = null;
  const _WS_BUS_CHANNEL = 'hecos_workspace_bus';
  const _WS_BUS_STORAGE_KEY = 'hecos_workspace_bus_event';
  const _wsTabId = 'wr_' + Math.random().toString(36).slice(2) + '_' + Date.now().toString(36);
  let _wsSeq = 0;
  let _wsChannel = null;
  let _standaloneWinRef = null;
  let _isStandaloneMounted = false;
  let _workspaceRootDir = 'C:/Hecos/hecos/media/workspace';

  function _handleWorkspaceBusMessage(msg) {
    if (!msg || typeof msg !== 'object' || msg.tabId === _wsTabId) return;
    if (msg.type === 'wr_standalone_opened' && !_isStandaloneMounted) {
      closeModal();
    } else if (msg.type === 'wr_runs_changed') {
      updateTopbarBadge();
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

  function _emitWorkspaceBusEvent(type) {
    const msg = { type, tabId: _wsTabId, seq: ++_wsSeq, ts: Date.now() };
    try {
      if (_wsChannel) _wsChannel.postMessage(msg);
    } catch (e) {}
    try {
      localStorage.setItem(_WS_BUS_STORAGE_KEY, JSON.stringify(msg));
    } catch (e) {}
  }

  function _openStandaloneWorkspace() {
    closeModal();
    if (_standaloneWinRef && !_standaloneWinRef.closed) {
      try { _standaloneWinRef.focus(); } catch (e) {}
      return;
    }
    const win = window.open('/workspace', 'hecos_workspace_standalone');
    if (win) {
      _standaloneWinRef = win;
      try { win.focus(); } catch (e) {}
    } else {
      window.location.href = '/workspace';
    }
  }

  function _escHtml(str) {
    return String(str ?? '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function _formatDuration(ms) {
    const n = Number(ms || 0);
    if (n < 1000) return `${n}ms`;
    return `${(n / 1000).toFixed(1)}s`;
  }

  function _getBadgeStyle(status) {
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

  function _renderUrlButtons(urls) {
    if (!Array.isArray(urls) || !urls.length) return '';
    return urls.map((u) => `
      <a href="${_escHtml(u)}" target="_blank" rel="noopener noreferrer" class="wr-btn wr-btn-url" title="Open local web app in browser">
        <i class="fas fa-external-link-alt"></i> Open App
      </a>
    `).join('');
  }

  function _clearPoller(key) {
    if (_activePollers.has(key)) {
      clearInterval(_activePollers.get(key));
      _activePollers.delete(key);
    }
  }

  function _ensureConsoleSlot(anchorEl) {
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

  function _formatBytes(bytes) {
    const n = Number(bytes || 0);
    if (!n || n <= 0) return '';
    if (n < 1024) return `${n} B`;
    if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
    return `${(n / (1024 * 1024)).toFixed(2)} MB`;
  }

  function _applyConsoleFilter(slot) {
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

  function _renderConsole(slot, state) {
    if (!slot) return;
    const isErrExit = state.status === 'exited' && state.exit_code !== 0 && state.exit_code !== undefined && state.exit_code !== null;
    const pill = isErrExit
      ? { label: `EXIT ${state.exit_code}`, cls: 'wr-pill-err' }
      : (state.status === 'exited'
          ? { label: `EXIT ${state.exit_code ?? 0}`, cls: 'wr-pill-ok' }
          : _getBadgeStyle(state.status));

    const metaParts = [];
    if (state.command) metaParts.push(state.command);
    if (state.pid && state.status === 'running') metaParts.push(`PID ${state.pid}`);
    if (state.duration_ms !== undefined && state.status !== 'running') {
      metaParts.push(_formatDuration(state.duration_ms));
    }
    if (state.total_bytes) {
      const byteStr = _formatBytes(state.total_bytes);
      metaParts.push(state.truncated ? `${byteStr} (tail)` : byteStr);
    }

    const rawLogBtns = state.run_id
      ? `<a href="/api/workspace/runs/${encodeURIComponent(state.run_id)}/logs/raw" target="_blank" rel="noopener noreferrer" class="wr-btn wr-btn-view wr-btn-xs" title="Open full uncompressed app log in new tab"><i class="fas fa-external-link-alt"></i> Full Log</a>` +
        `<a href="/api/workspace/runs/${encodeURIComponent(state.run_id)}/logs/raw?download=1" class="wr-btn wr-btn-dl wr-btn-xs" title="Download complete raw .log file"><i class="fas fa-download"></i></a>`
      : '';

    const stopBtn = state.status === 'running' && state.run_id
      ? `<button type="button" class="wr-btn wr-btn-stop wr-action-btn" data-wr-action="stop" data-wr-run-id="${_escHtml(state.run_id)}" title="Stop running process">
           <i class="fas fa-stop"></i> Stop
         </button>`
      : '';

    const genTestBtn = state.no_tests_found && state.path
      ? `<button type="button" class="wr-btn wr-btn-ai wr-action-btn" data-wr-action="gen-tests" data-wr-path="${_escHtml(state.path)}" title="Ask AI to generate unit tests">
           <i class="fas fa-magic"></i> Generate &amp; Run Tests with AI
         </button>`
      : '';

    const closeBtn = slot.dataset.wrSticky === '1'
      ? ''
      : `<button type="button" class="wr-btn wr-btn-close wr-action-btn" data-wr-action="close-console" title="Hide output">
           <i class="fas fa-times"></i>
         </button>`;

    const probe = state.http_probe;
    const probeFailed = probe && probe.ok === false;
    const diags = Array.isArray(state.web_diagnostics) ? state.web_diagnostics : [];
    const probeHtml = probeFailed
      ? `<div class="wr-probe-alert" style="margin:6px 0 4px;padding:7px 10px;border-radius:6px;background:rgba(239,68,68,0.12);border:1px solid rgba(239,68,68,0.45);color:#fca5a5;font-size:12px;line-height:1.4;">` +
        `<div><i class="fas fa-exclamation-triangle"></i> <strong>Health-check failed:</strong> ${_escHtml(probe.url || '')} → ${_escHtml(probe.summary || probe.error || 'HTTP Error')}</div>` +
        (diags.length ? `<div style="margin-top:4px;color:#fde68a;">${diags.map((d) => _escHtml(d)).join('<br>')}</div>` : '') +
        `</div>`
      : '';

    const bodyText = state.output !== undefined && state.output !== ''
      ? state.output
      : (state.error || '(waiting for output...)');
    slot._wrRawOutput = bodyText;
    if (slot._wrAutoScroll === undefined) slot._wrAutoScroll = true;

    const controlsHtml = `${_renderUrlButtons(state.detected_urls)}${rawLogBtns}${stopBtn}${genTestBtn}${closeBtn}`;
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
        cmdEl.textContent = metaParts.join(' · ') || state.title || 'Execution';
      }
      if (ctrlEl) {
        ctrlEl.innerHTML = controlsHtml;
      }
      const prevAlert = slot.querySelector('.wr-probe-alert');
      if (prevAlert) prevAlert.remove();
      if (probeHtml) existingPre.insertAdjacentHTML('beforebegin', probeHtml);
      slot.style.display = 'block';
      _applyConsoleFilter(slot);
      return;
    }

    slot.innerHTML = `
      <div class="wr-console-bar">
        <div class="wr-console-meta">
          <span class="wr-status-pill ${pill.cls}">${_escHtml(pill.label)}</span>
          <span class="wr-console-cmd" title="${_escHtml(metaParts.join(' | '))}">${_escHtml(metaParts.join(' · ') || state.title || 'Execution')}</span>
        </div>
        <div class="wr-console-controls">
          ${controlsHtml}
        </div>
      </div>
      <div class="wr-console-tools">
        <div class="wr-console-filter-wrap">
          <i class="fas fa-search"></i>
          <input type="text" class="wr-console-filter" placeholder="Filter console output..." value="${_escHtml(slot._wrFilter || '')}" title="Filter log lines in real time">
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
        _applyConsoleFilter(slot);
      });
    }
    const autoCb = slot.querySelector('.wr-console-autoscroll-cb');
    if (autoCb) {
      autoCb.addEventListener('change', () => {
        slot._wrAutoScroll = autoCb.checked;
        if (autoCb.checked) _applyConsoleFilter(slot);
      });
    }
    slot.style.display = 'block';
    _applyConsoleFilter(slot);
  }

  async function _startLogPolling(slot, key, initialState) {
    _clearPoller(key);
    let offset = Number(initialState.offset || 0);
    let accOutput = initialState.output || '';
    let urls = Array.isArray(initialState.detected_urls) ? [...initialState.detected_urls] : [];
    let totalBytes = Number(initialState.total_bytes || 0);
    let truncated = Boolean(initialState.truncated);
    const runId = initialState.run_id;

    const timer = setInterval(async () => {
      if (!document.body.contains(slot)) {
        _clearPoller(key);
        return;
      }
      try {
        const resp = await fetch(`/api/workspace/runs/${encodeURIComponent(runId)}/logs?offset=${offset}`);
        const data = await resp.json();
        if (!data.ok) {
          _clearPoller(key);
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
        _renderConsole(slot, {
          ...initialState,
          status: data.status,
          exit_code: data.exit_code,
          duration_ms: data.duration_ms,
          total_bytes: totalBytes,
          truncated,
          detected_urls: urls,
          output: accOutput || (data.status === 'running' ? '(running... waiting for stdout)' : '(no output)'),
        });
        if (data.status !== 'running') {
          _clearPoller(key);
          updateTopbarBadge();
        }
      } catch (err) {
        console.warn('[WorkspaceRunner] log poll error:', err);
      }
    }, 1000);

    _activePollers.set(key, timer);
    updateTopbarBadge();
  }

  async function _executeIntoSlot(slot, path, mode, triggerBtn) {
    if (!slot || !path) return;
    const pollerKey = slot.dataset.wrKey || ('slot_' + Math.random().toString(36).slice(2, 10));
    slot.dataset.wrKey = pollerKey;
    _clearPoller(pollerKey);

    const prevHtml = triggerBtn ? triggerBtn.innerHTML : null;
    if (triggerBtn) {
      triggerBtn.disabled = true;
      triggerBtn.innerHTML = `<i class="fas fa-spinner fa-spin"></i> ${mode === 'test' ? 'Testing...' : 'Running...'}`;
    }

    _renderConsole(slot, {
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
      _renderConsole(slot, {
        ...data,
        path,
        title: path.split(/[\\/]/).pop(),
      });

      if (data.status === 'running' && data.run_id) {
        _startLogPolling(slot, pollerKey, { ...data, path });
      } else {
        updateTopbarBadge();
      }
    } catch (err) {
      _renderConsole(slot, {
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

  async function _stopManagedRun(runId, slot) {
    if (!runId) return;
    try {
      await fetch(`/api/workspace/runs/${encodeURIComponent(runId)}/stop`, { method: 'POST' });
      if (slot && slot.dataset.wrKey) {
        _clearPoller(slot.dataset.wrKey);
        const logResp = await fetch(`/api/workspace/runs/${encodeURIComponent(runId)}/logs?offset=0`);
        const logData = await logResp.json();
        if (logData.ok) {
          _renderConsole(slot, {
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
      updateTopbarBadge();
      if (document.getElementById('wr-modal-backdrop')?.classList.contains('open')) {
        refreshModal();
      }
    } catch (err) {
      console.error('[WorkspaceRunner] Failed to stop run:', err);
    }
  }

  function _askAiToGenerateTests(filePath) {
    const input = document.getElementById('user-input');
    if (!input) return;
    const fileName = (filePath || '').split(/[\\/]/).pop() || 'module';
    const prompt = `Create clean unittest unit tests for ${fileName} (path: ${filePath}) and verify they pass with EXECUTOR__run_project_test.`;
    input.value = prompt;
    input.dispatchEvent(new Event('input', { bubbles: true }));
    closeModal();
    input.focus();
    if (typeof window.sendMessage === 'function') {
      window.sendMessage();
    }
  }

  function _inferWorkspaceRoot(filePath) {
    const norm = String(filePath || '').replace(/\\/g, '/');
    const marker = '/hecos/media/workspace/';
    const idx = norm.toLowerCase().indexOf(marker);
    if (idx !== -1) {
      const rest = norm.slice(idx + marker.length).replace(/^\/+/, '');
      const proj = rest.split('/')[0];
      if (proj) return norm.slice(0, idx + marker.length) + proj;
    }
    const lastSlash = norm.lastIndexOf('/');
    return lastSlash > 0 ? norm.slice(0, lastSlash) : '';
  }

  function openMonacoModal(filePath, explicitWorkspaceRoot = '') {
    if (!filePath) return;
    const normTarget = String(filePath || '').replace(/\\/g, '/').replace(/\/+$/, '');
    const fileName = normTarget.split('/').pop() || normTarget;
    const wsRoot = (explicitWorkspaceRoot || _inferWorkspaceRoot(filePath)).replace(/\\/g, '/').replace(/\/+$/, '');
    const isFolderMode = Boolean(explicitWorkspaceRoot && normTarget.toLowerCase() === wsRoot.toLowerCase());
    const fullUrl = isFolderMode
      ? `/drive/editor?workspace=${encodeURIComponent(wsRoot)}`
      : `/drive/editor?path=${encodeURIComponent(filePath)}${wsRoot ? `&workspace=${encodeURIComponent(wsRoot)}` : ''}`;
    const embedUrl = `${fullUrl}&embed=1`;
    const modalTitle = isFolderMode
      ? `Monaco Workspace Explorer — ${fileName}`
      : `Monaco Editor — ${fileName}`;

    let backdrop = document.getElementById('wr-monaco-backdrop');
    if (!backdrop) {
      backdrop = document.createElement('div');
      backdrop.id = 'wr-monaco-backdrop';
      backdrop.className = 'wr-modal-backdrop';
      backdrop.addEventListener('click', (e) => {
        if (e.target === backdrop) backdrop.classList.remove('open');
      });
      document.body.appendChild(backdrop);
    }

    backdrop.innerHTML = `
      <div class="wr-modal wr-monaco-modal" role="dialog" aria-label="Monaco Code Editor">
        <div class="wr-modal-header">
          <div class="wr-modal-title-wrap">
            <i class="fas fa-code" style="color:var(--accent);"></i>
            <div>
              <div class="wr-modal-title">${_escHtml(modalTitle)}</div>
              <div class="wr-modal-sub">${_escHtml(normTarget || filePath)}</div>
            </div>
          </div>
          <div class="wr-modal-header-actions">
            <a href="${fullUrl}" target="_blank" rel="noopener noreferrer" class="wr-btn wr-btn-view" id="wr-monaco-open-tab" title="Open Monaco Editor in new browser tab"><i class="fas fa-external-link-alt"></i> Open Tab</a>
            <button type="button" class="wr-btn wr-btn-close" id="wr-monaco-close"><i class="fas fa-times"></i></button>
          </div>
        </div>
        <div class="wr-monaco-frame-wrap">
          <iframe class="wr-monaco-frame" src="${embedUrl}" title="${_escHtml(modalTitle)}"></iframe>
        </div>
      </div>
    `;
    backdrop.classList.add('open');
    backdrop.querySelector('#wr-monaco-close').onclick = () => backdrop.classList.remove('open');
    const monacoTabBtn = backdrop.querySelector('#wr-monaco-open-tab');
    if (monacoTabBtn) {
      monacoTabBtn.addEventListener('click', () => backdrop.classList.remove('open'));
    }
  }

  async function viewSource(filePath) {
    if (!filePath) return;
    const fileName = filePath.split(/[\\/]/).pop() || filePath;
    const ext = (fileName.match(/\.([a-z0-9]+)$/i) || ['', ''])[1].toLowerCase();
    const apiUrl = `/api/local_file?path=${encodeURIComponent(filePath)}`;
    const editBtn = EDITABLE_EXTS.has(ext)
      ? `<button type="button" class="wr-btn wr-btn-edit" id="wr-src-edit"><i class="fas fa-code"></i> Edit in Monaco</button>`
      : '';

    let backdrop = document.getElementById('wr-source-backdrop');
    if (!backdrop) {
      backdrop = document.createElement('div');
      backdrop.id = 'wr-source-backdrop';
      backdrop.className = 'wr-modal-backdrop';
      backdrop.addEventListener('click', (e) => {
        if (e.target === backdrop) backdrop.classList.remove('open');
      });
      document.body.appendChild(backdrop);
    }

    backdrop.innerHTML = `
      <div class="wr-modal wr-source-modal" role="dialog" aria-label="Source Viewer">
        <div class="wr-modal-header">
          <div class="wr-modal-title-wrap">
            <i class="fas fa-file-code" style="color:var(--accent);"></i>
            <div>
              <div class="wr-modal-title">${_escHtml(fileName)}</div>
              <div class="wr-modal-sub">${_escHtml(filePath)}</div>
            </div>
          </div>
          <div class="wr-modal-header-actions">
            ${editBtn}
            <button type="button" class="wr-btn wr-btn-view" id="wr-src-copy"><i class="fas fa-copy"></i> Copy</button>
            <a href="${apiUrl}" download="${_escHtml(fileName)}" class="wr-btn wr-btn-dl"><i class="fas fa-download"></i> Download</a>
            <button type="button" class="wr-btn wr-btn-close" id="wr-src-close"><i class="fas fa-times"></i></button>
          </div>
        </div>
        <div class="wr-source-body">
          <pre class="wr-source-pre" id="wr-src-content">Loading source file...</pre>
        </div>
      </div>
    `;
    backdrop.classList.add('open');

    backdrop.querySelector('#wr-src-close').onclick = () => backdrop.classList.remove('open');
    const editEl = backdrop.querySelector('#wr-src-edit');
    if (editEl) {
      editEl.onclick = () => {
        backdrop.classList.remove('open');
        openMonacoModal(filePath);
      };
    }
    try {
      const resp = await fetch(apiUrl);
      const text = await resp.text();
      const pre = backdrop.querySelector('#wr-src-content');
      pre.textContent = resp.ok ? text : `Failed to load file (HTTP ${resp.status}).`;
      backdrop.querySelector('#wr-src-copy').onclick = () => {
        navigator.clipboard?.writeText(pre.textContent || '');
        if (window.showToast) window.showToast(`Copied ${fileName}`);
      };
    } catch (err) {
      backdrop.querySelector('#wr-src-content').textContent = `Error reading file: ${err.message || err}`;
    }
  }

  function buildCardActionsHtml({ docPath, src, fileName, ext, isPreviewable, previewId, extraButtonsHtml = '' }) {
    const cleanExt = (ext || '').toLowerCase();
    const isRunnable = RUNNABLE_EXTS.has(cleanExt);
    const isTestable = TESTABLE_EXTS.has(cleanExt);
    const isViewable = VIEWABLE_EXTS.has(cleanExt);
    const isEditable = EDITABLE_EXTS.has(cleanExt);
    const escapedPath = _escHtml(docPath);

    const parts = [];
    if (isRunnable) {
      parts.push(
        `<button type="button" class="wr-btn wr-btn-run wr-action-btn" data-wr-action="run" data-wr-path="${escapedPath}" title="Run script or app in Hecos workspace">` +
        `<i class="fas fa-play"></i> Run</button>`
      );
    }
    if (isTestable) {
      parts.push(
        `<button type="button" class="wr-btn wr-btn-test wr-action-btn" data-wr-action="test" data-wr-path="${escapedPath}" title="Run unit tests">` +
        `<i class="fas fa-vial"></i> Test</button>`
      );
    }
    if (isViewable) {
      parts.push(
        `<button type="button" class="wr-btn wr-btn-view wr-action-btn" data-wr-action="view" data-wr-path="${escapedPath}" title="Inspect file source">` +
        `<i class="fas fa-eye"></i> View</button>`
      );
    }
    if (isEditable) {
      parts.push(
        `<button type="button" class="wr-btn wr-btn-edit wr-action-btn" data-wr-action="edit" data-wr-path="${escapedPath}" title="Edit code in Monaco Editor">` +
        `<i class="fas fa-code"></i> Edit</button>`
      );
    }
    if (extraButtonsHtml) {
      parts.push(extraButtonsHtml);
    }
    parts.push(
      `<a href="${_escHtml(src)}" target="_blank" download="${_escHtml(fileName)}" class="wr-btn wr-btn-dl">` +
      `<i class="fas fa-download"></i> Download</a>`
    );
    if (isPreviewable && previewId) {
      parts.push(
        `<button type="button" class="chat-file-zoom-btn wr-btn wr-btn-view" data-preview-id="${_escHtml(previewId)}" onclick="window.togglePdfPreviewZoom('${_escHtml(previewId)}')" title="Expand preview in chat">` +
        `<i class="fas fa-expand-arrows-alt"></i> <span class="zoom-label">Zoom</span></button>`
      );
    }
    return parts.join('');
  }

  function _ensureRunnerModal() {
    let backdrop = document.getElementById('wr-modal-backdrop');
    if (backdrop) return backdrop;

    backdrop = document.createElement('div');
    backdrop.id = 'wr-modal-backdrop';
    backdrop.className = 'wr-modal-backdrop';
    backdrop.innerHTML = `
      <div class="wr-modal" role="dialog" aria-label="Workspace Runner">
        <div class="wr-modal-header">
          <div class="wr-modal-title-wrap">
            <i class="fas fa-terminal" style="color:var(--accent);"></i>
            <div>
              <div class="wr-modal-title">Workspace Runner</div>
              <div class="wr-modal-sub" id="wr-modal-ws-path">C:\\Hecos\\hecos\\media\\workspace</div>
            </div>
          </div>
          <div class="wr-modal-header-actions">
            <button type="button" class="wr-btn wr-btn-edit" id="wr-modal-open-monaco-ws" title="Open Workspace root in Monaco IDE (live file &amp; folder explorer)"><i class="fas fa-code"></i> Monaco IDE</button>
            <a href="/workspace" target="_blank" rel="noopener noreferrer" class="wr-btn wr-btn-url" id="wr-modal-open-page" title="Open Workspace Runner in a full dedicated tab"><i class="fas fa-expand-arrows-alt"></i> Open Page</a>
            <button type="button" class="wr-btn wr-btn-view" id="wr-modal-open-folder" title="Open local workspace folder"><i class="fas fa-folder-open"></i> Open Media Folder</button>
            <button type="button" class="wr-btn wr-btn-view" id="wr-modal-refresh" title="Refresh project &amp; process list"><i class="fas fa-sync-alt"></i> Refresh</button>
            <button type="button" class="wr-btn wr-btn-close" id="wr-modal-close" title="Close Workspace Runner"><i class="fas fa-times"></i></button>
          </div>
        </div>
        <div class="wr-modal-tabs">
          <button type="button" class="wr-tab-btn active" data-wr-tab="projects"><i class="fas fa-cubes"></i> Projects &amp; Scripts</button>
          <button type="button" class="wr-tab-btn" data-wr-tab="runs"><i class="fas fa-stream"></i> Running &amp; Recent <span class="wr-tab-count" id="wr-tab-run-count">0</span></button>
        </div>
        <div class="wr-aider-bar" id="wr-aider-bar">
          <div class="wr-aider-info" id="wr-aider-status-text"><i class="fas fa-robot"></i> Checking Aider sidecar...</div>
          <div class="wr-row-actions">
            <button type="button" class="wr-btn wr-btn-edit wr-btn-xs" id="wr-aider-action-btn" style="display:none;"><i class="fas fa-sync"></i> Install / Update Aider</button>
          </div>
        </div>
        <div class="wr-modal-body" id="wr-modal-body">
          <div class="wr-empty">Loading workspace...</div>
        </div>
        <div class="wr-card-console wr-modal-console" id="wr-modal-console" style="display:none;"></div>
      </div>
    `;
    document.body.appendChild(backdrop);

    backdrop.addEventListener('click', (e) => {
      if (e.target === backdrop) closeModal();
    });
    backdrop.querySelector('#wr-modal-close').onclick = closeModal;
    backdrop.querySelector('#wr-modal-refresh').onclick = refreshModal;
    backdrop.querySelector('#wr-modal-open-monaco-ws').onclick = () => {
      const el = backdrop.querySelector('#wr-modal-ws-path');
      const wsRoot = (_workspaceRootDir || (el && el.textContent) || 'C:/Hecos/hecos/media/workspace').trim();
      openMonacoModal(wsRoot, wsRoot);
    };
    const openPageBtn = backdrop.querySelector('#wr-modal-open-page');
    if (openPageBtn) {
      openPageBtn.addEventListener('click', (e) => {
        e.preventDefault();
        _openStandaloneWorkspace();
      });
      openPageBtn.addEventListener('auxclick', (e) => {
        if (e.button === 1) closeModal();
      });
    }
    backdrop.querySelector('#wr-modal-open-folder').onclick = async () => {
      try {
        await fetch('/api/media/open-folder', { method: 'POST' });
      } catch (e) {}
    };
    backdrop.querySelectorAll('.wr-tab-btn').forEach((tabBtn) => {
      tabBtn.addEventListener('click', () => {
        _modalActiveTab = tabBtn.dataset.wrTab;
        backdrop.querySelectorAll('.wr-tab-btn').forEach((b) => b.classList.toggle('active', b === tabBtn));
        refreshModal();
      });
    });

    return backdrop;
  }

  function _renderProjectsTab(projects, uiEnabled) {
    if (!projects.length) {
      return `<div class="wr-empty">No generated scripts or projects found in workspace yet. Ask Hecos Coder to build a Python module or app.</div>`;
    }
    return `<div class="wr-list">` + projects.map((item) => {
      const icon = item.kind === 'project' ? 'fa-folder' : 'fa-file-code';
      const activeBadge = item.active_runs > 0 ? `<span class="wr-status-pill wr-pill-running">${item.active_runs} RUNNING</span>` : '';
      const testBadge = item.has_tests ? `<span class="wr-status-pill wr-pill-muted">${item.test_count} test(s)</span>` : '';
      const entryPath = item.entry_point || item.path;
      const runBtn = (uiEnabled && entryPath)
        ? `<button type="button" class="wr-btn wr-btn-run wr-modal-act" data-act="run" data-path="${_escHtml(entryPath)}" title="Run ${_escHtml(item.entry_name || item.name || 'script / app')}"><i class="fas fa-play"></i> Run${item.entry_name && item.kind === 'project' ? ' ' + _escHtml(item.entry_name) : ''}</button>`
        : '';
      const testBtn = (uiEnabled && (item.kind === 'project' || TESTABLE_EXTS.has((item.ext || '').toLowerCase())))
        ? `<button type="button" class="wr-btn wr-btn-test wr-modal-act" data-act="test" data-path="${_escHtml(item.path)}" title="Run unit tests"><i class="fas fa-vial"></i> Test</button>`
        : '';
      const viewBtn = item.kind === 'file'
        ? `<button type="button" class="wr-btn wr-btn-view wr-modal-act" data-act="view" data-path="${_escHtml(item.path)}" title="View file source"><i class="fas fa-eye"></i> View</button>`
        : '';
      const editItemBtn = (item.kind === 'file' && EDITABLE_EXTS.has((item.ext || '').toLowerCase()))
        ? `<button type="button" class="wr-btn wr-btn-edit wr-modal-act" data-act="edit" data-path="${_escHtml(item.path)}" title="Edit in Monaco"><i class="fas fa-code"></i> Edit</button>`
        : (item.kind === 'project' && entryPath && EDITABLE_EXTS.has((entryPath.split('.').pop() || '').toLowerCase()))
          ? `<button type="button" class="wr-btn wr-btn-edit wr-modal-act" data-act="edit" data-path="${_escHtml(entryPath)}" title="Edit ${_escHtml(item.entry_name || 'entry file')} in Monaco"><i class="fas fa-code"></i> Edit</button>`
          : '';

      // Direct "Open in Browser" button for HTML projects or standalone HTML files
      let htmlEntryPath = '';
      if (item.kind === 'file' && /^(html|htm)$/i.test(item.ext || '')) {
        htmlEntryPath = item.path || '';
      } else if (item.kind === 'project' && Array.isArray(item.files)) {
        const htmlFiles = item.files.filter((f) => /\.(html|htm)$/i.test(f.name || ''));
        const preferred = htmlFiles.find((f) => /(^|\/)index\.html?$/i.test(f.name || '')) || htmlFiles[0];
        if (preferred && preferred.path) htmlEntryPath = preferred.path;
      }
      const openBrowserBtn = htmlEntryPath
        ? `<a href="/api/serve_html?path=${encodeURIComponent(htmlEntryPath)}" target="_blank" rel="noopener noreferrer" class="wr-btn wr-btn-url" title="Open HTML page in new browser tab"><i class="fas fa-external-link-alt"></i> Open in Browser</a>`
        : '';

      const subfilesHtml = (item.kind === 'project' && item.files && item.files.length)
        ? `<details class="wr-subfiles"><summary>${item.file_count} file(s)</summary><div class="wr-subfile-list">` +
          item.files.map((f) => {
            const isSubHtml = /\.(html|htm)$/i.test(f.name || '');
            const subExt = ((f.name || '').match(/\.([a-z0-9]+)$/i) || ['', ''])[1].toLowerCase();
            const subEditBtn = EDITABLE_EXTS.has(subExt) && f.path
              ? `<button type="button" class="wr-btn wr-btn-edit wr-btn-xs wr-modal-act" data-act="edit" data-path="${_escHtml(f.path)}" title="Edit in Monaco"><i class="fas fa-code"></i></button>`
              : '';
            const subOpenBtn = isSubHtml && f.path
              ? `<a href="/api/serve_html?path=${encodeURIComponent(f.path)}" target="_blank" rel="noopener noreferrer" class="wr-btn wr-btn-url wr-btn-xs" title="Open in Browser"><i class="fas fa-external-link-alt"></i></a>`
              : '';
            return `
            <div class="wr-subfile-row">
              <span class="wr-subfile-name">${_escHtml(f.name)}</span>
              <div class="wr-row-actions">
                ${subOpenBtn}
                ${(uiEnabled && f.runnable) ? `<button type="button" class="wr-btn wr-btn-run wr-btn-xs wr-modal-act" data-act="run" data-path="${_escHtml(f.path)}" title="Run file / script"><i class="fas fa-play"></i></button>` : ''}
                ${(uiEnabled && f.is_test) ? `<button type="button" class="wr-btn wr-btn-test wr-btn-xs wr-modal-act" data-act="test" data-path="${_escHtml(f.path)}" title="Run unit tests"><i class="fas fa-vial"></i></button>` : ''}
                ${subEditBtn}
                <button type="button" class="wr-btn wr-btn-view wr-btn-xs wr-modal-act" data-act="view" data-path="${_escHtml(f.path)}" title="View file source"><i class="fas fa-eye"></i></button>
              </div>
            </div>
          `;
          }).join('') + `</div></details>`
        : '';

      return `
        <div class="wr-item-card">
          <div class="wr-item-main">
            <div class="wr-item-title">
              <i class="fas ${icon}" style="color:var(--accent);"></i>
              <strong>${_escHtml(item.name)}</strong>
              ${activeBadge}
              ${testBadge}
            </div>
            <div class="wr-item-actions">${openBrowserBtn}${runBtn}${testBtn}${editItemBtn}${viewBtn}</div>
          </div>
          ${subfilesHtml}
        </div>
      `;
    }).join('') + `</div>`;
  }

  function _renderRunsTab(runs) {
    if (!runs.length) {
      return `<div class="wr-empty">No recent or active workspace runs in this server session.</div>`;
    }
    return `<div class="wr-list">` + runs.map((r) => {
      const pill = r.status === 'exited' && r.exit_code !== 0
        ? { label: `EXIT ${r.exit_code}`, cls: 'wr-pill-err' }
        : _getBadgeStyle(r.status);
      const stopBtn = r.status === 'running'
        ? `<button type="button" class="wr-btn wr-btn-stop wr-modal-act" data-act="stop" data-run-id="${_escHtml(r.run_id)}"><i class="fas fa-stop"></i> Stop</button>`
        : '';
      return `
        <div class="wr-item-card">
          <div class="wr-item-main">
            <div class="wr-item-title">
              <span class="wr-status-pill ${pill.cls}">${_escHtml(pill.label)}</span>
              <strong>${_escHtml(r.name)}</strong>
              <span class="wr-muted-meta">PID ${_escHtml(r.pid)} · ${_formatDuration(r.duration_ms)}</span>
            </div>
            <div class="wr-item-actions">
              ${_renderUrlButtons(r.detected_urls)}
              <button type="button" class="wr-btn wr-btn-view wr-modal-act" data-act="logs" data-run-id="${_escHtml(r.run_id)}" title="Show recent &amp; live app logs"><i class="fas fa-file-alt"></i> Logs</button>
              <a href="/api/workspace/runs/${_escHtml(r.run_id)}/logs/raw" target="_blank" rel="noopener noreferrer" class="wr-btn wr-btn-dl" title="Open full raw log file in new tab"><i class="fas fa-external-link-alt"></i> Raw</a>
              ${stopBtn}
            </div>
          </div>
        </div>
      `;
    }).join('') + `</div>`;
  }

  async function refreshAiderBar(backdrop) {
    const statusEl = backdrop.querySelector('#wr-aider-status-text');
    const actBtn = backdrop.querySelector('#wr-aider-action-btn');
    if (!statusEl || !actBtn) return;
    try {
      const resp = await fetch('/api/workspace/aider/status');
      const data = await resp.json();
      if (!resp.ok || !data.ok) {
        statusEl.innerHTML = '<i class="fas fa-robot"></i> Aider sidecar unavailable';
        actBtn.style.display = 'none';
        return;
      }
      if (data.installed) {
        statusEl.innerHTML = `<i class="fas fa-robot" style="color:#34d399;"></i> <strong>${_escHtml(data.version || 'Aider Ready')}</strong> · <code>${_escHtml(data.model || '')}</code> (ctx ${_escHtml(data.num_ctx || 16384)})`;
        actBtn.innerHTML = '<i class="fas fa-sync-alt"></i> Update Aider';
        actBtn.style.display = data.uv_available ? 'inline-flex' : 'none';
      } else {
        statusEl.innerHTML = '<i class="fas fa-robot" style="color:#fbbf24;"></i> Aider sidecar not yet installed in <code>tools/aider_env</code>';
        actBtn.innerHTML = '<i class="fas fa-download"></i> Install Aider';
        actBtn.style.display = data.uv_available ? 'inline-flex' : 'none';
      }
      actBtn.onclick = async () => {
        actBtn.disabled = true;
        actBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Updating...';
        try {
          const r2 = await fetch('/api/workspace/aider/install', { method: 'POST' });
          const d2 = await r2.json();
          if (window.showToast) window.showToast(d2.message || d2.error || 'Done', !d2.ok);
        } catch (err) {
          if (window.showToast) window.showToast('Aider update error: ' + err, true);
        } finally {
          actBtn.disabled = false;
          refreshAiderBar(backdrop);
        }
      };
    } catch (e) {
      statusEl.innerHTML = '<i class="fas fa-robot"></i> Aider status offline';
      actBtn.style.display = 'none';
    }
  }

  async function refreshModal() {
    const backdrop = _ensureRunnerModal();
    refreshAiderBar(backdrop);
    const body = backdrop.querySelector('#wr-modal-body');
    const wsPathEl = backdrop.querySelector('#wr-modal-ws-path');
    const runCountEl = backdrop.querySelector('#wr-tab-run-count');
    const modalConsole = backdrop.querySelector('#wr-modal-console');

    try {
      const [projResp, runsResp] = await Promise.all([
        fetch('/api/workspace/projects'),
        fetch('/api/workspace/runs'),
      ]);
      const projData = await projResp.json();
      const runsData = await runsResp.json();

      if (projData.workspace_dir) {
        _workspaceRootDir = String(projData.workspace_dir).replace(/\\/g, '/');
        wsPathEl.textContent = projData.workspace_dir;
      }
      const activeCount = Number(runsData.active_count || 0);
      runCountEl.textContent = String(activeCount);
      _setBadgeCount(activeCount);

      if (_modalActiveTab === 'runs') {
        body.innerHTML = _renderRunsTab(runsData.runs || []);
      } else {
        body.innerHTML = _renderProjectsTab(projData.projects || [], projData.ui_execution_enabled !== false);
      }

      body.querySelectorAll('.wr-modal-act').forEach((btn) => {
        btn.addEventListener('click', async () => {
          const act = btn.dataset.act;
          const path = btn.dataset.path;
          const runId = btn.dataset.runId;
          if (act === 'run' || act === 'test') {
            await _executeIntoSlot(modalConsole, path, act === 'test' ? 'test' : 'auto', btn);
            setTimeout(() => {
              if (backdrop.classList.contains('open')) refreshModal();
            }, 250);
          } else if (act === 'view') {
            viewSource(path);
          } else if (act === 'edit') {
            openMonacoModal(path);
          } else if (act === 'stop') {
            await _stopManagedRun(runId, modalConsole);
          } else if (act === 'logs') {
            const resp = await fetch(`/api/workspace/runs/${encodeURIComponent(runId)}/logs?offset=0&tail_bytes=131072`);
            const logData = await resp.json();
            if (logData.ok) {
              _renderConsole(modalConsole, {
                ...logData,
                output: logData.chunk || '(no log output yet)',
              });
              if (logData.status === 'running') {
                modalConsole.dataset.wrKey = 'modal_console';
                _startLogPolling(modalConsole, 'modal_console', { ...logData, output: logData.chunk || '' });
              }
            }
          }
        });
      });
    } catch (err) {
      body.innerHTML = `<div class="wr-empty">Failed to load workspace data: ${_escHtml(err.message || err)}</div>`;
    }
  }

  function openModal() {
    if (_standaloneWinRef && !_standaloneWinRef.closed) {
      closeModal();
      try { _standaloneWinRef.focus(); } catch (e) {}
      if (window.showToast) window.showToast('Workspace Runner is already open in a dedicated tab', 'info');
      return;
    }
    const backdrop = _ensureRunnerModal();
    backdrop.classList.add('open');
    refreshModal();
    if (_modalPoller) clearInterval(_modalPoller);
    _modalPoller = setInterval(() => {
      if (!backdrop.classList.contains('open')) {
        clearInterval(_modalPoller);
        _modalPoller = null;
        return;
      }
      if (_modalActiveTab === 'runs') refreshModal();
    }, 3000);
  }

  function closeModal() {
    const backdrop = document.getElementById('wr-modal-backdrop');
    if (backdrop) backdrop.classList.remove('open');
    if (_modalPoller) {
      clearInterval(_modalPoller);
      _modalPoller = null;
    }
    _clearPoller('modal_console');
  }

  function _setBadgeCount(activeCount) {
    const badge = document.getElementById('topbar-runner-badge');
    if (!badge) return;
    if (activeCount > 0) {
      badge.textContent = String(activeCount);
      badge.style.display = 'inline-flex';
    } else {
      badge.style.display = 'none';
    }
  }

  async function updateTopbarBadge() {
    try {
      const resp = await fetch('/api/workspace/runs');
      if (!resp.ok) return;
      const data = await resp.json();
      const active = Number(data.active_count || 0);
      _setBadgeCount(active);
      if (active > 0 && !_badgePoller) {
        _badgePoller = setInterval(updateTopbarBadge, 4000);
      } else if (active === 0 && _badgePoller) {
        clearInterval(_badgePoller);
        _badgePoller = null;
      }
    } catch (e) {}
  }

  document.addEventListener('click', (evt) => {
    const btn = evt.target.closest('.wr-action-btn');
    if (!btn) return;
    const action = btn.getAttribute('data-wr-action');
    const path = btn.getAttribute('data-wr-path');
    const runId = btn.getAttribute('data-wr-run-id');

    if (action === 'run' || action === 'test') {
      const slot = _ensureConsoleSlot(btn);
      _executeIntoSlot(slot, path, action === 'test' ? 'test' : 'auto', btn);
    } else if (action === 'view') {
      viewSource(path);
    } else if (action === 'edit') {
      openMonacoModal(path);
    } else if (action === 'stop') {
      const slot = btn.closest('.wr-card-console');
      _stopManagedRun(runId, slot);
    } else if (action === 'gen-tests') {
      _askAiToGenerateTests(path);
    } else if (action === 'close-console') {
      const slot = btn.closest('.wr-card-console');
      if (slot) {
        if (slot.dataset.wrKey) _clearPoller(slot.dataset.wrKey);
        slot.style.display = 'none';
      }
    }
  });

  async function mountStandalonePage(rootSelector) {
    const root = typeof rootSelector === 'string'
      ? document.querySelector(rootSelector)
      : rootSelector;
    if (!root) return;

    _isStandaloneMounted = true;
    _emitWorkspaceBusEvent('wr_standalone_opened');
    if (!window._wrStandaloneFocusHooked) {
      window._wrStandaloneFocusHooked = true;
      window.addEventListener('focus', () => {
        if (_isStandaloneMounted) _emitWorkspaceBusEvent('wr_standalone_opened');
      });
      document.addEventListener('visibilitychange', () => {
        if (_isStandaloneMounted && document.visibilityState === 'visible') {
          _emitWorkspaceBusEvent('wr_standalone_opened');
        }
      });
    }

    let activeTab = 'projects';
    let lastAutoRunId = '';

    root.innerHTML = `
      <div class="wr-standalone-shell">
        <div class="wr-aider-bar" id="wr-sa-aider-bar">
          <div class="wr-aider-info" id="wr-aider-status-text"><i class="fas fa-robot"></i> Checking Aider sidecar...</div>
          <div class="wr-row-actions">
            <span class="wr-muted-meta" id="wr-sa-ws-path">C:\\Hecos\\hecos\\media\\workspace</span>
            <button type="button" class="wr-btn wr-btn-edit wr-btn-xs" id="wr-aider-action-btn" style="display:none;"><i class="fas fa-sync"></i> Install / Update Aider</button>
            <button type="button" class="wr-btn wr-btn-edit wr-btn-xs" id="wr-sa-open-monaco-ws" title="Open Workspace root in Monaco IDE (watch folders &amp; files appear live)"><i class="fas fa-code"></i> Monaco Workspace</button>
            <button type="button" class="wr-btn wr-btn-view wr-btn-xs" id="wr-sa-open-folder" title="Open local workspace folder"><i class="fas fa-folder-open"></i> Open Media Folder</button>
            <button type="button" class="wr-btn wr-btn-view wr-btn-xs" id="wr-sa-refresh" title="Refresh projects and running processes"><i class="fas fa-sync-alt"></i> Refresh</button>
          </div>
        </div>
        <div class="wr-standalone-grid">
          <section class="wr-standalone-left">
            <div class="wr-modal-tabs">
              <button type="button" class="wr-tab-btn active" data-sa-tab="projects"><i class="fas fa-cubes"></i> Projects &amp; Scripts</button>
              <button type="button" class="wr-tab-btn" data-sa-tab="runs"><i class="fas fa-stream"></i> Running &amp; Recent <span class="wr-tab-count" id="wr-sa-run-count">0</span></button>
            </div>
            <div class="wr-standalone-list" id="wr-sa-body">
              <div class="wr-empty">Loading workspace...</div>
            </div>
          </section>
          <section class="wr-standalone-right">
            <div class="wr-card-console wr-standalone-console" id="wr-sa-console" data-wr-sticky="1" data-wr-key="sa_console">
              <div class="wr-empty">Select <strong>Run</strong>, <strong>Test</strong>, or <strong>Logs</strong> on the left to inspect complete live process output.</div>
            </div>
          </section>
        </div>
      </div>
    `;

    const bodyEl = root.querySelector('#wr-sa-body');
    const wsPathEl = root.querySelector('#wr-sa-ws-path');
    const runCountEl = root.querySelector('#wr-sa-run-count');
    const consoleEl = root.querySelector('#wr-sa-console');

    async function loadLogsIntoConsole(runId) {
      if (!runId) return;
      const resp = await fetch(`/api/workspace/runs/${encodeURIComponent(runId)}/logs?offset=0&tail_bytes=131072`);
      const logData = await resp.json();
      if (logData.ok) {
        _renderConsole(consoleEl, {
          ...logData,
          output: logData.chunk || '(no log output yet)',
        });
        if (logData.status === 'running') {
          _startLogPolling(consoleEl, 'sa_console', { ...logData, output: logData.chunk || '' });
        }
      }
    }

    async function refreshStandalone() {
      refreshAiderBar(root);
      try {
        const [projResp, runsResp] = await Promise.all([
          fetch('/api/workspace/projects'),
          fetch('/api/workspace/runs'),
        ]);
        const projData = await projResp.json();
        const runsData = await runsResp.json();

        if (projData.workspace_dir) {
          _workspaceRootDir = String(projData.workspace_dir).replace(/\\/g, '/');
          if (wsPathEl) wsPathEl.textContent = projData.workspace_dir;
        }
        const activeCount = Number(runsData.active_count || 0);
        if (runCountEl) runCountEl.textContent = String(activeCount);
        _setBadgeCount(activeCount);

        const runs = runsData.runs || [];
        if (activeTab === 'runs') {
          bodyEl.innerHTML = _renderRunsTab(runs);
        } else {
          bodyEl.innerHTML = _renderProjectsTab(projData.projects || [], projData.ui_execution_enabled !== false);
        }

        if (!lastAutoRunId && runs.length) {
          const preferred = runs.find((r) => r.status === 'running') || runs[0];
          if (preferred && preferred.run_id) {
            lastAutoRunId = preferred.run_id;
            loadLogsIntoConsole(preferred.run_id);
          }
        }

        bodyEl.querySelectorAll('.wr-modal-act').forEach((btn) => {
          btn.addEventListener('click', async () => {
            const act = btn.dataset.act;
            const path = btn.dataset.path;
            const runId = btn.dataset.runId;
            if (act === 'run' || act === 'test') {
              await _executeIntoSlot(consoleEl, path, act === 'test' ? 'test' : 'auto', btn);
              lastAutoRunId = 'manual';
              setTimeout(refreshStandalone, 250);
            } else if (act === 'view') {
              viewSource(path);
            } else if (act === 'edit') {
              openMonacoModal(path);
            } else if (act === 'stop') {
              await _stopManagedRun(runId, consoleEl);
              refreshStandalone();
            } else if (act === 'logs') {
              lastAutoRunId = runId;
              await loadLogsIntoConsole(runId);
            }
          });
        });
      } catch (err) {
        bodyEl.innerHTML = `<div class="wr-empty">Failed to load workspace: ${_escHtml(err.message || err)}</div>`;
      }
    }

    root.querySelector('#wr-sa-refresh').onclick = refreshStandalone;
    root.querySelector('#wr-sa-open-monaco-ws').onclick = () => {
      const wsRoot = (_workspaceRootDir || (wsPathEl && wsPathEl.textContent) || 'C:/Hecos/hecos/media/workspace').trim();
      openMonacoModal(wsRoot, wsRoot);
    };
    root.querySelector('#wr-sa-open-folder').onclick = async () => {
      try { await fetch('/api/media/open-folder', { method: 'POST' }); } catch (e) {}
    };
    root.querySelectorAll('[data-sa-tab]').forEach((tabBtn) => {
      tabBtn.addEventListener('click', () => {
        activeTab = tabBtn.dataset.saTab;
        root.querySelectorAll('[data-sa-tab]').forEach((b) => b.classList.toggle('active', b === tabBtn));
        refreshStandalone();
      });
    });

    await refreshStandalone();
    const timer = setInterval(() => {
      if (!document.body.contains(root)) {
        clearInterval(timer);
        _clearPoller('sa_console');
        return;
      }
      if (activeTab === 'runs') refreshStandalone();
    }, 3500);
  }

  document.addEventListener('DOMContentLoaded', () => {
    setTimeout(updateTopbarBadge, 1500);
  });

  window.WorkspaceRunner = {
    buildCardActionsHtml,
    viewSource,
    openMonacoModal,
    openModal,
    closeModal,
    refreshModal,
    mountStandalonePage,
    updateTopbarBadge,
  };
})();
