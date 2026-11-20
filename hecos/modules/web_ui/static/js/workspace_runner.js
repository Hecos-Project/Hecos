/**
 * MODULE: workspace_runner.js
 * PURPOSE: Orchestrator & public API (window.WorkspaceRunner) connecting chat card actions,
 *          topbar active-runs badge, and standalone /workspace mounting.
 *          Requires workspace_console.js and workspace_modal.js loaded beforehand.
 */

(function () {
  const S = window._HecosWorkspaceShared;
  if (!S) return;

  let _badgePoller = null;

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

  function _isCodingEnabledInTopbar() {
    const btn = document.getElementById('topbar-runner-btn');
    if (!btn) return false;
    if (btn.dataset.codingEnabled !== undefined) {
      return btn.dataset.codingEnabled === '1';
    }
    return btn.style.display !== 'none';
  }

  function setCodingVisibility(enabled) {
    const btn = document.getElementById('topbar-runner-btn');
    const isOn = Boolean(enabled);
    if (btn) {
      btn.dataset.codingEnabled = isOn ? '1' : '0';
      btn.style.display = isOn ? '' : 'none';
    }
    if (isOn) {
      updateTopbarBadge();
    } else {
      if (_badgePoller) {
        clearInterval(_badgePoller);
        _badgePoller = null;
      }
      _setBadgeCount(0);
      S.closeModal?.();
    }
  }

  async function updateTopbarBadge() {
    if (!_isCodingEnabledInTopbar()) return;
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

  S.registerUiHooks({
    closeModal: () => S.closeModal?.(),
    refreshModal: () => S.refreshModal?.(),
    updateTopbarBadge,
    setBadgeCount: _setBadgeCount,
    setCodingVisibility,
    onFilesChanged: () => {
      if (document.getElementById('wr-modal-backdrop')?.classList.contains('open')) {
        S.refreshModal?.({ silent: true });
      }
    },
  });

  document.addEventListener('click', (evt) => {
    const btn = evt.target.closest('.wr-action-btn');
    if (!btn) return;
    const action = btn.getAttribute('data-wr-action');
    const path = btn.getAttribute('data-wr-path');
    const runId = btn.getAttribute('data-wr-run-id');

    if (action === 'run' || action === 'test') {
      const slot = S.ensureConsoleSlot(btn);
      S.executeIntoSlot(slot, path, action === 'test' ? 'test' : 'auto', btn);
    } else if (action === 'view') {
      S.viewSource?.(path);
    } else if (action === 'edit') {
      S.openMonacoModal?.(path);
    } else if (action === 'stop') {
      const slot = btn.closest('.wr-card-console');
      S.stopManagedRun(runId, slot);
    } else if (action === 'gen-tests') {
      S.askAiToGenerateTests?.(path, btn);
    } else if (action === 'fix-ai') {
      const slot = btn.closest('.wr-card-console');
      S.askAiToFixRun?.(slot, path, btn);
    } else if (action === 'close-console') {
      const slot = btn.closest('.wr-card-console');
      if (slot) {
        if (slot.dataset.wrKey) S.clearPoller(slot.dataset.wrKey);
        slot.style.display = 'none';
      }
    }
  });

  async function mountStandalonePage(rootSelector) {
    const root = typeof rootSelector === 'string'
      ? document.querySelector(rootSelector)
      : rootSelector;
    if (!root) return;

    S.state.isStandaloneMounted = true;
    S.emitWorkspaceBusEvent('wr_standalone_opened');
    if (!window._wrStandaloneFocusHooked) {
      window._wrStandaloneFocusHooked = true;
      window.addEventListener('focus', () => {
        if (S.state.isStandaloneMounted) S.emitWorkspaceBusEvent('wr_standalone_opened');
      });
      document.addEventListener('visibilitychange', () => {
        if (S.state.isStandaloneMounted && document.visibilityState === 'visible') {
          S.emitWorkspaceBusEvent('wr_standalone_opened');
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
            <button type="button" class="wr-btn wr-btn-view wr-btn-xs" id="wr-sa-open-trace" title="Open Live Coding Action Trace console in Windows PowerShell"><i class="fas fa-satellite-dish"></i> Action Console</button>
            <button type="button" class="wr-btn wr-btn-view wr-btn-xs" id="wr-sa-open-shell" title="Open native Windows PowerShell in Workspace root"><i class="fas fa-terminal"></i> Workspace CLI</button>
            <button type="button" class="wr-btn wr-btn-edit wr-btn-xs" id="wr-sa-open-aider" title="Launch Interactive Aider CLI in Workspace root"><i class="fas fa-bolt"></i> Interactive Aider</button>
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

    let _lastSaDataSig = '';
    let _saRefreshing = false;

    async function refreshStandalone(opts = {}) {
      const silent = Boolean(opts && opts.silent);
      if (_saRefreshing) return;
      _saRefreshing = true;
      if (!silent) S.refreshAiderBar?.(root);
      try {
        const [projResp, runsResp] = await Promise.all([
          fetch('/api/workspace/projects'),
          fetch('/api/workspace/runs'),
        ]);
        const projData = await projResp.json();
        const runsData = await runsResp.json();

        if (projData.workspace_dir) {
          S.state.workspaceRootDir = String(projData.workspace_dir).replace(/\\/g, '/');
          if (wsPathEl) wsPathEl.textContent = projData.workspace_dir;
        }
        const activeCount = Number(runsData.active_count || 0);
        if (runCountEl) runCountEl.textContent = String(activeCount);
        _setBadgeCount(activeCount);

        const runs = runsData.runs || [];
        const sig = JSON.stringify([activeTab, projData.ui_execution_enabled !== false, projData.projects || [], runs]);
        if (silent && sig === _lastSaDataSig && bodyEl.querySelector('.wr-list')) {
          return;
        }
        _lastSaDataSig = sig;

        const openSubPaths = new Set(
          Array.from(bodyEl.querySelectorAll('details.wr-subfiles[open]'))
            .map((d) => d.getAttribute('data-project-path') || '')
            .filter(Boolean)
        );

        if (activeTab === 'runs') {
          bodyEl.innerHTML = S.renderRunsTab?.(runs) || '';
        } else {
          bodyEl.innerHTML = S.renderProjectsTab?.(projData.projects || [], projData.ui_execution_enabled !== false) || '';
          if (openSubPaths.size) {
            bodyEl.querySelectorAll('details.wr-subfiles').forEach((d) => {
              if (openSubPaths.has(d.getAttribute('data-project-path') || '')) d.open = true;
            });
          }
        }

        if (!lastAutoRunId && runs.length) {
          const preferred = runs.find((r) => r.status === 'running') || runs[0];
          if (preferred && preferred.run_id) {
            lastAutoRunId = preferred.run_id;
            S.loadLogsIntoConsole(consoleEl, 'sa_console', preferred.run_id);
          }
        }

        S.bindWorkspaceActionList?.(bodyEl, consoleEl, 'sa_console', {
          onRefresh: () => refreshStandalone(),
          onRunStarted: () => { lastAutoRunId = 'manual'; },
          onSelectRunLog: (rid) => { lastAutoRunId = rid; },
        });
      } catch (err) {
        if (!silent) bodyEl.innerHTML = `<div class="wr-empty">Failed to load workspace: ${S.escHtml(err.message || err)}</div>`;
      } finally {
        _saRefreshing = false;
      }
    }

    S.registerUiHooks({
      onFilesChanged: () => {
        if (document.body.contains(root)) refreshStandalone({ silent: true });
      },
    });
    const _onStandaloneResume = () => {
      if (document.body.contains(root) && document.visibilityState === 'visible') {
        refreshStandalone({ silent: true });
      }
    };
    window.addEventListener('focus', _onStandaloneResume);
    document.addEventListener('visibilitychange', _onStandaloneResume);

    root.querySelector('#wr-sa-refresh').onclick = () => refreshStandalone();
    root.querySelector('#wr-sa-open-trace').onclick = () => S.openWorkspaceCli?.('trace');
    root.querySelector('#wr-sa-open-shell').onclick = () => S.openWorkspaceCli?.('shell');
    root.querySelector('#wr-sa-open-aider').onclick = () => S.openWorkspaceCli?.('aider');
    root.querySelector('#wr-sa-open-monaco-ws').onclick = () => {
      const wsRoot = (S.state.workspaceRootDir || (wsPathEl && wsPathEl.textContent) || 'C:/Hecos/hecos/media/workspace').trim();
      S.openMonacoModal?.(wsRoot, wsRoot);
    };
    root.querySelector('#wr-sa-open-folder').onclick = async () => {
      try { await fetch('/api/media/open-folder', { method: 'POST' }); } catch (e) {}
    };
    root.querySelectorAll('[data-sa-tab]').forEach((tabBtn) => {
      tabBtn.addEventListener('click', () => {
        activeTab = tabBtn.dataset.saTab;
        root.querySelectorAll('[data-sa-tab]').forEach((b) => b.classList.toggle('active', b === tabBtn));
        _lastSaDataSig = '';
        refreshStandalone();
      });
    });

    await refreshStandalone();
    const timer = setInterval(() => {
      if (!document.body.contains(root)) {
        clearInterval(timer);
        S.clearPoller('sa_console');
        window.removeEventListener('focus', _onStandaloneResume);
        document.removeEventListener('visibilitychange', _onStandaloneResume);
        return;
      }
      if (document.visibilityState === 'visible') {
        refreshStandalone({ silent: true });
      }
    }, 3000);
  }

  document.addEventListener('DOMContentLoaded', () => {
    setTimeout(updateTopbarBadge, 1500);
  });

  window.WorkspaceRunner = {
    buildCardActionsHtml: (...args) => S.buildCardActionsHtml(...args),
    viewSource: (...args) => S.viewSource(...args),
    openMonacoModal: (...args) => S.openMonacoModal(...args),
    openModal: (...args) => S.openModal(...args),
    closeModal: (...args) => S.closeModal(...args),
    refreshModal: (...args) => S.refreshModal(...args),
    mountStandalonePage,
    updateTopbarBadge,
    setCodingVisibility,
  };
})();
