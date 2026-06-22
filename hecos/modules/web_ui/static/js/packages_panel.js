/**
 * packages_panel.js
 * ─────────────────────────────────────────────────────────────────────────────
 * Hecos Package Manager — Unified Module Manager Frontend
 *
 * Displays ALL modules (core L1 + HPM-installed L2-L8) in a single
 * grouped, collapsible hierarchy.  Core modules are read-only (no Uninstall);
 * HPM modules support enable/disable and uninstall.
 * ─────────────────────────────────────────────────────────────────────────────
 */

// ── Level Metadata ────────────────────────────────────────────────────────────

const HPM_LEVELS = {
  1: { label: 'Level 1 — Core Modules',    badge: 'CORE',    color: '#66fcf1', types: ['core_module'] },
  2: { label: 'Level 2 — Plugins',         badge: 'PLUGIN',  color: '#3b82f6', types: ['plugin', 'module'] },
  3: { label: 'Level 3 — Extensions',      badge: 'EXT',     color: '#45a29e', types: ['extension'] },
  4: { label: 'Level 4 — Apps',            badge: 'APP',     color: '#8b5cf6', types: ['app'] },
  5: { label: 'Level 5 — Widgets',         badge: 'WIDGET',  color: '#f59e0b', types: ['widget'] },
  6: { label: 'Level 6 — Personas',        badge: 'PERSONA', color: '#ec4899', types: ['persona'] },
  7: { label: 'Level 7 — Themes',          badge: 'THEME',   color: '#10b981', types: ['theme'] },
  8: { label: 'Level 8 — Skill Packs',     badge: 'SKILLS',  color: '#f97316', types: ['skill_pack'] },
};

// ── Init ─────────────────────────────────────────────────────────────────────

window.hpmInit = function () {
  hpmSwitchTab('packages');
};

// ── Tabs ──────────────────────────────────────────────────────────────────────

window.hpmSwitchTab = async function(tabId) {
  // Update buttons
  const btnPackages = document.getElementById('hpm-tab-btn-packages');
  const btnBuiltin = document.getElementById('hpm-tab-btn-builtin');
  
  if (btnPackages && btnBuiltin) {
    if (tabId === 'packages') {
      btnPackages.classList.add('active');
      btnBuiltin.classList.remove('active');
    } else {
      btnPackages.classList.remove('active');
      btnBuiltin.classList.add('active');
    }
  }

  // Update panes
  document.getElementById('hpm-pane-packages').style.display = tabId === 'packages' ? 'block' : 'none';
  document.getElementById('hpm-pane-builtin').style.display = tabId === 'builtin' ? 'block' : 'none';

  if (tabId === 'packages') {
    hpmLoadPackages();
  } else if (tabId === 'builtin') {
    const builtinContainer = document.getElementById('hpm-builtin-container');
    const existingTab = document.getElementById('tab-plugins');
    
    if (existingTab && existingTab.parentElement !== builtinContainer) {
        builtinContainer.innerHTML = '';
        builtinContainer.appendChild(existingTab);
        existingTab.classList.remove('panel');
        existingTab.style.display = 'block';
        existingTab.classList.add('active');
        if (typeof populatePlugins === 'function') populatePlugins();
    } else if (!existingTab && builtinContainer && builtinContainer.innerHTML.includes('fa-spinner')) {
      try {
        if (typeof _loadPanel === 'function') {
            await _loadPanel('plugins');
            const loadedTab = document.getElementById('tab-plugins');
            if (loadedTab) {
                builtinContainer.innerHTML = '';
                builtinContainer.appendChild(loadedTab);
                loadedTab.classList.remove('panel');
                loadedTab.style.display = 'block';
                loadedTab.classList.add('active');
            }
        } else {
            throw new Error("_loadPanel function not found");
        }
      } catch (err) {
        builtinContainer.innerHTML = `<div style="color:var(--danger);padding:20px;">Failed to load built-in modules: ${err.message}</div>`;
      }
    }
  }
};

// ── Load & Render ─────────────────────────────────────────────────────────────

