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

window.hpmInstallFile = async function(file, forceAllowUnsigned = false) {
  if (!file.name.endsWith('.hpkg') && !file.name.endsWith('.zip')) {
    if (window.showToast) window.showToast('File must be a .hpkg package', 'error');
    return;
  }

  window.hpmSetProgress(true, `Installing ${file.name}...`, 30);

  const formData = new FormData();
  formData.append('hpkg_file', file);

  const allowUnsigned = forceAllowUnsigned || (document.getElementById('hpm-allow-unsigned')?.checked || false);
  formData.append('allow_unsigned', allowUnsigned ? 'true' : 'false');

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
                // Check the box visually so the user sees it's now allowed
                const checkbox = document.getElementById('hpm-allow-unsigned');
                if (checkbox) checkbox.checked = true;
                // Retry install forcing unsigned
                window.hpmInstallFile(file, true);
            });
        }
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
