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

window.hpmInstallBatch = async function(fileList, forceAllowUnsigned = false, skipDepCheck = false) {
  const files = Array.from(fileList).filter(f => f.name.endsWith('.hpkg') || f.name.endsWith('.zip'));
  
  if (files.length === 0) {
    if (window.showToast) window.showToast('No valid .hpkg packages selected', 'error');
    return;
  }

  const _ti = (en, it, es) => { const l = (document.documentElement.lang||'en').toLowerCase(); if(l.startsWith('it')) return it; if(l.startsWith('es')) return es; return en; };
  
  const isSingle = files.length === 1;
  const label = isSingle ? `Installing ${files[0].name}...` : `Installing ${files.length} packages...`;
  
  window.hpmSetProgress(true, label, 30);

  const formData = new FormData();
  files.forEach(f => formData.append('hpkg_files[]', f));

  const allowUnsigned = forceAllowUnsigned || (document.getElementById('hpm-allow-unsigned')?.checked || false);
  formData.append('allow_unsigned', allowUnsigned ? 'true' : 'false');
  if (skipDepCheck) {
    formData.append('skip_dep_check', 'true');
  }

  try {
    window.hpmSetProgress(true, `<i class="fas fa-cog fa-spin" style="margin-right:6px; color:var(--accent);"></i> Uploading & processing...`, 50);
    
    let simPct = 50;
    const simTimer = setInterval(() => {
      if (simPct < 90) {
        simPct += 5;
        window.hpmSetProgress(true, `<i class="fas fa-cog fa-spin" style="margin-right:6px; color:var(--accent);"></i> Processing batch...`, simPct);
      }
    }, 2000);

    const resp = await fetch('/api/packages/install/batch', { method: 'POST', body: formData });
    clearInterval(simTimer);
    
    window.hpmSetProgress(true, '<i class="fas fa-cog fa-spin" style="margin-right:6px; color:var(--accent);"></i> Finalizing...', 95);
    const data = await resp.json();

    if (data.ok) {
      let extraHTML = `<div style="text-align:left; background:rgba(0,0,0,0.2); border-radius:8px; padding:10px; margin-top:12px; max-height:150px; overflow-y:auto; font-size:0.85em; border:1px solid rgba(255,255,255,0.05);">`;
      
      data.results.forEach(r => {
          const icon = r.ok ? '<i class="fas fa-check" style="color:#10b981; margin-right:6px; width:14px;"></i>' : '<i class="fas fa-times" style="color:#ef4444; margin-right:6px; width:14px;"></i>';
          const msg = r.ok ? '<span style="color:var(--muted)">installed</span>' : `<span style="color:#ef4444">${r.error || 'error'}</span>`;
          extraHTML += `<div style="margin-bottom:4px; display:flex; justify-content:space-between;">
              <span style="color:var(--text); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; max-width:60%;">${icon}${r.filename}</span>
              ${msg}
          </div>`;
      });
      extraHTML += `</div>`;

      // Se almeno 1 pacchetto ha avuto successo, suoniamo success (suono unico)
      if (data.succeeded > 0) {
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
      const lblSuccess = data.failed === 0 
          ? _ti('Batch completed successfully!', 'Operazione completata!', '¡Completado con éxito!')
          : _ti('Completed with some errors', 'Completato con errori', 'Completado con errores');
      
      const mainIconColor = data.failed === 0 ? '#10b981' : (data.succeeded > 0 ? '#f59e0b' : '#ef4444');
      const mainIcon = data.failed === 0 ? 'fa-check-circle' : (data.succeeded > 0 ? 'fa-exclamation-circle' : 'fa-times-circle');

      window.hpmSetProgress(true, `
        <div style="text-align:center; padding: 10px 0;">
            <i class="fas ${mainIcon}" style="margin-right:6px; color:${mainIconColor}; font-size:1.5em; margin-bottom:8px; display:block;"></i> 
            <b style="font-size:1.1em; color:var(--text)">${lblSuccess}</b>
            <div style="font-size:0.85em; color:var(--muted); margin-top:4px;">${data.succeeded} succeeded • ${data.failed} failed</div>
            ${extraHTML}
            ${hintHTML}
        </div>`, 100);
      
      const container = document.getElementById('hpm-install-progress');
      if (container) {
          container.ondblclick = () => window.hpmSetProgress(false);
          container.style.cursor = 'default';
      }

      // Check missing deps per fallbacks (we handle only the first one with missing deps for simplicity)
      const missingDepsResult = data.results.find(r => !r.ok && r.missing_deps && r.missing_deps.length > 0);
      if (missingDepsResult && data.results.length === 1 && !forceAllowUnsigned) {
         // Trigger the interactive missing deps dialogue just for single-file for UX continuity
         return _handleMissingDepsDialogue(fileList[0], missingDepsResult.missing_deps, forceAllowUnsigned);
      }

      if (data.failed > 0 && window.showToast) {
         window.showToast(`Batch finished with ${data.failed} error(s)`, 'warning');
      }

      if (typeof window.hpmLoadPackages === 'function') window.hpmLoadPackages();
      if (typeof window.hpmRefreshConfigHub === 'function') window.hpmRefreshConfigHub();
      if (typeof window.loadWidgetsPanel === 'function') window.loadWidgetsPanel();

    } else {
      window.hpmSetProgress(false);
      if (window.showToast) window.showToast(`Install failed: ${data.error}`, 'error');
    }
  } catch (err) {
    window.hpmSetProgress(false);
    if (window.showToast) window.showToast(`Network error: ${err.message}`, 'error');
  }
};

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
