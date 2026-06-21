/**
 * packages_panel.js
 * ─────────────────────────────────────────────────────────────────────────────
 * Hecos Package Manager — Frontend Logic
 *
 * Handles:
 *   - Listing installed packages as cards
 *   - Drag-and-drop / file-picker upload for .hpkg files
 *   - Install, disable/enable, uninstall operations
 *   - Live updates via hpm:* events (SSE / state manager)
 * ─────────────────────────────────────────────────────────────────────────────
 */

// ── Init ─────────────────────────────────────────────────────────────────────

window.hpmInit = function () {
  hpmLoadPackages();
};

// hpmInit auto-execution moved to bottom

// ── Load & Render Installed Packages ─────────────────────────────────────────

window.hpmLoadPackages = async function () {
  const grid = document.getElementById('hpm-packages-grid');
  if (!grid) return;

  grid.innerHTML = `
    <div style="text-align:center;padding:30px;color:var(--muted);font-size:0.9em;">
      <i class="fas fa-spinner fa-spin" style="margin-right:6px;"></i>
      Loading installed packages...
    </div>`;

  try {
    const resp = await fetch('/api/packages');
    const data = await resp.json();

    if (!data.ok) throw new Error(data.error || 'Unknown error');

    const packages = data.packages || [];

    if (packages.length === 0) {
      grid.innerHTML = `
        <div style="text-align:center;padding:40px;color:var(--muted);">
          <i class="fas fa-box-open" style="font-size:2em;margin-bottom:10px;display:block;opacity:0.4;"></i>
          <div style="font-size:0.9em;">No packages installed yet.</div>
          <div style="font-size:0.8em;margin-top:4px;">Drop a .hpkg file above to get started.</div>
        </div>`;
      return;
    }

    grid.innerHTML = packages.map(hpmRenderCard).join('');

  } catch (err) {
    grid.innerHTML = `
      <div style="color:var(--danger,#ef4444);padding:16px;text-align:center;font-size:0.85em;">
        <i class="fas fa-exclamation-triangle" style="margin-right:6px;"></i>
        Failed to load packages: ${err.message}
      </div>`;
  }
};

// ── Card Renderer ─────────────────────────────────────────────────────────────

function hpmRenderCard(pkg) {
  const isDisabled = pkg.status === 'disabled';
  const isBroken   = pkg.status === 'broken';

  const typeColors = {
    plugin:     '#3b82f6',
    module:     '#8b5cf6',
    theme:      '#10b981',
    skill_pack: '#f59e0b',
  };
  const typeColor = typeColors[pkg.type] || '#6b7280';

  const statusBadge = isDisabled
    ? `<span style="background:#6b7280;color:#fff;font-size:0.68em;padding:2px 7px;border-radius:4px;">DISABLED</span>`
    : isBroken
      ? `<span style="background:#ef4444;color:#fff;font-size:0.68em;padding:2px 7px;border-radius:4px;">BROKEN</span>`
      : `<span style="background:#10b981;color:#fff;font-size:0.68em;padding:2px 7px;border-radius:4px;">ACTIVE</span>`;

  return `
    <div class="hpm-card" id="hpm-pkg-${pkg.id}"
         style="background:var(--bg2);border:1px solid var(--border-color);
                border-radius:12px;padding:14px 16px;
                display:flex;align-items:center;gap:14px;
                transition:opacity .2s;${isDisabled ? 'opacity:0.65;' : ''}">

      <!-- Icon -->
      <div style="width:38px;height:38px;border-radius:9px;flex-shrink:0;
                  background:${typeColor}22;display:flex;align-items:center;
                  justify-content:center;">
        <i class="fas fa-${hpmTypeIcon(pkg.type)}"
           style="color:${typeColor};font-size:15px;"></i>
      </div>

      <!-- Info -->
      <div style="flex:1;min-width:0;">
        <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
          <span style="font-weight:600;color:var(--text);font-size:0.95em;">${_hesc(pkg.name)}</span>
          ${statusBadge}
          <span style="font-size:0.72em;color:var(--muted);background:var(--bg3,var(--bg2));
                       padding:1px 6px;border-radius:4px;border:1px solid var(--border-color);">
            v${_hesc(pkg.version)}
          </span>
        </div>
        <div style="font-size:0.78em;color:var(--muted);margin-top:2px;
                    white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">
          ${_hesc(pkg.description || '')}
          ${pkg.author ? `<span style="margin-left:6px;opacity:0.6;">by ${_hesc(pkg.author)}</span>` : ''}
        </div>
        <div style="font-size:0.72em;color:var(--muted);margin-top:3px;opacity:0.7;">
          Installed: ${pkg.installed_at ? pkg.installed_at.substring(0,10) : '—'}
        </div>
      </div>

      <!-- Actions -->
      <div style="display:flex;gap:6px;flex-shrink:0;">
        ${isDisabled
          ? `<button class="btn-sm btn-outline" onclick="hpmSetStatus('${pkg.id}','installed')" title="Enable">
               <i class="fas fa-play" style="font-size:11px;"></i>
             </button>`
          : `<button class="btn-sm btn-outline" onclick="hpmSetStatus('${pkg.id}','disabled')" title="Disable">
               <i class="fas fa-pause" style="font-size:11px;"></i>
             </button>`
        }
        <button class="btn-sm btn-outline" style="color:var(--danger,#ef4444);border-color:var(--danger,#ef4444);"
                onclick="hpmConfirmUninstall('${pkg.id}','${_hesc(pkg.name)}')"
                title="Uninstall">
          <i class="fas fa-trash-alt" style="font-size:11px;"></i>
        </button>
      </div>
    </div>`;
}

