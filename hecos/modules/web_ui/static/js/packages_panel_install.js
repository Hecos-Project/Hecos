/**
 * packages_panel_install.js
 * ─────────────────────────────────────────────────────────────────────────────
 * Install logic for Hecos Package Manager
 */

window._isHpmInstalling = false;

// ── Translation Helper ────────────────────────────────────────────────────────
function _ti(en, it, es) {
  const l = (document.documentElement.lang || localStorage.getItem('hecos_language') || 'it').toLowerCase();
  if (l.startsWith('it')) return it;
  if (l.startsWith('es')) return es || it;
  return en;
}

window.addEventListener('beforeunload', (e) => {
  if (window._isHpmInstalling) {
    e.preventDefault();
    e.returnValue = ''; // Required for legacy browsers
  }
});

// ── Inject persistent spinner keyframe once (avoids CSS reset on innerHTML update) ──
(function _injectHpmSpinStyle() {
  if (document.getElementById('hpm-spin-style')) return;
  const s = document.createElement('style');
  s.id = 'hpm-spin-style';
  s.textContent = `
    @keyframes hpm-spin {
      from { transform: rotate(0deg); }
      to   { transform: rotate(360deg); }
    }
    .hpm-spinner {
      display: inline-block;
      width: 14px;
      height: 14px;
      border: 2px solid transparent;
      border-top-color: var(--accent, #6366f1);
      border-right-color: var(--accent, #6366f1);
      border-radius: 50%;
      animation: hpm-spin 0.7s linear infinite;
      flex-shrink: 0;
      vertical-align: middle;
    }
  `;
  (document.head || document.documentElement).appendChild(s);
})();

window.hpmDragOver = function (e) {
  e.preventDefault();
  const dz = document.getElementById('hpm-dropzone');
  if (dz) {
    dz.style.borderColor = 'var(--accent)';
    dz.style.background  = 'color-mix(in srgb, var(--accent) 8%, var(--bg2))';
  }
};

window.hpmDragLeave = function (e) {
  const dz = document.getElementById('hpm-dropzone');
  if (dz) {
    dz.style.borderColor = 'var(--border-color)';
    dz.style.background  = 'var(--bg2)';
  }
};

window.hpmDrop = function (e) {
  e.preventDefault();
  window.hpmDragLeave(e);
  const files = e.dataTransfer?.files;
  if (files && files.length > 0) window.hpmInstallBatch(files);
};

window.hpmFileSelected = function (e) {
  const files = e.target?.files;
  if (files && files.length > 0) window.hpmInstallBatch(files);
  e.target.value = '';
};

// Legacy compatibility wrapper
window.hpmInstallFile = function(file, forceAllowUnsigned = false, skipDepCheck = false) {
    window.hpmInstallBatch([file], forceAllowUnsigned, skipDepCheck);
};

window._hpmInstallQueue = [];
window._hpmInstallRunning = false;

window.hpmInstallBatch = async function(fileList, forceAllowUnsigned = false, forceSkipDepCheck = false) {
  const files = Array.from(fileList).filter(f => f.name.endsWith('.hpkg') || f.name.endsWith('.zip'));
  if (files.length === 0) {
    if (window.showToast) window.showToast('No valid .hpkg packages selected', 'error');
    return;
  }

  const allowUnsigned = forceAllowUnsigned || (document.getElementById('hpm-allow-unsigned')?.checked || false);
  const skipDepCheck = forceSkipDepCheck || (document.getElementById('hpm-skip-deps')?.checked || false);

  // Add files to the queue
  files.forEach(f => {
      window._hpmInstallQueue.push({
          id: Math.random().toString(36).substring(2, 10),
          file: f,
          status: 'pending', // pending, installing, done, failed, canceled
          allowUnsigned,
          skipDepCheck,
          progressMsg: '',   // row 1: current step label
          pipLogMsg: '',     // row 2: latest pip log line
          result: null
      });
  });

  window.hpmRenderInstallQueue();

  if (!window._hpmInstallRunning) {
      window._hpmInstallRunning = true;
      window._isHpmInstalling = true;
      _hpmProcessQueue(); // non-blocking start
  }
};

