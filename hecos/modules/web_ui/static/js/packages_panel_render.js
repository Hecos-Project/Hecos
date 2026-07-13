/**
 * packages_panel_render.js
 * ─────────────────────────────────────────────────────────────────────────────
 * Hierarchy and Row Renderer for Hecos Package Manager
 */

window.HPM_LEVELS = {
  1: { label: 'Level 1 — Core Modules',    badge: 'CORE',    color: '#66fcf1', types: ['core_module'] },
  2: { label: 'Level 2 — Plugins',         badge: 'PLUGIN',  color: '#3b82f6', types: ['plugin', 'module'] },
  3: { label: 'Level 3 — Extensions',      badge: 'EXT',     color: '#45a29e', types: ['extension'] },
  4: { label: 'Level 4 — Apps',            badge: 'APP',     color: '#8b5cf6', types: ['app'] },
  5: { label: 'Level 5 — Widgets',         badge: 'WIDGET',  color: '#f59e0b', types: ['widget'] },
  6: { label: 'Level 6 — Personas',        badge: 'PERSONA', color: '#ec4899', types: ['persona'] },
  7: { label: 'Level 7 — Themes',          badge: 'THEME',   color: '#10b981', types: ['theme'] },
  8: { label: 'Level 8 — Skill Packs',     badge: 'SKILLS',  color: '#f97316', types: ['skill_pack'] },
};

window.HPM_UI_STATE = window.HPM_UI_STATE || { collapsedCategories: [] };

window._hesc = function(s) {
  return String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
};

window.hpmToggleCategory = function(catLvl) {
  const isCollapsed = window.HPM_UI_STATE.collapsedCategories.includes(catLvl);
  if (isCollapsed) {
    window.HPM_UI_STATE.collapsedCategories = window.HPM_UI_STATE.collapsedCategories.filter(c => c !== catLvl);
  } else {
    window.HPM_UI_STATE.collapsedCategories.push(catLvl);
  }
  window.hpmRenderHierarchy();
};

window.hpmRenderHierarchy = function(packages) {
  if (!packages) packages = window._packages; // fallback if called from toggle
  if (!packages) return '';
  let html = '';

  const totalCountEl = document.getElementById('hpm-total-count');
  if (totalCountEl) totalCountEl.textContent = packages.length;

  for (const [lvl, meta] of Object.entries(window.HPM_LEVELS)) {
    const level = parseInt(lvl);
    const group = packages.filter(p => (p.level || 2) === level);
    if (group.length === 0) continue;

    let isCollapsed = window.HPM_UI_STATE.collapsedCategories.includes(level);

    html += `
      <div class="category-group ${isCollapsed ? 'collapsed' : ''}" style="margin-bottom:12px;">
        <div class="category-header" onclick="hpmToggleCategory(${level})" 
             style="cursor:pointer;display:flex;align-items:center;gap:10px;
                    padding:10px 14px;border-radius:10px;
                    background:var(--bg2);border:1px solid var(--border-color);
                    user-select:none;">
          <span class="cat-toggle" style="font-size:14px;color:var(--muted);width:16px;text-align:center;">${isCollapsed ? '⊕' : '⊖'}</span>
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
        </div>
        <div class="category-content" style="${isCollapsed ? 'display:none;' : 'display:grid;gap:6px;margin-top:8px;padding:0 2px;'}">
          ${group.map(pkg => window.hpmRenderRow(pkg, meta)).join('')}
        </div>
      </div>`;
  }

  const grid = document.getElementById('hpm-packages-grid');
  if (grid) {
    grid.innerHTML = html || `<p style="color:var(--muted);text-align:center;padding:20px;">${window.HPM_I18N?.no_modules || 'No modules found.'}</p>`;
  }
  return html;
};

