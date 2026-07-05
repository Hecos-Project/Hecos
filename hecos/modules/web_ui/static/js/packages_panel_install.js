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
  const file = e.dataTransfer?.files?.[0];
  if (file) window.hpmInstallFile(file);
};

window.hpmFileSelected = function (e) {
  const file = e.target?.files?.[0];
  if (file) window.hpmInstallFile(file);
  e.target.value = '';
};

window.hpmInstallFile = async function(file, forceAllowUnsigned = false, skipDepCheck = false) {
  if (!file.name.endsWith('.hpkg') && !file.name.endsWith('.zip')) {
    if (window.showToast) window.showToast('File must be a .hpkg package', 'error');
    return;
  }

  window.hpmSetProgress(true, `Installing ${file.name}...`, 30);

  const formData = new FormData();
  formData.append('hpkg_file', file);

  const allowUnsigned = forceAllowUnsigned || (document.getElementById('hpm-allow-unsigned')?.checked || false);
  formData.append('allow_unsigned', allowUnsigned ? 'true' : 'false');
  if (skipDepCheck) {
    formData.append('skip_dep_check', 'true');
  }

  try {
    window.hpmSetProgress(true, '<i class="fas fa-cog fa-spin" style="margin-right:6px; color:var(--accent);"></i> Uploading to Hecos...', 50);
    
    // Simulate backend progress steps while waiting for fetch
    let simPct = 50;
    const simSteps = [
      { t: 1500, l: "Verifying Cryptographic Signature..." },
      { t: 3000, l: "Extracting Package Contents..." },
      { t: 5000, l: "Configuring Extensions..." },
      { t: 8000, l: "Finalizing Installation..." }
    ];
    
    const simTimers = simSteps.map((step, idx) => {
      return setTimeout(() => {
        simPct += 10;
        window.hpmSetProgress(true, `<i class="fas fa-cog fa-spin" style="margin-right:6px; color:var(--accent);"></i> ${step.l}`, simPct);
      }, step.t);
    });

    const resp = await fetch('/api/packages/install', { method: 'POST', body: formData });
    
    // Clear simulation timers if fetch finishes early
    simTimers.forEach(t => clearTimeout(t));
    
    window.hpmSetProgress(true, '<i class="fas fa-cog fa-spin" style="margin-right:6px; color:var(--accent);"></i> Processing response...', 95);
    const data = await resp.json();

    if (data.ok) {
      const _ti = (en, it, es) => { const l = (document.documentElement.lang||'en').toLowerCase(); if(l.startsWith('it')) return it; if(l.startsWith('es')) return es; return en; };
      let extraHTML = '';
      if (data.install_path) {
          const lblPath = _ti('Installed in:', 'Installato in:', 'Instalado en:');
          extraHTML += `<div style="margin-top:12px; font-size: 0.95em; color: var(--text); font-weight:normal;">${lblPath}<br><code style="display:inline-block; margin-top:4px; color:var(--accent); background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); padding: 4px 8px; border-radius: 6px;">${data.install_path}</code></div>`;
      }
      if (data.config_panel) {
          const lblCfg = _ti('Available in the Configuration menu', 'Disponibile nel menu Configurazione', 'Disponible en el menú Configuración');
          extraHTML += `<div style="margin-top:8px; font-size: 0.85em; color: var(--muted); font-weight:normal;"><i class="fas fa-cogs" style="margin-right:4px;"></i>${lblCfg}</div>`;
      }
      
      const lblHint = _ti('Double click anywhere to close', 'Fai doppio clic per chiudere', 'Haz doble clic para cerrar');
      const hintHTML = `<div style="font-size:0.75em;color:var(--muted);margin-top:15px;opacity:0.6;font-weight:normal;">${lblHint}</div>`;
      const lblSuccess = _ti('Installed successfully!', 'Installato con successo!', '¡Instalado con éxito!');
      
      window.hpmSetProgress(true, `<div style="text-align:center; padding: 10px 0;"><i class="fas fa-check-circle" style="margin-right:6px; color:#10b981; font-size:1.5em; margin-bottom:8px; display:block;"></i> <b style="font-size:1.1em; color:var(--text)">${lblSuccess}</b>${extraHTML}${hintHTML}</div>`, 100);
      
      const container = document.getElementById('hpm-install-progress');
      if (container) {
          container.ondblclick = () => window.hpmSetProgress(false);
          container.style.cursor = 'default';
      }

      const sound = localStorage.getItem('hpm_install_sound') || 'success.mp3';
      if (sound !== 'none') {
          if (sound.startsWith('custom|')) {
              const path = sound.substring(7);
              new Audio('/api/local_file?path=' + encodeURIComponent(path)).play().catch(() => {});
          } else {
              new Audio(`/static/sounds/${sound}`).play().catch(() => {});
          }
      }

      // Rimuovo il setTimeout automatico
      if (data.warnings?.length) {
        if (window.showToast) window.showToast(`Warning: ${data.warnings[0]}`, 'warning');
      }
      if (typeof window.hpmLoadPackages === 'function') window.hpmLoadPackages();
      if (typeof window.hpmRefreshConfigHub === 'function') window.hpmRefreshConfigHub();
      if (typeof window.loadWidgetsPanel === 'function') window.loadWidgetsPanel();
    } else {
      window.hpmSetProgress(false);
      // Handle signature error explicitly
      if (data.signature_error && !forceAllowUnsigned) {
        const msg = `This package is unsigned or untrusted. Installing unsigned packages can be a security risk.<br><br>Do you want to force install "<b>${file.name}</b>" anyway?`;
        if (typeof window.hpmShowConfirm === 'function') {
            window.hpmShowConfirm(msg, 'Force Install', () => {
                const checkbox = document.getElementById('hpm-allow-unsigned');
                if (checkbox) checkbox.checked = true;
                window.hpmInstallFile(file, true);
            });
        }
      } else if (data.missing_deps && data.missing_deps.length > 0) {
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
              <i class="fas fa-box-open" style="margin-right:6px;"></i>${lblMissing} <b style="color:var(--text);">${data.missing_deps.join(', ')}</b>
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
        
        // Remove click-to-close behavior so user has to choose
        const container = document.getElementById('hpm-install-progress');
        if (container) { container.ondblclick = null; container.style.cursor = 'default'; }

        document.getElementById('hpm-local-dep-all').onclick = async () => {
           window.hpmSetProgress(true, `<div style="text-align:center;"><i class="fas fa-spinner fa-spin" style="margin-right:6px;"></i> ${_ti('Resolving...', 'Risoluzione in corso...', 'Resolviendo...')}</div>`, 50);
           try {
             // To install remote deps for a local file, we fetch the catalog, install them via API, then retry local
             const catResp = await fetch('/api/hpm/store/catalog?refresh=1');
             const catData = await catResp.json();
             if (catData && catData.catalog && catData.catalog.packages) {
                for (const d of data.missing_deps) {
                   const depPkg = catData.catalog.packages.find(p => p.id === d);
                   if (depPkg) {
                      // Attempt single remote install using the store API manually
                      await fetch('/api/hpm/store/install', {
                         method: 'POST',
                         headers: { 'Content-Type': 'application/json' },
                         body: JSON.stringify({ id: depPkg.id, download_url: depPkg.download_url, allow_unsigned: true, skip_dep_check: true })
                      });
                   }
                }
             }
             // Retry local install forced
             formData.set('skip_dep_check', 'true');
             window.hpmInstallFile(file, forceAllowUnsigned, true);
           } catch(e) {
             if (window.showToast) window.showToast('Error resolving dependencies', 'error');
           }
        };

        document.getElementById('hpm-local-dep-only').onclick = () => {
           window.hpmInstallFile(file, forceAllowUnsigned, true);
        };
      } else {
        if (window.showToast) window.showToast(`Install failed: ${data.error}`, 'error');
      }
    }
  } catch (err) {
    window.hpmSetProgress(false);
    if (window.showToast) window.showToast(`Network error: ${err.message}`, 'error');
  }
};

window.hpmSetProgress = function(visible, label = '', pct = 0) {
  const container = document.getElementById('hpm-install-progress');
  const bar       = document.getElementById('hpm-progress-bar');
  const lbl       = document.getElementById('hpm-progress-label');
  if (!container) return;
  container.style.display = visible ? 'block' : 'none';
  if (bar) bar.style.width = `${pct}%`;
  if (lbl) lbl.innerHTML = label;
};