window.hpmCancelQueueItem = function(id) {
    const item = window._hpmInstallQueue.find(i => i.id === id);
    if (item && item.status === 'pending') {
        item.status = 'canceled';
        window.hpmRenderInstallQueue();
    }
};

window.hpmRenderInstallQueue = function() {
    let html = `<div style="text-align:left; background:rgba(0,0,0,0.3); border-radius:10px; padding:12px; margin-top:8px; max-height:260px; overflow-y:auto; font-size:13px; border:1px solid rgba(255,255,255,0.08);">`;
    
    let total = window._hpmInstallQueue.length;
    let completed = 0;

    window._hpmInstallQueue.forEach(item => {
        let badge = '';
        let action = '';

        if (item.status === 'pending') {
            badge = `<span style="display:inline-flex;align-items:center;gap:5px;padding:3px 10px;border-radius:12px;background:rgba(255,255,255,0.05);color:var(--muted);font-size:11px;font-weight:600;"><i class="far fa-clock"></i> ${_ti('Waiting...', 'In attesa...', 'Esperando...')}</span>`;
            action = `<button onclick="window.hpmCancelQueueItem('${item.id}')" style="background:none;border:none;color:#ef4444;cursor:pointer;padding:0 5px;" title="${_ti('Cancel', 'Annulla', 'Cancelar')}"><i class="fas fa-times"></i></button>`;
        } else if (item.status === 'installing') {
            const stepTxt = item.progressMsg ? item.progressMsg : _ti('Installing...', 'Installazione...', 'Instalando...');
            badge = `<span style="display:inline-flex;align-items:center;gap:6px;padding:3px 10px;border-radius:12px;background:rgba(99,102,241,0.18);border:1px solid rgba(99,102,241,0.3);color:var(--accent);font-size:11px;font-weight:600;"><i class="fas fa-spinner fa-spin"></i> <span id="hpm-queue-step-${item.id}">${stepTxt}</span></span>`;
        } else if (item.status === 'done') {
            const statusLabel = item.result?.is_update ? _ti('Updated', 'Aggiornato', 'Actualizado') : _ti('Installed', 'Installato', 'Instalado');
            badge = `<span style="display:inline-flex;align-items:center;gap:5px;padding:3px 10px;border-radius:12px;background:rgba(99,102,241,0.18);border:1px solid rgba(99,102,241,0.3);color:var(--accent);font-size:11px;font-weight:600;"><i class="fas fa-check"></i> ${statusLabel}</span>`;
            completed++;
        } else if (item.status === 'failed') {
            badge = `<span style="display:inline-flex;align-items:center;gap:5px;padding:3px 10px;border-radius:12px;background:rgba(239,68,68,0.15);border:1px solid rgba(239,68,68,0.3);color:#ef4444;font-size:11px;font-weight:600;" title="${item.result?.error || ''}"><i class="fas fa-times"></i> ${_ti('Error', 'Errore', 'Error')}</span>`;
            completed++;
        } else if (item.status === 'canceled') {
            badge = `<span style="display:inline-flex;align-items:center;gap:5px;padding:3px 10px;border-radius:12px;background:rgba(255,255,255,0.05);color:var(--muted);font-size:11px;font-weight:600;"><i class="fas fa-ban"></i> ${_ti('Canceled', 'Annullato', 'Cancelado')}</span>`;
            completed++;
        }

        const logRow = (item.status === 'installing') ? `
            <div id="hpm-queue-log-${item.id}" class="hp-log-line" style="${item.pipLogMsg ? 'display:block;' : 'display:none;'} margin-top:6px; font-size:12px;">${item.pipLogMsg || ''}</div>` : '';

        const installPath = (item.status === 'done' && item.result?.install_path) ? `
            <div style="margin-left:24px; font-size:11px; font-family:monospace; color:var(--accent); opacity:0.85; margin-top:4px;">${_ti('Installed in:', 'Installato in:', 'Instalado en:')} ${item.result.install_path}</div>` : '';

        const isCurrent = item.status === 'installing';
        html += `
          <div style="margin-bottom:8px; padding:8px 12px; border-radius:8px; transition:all 0.2s ease; ${isCurrent ? 'background:rgba(99,102,241,0.08); border:1px solid rgba(99,102,241,0.25);' : 'background:rgba(255,255,255,0.02); border:1px solid rgba(255,255,255,0.05);'}">
            <div style="display:flex; justify-content:space-between; align-items:center; gap:8px;">
              <span style="color:var(--text); font-weight:600; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; max-width:60%; font-size:13px;" title="${item.file.name}">
                <i class="fas fa-file-archive" style="color:var(--accent); margin-right:8px;"></i>${item.file.name}
              </span>
              <div style="display:flex; align-items:center; gap:8px;">
                ${badge}
                ${action}
              </div>
            </div>
            ${logRow}
            ${installPath}
          </div>
        `;
    });
    
    html += `</div>`;
    
    let pct = total > 0 ? Math.round((completed / total) * 100) : 0;
    
    const header = `<div style="font-weight:700; color:var(--text); margin-bottom:6px; font-size:1.05em; display:flex; justify-content:space-between; align-items:center;">
        <span><i class="fas fa-layer-group" style="color:var(--accent); margin-right:8px;"></i>${_ti('Installation Queue', 'Coda di installazione', 'Cola de instalación')}</span>
        <span style="font-size:0.85em; color:var(--muted); font-weight:normal;">(${completed}/${total})</span>
    </div>`;
    
    window.hpmSetProgress(true, header + html, pct);
};