function hpmTypeIcon(type) {
  const icons = { plugin: 'plug', module: 'cubes', theme: 'palette', skill_pack: 'bolt' };
  return icons[type] || 'cube';
}

function _hesc(s) {
  return String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

// ── Drag & Drop ───────────────────────────────────────────────────────────────

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
  hpmDragLeave(e);
  const file = e.dataTransfer?.files?.[0];
  if (file) hpmInstallFile(file);
};

window.hpmFileSelected = function (e) {
  const file = e.target?.files?.[0];
  if (file) hpmInstallFile(file);
  // Reset input so the same file can be selected again
  e.target.value = '';
};

// ── Install ───────────────────────────────────────────────────────────────────

async function hpmInstallFile(file) {
  if (!file.name.endsWith('.hpkg') && !file.name.endsWith('.zip')) {
    if (window.showToast) window.showToast('❌ File must be a .hpkg package', 'error');
    return;
  }

  hpmSetProgress(true, `Installing ${file.name}...`, 30);

  const formData = new FormData();
  formData.append('hpkg_file', file);

  try {
    hpmSetProgress(true, 'Uploading...', 50);
    const resp = await fetch('/api/packages/install', { method: 'POST', body: formData });
    hpmSetProgress(true, 'Processing...', 80);
    const data = await resp.json();

    if (data.ok) {
      hpmSetProgress(true, '✅ Installed successfully!', 100);
      setTimeout(() => hpmSetProgress(false), 1500);

      if (data.warnings?.length) {
        if (window.showToast) window.showToast(`⚠️ ${data.warnings[0]}`, 'warning');
      } else {
        if (window.showToast) window.showToast(`✅ Package installed!`, 'success');
      }

      // Reload the list and inject config tab if needed
      hpmLoadPackages();
      if (data.id) hpmInjectTab(data);

    } else {
      hpmSetProgress(false);
      if (window.showToast) window.showToast(`❌ Install failed: ${data.error}`, 'error');
    }
  } catch (err) {
    hpmSetProgress(false);
    if (window.showToast) window.showToast(`❌ Network error: ${err.message}`, 'error');
  }
}

// ── Enable / Disable ──────────────────────────────────────────────────────────

window.hpmSetStatus = async function (id, status) {
  const card = document.getElementById(`hpm-pkg-${id}`);
  if (card) { card.style.opacity = '0.4'; card.style.pointerEvents = 'none'; }

  try {
    const resp = await fetch(`/api/packages/${id}/status`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status }),
    });
    const data = await resp.json();
    if (data.ok) {
      if (window.showToast) window.showToast(`Package ${status === 'installed' ? 'enabled' : 'disabled'}`, 'info');
      hpmLoadPackages();
    } else {
      if (window.showToast) window.showToast(`❌ ${data.error}`, 'error');
      if (card) { card.style.opacity = '1'; card.style.pointerEvents = ''; }
    }
  } catch (err) {
    if (window.showToast) window.showToast(`❌ ${err.message}`, 'error');
    if (card) { card.style.opacity = '1'; card.style.pointerEvents = ''; }
  }
};