window.hpmLoadPackages = async function () {
  const grid = document.getElementById('hpm-packages-grid');
  if (!grid) return;

  grid.innerHTML = `
    <div style="text-align:center;padding:30px;color:var(--muted);font-size:0.9em;">
      <i class="fas fa-spinner fa-spin" style="margin-right:6px;"></i>
      ${window.HPM_I18N?.loading || 'Loading modules...'}
    </div>`;

  try {
    const resp = await fetch('/api/packages/all');
    const data = await resp.json();
    if (!data.ok) throw new Error(data.error || 'Unknown error');

    const packages = data.packages || [];
    if (packages.length === 0) {
      grid.innerHTML = `
        <div style="text-align:center;padding:40px;color:var(--muted);">
          <i class="fas fa-box-open" style="font-size:2em;margin-bottom:10px;display:block;opacity:0.4;"></i>
          <div style="font-size:0.9em;">${window.HPM_I18N?.no_modules || 'No modules found.'}</div>
        </div>`;
      return;
    }

    grid.innerHTML = hpmRenderHierarchy(packages);

  } catch (err) {
    grid.innerHTML = `
      <div style="color:var(--danger,#ef4444);padding:16px;text-align:center;font-size:0.85em;">
        <i class="fas fa-exclamation-triangle" style="margin-right:6px;"></i>
        ${window.HPM_I18N?.failed_load || 'Failed to load modules:'} ${err.message}
      </div>`;
  }
};

// ── Hierarchy Renderer ────────────────────────────────────────────────────────

function hpmRenderHierarchy(packages) {
  let html = '';

  for (const [lvl, meta] of Object.entries(HPM_LEVELS)) {
    const level = parseInt(lvl);
    const group = packages.filter(p => (p.level || 2) === level);
    if (group.length === 0) continue;

    const isOpen = level <= 4; // collapse higher levels by default
    html += `
      <details ${isOpen ? 'open' : ''} style="margin-bottom:12px;">
        <summary style="cursor:pointer;display:flex;align-items:center;gap:10px;
                        padding:10px 14px;border-radius:10px;
                        background:var(--bg2);border:1px solid var(--border-color);
                        user-select:none;list-style:none;">
          <span style="font-size:10px;font-weight:800;letter-spacing:1.2px;
                       text-transform:uppercase;color:${meta.color};">${meta.label}</span>
          <span style="background:${meta.color}22;color:${meta.color};
                       font-size:9px;font-weight:700;letter-spacing:.8px;
                       padding:2px 7px;border-radius:4px;border:1px solid ${meta.color}44;">
            ${meta.badge}
          </span>
          <span style="margin-left:auto;font-size:10px;color:var(--muted);
                       background:rgba(255,255,255,0.05);padding:2px 8px;border-radius:10px;">
            ${group.length}
          </span>
        </summary>
        <div style="display:grid;gap:6px;margin-top:8px;padding:0 2px;">
          ${group.map(pkg => hpmRenderRow(pkg, meta)).join('')}
        </div>
      </details>`;
  }

  return html || `<p style="color:var(--muted);text-align:center;padding:20px;">${window.HPM_I18N?.no_modules || 'No modules found.'}</p>`;
}

// ── Row Renderer ──────────────────────────────────────────────────────────────