async function _hpmProcessQueue() {
    try {
        let hasPending = true;
        while (hasPending) {
            const item = window._hpmInstallQueue.find(i => i.status === 'pending');
            if (!item) {
                hasPending = false;
                break;
            }

            item.status = 'installing';
            const titleEl = document.getElementById('hpm-progress-title');
            if (titleEl) {
                titleEl.textContent = `${_ti('Installing', 'Installazione', 'Instalando')} ${item.file.name}…`;
            }
            const iconEl = document.getElementById('hpm-progress-icon');
            if (iconEl) {
                iconEl.className = 'fas fa-spinner fa-spin hp-icon';
                iconEl.style.color = 'var(--accent)';
            }
            window.hpmRenderInstallQueue();

            const formData = new FormData();
            formData.append('hpkg_files[]', item.file);
            formData.append('allow_unsigned', item.allowUnsigned ? 'true' : 'false');
            if (item.skipDepCheck) formData.append('skip_dep_check', 'true');

            try {
                const resp = await fetch('/api/packages/install/batch', { method: 'POST', body: formData });
                const data = await resp.json();
                
                if (data.ok && data.results && data.results.length > 0) {
                    const r = data.results[0];
                    item.status = r.ok ? 'done' : 'failed';
                    item.result = r;
                } else {
                    item.status = 'failed';
                    item.result = { ok: false, error: data.error || 'Unknown error' };
                }
            } catch (err) {
                item.status = 'failed';
                item.result = { ok: false, error: err.message };
            }

            window.hpmRenderInstallQueue();
        }
    } catch (e) {
        console.error('[HPM:Queue] Unexpected error in _hpmProcessQueue:', e);
    } finally {
        window._hpmInstallRunning = false;
        window._isHpmInstalling = false;
        _hpmShowFinalSummary();
    }
}

