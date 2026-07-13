/**
 * packages_panel_install.js
 * ─────────────────────────────────────────────────────────────────────────────
 * Install logic for Hecos Package Manager
 */

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
          progressMsg: '',
          result: null
      });
  });

  window.hpmRenderInstallQueue();

  if (!window._hpmInstallRunning) {
      window._hpmInstallRunning = true;
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
    const _ti = (en, it, es) => { const l = (document.documentElement.lang||'en').toLowerCase(); if(l.startsWith('it')) return it; if(l.startsWith('es')) return es; return en; };
    let html = `<div style="text-align:left; background:rgba(0,0,0,0.2); border-radius:8px; padding:10px; margin-top:12px; max-height:200px; overflow-y:auto; font-size:0.85em; border:1px solid rgba(255,255,255,0.05);">`;
    
    let total = window._hpmInstallQueue.length;
    let completed = 0;

    window._hpmInstallQueue.forEach(item => {
        let icon = '';
        let msg = '';
        let action = '';

        if (item.status === 'pending') {
            icon = '<i class="far fa-circle" style="color:var(--muted); margin-right:6px; width:14px;"></i>';
            msg = `<span style="color:var(--muted)">${_ti('Waiting...', 'In attesa...', 'Esperando...')}</span>`;
            action = `<button onclick="window.hpmCancelQueueItem('${item.id}')" style="background:none;border:none;color:#ef4444;cursor:pointer;padding:0 5px;" title="${_ti('Cancel', 'Annulla', 'Cancelar')}"><i class="fas fa-times"></i></button>`;
        } else if (item.status === 'installing') {
            icon = '<i class="fas fa-circle-notch fa-spin" style="color:var(--accent); margin-right:6px; width:14px;"></i>';
            let txt = item.progressMsg ? item.progressMsg : _ti('Installing...', 'Installazione...', 'Instalando...');
            msg = `<span style="color:var(--accent)">${txt}</span>`;
        } else if (item.status === 'done') {
            icon = '<i class="fas fa-check" style="color:#10b981; margin-right:6px; width:14px;"></i>';
            msg = `<span style="color:var(--muted)">${_ti('Installed', 'Installato', 'Instalado')}</span>`;
            completed++;
        } else if (item.status === 'failed') {
            icon = '<i class="fas fa-times" style="color:#ef4444; margin-right:6px; width:14px;"></i>';
            msg = `<span style="color:#ef4444" title="${item.result?.error || ''}">${_ti('Error', 'Errore', 'Error')}</span>`;
            completed++;
        } else if (item.status === 'canceled') {
            icon = '<i class="fas fa-ban" style="color:var(--muted); margin-right:6px; width:14px;"></i>';
            msg = `<span style="color:var(--muted)">${_ti('Canceled', 'Annullato', 'Cancelado')}</span>`;
            completed++;
        }

        html += `<div style="margin-bottom:6px; display:flex; justify-content:space-between; align-items:center; padding: 4px; border-radius: 4px; ${item.status==='installing' ? 'background:rgba(255,255,255,0.05);' : ''}">
            <span style="color:var(--text); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; max-width:60%;" title="${item.file.name}">${icon}${item.file.name}</span>
            <div style="display:flex; align-items:center; gap:8px;">${msg}${action}</div>
        </div>`;
    });
    
    html += `</div>`;
    
    let pct = total > 0 ? Math.round((completed / total) * 100) : 0;
    
    const header = `<div style="font-weight:bold; color:var(--text); margin-bottom:8px;">${_ti('Installation Queue', 'Coda di installazione', 'Cola de instalación')} (${completed}/${total})</div>`;
    
    window.hpmSetProgress(true, header + html, pct);
};

