/**
 * MODULE: workspace_modal.js
 * PURPOSE: Workspace Runner modal, Projects/Runs tabs, Aider sidecar status bar,
 *          chat card action builders, source viewer, and embedded Monaco IDE modal.
 */

(function () {
  const S = window._HecosWorkspaceShared;
  if (!S) return;

  const {
    RUNNABLE_EXTS,
    TESTABLE_EXTS,
    VIEWABLE_EXTS,
    EDITABLE_EXTS,
    state,
    escHtml,
    formatDuration,
    getBadgeStyle,
    renderUrlButtons,
    clearPoller,
    executeIntoSlot,
    stopManagedRun,
    stopProjectProcesses,
    stopAllWorkspaceProcesses,
    deleteWorkspaceProject,
    openWorkspaceCli,
    loadLogsIntoConsole,
  } = S;

  let _modalActiveTab = 'projects';
  let _modalPoller = null;

  function _openStandaloneWorkspace() {
    closeModal();
    if (state.standaloneWinRef && !state.standaloneWinRef.closed) {
      try { state.standaloneWinRef.focus(); } catch (e) {}
      return;
    }
    const win = window.open('/workspace', 'hecos_workspace_standalone');
    if (win) {
      state.standaloneWinRef = win;
      try { win.focus(); } catch (e) {}
    } else {
      window.location.href = '/workspace';
    }
  }

  function askAiToGenerateTests(filePath, triggerBtn = null) {
    if (!filePath) return;
    const fileName = (filePath || '').split(/[\\/]/).pop() || 'module';
    const prompt = `Create clean unittest unit tests for ${fileName} (path: ${filePath}) and verify they pass with EXECUTOR__run_project_test.`;
    S.sendPromptToCoder?.(prompt, { autoSend: true, triggerBtn });
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
              <div class="wr-modal-title">${escHtml(modalTitle)}</div>
              <div class="wr-modal-sub">${escHtml(normTarget || filePath)}</div>
            </div>
          </div>
          <div class="wr-modal-header-actions">
            <a href="${fullUrl}" target="_blank" rel="noopener noreferrer" class="wr-btn wr-btn-view" id="wr-monaco-open-tab" title="Open Monaco Editor in new browser tab"><i class="fas fa-external-link-alt"></i> Open Tab</a>
            <button type="button" class="wr-btn wr-btn-close" id="wr-monaco-close"><i class="fas fa-times"></i></button>
          </div>
        </div>
        <div class="wr-monaco-frame-wrap">
          <iframe class="wr-monaco-frame" src="${embedUrl}" title="${escHtml(modalTitle)}"></iframe>
        </div>
      </div>
    `;
    backdrop.classList.add('open');
    backdrop.querySelector('#wr-monaco-close').onclick = closeMonacoModal;
    const monacoTabBtn = backdrop.querySelector('#wr-monaco-open-tab');
    if (monacoTabBtn) {
      monacoTabBtn.addEventListener('click', closeMonacoModal);
    }
  }

  function closeMonacoModal() {
    const backdrop = document.getElementById('wr-monaco-backdrop');
    if (!backdrop || !backdrop.classList.contains('open')) return false;
    backdrop.classList.remove('open');
    try {
      const wrModal = document.getElementById('wr-modal-backdrop');
      if (wrModal && wrModal.classList.contains('open')) {
        window.focus?.();
        wrModal.querySelector('#wr-modal-close')?.focus?.({ preventScroll: true });
      }
    } catch (e) {}
    return true;
  }

  function closeSourceModal() {
    const backdrop = document.getElementById('wr-source-backdrop');
    if (!backdrop || !backdrop.classList.contains('open')) return false;
    backdrop.classList.remove('open');
    return true;
  }

  function closeTopWorkspaceModal() {
    if (closeMonacoModal()) return true;
    if (closeSourceModal()) return true;
    const wrModal = document.getElementById('wr-modal-backdrop');
    if (wrModal && wrModal.classList.contains('open')) {
      closeModal();
      return true;
    }
    return false;
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
              <div class="wr-modal-title">${escHtml(fileName)}</div>
              <div class="wr-modal-sub">${escHtml(filePath)}</div>
            </div>
          </div>
          <div class="wr-modal-header-actions">
            ${editBtn}
            <button type="button" class="wr-btn wr-btn-view" id="wr-src-copy"><i class="fas fa-copy"></i> Copy</button>
            <a href="${apiUrl}" download="${escHtml(fileName)}" class="wr-btn wr-btn-dl"><i class="fas fa-download"></i> Download</a>
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
    const escapedPath = escHtml(docPath);

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
    if (extraButtonsHtml) parts.push(extraButtonsHtml);
    parts.push(
      `<a href="${escHtml(src)}" target="_blank" download="${escHtml(fileName)}" class="wr-btn wr-btn-dl">` +
      `<i class="fas fa-download"></i> Download</a>`
    );
    if (isPreviewable && previewId) {
      parts.push(
        `<button type="button" class="chat-file-zoom-btn wr-btn wr-btn-view" data-preview-id="${escHtml(previewId)}" onclick="window.togglePdfPreviewZoom('${escHtml(previewId)}')" title="Expand preview in chat">` +
        `<i class="fas fa-expand-arrows-alt"></i> <span class="zoom-label">Zoom</span></button>`
      );
    }
    return parts.join('');
  }

  function renderProjectsTab(projects, uiEnabled) {
    if (!projects.length) {
      return `<div class="wr-empty">No generated scripts or projects found in workspace yet. Ask Hecos Coder to build a Python module or app.</div>`;
    }
    return `<div class="wr-list">` + projects.map((item) => {
      const icon = item.kind === 'project' ? 'fa-folder' : 'fa-file-code';
      const activeBadge = item.active_runs > 0 ? `<span class="wr-status-pill wr-pill-running">${item.active_runs} RUNNING</span>` : '';
      const testBadge = item.has_tests ? `<span class="wr-status-pill wr-pill-muted">${item.test_count} test(s)</span>` : '';
      const entryPath = item.entry_point || item.path;
      const runBtn = (uiEnabled && entryPath)
        ? `<button type="button" class="wr-btn wr-btn-run wr-modal-act" data-act="run" data-path="${escHtml(entryPath)}" title="Run ${escHtml(item.entry_name || item.name || 'script / app')}"><i class="fas fa-play"></i> Run${item.entry_name && item.kind === 'project' ? ' ' + escHtml(item.entry_name) : ''}</button>`
        : '';
      const testBtn = (uiEnabled && (item.kind === 'project' || TESTABLE_EXTS.has((item.ext || '').toLowerCase())))
        ? `<button type="button" class="wr-btn wr-btn-test wr-modal-act" data-act="test" data-path="${escHtml(item.path)}" title="Run unit tests"><i class="fas fa-vial"></i> Test</button>`
        : '';
      const viewBtn = item.kind === 'file'
        ? `<button type="button" class="wr-btn wr-btn-view wr-modal-act" data-act="view" data-path="${escHtml(item.path)}" title="View file source"><i class="fas fa-eye"></i> View</button>`
        : '';
      const editItemBtn = (item.kind === 'file' && EDITABLE_EXTS.has((item.ext || '').toLowerCase()))
        ? `<button type="button" class="wr-btn wr-btn-edit wr-modal-act" data-act="edit" data-path="${escHtml(item.path)}" title="Edit in Monaco"><i class="fas fa-code"></i> Edit</button>`
        : (item.kind === 'project' && entryPath && EDITABLE_EXTS.has((entryPath.split('.').pop() || '').toLowerCase()))
          ? `<button type="button" class="wr-btn wr-btn-edit wr-modal-act" data-act="edit" data-path="${escHtml(entryPath)}" title="Edit ${escHtml(item.entry_name || 'entry file')} in Monaco"><i class="fas fa-code"></i> Edit</button>`
          : '';

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
      const stopProjBtn = item.active_runs > 0
        ? `<button type="button" class="wr-btn wr-btn-stop wr-modal-act" data-act="stop-path" data-path="${escHtml(item.path)}" title="Stop all running or orphaned processes for this project"><i class="fas fa-stop"></i> Stop</button>`
        : '';
      const cliProjBtn = (uiEnabled && item.path)
        ? `<button type="button" class="wr-btn wr-btn-view wr-modal-act" data-act="open-cli" data-path="${escHtml(item.path)}" title="Open native Windows PowerShell in this project"><i class="fas fa-terminal"></i> CLI</button>`
        : '';
      const aiderCliProjBtn = (uiEnabled && item.path)
        ? `<button type="button" class="wr-btn wr-btn-edit wr-modal-act" data-act="open-aider-cli" data-path="${escHtml(item.path)}" title="Launch Interactive Aider CLI in native terminal for this project"><i class="fas fa-bolt"></i> Aider CLI</button>`
        : '';
      const delProjBtn = item.path
        ? `<button type="button" class="wr-btn wr-btn-stop wr-modal-act" data-act="delete-project" data-path="${escHtml(item.path)}" data-name="${escHtml(item.name)}" title="Stop any open processes and delete this item"><i class="fas fa-trash"></i></button>`
        : '';

      const subfilesHtml = (item.kind === 'project' && item.files && item.files.length)
        ? `<details class="wr-subfiles" data-project-path="${escHtml(item.path || item.name || '')}"><summary>${item.file_count} file(s)</summary><div class="wr-subfile-list">` +
          item.files.map((f) => {
            const isSubHtml = /\.(html|htm)$/i.test(f.name || '');
            const subExt = ((f.name || '').match(/\.([a-z0-9]+)$/i) || ['', ''])[1].toLowerCase();
            const subEditBtn = EDITABLE_EXTS.has(subExt) && f.path
              ? `<button type="button" class="wr-btn wr-btn-edit wr-btn-xs wr-modal-act" data-act="edit" data-path="${escHtml(f.path)}" title="Edit in Monaco"><i class="fas fa-code"></i></button>`
              : '';
            const subOpenBtn = isSubHtml && f.path
              ? `<a href="/api/serve_html?path=${encodeURIComponent(f.path)}" target="_blank" rel="noopener noreferrer" class="wr-btn wr-btn-url wr-btn-xs" title="Open in Browser"><i class="fas fa-external-link-alt"></i></a>`
              : '';
            return `
            <div class="wr-subfile-row">
              <span class="wr-subfile-name">${escHtml(f.name)}</span>
              <div class="wr-row-actions">
                ${subOpenBtn}
                ${(uiEnabled && f.runnable) ? `<button type="button" class="wr-btn wr-btn-run wr-btn-xs wr-modal-act" data-act="run" data-path="${escHtml(f.path)}" title="Run file / script"><i class="fas fa-play"></i></button>` : ''}
                ${(uiEnabled && f.is_test) ? `<button type="button" class="wr-btn wr-btn-test wr-btn-xs wr-modal-act" data-act="test" data-path="${escHtml(f.path)}" title="Run unit tests"><i class="fas fa-vial"></i></button>` : ''}
                ${subEditBtn}
                <button type="button" class="wr-btn wr-btn-view wr-btn-xs wr-modal-act" data-act="view" data-path="${escHtml(f.path)}" title="View file source"><i class="fas fa-eye"></i></button>
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
              <strong>${escHtml(item.name)}</strong>
              ${activeBadge}
              ${testBadge}
            </div>
            <div class="wr-item-actions">${openBrowserBtn}${stopProjBtn}${runBtn}${testBtn}${editItemBtn}${cliProjBtn}${aiderCliProjBtn}${viewBtn}${delProjBtn}</div>
          </div>
          ${subfilesHtml}
        </div>
      `;
    }).join('') + `</div>`;
  }

  function renderRunsTab(runs) {
    if (!runs.length) {
      return `<div class="wr-empty">No recent or active workspace processes running.</div>`;
    }
    const activeRuns = runs.filter((r) => r.status === 'running');
    const toolbarHtml = activeRuns.length > 0
      ? `<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;gap:8px;">
           <span class="wr-muted-meta">${activeRuns.length} active workspace process(es)</span>
           <button type="button" class="wr-btn wr-btn-stop wr-btn-xs wr-modal-act" data-act="stop-all" title="Terminate all running & orphaned workspace processes">
             <i class="fas fa-power-off"></i> Stop All (${activeRuns.length})
           </button>
         </div>`
      : '';

    return toolbarHtml + `<div class="wr-list">` + runs.map((r) => {
      const isOrphan = r.source === 'orphan_os';
      const pill = r.status === 'exited' && r.exit_code !== 0
        ? { label: `EXIT ${r.exit_code}`, cls: 'wr-pill-err' }
        : (isOrphan ? { label: 'ORPHAN OS', cls: 'wr-pill-warn' } : getBadgeStyle(r.status));
      const stopBtn = r.status === 'running'
        ? `<button type="button" class="wr-btn wr-btn-stop wr-modal-act" data-act="stop" data-run-id="${escHtml(r.run_id)}"><i class="fas fa-stop"></i> Stop</button>`
        : '';
      const logBtns = isOrphan
        ? ''
        : `<button type="button" class="wr-btn wr-btn-view wr-modal-act" data-act="logs" data-run-id="${escHtml(r.run_id)}" title="Show recent &amp; live app logs"><i class="fas fa-file-alt"></i> Logs</button>
           <a href="/api/workspace/runs/${escHtml(r.run_id)}/logs/raw" target="_blank" rel="noopener noreferrer" class="wr-btn wr-btn-dl" title="Open full raw log file in new tab"><i class="fas fa-external-link-alt"></i> Raw</a>`;
      return `
        <div class="wr-item-card">
          <div class="wr-item-main">
            <div class="wr-item-title">
              <span class="wr-status-pill ${pill.cls}">${escHtml(pill.label)}</span>
              <strong>${escHtml(r.name)}</strong>
              <span class="wr-muted-meta">PID ${escHtml(r.pid)} · ${formatDuration(r.duration_ms)}</span>
            </div>
            <div class="wr-item-actions">
              ${renderUrlButtons(r.detected_urls)}
              ${logBtns}
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
        statusEl.innerHTML = `<i class="fas fa-robot" style="color:#34d399;"></i> <strong>${escHtml(data.version || 'Aider Ready')}</strong> · <code>${escHtml(data.model || '')}</code> (ctx ${escHtml(data.num_ctx || 16384)})`;
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

  function bindWorkspaceActionList(containerEl, consoleSlot, pollerKey, { onRefresh, onRunStarted, onSelectRunLog }) {
    containerEl.querySelectorAll('.wr-modal-act').forEach((btn) => {
      btn.addEventListener('click', async () => {
        const act = btn.dataset.act;
        const path = btn.dataset.path;
        const name = btn.dataset.name || '';
        const runId = btn.dataset.runId;
        if (act === 'run' || act === 'test') {
          await executeIntoSlot(consoleSlot, path, act === 'test' ? 'test' : 'auto', btn);
          if (onRunStarted) onRunStarted();
          setTimeout(() => onRefresh && onRefresh(), 250);
        } else if (act === 'view') {
          viewSource(path);
        } else if (act === 'edit') {
          openMonacoModal(path);
        } else if (act === 'stop') {
          await stopManagedRun(runId, consoleSlot);
          if (onRefresh) onRefresh();
        } else if (act === 'stop-path') {
          btn.disabled = true;
          await stopProjectProcesses?.(path);
          if (onRefresh) onRefresh();
        } else if (act === 'stop-all') {
          btn.disabled = true;
          await stopAllWorkspaceProcesses?.();
          if (onRefresh) onRefresh();
        } else if (act === 'delete-project') {
          btn.disabled = true;
          await deleteWorkspaceProject?.(path, name);
          if (onRefresh) onRefresh();
        } else if (act === 'open-cli') {
          await openWorkspaceCli?.('shell', path);
        } else if (act === 'open-aider-cli') {
          await openWorkspaceCli?.('aider', path);
        } else if (act === 'logs') {
          if (onSelectRunLog) onSelectRunLog(runId);
          await loadLogsIntoConsole(consoleSlot, pollerKey, runId);
        }
      });
    });
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
            <button type="button" class="wr-btn wr-btn-view" id="wr-modal-open-trace" title="Open Live Coding Action Trace console in Windows PowerShell"><i class="fas fa-satellite-dish"></i> Action Console</button>
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
            <button type="button" class="wr-btn wr-btn-view wr-btn-xs" id="wr-aider-open-shell-btn" title="Open native Windows PowerShell in Workspace root"><i class="fas fa-terminal"></i> Workspace CLI</button>
            <button type="button" class="wr-btn wr-btn-edit wr-btn-xs" id="wr-aider-open-cli-btn" title="Launch Interactive Aider CLI in Workspace root"><i class="fas fa-bolt"></i> Interactive Aider</button>
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
      const wsRoot = (state.workspaceRootDir || (el && el.textContent) || 'C:/Hecos/hecos/media/workspace').trim();
      openMonacoModal(wsRoot, wsRoot);
    };
    const traceBtn = backdrop.querySelector('#wr-modal-open-trace');
    if (traceBtn) traceBtn.onclick = () => openWorkspaceCli?.('trace');
    const wsShellBtn = backdrop.querySelector('#wr-aider-open-shell-btn');
    if (wsShellBtn) wsShellBtn.onclick = () => openWorkspaceCli?.('shell');
    const wsAiderBtn = backdrop.querySelector('#wr-aider-open-cli-btn');
    if (wsAiderBtn) wsAiderBtn.onclick = () => openWorkspaceCli?.('aider');
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

  let _lastModalSig = '';
  let _modalRefreshing = false;

  async function refreshModal(opts = {}) {
    const backdrop = _ensureRunnerModal();
    const silent = Boolean(opts && opts.silent);
    if (_modalRefreshing) return;
    _modalRefreshing = true;
    if (!silent) refreshAiderBar(backdrop);
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
        state.workspaceRootDir = String(projData.workspace_dir).replace(/\\/g, '/');
        wsPathEl.textContent = projData.workspace_dir;
      }
      const activeCount = Number(runsData.active_count || 0);
      runCountEl.textContent = String(activeCount);
      S.hooks.setBadgeCount?.(activeCount);

      const sig = JSON.stringify([_modalActiveTab, projData.ui_execution_enabled !== false, projData.projects || [], runsData.runs || []]);
      if (silent && sig === _lastModalSig && body.querySelector('.wr-list')) {
        return;
      }
      _lastModalSig = sig;

      const openSubPaths = new Set(
        Array.from(body.querySelectorAll('details.wr-subfiles[open]'))
          .map((d) => d.getAttribute('data-project-path') || '')
          .filter(Boolean)
      );

      if (_modalActiveTab === 'runs') {
        body.innerHTML = renderRunsTab(runsData.runs || []);
      } else {
        body.innerHTML = renderProjectsTab(projData.projects || [], projData.ui_execution_enabled !== false);
        if (openSubPaths.size) {
          body.querySelectorAll('details.wr-subfiles').forEach((d) => {
            if (openSubPaths.has(d.getAttribute('data-project-path') || '')) d.open = true;
          });
        }
      }

      bindWorkspaceActionList(body, modalConsole, 'modal_console', {
        onRefresh: () => backdrop.classList.contains('open') && refreshModal(),
      });
    } catch (err) {
      if (!silent) body.innerHTML = `<div class="wr-empty">Failed to load workspace data: ${escHtml(err.message || err)}</div>`;
    } finally {
      _modalRefreshing = false;
    }
  }

  function openModal() {
    if (state.standaloneWinRef && !state.standaloneWinRef.closed) {
      closeModal();
      try { state.standaloneWinRef.focus(); } catch (e) {}
      if (window.showToast) window.showToast('Workspace Runner is already open in a dedicated tab', 'info');
      return;
    }
    const backdrop = _ensureRunnerModal();
    backdrop.classList.add('open');
    _lastModalSig = '';
    refreshModal();
    if (_modalPoller) clearInterval(_modalPoller);
    _modalPoller = setInterval(() => {
      if (!backdrop.classList.contains('open')) {
        clearInterval(_modalPoller);
        _modalPoller = null;
        return;
      }
      if (document.visibilityState === 'visible') {
        refreshModal({ silent: true });
      }
    }, 2500);
  }

  function closeModal() {
    const backdrop = document.getElementById('wr-modal-backdrop');
    if (backdrop) backdrop.classList.remove('open');
    if (_modalPoller) {
      clearInterval(_modalPoller);
      _modalPoller = null;
    }
    clearPoller('modal_console');
  }

  let _escBridgeBound = false;
  function _ensureEscAndIframeBridge() {
    if (_escBridgeBound) return;
    _escBridgeBound = true;

    // Close embedded Monaco modal cleanly when Escape originates inside its child iframe
    window.addEventListener('message', (ev) => {
      if (!ev || !ev.data || ev.data.type !== 'hecos:close_monaco_modal') return;
      const monacoBackdrop = document.getElementById('wr-monaco-backdrop');
      if (!monacoBackdrop || !monacoBackdrop.classList.contains('open')) return;
      const frame = monacoBackdrop.querySelector('.wr-monaco-frame');
      const originOk = ev.origin === window.location.origin;
      const sourceOk = frame && frame.contentWindow && ev.source === frame.contentWindow;
      if (originOk || sourceOk) {
        closeMonacoModal();
      }
    });

    // Fallback Escape handler for standalone pages without global HKS (e.g. /workspace)
    document.addEventListener('keydown', (ev) => {
      if (ev.key !== 'Escape' || ev.defaultPrevented) return;
      if (window.HKS && typeof window.HKS.isEnabled === 'function' && window.HKS.isEnabled()) return;
      if (closeTopWorkspaceModal()) {
        ev.preventDefault();
        ev.stopPropagation();
      }
    });
  }
  _ensureEscAndIframeBridge();

  Object.assign(S, {
    askAiToGenerateTests,
    openMonacoModal,
    closeMonacoModal,
    viewSource,
    closeSourceModal,
    closeTopWorkspaceModal,
    buildCardActionsHtml,
    renderProjectsTab,
    renderRunsTab,
    refreshAiderBar,
    bindWorkspaceActionList,
    refreshModal,
    openModal,
    closeModal,
    openStandaloneWorkspace: _openStandaloneWorkspace,
  });
})();