function _hpmShowFinalSummary() {
    const _ti = (en, it, es) => { const l = (document.documentElement.lang||'en').toLowerCase(); if(l.startsWith('it')) return it; if(l.startsWith('es')) return es; return en; };
    
    let succeeded = window._hpmInstallQueue.filter(i => i.status === 'done').length;
    let failed = window._hpmInstallQueue.filter(i => i.status === 'failed').length;
    let canceled = window._hpmInstallQueue.filter(i => i.status === 'canceled').length;
    let total = window._hpmInstallQueue.length;
    let isSingle = total === 1;

    // Check missing deps for single-file install UX continuity
    if (isSingle && failed === 1) {
        const r = window._hpmInstallQueue[0].result;
        if (r && !r.ok && r.missing_deps && r.missing_deps.length > 0 && !window._hpmInstallQueue[0].allowUnsigned) {
            const fileItem = window._hpmInstallQueue[0].file;
            window._hpmInstallQueue = []; // Reset queue before recursive dialog
            return _handleMissingDepsDialogue(fileItem, r.missing_deps, false);
        }
    }

    // ── Process succeeded installs: NEW badge + install_path ────────────────
    let needsRestartPkg = null; // Track first package requiring restart for popup
    const lblPath = _ti('Installed in:', 'Installato in:', 'Instalado en:');
    const lblCfg  = _ti('Configuration available in', 'Configurazione disponibile in', 'Configuración disponible en');

    let newPanels = [];
    try { newPanels = JSON.parse(localStorage.getItem('hpm_new_panels') || '[]'); } catch(e) {}

    let singleExtraHTML = '';
    window._hpmInstallQueue.forEach(item => {
        if (item.status !== 'done' || !item.result?.ok) return;
        const r = item.result;

        // Save NEW badge: use BOTH tab_id AND pkg id for reliable matching
        if (r.config_panel) {
            const tabId = r.config_panel.tab_id || r.id;
            const pkgId = r.id || '';
            for (const key of [tabId, pkgId]) {
                if (key && !newPanels.includes(key)) newPanels.push(key);
            }
        }

        // Track first package requiring restart
        if (r.requires_restart && !needsRestartPkg) {
            needsRestartPkg = r.name || r.id;
        }

        // Build extra HTML for single installs
        if (isSingle) {
            if (r.install_path) {
                singleExtraHTML += `<div style="margin-top:12px; font-size:1.05em; color:var(--text); font-weight:normal;">${lblPath}<br><code style="display:inline-block; margin-top:4px; color:var(--accent); background:rgba(255,255,255,0.05); border:1px solid rgba(255,255,255,0.1); padding:4px 8px; border-radius:6px;">${r.install_path}</code></div>`;
            }
            if (r.config_panel) {
                const tabId    = r.config_panel.tab_id || r.id;
                const catLabel = r.config_panel.category || '';
                const tabLabel = r.config_panel.tab_label || r.name || r.id;
                singleExtraHTML += `<div style="margin-top:8px; font-size:1em; font-weight:normal;">
                    <i class="fas fa-cogs" style="margin-right:4px; color:var(--muted);"></i>
                    <span style="color:var(--muted);">${lblCfg}</span>
                    <a href="#${window._hesc(tabId)}" style="color:var(--accent); text-decoration:none; font-weight:600; margin-left:4px;"
                       onclick="document.getElementById('packages-install-modal').style.display='none';">
                        ${window._hesc(catLabel)}${catLabel ? ' &rarr; ' : ''}${window._hesc(tabLabel)}
                    </a>
                </div>`;
            }
        }
    });

    // Persist updated NEW panels list
    try { localStorage.setItem('hpm_new_panels', JSON.stringify(newPanels)); } catch(e) {}

    // ── Build extraHTML ──────────────────────────────────────────────────────
    let extraHTML = '';

    if (isSingle && succeeded === 1) {
        // Single install: show path + config panel link
        extraHTML = singleExtraHTML;
    } else {
        // Batch: show per-item status list with install paths
        extraHTML = `<div style="text-align:left; background:rgba(0,0,0,0.2); border-radius:8px; padding:10px; margin-top:12px; max-height:180px; overflow-y:auto; font-size:1.05em; border:1px solid rgba(255,255,255,0.05);">`;
        window._hpmInstallQueue.forEach(item => {
            let icon = '', msg = '';
            if (item.status === 'done') {
                icon = '<i class="fas fa-check" style="color:var(--accent); margin-right:6px; width:14px;"></i>';
                const rr = item.result;
                const pathSnippet = (rr?.install_path)
                    ? ` <code style="font-size:1em;color:var(--accent);opacity:0.8;">${rr.install_path}</code>`
                    : `<span style="color:var(--muted)">${_ti('installed','installato','instalado')}</span>`;
                msg = pathSnippet;
            } else if (item.status === 'failed') {
                icon = '<i class="fas fa-times" style="color:#ef4444; margin-right:6px; width:14px;"></i>';
                msg = `<span style="color:#ef4444">${item.result?.error || 'error'}</span>`;
            } else if (item.status === 'canceled') {
                icon = '<i class="fas fa-ban" style="color:var(--muted); margin-right:6px; width:14px;"></i>';
                msg = `<span style="color:var(--muted)">${_ti('canceled','annullato','cancelado')}</span>`;
            }
            extraHTML += `<div style="margin-bottom:5px; display:flex; justify-content:space-between; align-items:baseline; gap:8px;">
                <span style="color:var(--text); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; flex-shrink:0; max-width:45%;">${icon}${item.file.name}</span>
                <span style="flex:1; text-align:right; overflow:hidden; text-overflow:ellipsis;">${msg}</span>
            </div>`;
        });
        extraHTML += `</div>`;
    }

    if (succeeded > 0) {
        const sound = localStorage.getItem('hpm_install_sound') || 'success.mp3';
        if (sound !== 'none') {
            if (sound.startsWith('custom|')) {
                const path = sound.substring(7);
                new Audio('/api/local_file?path=' + encodeURIComponent(path)).play().catch(() => {});
            } else {
                new Audio(`/static/sounds/${sound}`).play().catch(() => {});
            }
        }
    }

    const lblHint = _ti('Double click anywhere to close', 'Fai doppio clic per chiudere', 'Haz doble clic para cerrar');
    const hintHTML = `<div style="font-size:1em;color:var(--muted);margin-top:15px;opacity:0.6;font-weight:normal;">${lblHint}</div>`;
    
    let lblSuccess = '';
    if (isSingle) {
        if (succeeded === 1) lblSuccess = _ti('Installed successfully!', 'Installato con successo!', '¡Instalado con éxito!');
        else if (canceled === 1) lblSuccess = _ti('Installation canceled', 'Installazione annullata', 'Instalación cancelada');
        else lblSuccess = _ti('Installation failed', 'Installazione fallita', 'Instalación fallida');
    } else {
        if (failed === 0 && canceled === 0) lblSuccess = _ti('Batch completed successfully!', 'Operazione completata!', '¡Completado con éxito!');
        else lblSuccess = _ti('Completed with some issues', 'Completato con problemi', 'Completado con problemas');
    }
    
    const mainIconColor = (failed === 0 && canceled === 0) ? 'var(--accent, #6366f1)' : (succeeded > 0 ? '#f59e0b' : '#ef4444');
    const mainIcon = (failed === 0 && canceled === 0) ? 'fa-check-circle' : (succeeded > 0 ? 'fa-exclamation-circle' : 'fa-times-circle');
    
    const titleEl = document.getElementById('hpm-progress-title');
    if (titleEl) titleEl.textContent = lblSuccess;
    const iconEl = document.getElementById('hpm-progress-icon');
    if (iconEl) {
        iconEl.className = `fas ${mainIcon} hp-icon`;
        iconEl.style.color = mainIconColor;
    }
    const msgEl = document.getElementById('hpm-progress-msg');
    if (msgEl) msgEl.textContent = '';
    const logEl = document.getElementById('hpm-progress-log');
    if (logEl) { logEl.textContent = ''; logEl.style.display = 'none'; }

    window.hpmSetProgress(true, `
      <div style="text-align:center; padding: 10px 0;">
          <i class="fas ${mainIcon}" style="margin-right:6px; color:${mainIconColor}; font-size:1.5em; margin-bottom:8px; display:block;"></i> 
          <b style="font-size:1.1em; color:var(--text)">${lblSuccess}</b>
          ${batchStatsHtml}
          ${extraHTML}
          ${hintHTML}
      </div>`, 100);
    
    const container = document.getElementById('hpm-install-progress');
    if (container) {
        container.ondblclick = () => {
            window.hpmSetProgress(false);
            window._hpmInstallQueue = []; // Clear queue on close
        };
        container.style.cursor = 'default';
    }

    if (failed > 0 && window.showToast && !isSingle) {
       window.showToast(`Batch finished with ${failed} error(s)`, 'warning');
    }

    if (typeof window.hpmLoadPackages === 'function') window.hpmLoadPackages();
    if (typeof window.hpmRefreshConfigHub === 'function') window.hpmRefreshConfigHub();
    if (typeof window.loadWidgetsPanel === 'function') window.loadWidgetsPanel();

    // ── Restart Required signal ──────────────────────────────────────────────
    if (needsRestartPkg && typeof window.hpmSignalRestartPending === 'function') {
        window.hpmSignalRestartPending();
    }
}