async function _hpmProcessQueue() {
    let hasPending = true;
    while (hasPending) {
        const item = window._hpmInstallQueue.find(i => i.status === 'pending');
        if (!item) {
            hasPending = false;
            break;
        }

        item.status = 'installing';
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

    window._hpmInstallRunning = false;
    _hpmShowFinalSummary();
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

    let extraHTML = `<div style="text-align:left; background:rgba(0,0,0,0.2); border-radius:8px; padding:10px; margin-top:12px; max-height:150px; overflow-y:auto; font-size:0.85em; border:1px solid rgba(255,255,255,0.05);">`;
    window._hpmInstallQueue.forEach(item => {
        let icon = '', msg = '';
        if (item.status === 'done') {
            icon = '<i class="fas fa-check" style="color:#10b981; margin-right:6px; width:14px;"></i>';
            msg = `<span style="color:var(--muted)">${_ti('installed', 'installato', 'instalado')}</span>`;
        } else if (item.status === 'failed') {
            icon = '<i class="fas fa-times" style="color:#ef4444; margin-right:6px; width:14px;"></i>';
            msg = `<span style="color:#ef4444">${item.result?.error || 'error'}</span>`;
        } else if (item.status === 'canceled') {
            icon = '<i class="fas fa-ban" style="color:var(--muted); margin-right:6px; width:14px;"></i>';
            msg = `<span style="color:var(--muted)">${_ti('canceled', 'annullato', 'cancelado')}</span>`;
        }
        
        extraHTML += `<div style="margin-bottom:4px; display:flex; justify-content:space-between;">
            <span style="color:var(--text); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; max-width:60%;">${icon}${item.file.name}</span>
            ${msg}
        </div>`;
    });
    extraHTML += `</div>`;

    if (isSingle && succeeded === 1) {
        extraHTML = '';
        const r = window._hpmInstallQueue[0].result;
        if (r && r.install_path) {
            const lblPath = _ti('Installed in:', 'Installato in:', 'Instalado en:');
            extraHTML += `<div style="margin-top:12px; font-size: 0.95em; color: var(--text); font-weight:normal;">${lblPath}<br><code style="display:inline-block; margin-top:4px; color:var(--accent); background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); padding: 4px 8px; border-radius: 6px;">${r.install_path}</code></div>`;
        }
        if (r && r.config_panel) {
            const lblCfg = _ti('Available in the Configuration menu', 'Disponibile nel menu Configurazione', 'Disponible en el menú Configuración');
            extraHTML += `<div style="margin-top:8px; font-size: 0.85em; color: var(--muted); font-weight:normal;"><i class="fas fa-cogs" style="margin-right:4px;"></i>${lblCfg}</div>`;
        }
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
    const hintHTML = `<div style="font-size:0.75em;color:var(--muted);margin-top:15px;opacity:0.6;font-weight:normal;">${lblHint}</div>`;
    
    let lblSuccess = '';
    if (isSingle) {
        if (succeeded === 1) lblSuccess = _ti('Installed successfully!', 'Installato con successo!', '¡Instalado con éxito!');
        else if (canceled === 1) lblSuccess = _ti('Installation canceled', 'Installazione annullata', 'Instalación cancelada');
        else lblSuccess = _ti('Installation failed', 'Installazione fallita', 'Instalación fallida');
    } else {
        if (failed === 0 && canceled === 0) lblSuccess = _ti('Batch completed successfully!', 'Operazione completata!', '¡Completado con éxito!');
        else lblSuccess = _ti('Completed with some issues', 'Completato con problemi', 'Completado con problemas');
    }
    
    const mainIconColor = (failed === 0 && canceled === 0) ? '#10b981' : (succeeded > 0 ? '#f59e0b' : '#ef4444');
    const mainIcon = (failed === 0 && canceled === 0) ? 'fa-check-circle' : (succeeded > 0 ? 'fa-exclamation-circle' : 'fa-times-circle');
    
    const batchStatsHtml = isSingle ? '' : `<div style="font-size:0.85em; color:var(--muted); margin-top:4px;">${succeeded} ${_ti('succeeded', 'installati', 'completados')} • ${failed} ${_ti('failed', 'falliti', 'fallidos')} • ${canceled} ${_ti('canceled', 'annullati', 'cancelados')}</div>`;

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
        <div style="font-size:0.9em; color:var(--muted); margin-bottom:20px;">
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

window.hpmSetProgress = function(visible, label = '', pct = 0) {
  const container = document.getElementById('hpm-install-progress');
  const bar       = document.getElementById('hpm-progress-bar');
  const lbl       = document.getElementById('hpm-progress-label');
  if (!container) return;
  container.style.display = visible ? 'block' : 'none';
  if (bar) bar.style.width = `${pct}%`;
  if (lbl) lbl.innerHTML = label;
};

document.addEventListener('hpmProgressUpdate', (e) => {
    if (window._hpmInstallQueue) {
        const item = window._hpmInstallQueue.find(i => i.status === 'installing');
        if (item) {
            item.progressMsg = e.detail.message || e.detail.step || '';
            window.hpmRenderInstallQueue();
        }
    }
});