function hpmRenderRow(pkg, meta) {
  const isDisabled  = pkg.status === 'disabled';
  const isBroken    = pkg.status === 'broken';
  const isRemovable = pkg.removable === true;
  const isCore      = pkg.level === 1;

  const statusDot = isBroken
    ? `<span style="width:7px;height:7px;border-radius:50%;background:#ef4444;flex-shrink:0;" title="Broken"></span>`
    : isDisabled
      ? `<span style="width:7px;height:7px;border-radius:50%;background:#6b7280;flex-shrink:0;" title="Disabled"></span>`
      : `<span style="width:7px;height:7px;border-radius:50%;background:#10b981;flex-shrink:0;" title="Active"></span>`;

  const tagBadge = pkg.tag
    ? `<code style="font-size:9px;background:rgba(255,255,255,0.05);color:var(--muted);
                    padding:1px 5px;border-radius:3px;letter-spacing:.5px;">${_hesc(pkg.tag)}</code>`
    : '';

  const versionBadge = (pkg.version && pkg.version !== 'built-in')
    ? `<span style="font-size:0.68em;color:var(--muted);background:var(--bg3,var(--bg2));
                    padding:1px 5px;border-radius:3px;border:1px solid var(--border-color);">
         v${_hesc(pkg.version)}
       </span>`
    : '';

  // Toggles Logic
  const disableLazy = pkg.tag ? ['REMINDER','CALENDAR','WEB_UI','MCP_BRIDGE','DASHBOARD'].includes(pkg.tag.toUpperCase()) : false;
  const disableEnabled = pkg.tag ? ['WEB_UI'].includes(pkg.tag.toUpperCase()) : false;
  const isLazy = pkg.lazy_load === true;
  const isBuiltin = (pkg.version === 'built-in');

  let lazyHtml = '';
  if (!disableLazy) {
    lazyHtml = `
      <label class="lazy-label" style="font-size:10px; margin-right:8px; display:inline-flex; align-items:center; gap:4px; cursor:pointer;">
        <input type="checkbox" onchange="hpmToggleLazy('${pkg.id}', ${isBuiltin}, this.checked)" ${isLazy ? 'checked' : ''}> Lazy
      </label>
    `;
  }

  let switchHtml = '';
  if (!isBroken) {
    switchHtml = `
      <label class="switch" ${disableEnabled ? 'style="visibility:hidden;pointer-events:none;"' : ''} title="${window.HPM_I18N?.enable || 'Enable'}/${window.HPM_I18N?.disable || 'Disable'}">
        <input type="checkbox" onchange="hpmToggleEnabled('${pkg.id}', ${isBuiltin}, this.checked)" ${!isDisabled ? 'checked' : ''} ${disableEnabled ? 'disabled' : ''}>
        <span class="slider"></span>
      </label>
    `;
  }

  // Actions
  let actions = '';
  if (isRemovable) {
    actions += `
      <button class="btn btn-sm btn-danger"
              style="font-size:10px;padding:4px 10px;margin-left:4px;"
              onclick="hpmConfirmUninstall('${pkg.id}','${_hesc(pkg.name)}')"
              title="${window.HPM_I18N?.uninstall || 'Uninstall'}">
        <i class="fas fa-trash-alt" style="font-size:10px;"></i>
      </button>`;
  } else {
    // Core / built-in: only show a lock icon to signal it's protected from uninstall
    actions = `<span title="${window.HPM_I18N?.tooltip_builtin || 'Built-in module — cannot be removed'}"
                     style="font-size:10px;color:var(--muted);opacity:0.5;padding:0 4px;margin-left:4px;">
                 <i class="fas fa-lock"></i>
               </span>`;
  }

  return `
    <div class="hpm-card" id="hpm-pkg-${pkg.id}"
         style="background:var(--bg2);border:1px solid var(--border-color);
                border-radius:9px;padding:10px 13px;
                display:flex;align-items:center;gap:12px;
                transition:opacity .2s;${isDisabled ? 'opacity:0.6;' : ''}">

      <!-- Icon -->
      <div style="width:34px;height:34px;border-radius:8px;flex-shrink:0;
                  background:${meta.color}18;display:flex;align-items:center;justify-content:center;">
        <i class="fas ${_hesc(pkg.fa_icon || 'fa-cube')}"
           style="color:${meta.color};font-size:14px;"></i>
      </div>

      <!-- Info -->
      <div style="flex:1;min-width:0;">
        <div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap;">
          ${statusDot}
          <span style="font-weight:600;color:var(--text);font-size:0.88em;">${_hesc(pkg.name)}</span>
          ${tagBadge}
          ${versionBadge}
        </div>
        ${pkg.description ? `
        <div style="font-size:0.75em;color:var(--muted);margin-top:2px;
                    white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:360px;">
          ${_hesc(pkg.description)}
        </div>` : ''}
        ${!isCore ? `
        <div style="font-size:0.68em;color:var(--muted);margin-top:2px;opacity:0.6;">
          ${pkg.author ? `by ${_hesc(pkg.author)}` : ''}
          ${pkg.installed_at ? ` · Installed ${pkg.installed_at.substring(0,10)}` : ''}
        </div>` : ''}
      </div>

      <!-- Actions -->
      <div style="display:flex;gap:5px;flex-shrink:0;align-items:center;">
        ${lazyHtml}
        ${switchHtml}
        ${actions}
      </div>
    </div>`;
}

// ── Toggles ───────────────────────────────────────────────────────────────────

window.hpmToggleEnabled = function(id, isBuiltin, isChecked) {
    const tag = id;
    if (window.cfg) {
        if (!window.cfg.plugins) window.cfg.plugins = {};
        if (!window.cfg.plugins[tag]) window.cfg.plugins[tag] = {};
        window.cfg.plugins[tag].enabled = isChecked;
    }

    if (!isBuiltin) {
        // HPM Packages need to also update the registry DB via API
        const status = isChecked ? 'installed' : 'disabled';
        hpmSetStatus(id, status, true); // true = skip rendering to avoid conflict
    } else {
        if (typeof window.saveConfig === 'function') window.saveConfig(true);
        // Refresh local UI instantly
        const pkg = _packages.find(p => p.id === id);
        if (pkg) {
            pkg.status = isChecked ? 'installed' : 'disabled';
            hpmRenderHierarchy();
        }
    }
};

window.hpmToggleLazy = function(id, isBuiltin, isChecked) {
    const tag = id;
    if (window.cfg) {
        if (!window.cfg.plugins) window.cfg.plugins = {};
        if (!window.cfg.plugins[tag]) window.cfg.plugins[tag] = {};
        window.cfg.plugins[tag].lazy_load = isChecked;
    }
    
    if (typeof window.saveConfig === 'function') window.saveConfig(true);
    
    const pkg = _packages.find(p => p.id === id);
    if (pkg) {
        pkg.lazy_load = isChecked;
    }
};