function _handleMissingDepsDialogue(file, missing_deps, forceAllowUnsigned) {
    const _ti = (en, it, es) => { const l = (document.documentElement.lang||'en').toLowerCase(); if(l.startsWith('it')) return it; if(l.startsWith('es')) return es; return en; };
    const lblMissing = _ti('Missing required modules:', 'Moduli richiesti mancanti:', 'Módulos requeridos faltantes:');
    const question = _ti('Do you want to install them automatically?', 'Vuoi installarli automaticamente?', '¿Quieres instalarlos automáticamente?');
    const btnAll = _ti('Install All', 'Installa Tutto', 'Instalar Todo');
    const btnOnly = _ti('Install Only', 'Installa Solo', 'Instalar Solo');

    const html = `
      <div style="text-align:center; padding:10px 0;">
        <i class="fas fa-exclamation-triangle" style="font-size:1.8em; color:#f59e0b; margin-bottom:12px;"></i>
        <div style="font-size:1.05em; margin-bottom:12px; color:var(--text);">${question}</div>
        <div style="font-size:1em; color:var(--muted); margin-bottom:20px;">
          <i class="fas fa-box-open" style="margin-right:6px;"></i>${lblMissing} <b style="color:var(--text);">${missing_deps.join(', ')}</b>
        </div>
        <div style="display:flex; gap:10px; justify-content:center;">
          <button id="hpm-local-dep-all" style="background:linear-gradient(135deg,var(--accent),var(--accent2,#7c3aed));color:#fff;border:none;padding:10px 18px;border-radius:8px;font-weight:700;cursor:pointer;flex:1;">
            <i class="fas fa-download" style="margin-right:6px;"></i> ${btnAll}
          </button>
          <button id="hpm-local-dep-only" style="background:rgba(255,255,255,0.05);color:var(--text);border:1px solid rgba(255,255,255,0.1);padding:10px 18px;border-radius:8px;font-weight:600;cursor:pointer;flex:1;">
            ${btnOnly}
          </button>
        </div>
      </div>
    `;
    window.hpmSetProgress(true, html, 100);
    
    const container = document.getElementById('hpm-install-progress');
    if (container) { container.ondblclick = null; container.style.cursor = 'default'; }

    document.getElementById('hpm-local-dep-all').onclick = async () => {
       window.hpmSetProgress(true, `<div style="text-align:center;"><i class="fas fa-spinner fa-spin" style="margin-right:6px;"></i> ${_ti('Resolving...', 'Risoluzione in corso...', 'Resolviendo...')}</div>`, 50);
       try {
         const catResp = await fetch('/api/hpm/store/catalog?refresh=1');
         const catData = await catResp.json();
         if (catData && catData.catalog && catData.catalog.packages) {
            for (const d of missing_deps) {
               const depPkg = catData.catalog.packages.find(p => p.id === d);
               if (depPkg) {
                  await fetch('/api/hpm/store/install', {
                     method: 'POST',
                     headers: { 'Content-Type': 'application/json' },
                     body: JSON.stringify({ id: depPkg.id, download_url: depPkg.download_url, allow_unsigned: true, skip_dep_check: true })
                  });
               }
            }
         }
         window.hpmInstallBatch([file], forceAllowUnsigned, true);
       } catch(e) {
         if (window.showToast) window.showToast('Error resolving dependencies', 'error');
       }
    };

    document.getElementById('hpm-local-dep-only').onclick = () => {
       window.hpmInstallBatch([file], forceAllowUnsigned, true);
    };
}