window.hpmRenderRow = function(pkg, meta) {
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
                    padding:1px 5px;border-radius:3px;letter-spacing:.5px;">${window._hesc(pkg.tag)}</code>`
    : '';

  const versionBadge = (pkg.version && pkg.version !== 'built-in')
    ? `<span style="font-size:0.68em;color:var(--muted);background:var(--bg3,var(--bg2));
                    padding:1px 5px;border-radius:3px;border:1px solid var(--border-color);">
         v${window._hesc(pkg.version)}
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
      <label class="lazy-label no-autosave" style="font-size:10px; margin-right:8px; display:inline-flex; align-items:center; gap:4px; cursor:pointer;">
        <input type="checkbox" onchange="hpmToggleLazy('${pkg.id}', ${isBuiltin}, this.checked)" ${isLazy ? 'checked' : ''}> Lazy
      </label>
    `;
  }

  let switchHtml = '';
  if (!isBroken) {
    switchHtml = `
      <label class="switch no-autosave" ${disableEnabled ? 'style="visibility:hidden;pointer-events:none;"' : ''} title="${window.HPM_I18N?.enable || 'Enable'}/${window.HPM_I18N?.disable || 'Disable'}">
        <input type="checkbox" onchange="hpmToggleEnabled('${pkg.id}', ${isBuiltin}, this.checked)" ${!isDisabled ? 'checked' : ''} ${disableEnabled ? 'disabled' : ''}>
        <span class="slider"></span>
      </label>
    `;
  }

  // Actions
  let actions = '';
  if (!window._hpmSelectionMode) {
      actions += `
        <button type="button"
                class="btn btn-sm"
                style="font-size:10px;padding:4px 10px;margin-left:4px;background:var(--bg3);border:1px solid var(--border-color);color:var(--text);"
                onclick="hpmShowCapabilities('${pkg.id}','${window._hesc(pkg.name)}')"
                title="View Capabilities">
          <i class="fas fa-info-circle" style="font-size:11px;color:#3b82f6;"></i>
        </button>`;

      if (!isCore) {
        actions += `
          <button type="button"
                  class="btn btn-sm"
                  style="font-size:10px;padding:4px 10px;margin-left:4px;background:var(--bg3);border:1px solid var(--border-color);color:var(--text);"
                  onclick="hpmShowDocs('${pkg.id}','${window._hesc(pkg.name)}')"
                  title="${window.HPM_I18N?.read_docs || 'Read Docs'}">
            <i class="fas fa-book" style="font-size:11px;color:#10b981;"></i>
          </button>`;
      }

      actions += `
        <button type="button"
                class="btn btn-sm"
                style="font-size:10px;padding:4px 10px;margin-left:4px; border:1px solid var(--border-color); color:var(--text-color); background:transparent;"
                onclick="window.hpmVerifyPackage('${pkg.id}', '${window._hesc(pkg.name)}')"
                title="${window.HPM_I18N?.verify || 'Verify Integrity'}">
          <i class="fas fa-check-double" style="font-size:10px; opacity:0.8;"></i>
        </button>`;

      if (isRemovable) {
        actions += `
          <button type="button"
                  class="btn btn-sm btn-danger"
                  style="font-size:10px;padding:4px 10px;margin-left:4px;"
                  onclick="hpmConfirmUninstall('${pkg.id}','${window._hesc(pkg.name)}')"
                  title="${window.HPM_I18N?.uninstall || 'Uninstall'}">
            <i class="fas fa-trash-alt" style="font-size:10px;"></i>
          </button>`;
      } else {
        actions += `<span title="${window.HPM_I18N?.tooltip_builtin || 'Built-in module — cannot be removed'}"
                         style="font-size:10px;color:var(--muted);opacity:0.5;padding:0 4px;margin-left:4px;">
                     <i class="fas fa-lock"></i>
                   </span>`;
      }
  }

  let selectionHtml = '';
  if (window._hpmSelectionMode) {
      if (isRemovable) {
          const isSelected = window._hpmSelectedPackages && window._hpmSelectedPackages.has(pkg.id);
          selectionHtml = `
            <div style="margin-right:2px; display:flex; align-items:center;">
              <input type="checkbox" style="width:16px; height:16px; accent-color:var(--accent); cursor:pointer;" 
                     ${isSelected ? 'checked' : ''} 
                     onchange="hpmTogglePackageSelection('${pkg.id}')">
            </div>
          `;
      } else {
          selectionHtml = `
            <div style="margin-right:2px; width:16px; display:flex; align-items:center; justify-content:center; opacity:0.3;" title="Built-in module">
              <i class="fas fa-lock" style="font-size:10px;"></i>
            </div>
          `;
      }
  }

  return `
    <div class="hpm-card" id="hpm-pkg-${pkg.id}"
         style="background:var(--bg2);border:1px solid var(--border-color);
                border-radius:9px;padding:10px 13px;
                display:flex;align-items:center;gap:12px;
                transition:opacity .2s;${isDisabled ? 'opacity:0.6;' : ''}">

      ${selectionHtml}

      <!-- Icon -->
      <div style="width:34px;height:34px;border-radius:8px;flex-shrink:0;
                  background:${meta.color}18;display:flex;align-items:center;justify-content:center;">
        <i class="fas ${window._hesc(pkg.fa_icon || 'fa-cube')}"
           style="color:${meta.color};font-size:14px;"></i>
      </div>

      <!-- Info -->
      <div style="flex:1;min-width:0;">
        <div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap;">
          ${statusDot}
          <span style="font-weight:600;color:var(--text);font-size:0.88em;">${window._hesc(pkg.name)}</span>
          ${tagBadge}
          ${versionBadge}
        </div>
        ${pkg.description ? `
        <div style="font-size:0.75em;color:var(--muted);margin-top:4px;
                    display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;line-height:1.4;max-width:450px;">
          ${window._hesc(pkg.description)}
        </div>` : ''}
        ${!isCore ? `
        <div style="font-size:0.68em;color:var(--muted);margin-top:2px;opacity:0.6;">
          ${pkg.author ? `by ${window._hesc(pkg.author)}` : ''}
          ${pkg.installed_at ? ` · Installed ${pkg.installed_at.substring(0,10)}` : ''}
        </div>` : ''}
      </div>

      <!-- Actions — class 'hpm-card-actions' is used by the update badge injector -->
      <div class="hpm-card-actions" style="display:flex;gap:5px;flex-shrink:0;align-items:center;">
        ${lazyHtml}
        ${switchHtml}
        ${actions}
      </div>
    </div>`;
};

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
        if (typeof window.hpmSetStatus === 'function') {
            window.hpmSetStatus(id, status, false);
        }
    } else {
        if (typeof window.saveConfig === 'function') window.saveConfig(true);
        // Refresh local UI instantly
        if (window._packages) {
            const pkg = window._packages.find(p => p.id === id);
            if (pkg) {
                pkg.status = isChecked ? 'installed' : 'disabled';
                window.hpmRenderHierarchy();
            }
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
    
    if (window._packages) {
        const pkg = window._packages.find(p => p.id === id);
        if (pkg) {
            pkg.lazy_load = isChecked;
        }
    }
};