// ── Utility ───────────────────────────────────────────────────────────────────

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
  e.target.value = '';
};

// ── Install ───────────────────────────────────────────────────────────────────

async function hpmInstallFile(file) {
  if (!file.name.endsWith('.hpkg') && !file.name.endsWith('.zip')) {
    if (window.showToast) window.showToast('File must be a .hpkg package', 'error');
    return;
  }

  hpmSetProgress(true, `Installing ${file.name}...`, 30);

  const formData = new FormData();
  formData.append('hpkg_file', file);

  const allowUnsigned = document.getElementById('hpm-allow-unsigned')?.checked || false;
  formData.append('allow_unsigned', allowUnsigned ? 'true' : 'false');

  try {
    hpmSetProgress(true, 'Uploading...', 50);
    const resp = await fetch('/api/packages/install', { method: 'POST', body: formData });
    hpmSetProgress(true, 'Processing...', 80);
    const data = await resp.json();

    if (data.ok) {
      hpmSetProgress(true, 'Installed successfully!', 100);
      setTimeout(() => hpmSetProgress(false), 1500);
      if (data.warnings?.length) {
        if (window.showToast) window.showToast(`Warning: ${data.warnings[0]}`, 'warning');
      } else {
        if (window.showToast) window.showToast(`Package installed!`, 'success');
      }
      hpmLoadPackages();
      if (data.id) hpmInjectTab(data);
    } else {
      hpmSetProgress(false);
      if (window.showToast) window.showToast(`Install failed: ${data.error}`, 'error');
    }
  } catch (err) {
    hpmSetProgress(false);
    if (window.showToast) window.showToast(`Network error: ${err.message}`, 'error');
  }
}

// ── Enable / Disable ──────────────────────────────────────────────────────────

window.hpmSetStatus = async function (id, status, skipRender = false) {
  try {
    const res = await fetch(`/api/packages/${id}/status`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status })
    });
    const data = await res.json();
    if (!data.ok) {
      if (window.showToast) window.showToast('Error: ' + data.error, 'error');
      return;
    }
    if (window.showToast) window.showToast(`Package ${status}`);
    
    // Always trigger saveConfig to ensure system.yaml is synced if we toggled the switch
    if (typeof window.saveConfig === 'function') {
        window.saveConfig(true).then(() => {
            if (typeof window.renderConfigHub === 'function') window.renderConfigHub(window.viewMode);
        });
    }

    if (!skipRender) {
      const p = _packages.find(x => x.id === id);
      if (p) { p.status = status; hpmRenderHierarchy(); }
    }
  } catch (err) {
    if (window.showToast) window.showToast('Network error', 'error');
  }
};

// ── Uninstall ─────────────────────────────────────────────────────────────────

window.hpmConfirmUninstall = function (id, name) {
  const msgTemplate = window.HPM_I18N?.confirm_uninstall || 'Are you sure you want to uninstall the package \'%s\'?';
  const msg = msgTemplate.replace('%s', name);
  if (!confirm(msg)) return;
  hpmUninstall(id, name);
};

async function hpmUninstall(id, name) {
  const card = document.getElementById(`hpm-pkg-${id}`);
  if (card) { card.style.opacity = '0.4'; card.style.pointerEvents = 'none'; }

  try {
    const resp = await fetch(`/api/packages/${id}`, { method: 'DELETE' });
    const data = await resp.json();

    if (data.ok) {
      if (window.showToast) window.showToast(`"${name}" uninstalled`, 'success');
      hpmRemoveTab(id);
      hpmLoadPackages();
    } else {
      if (window.showToast) window.showToast(`Uninstall failed: ${data.error}`, 'error');
      if (card) { card.style.opacity = '1'; card.style.pointerEvents = ''; }
    }
  } catch (err) {
    if (window.showToast) window.showToast(`${err.message}`, 'error');
    if (card) { card.style.opacity = '1'; card.style.pointerEvents = ''; }
  }
}

// ── Config Tab Injection (hot-reload without page refresh) ───────────────────

function hpmInjectTab(installResult) {
  if (!installResult.config_panel) return;
  const { tab_id, tab_label, tab_icon } = installResult.config_panel;
  if (!tab_id) return;
  if (document.querySelector(`[data-panel="${tab_id}"]`)) return;
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

window.hpmWelcomeDrop = function (e) {
  e.preventDefault();
  const dz = document.getElementById('welcome-hpm-dropzone');
  if (dz) dz.style.borderColor = 'var(--border-color)';
  const file = e.dataTransfer?.files?.[0];
  if (file) {
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

// ── Auto-init ─────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', window.hpmInit);
if (document.readyState !== 'loading') {
  window.hpmInit();
}