window.hpmSetProgress = function(visible, contentOrLabel = '', pct = 0) {
  const container = document.getElementById('hpm-install-progress');
  const bar       = document.getElementById('hpm-progress-bar');
  const pctEl     = document.getElementById('hpm-progress-pct');
  const lbl       = document.getElementById('hpm-progress-label');
  const msg       = document.getElementById('hpm-progress-msg');
  const logEl     = document.getElementById('hpm-progress-log');
  if (!container) return;

  if (!visible) {
    container.style.display = 'none';
    container.classList.remove('hp-state-running', 'hp-state-done', 'hp-state-error');
    if (bar) bar.style.width = '0%';
    if (pctEl) pctEl.textContent = '0%';
    if (msg) msg.textContent = '';
    if (logEl) { logEl.textContent = ''; logEl.style.display = 'none'; }
    if (lbl) lbl.innerHTML = '';
    return;
  }

  container.style.display = 'block';
  const p = Math.min(100, Math.max(0, Math.round(pct || 0)));
  if (bar) bar.style.width = `${p}%`;
  if (pctEl) pctEl.textContent = `${p}%`;

  container.classList.remove('hp-state-running', 'hp-state-done', 'hp-state-error');
  if (p >= 100) {
    container.classList.add('hp-state-done');
  } else if (p > 0) {
    container.classList.add('hp-state-running');
  }

  if (contentOrLabel) {
    if (typeof contentOrLabel === 'string' && (contentOrLabel.includes('<div') || contentOrLabel.includes('<b') || contentOrLabel.includes('<i') || contentOrLabel.includes('<code'))) {
      if (lbl) lbl.innerHTML = contentOrLabel;
    } else {
      if (msg) msg.textContent = contentOrLabel;
    }
  }
};