// ── Uninstall ─────────────────────────────────────────────────────────────────

window.hpmConfirmUninstall = function (id, name) {
  if (!confirm(`Uninstall "${name}"?\nAll files, templates and configuration for this package will be permanently removed.`)) return;
  hpmUninstall(id, name);
};

async function hpmUninstall(id, name) {
  const card = document.getElementById(`hpm-pkg-${id}`);
  if (card) { card.style.opacity = '0.4'; card.style.pointerEvents = 'none'; }

  try {
    const resp = await fetch(`/api/packages/${id}`, { method: 'DELETE' });
    const data = await resp.json();

    if (data.ok) {
      if (window.showToast) window.showToast(`✅ "${name}" uninstalled`, 'success');
      // Remove the tab from DOM if it was injected
      hpmRemoveTab(id);
      hpmLoadPackages();
    } else {
      if (window.showToast) window.showToast(`❌ Uninstall failed: ${data.error}`, 'error');
      if (card) { card.style.opacity = '1'; card.style.pointerEvents = ''; }
    }
  } catch (err) {
    if (window.showToast) window.showToast(`❌ ${err.message}`, 'error');
    if (card) { card.style.opacity = '1'; card.style.pointerEvents = ''; }
  }
}

// ── Config Tab Injection (hot-reload without page refresh) ───────────────────

function hpmInjectTab(installResult) {
  // installResult.config_panel = { tab_id, tab_label, tab_icon }
  if (!installResult.config_panel) return;
  const { tab_id, tab_label, tab_icon } = installResult.config_panel;
  if (!tab_id) return;

  // Avoid duplicates
  if (document.querySelector(`[data-panel="${tab_id}"]`)) return;

  // Find the sidebar nav and inject a new item (matches existing CONFIG_HUB pattern)
  const nav = document.querySelector('#config-sidebar-nav, .config-nav, .sidebar-nav');
  if (!nav) return;

  const li = document.createElement('li');
  li.setAttribute('data-panel', tab_id);
  li.className = 'nav-item hpm-injected';
  li.innerHTML = `
    <button class="nav-btn" onclick="showTab('${tab_id}')">
      <i class="fas ${tab_icon || 'fa-cube'}" style="margin-right:6px;"></i>
      ${_hesc(tab_label || tab_id)}
    </button>`;
  nav.appendChild(li);
}

function hpmRemoveTab(pkg_id) {
  // Remove any nav items injected for this package
  document.querySelectorAll(`.hpm-injected[data-panel="${pkg_id}"]`).forEach(el => el.remove());
}

// ── Progress Bar ──────────────────────────────────────────────────────────────

function hpmSetProgress(visible, label = '', pct = 0) {
  const container = document.getElementById('hpm-install-progress');
  const bar       = document.getElementById('hpm-progress-bar');
  const lbl       = document.getElementById('hpm-progress-label');
  if (!container) return;
  container.style.display = visible ? 'block' : 'none';
  if (bar) bar.style.width = `${pct}%`;
  if (lbl) lbl.textContent = label;
}

// ── Welcome Screen Drop Zone Helpers ─────────────────────────────────────────
// These are global so they can be called from inline handlers in config_welcome.html

window.hpmWelcomeDrop = function (e) {
  e.preventDefault();
  const dz = document.getElementById('welcome-hpm-dropzone');
  if (dz) dz.style.borderColor = 'var(--border-color)';
  const file = e.dataTransfer?.files?.[0];
  if (file) {
    // Navigate to packages tab first, then install
    if (typeof showTab === 'function') showTab('packages');
    setTimeout(() => hpmInstallFile(file), 400);
  }
};

window.hpmWelcomeFileSelected = function (e) {
  const file = e.target?.files?.[0];
  if (file) {
    if (typeof showTab === 'function') showTab('packages');
    setTimeout(() => hpmInstallFile(file), 400);
  }
  e.target.value = '';
};

// ── Auto-init ───────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', window.hpmInit);
if (document.readyState !== 'loading') {
  window.hpmInit();
}
