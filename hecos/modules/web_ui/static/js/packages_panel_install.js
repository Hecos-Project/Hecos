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
    window.hpmSetProgress(true, 'Uploading...', 50);
    const resp = await fetch('/api/packages/install', { method: 'POST', body: formData });
    window.hpmSetProgress(true, 'Processing...', 80);
    const data = await resp.json();

    if (data.ok) {
      window.hpmSetProgress(true, 'Installed successfully!', 100);
      setTimeout(() => window.hpmSetProgress(false), 1500);
      if (data.warnings?.length) {
        if (window.showToast) window.showToast(`Warning: ${data.warnings[0]}`, 'warning');
      } else {
        if (window.showToast) window.showToast(`Package installed!`, 'success');
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
  if (lbl) lbl.textContent = label;
};