document.addEventListener('hpmProgressUpdate', (e) => {
    const detail = e.detail || {};
    const bar = document.getElementById('hpm-progress-bar');
    const pctEl = document.getElementById('hpm-progress-pct');
    const msg = document.getElementById('hpm-progress-msg');
    const logEl = document.getElementById('hpm-progress-log');
    const container = document.getElementById('hpm-install-progress');

    // 1. Identify active installing item in queue
    const currentItem = window._hpmInstallQueue.find(i => i.status === 'installing');
    if (currentItem) {
        if (detail.step === 'pip_log') {
            currentItem.pipLogMsg = detail.message || '';
        } else {
            if (detail.message) currentItem.progressMsg = detail.message;
            if (detail.step !== 'pip_log') currentItem.pipLogMsg = '';
        }
        if (detail.percent != null && !isNaN(detail.percent)) {
            currentItem.percent = Math.min(100, Math.max(0, Math.round(detail.percent)));
        }
        // Update item in the queue UI if present
        const queueStepEl = document.getElementById(`hpm-queue-step-${currentItem.id}`);
        if (queueStepEl && currentItem.progressMsg) {
            queueStepEl.textContent = currentItem.progressMsg;
        }
        const queueLogEl = document.getElementById(`hpm-queue-log-${currentItem.id}`);
        if (queueLogEl) {
            if (currentItem.pipLogMsg) {
                queueLogEl.textContent = currentItem.pipLogMsg;
                queueLogEl.style.display = 'block';
            } else if (detail.step !== 'pip_log') {
                queueLogEl.style.display = 'none';
            }
        }
    }

    // 2. Secondary log row
    if (detail.step === 'pip_log') {
        if (logEl) {
            logEl.textContent = detail.message || '';
            logEl.style.display = detail.message ? 'block' : 'none';
        }
        return;
    } else if (logEl && detail.message) {
        logEl.textContent = '';
        logEl.style.display = 'none';
    }

    // 3. Primary message row
    if (msg && detail.message) {
        msg.textContent = detail.message;
    }

    // 4. Progress percentage
    if (detail.percent != null && !isNaN(detail.percent)) {
        const itemP = Math.min(100, Math.max(0, Math.round(detail.percent)));
        let overallP = itemP;
        const total = window._hpmInstallQueue.length;
        if (total > 1) {
            const completed = window._hpmInstallQueue.filter(i => i.status === 'done' || i.status === 'failed' || i.status === 'canceled').length;
            overallP = Math.min(100, Math.round(((completed + (itemP / 100)) / total) * 100));
        }
        if (bar) bar.style.width = `${overallP}%`;
        if (pctEl) pctEl.textContent = `${overallP}%`;
        if (container) {
            if (overallP >= 100) {
                container.classList.remove('hp-state-running');
                container.classList.add('hp-state-done');
            } else {
                container.classList.remove('hp-state-done');
                container.classList.add('hp-state-running');
            }
        }
    }
});
