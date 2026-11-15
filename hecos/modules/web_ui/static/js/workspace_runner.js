/**
 * MODULE: workspace_runner.js
 * PURPOSE: Execute, test, view, and monitor workspace scripts/apps directly from
 *          chat file cards and the persistent Workspace Runner modal.
 */

(function () {
  const RUNNABLE_EXTS = new Set(['py', 'bat', 'cmd', 'sh']);
  const TESTABLE_EXTS = new Set(['py']);
  const VIEWABLE_EXTS = new Set([
    'py', 'js', 'ts', 'jsx', 'tsx', 'css', 'html', 'htm',
    'json', 'yaml', 'yml', 'toml', 'sh', 'bat', 'cmd', 'ps1',
    'sql', 'txt', 'md', 'csv', 'log', 'ini'
  ]);

  const _activePollers = new Map(); // key -> intervalId
  let _modalActiveTab = 'projects';
  let _modalPoller = null;
  let _badgePoller = null;

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

    const stopBtn = state.status === 'running' && state.run_id
      ? `<button type="button" class="wr-btn wr-btn-stop wr-action-btn" data-wr-action="stop" data-wr-run-id="${_escHtml(state.run_id)}">
           <i class="fas fa-stop"></i> Stop
         </button>`
      : '';

    const genTestBtn = state.no_tests_found && state.path
      ? `<button type="button" class="wr-btn wr-btn-ai wr-action-btn" data-wr-action="gen-tests" data-wr-path="${_escHtml(state.path)}">
           <i class="fas fa-magic"></i> Generate &amp; Run Tests with AI
         </button>`
      : '';

    const closeBtn = `<button type="button" class="wr-btn wr-btn-close wr-action-btn" data-wr-action="close-console" title="Hide output">
        <i class="fas fa-times"></i>
      </button>`;

    const bodyText = state.output !== undefined && state.output !== ''
      ? state.output
      : (state.error || '(waiting for output...)');

    slot.innerHTML = `
      <div class="wr-console-bar">
        <div class="wr-console-meta">
          <span class="wr-status-pill ${pill.cls}">${_escHtml(pill.label)}</span>
          <span class="wr-console-cmd" title="${_escHtml(metaParts.join(' | '))}">${_escHtml(metaParts.join(' · ') || state.title || 'Execution')}</span>
        </div>
        <div class="wr-console-controls">
          ${_renderUrlButtons(state.detected_urls)}
          ${stopBtn}
          ${genTestBtn}
          ${closeBtn}
        </div>
      </div>
      <pre class="wr-console-pre">${_escHtml(bodyText)}</pre>
    `;
    slot.style.display = 'block';
    const pre = slot.querySelector('.wr-console-pre');
    if (pre) pre.scrollTop = pre.scrollHeight;
  }

  async function _startLogPolling(slot, key, initialState) {
    _clearPoller(key);
    let offset = Number(initialState.offset || 0);
    let accOutput = initialState.output || '';
    let urls = Array.isArray(initialState.detected_urls) ? [...initialState.detected_urls] : [];
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
          if (accOutput.length > 24000) accOutput = accOutput.slice(-24000);
        }
        offset = Number(data.offset ?? offset);
        if (Array.isArray(data.detected_urls) && data.detected_urls.length) {
          urls = data.detected_urls;
        }
        _renderConsole(slot, {
          ...initialState,
          status: data.status,
          exit_code: data.exit_code,
          duration_ms: data.duration_ms,
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

  async function viewSource(filePath) {
    if (!filePath) return;
    const fileName = filePath.split(/[\\/]/).pop() || filePath;
    const ext = (fileName.match(/\.([a-z0-9]+)$/i) || ['', ''])[1].toLowerCase();
    const apiUrl = `/api/local_file?path=${encodeURIComponent(filePath)}`;

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
            <button type="button" class="wr-btn wr-btn-view" id="wr-modal-open-folder" title="Open local workspace folder"><i class="fas fa-folder-open"></i> Open Media Folder</button>
            <button type="button" class="wr-btn wr-btn-view" id="wr-modal-refresh"><i class="fas fa-sync-alt"></i> Refresh</button>
            <button type="button" class="wr-btn wr-btn-close" id="wr-modal-close"><i class="fas fa-times"></i></button>
          </div>
        </div>
        <div class="wr-modal-tabs">
          <button type="button" class="wr-tab-btn active" data-wr-tab="projects"><i class="fas fa-cubes"></i> Projects &amp; Scripts</button>
          <button type="button" class="wr-tab-btn" data-wr-tab="runs"><i class="fas fa-stream"></i> Running &amp; Recent <span class="wr-tab-count" id="wr-tab-run-count">0</span></button>
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
        ? `<button type="button" class="wr-btn wr-btn-run wr-modal-act" data-act="run" data-path="${_escHtml(entryPath)}"><i class="fas fa-play"></i> Run${item.entry_name && item.kind === 'project' ? ' ' + _escHtml(item.entry_name) : ''}</button>`
        : '';
      const testBtn = (uiEnabled && (item.kind === 'project' || TESTABLE_EXTS.has((item.ext || '').toLowerCase())))
        ? `<button type="button" class="wr-btn wr-btn-test wr-modal-act" data-act="test" data-path="${_escHtml(item.path)}"><i class="fas fa-vial"></i> Test</button>`
        : '';
      const viewBtn = item.kind === 'file'
        ? `<button type="button" class="wr-btn wr-btn-view wr-modal-act" data-act="view" data-path="${_escHtml(item.path)}"><i class="fas fa-eye"></i> View</button>`
        : '';

      const subfilesHtml = (item.kind === 'project' && item.files && item.files.length)
        ? `<details class="wr-subfiles"><summary>${item.file_count} file(s)</summary><div class="wr-subfile-list">` +
          item.files.map((f) => `
            <div class="wr-subfile-row">
              <span class="wr-subfile-name">${_escHtml(f.name)}</span>
              <div class="wr-row-actions">
                ${(uiEnabled && f.runnable) ? `<button type="button" class="wr-btn wr-btn-run wr-btn-xs wr-modal-act" data-act="run" data-path="${_escHtml(f.path)}"><i class="fas fa-play"></i></button>` : ''}
                ${(uiEnabled && f.is_test) ? `<button type="button" class="wr-btn wr-btn-test wr-btn-xs wr-modal-act" data-act="test" data-path="${_escHtml(f.path)}"><i class="fas fa-vial"></i></button>` : ''}
                <button type="button" class="wr-btn wr-btn-view wr-btn-xs wr-modal-act" data-act="view" data-path="${_escHtml(f.path)}"><i class="fas fa-eye"></i></button>
              </div>
            </div>
          `).join('') + `</div></details>`
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
            <div class="wr-item-actions">${runBtn}${testBtn}${viewBtn}</div>
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
              <button type="button" class="wr-btn wr-btn-view wr-modal-act" data-act="logs" data-run-id="${_escHtml(r.run_id)}"><i class="fas fa-file-alt"></i> Logs</button>
              ${stopBtn}
            </div>
          </div>
        </div>
      `;
    }).join('') + `</div>`;
  }

  async function refreshModal() {
    const backdrop = _ensureRunnerModal();
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

      if (projData.workspace_dir) wsPathEl.textContent = projData.workspace_dir;
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
          } else if (act === 'stop') {
            await _stopManagedRun(runId, modalConsole);
          } else if (act === 'logs') {
            const resp = await fetch(`/api/workspace/runs/${encodeURIComponent(runId)}/logs?offset=0`);
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

  document.addEventListener('DOMContentLoaded', () => {
    setTimeout(updateTopbarBadge, 1500);
  });

  window.WorkspaceRunner = {
    buildCardActionsHtml,
    viewSource,
    openModal,
    closeModal,
    refreshModal,
    updateTopbarBadge,
  };
})();
