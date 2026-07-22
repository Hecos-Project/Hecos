/**
 * packages_panel_render_row.js
 * ─────────────────────────────────────────────────────────────────────────────
 * List View Row Renderer for Hecos Package Manager
 */

window.hpmRenderRow = function (pkg, meta) {
  const _ti = window.hpm_ti;
  const isDisabled = pkg.status === 'disabled';
  const isBroken = pkg.status === 'broken';
  const isRemovable = pkg.removable === true;
  const isCore = pkg.level === 1;

  const statusDot = isBroken
    ? `<span style="width:7px;height:7px;border-radius:50%;background:#ef4444;flex-shrink:0;" title="${_ti('Broken','Rotto','Roto')}"></span>`
    : isDisabled
      ? `<span style="width:7px;height:7px;border-radius:50%;background:#6b7280;flex-shrink:0;" title="${_ti('Disabled','Disabilitato','Desactivado')}"></span>`
      : `<span style="width:7px;height:7px;border-radius:50%;background:#10b981;flex-shrink:0;" title="${_ti('Active','Attivo','Activo')}"></span>`;

  const versionBadge = (pkg.version && pkg.version !== 'built-in')
    ? `<span style="font-size:0.68em;color:var(--muted);background:var(--bg3,var(--bg2));
                    padding:1px 5px;border-radius:3px;border:1px solid var(--border-color);">
         v${window._hesc(pkg.version)}
       </span>`
    : '';

  const disableLazy = pkg.tag ? ['REMINDER', 'CALENDAR', 'WEB_UI', 'MCP_BRIDGE', 'DASHBOARD'].includes(pkg.tag.toUpperCase()) : false;
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

  let actions = '';
  if (!window._hpmSelectionMode) {
    actions += `
        <button type="button"
                class="btn btn-sm"
                style="font-size:10px;padding:4px 10px;margin-left:4px;background:var(--bg3);border:1px solid var(--border-color);color:var(--text);"
                onclick="hpmShowCapabilities('${pkg.id}','${window._hesc(pkg.name)}')"
                title="${_ti('View Capabilities', 'Vedi Funzionalità', 'Ver Capacidades')}">
          <i class="fas fa-info-circle" style="font-size:11px;color:#3b82f6;"></i>
        </button>`;

    if (!isCore) {
      actions += `
          <button type="button"
                  class="btn btn-sm"
                  style="font-size:10px;padding:4px 10px;margin-left:4px;background:var(--bg3);border:1px solid var(--border-color);color:var(--text);"
                  onclick="hpmShowDocs('${pkg.id}','${window._hesc(pkg.name)}')"
                  title="${window.HPM_I18N?.read_docs || _ti('Read Docs','Leggi Docs','Leer Documentación')}">
            <i class="fas fa-book" style="font-size:11px;color:#10b981;"></i>
          </button>`;
    }

    actions += `
        <button type="button"
                class="btn btn-sm"
                style="font-size:10px;padding:4px 10px;margin-left:4px; border:1px solid var(--border-color); color:var(--text-color); background:transparent;"
                onclick="window.hpmVerifyPackage('${pkg.id}', '${window._hesc(pkg.name)}')"
                title="${window.HPM_I18N?.verify || _ti('Verify Integrity','Verifica Integrità','Verificar Integridad')}">
          <i class="fas fa-check-double" style="font-size:10px; opacity:0.8;"></i>
        </button>`;

    if (pkg.tag && !isDisabled && !isBroken) {
      if (pkg.requires_restart) {
        actions += `
            <button type="button"
                    class="btn btn-sm hpm-restart-required-btn"
                    style="font-size:10px;padding:4px 10px;margin-left:4px;
                           background:linear-gradient(135deg,#f59e0b,#d97706);
                           border:none;color:#fff;font-weight:700;
                           border-radius:6px;cursor:pointer;
                           animation:hpmPulse 2s ease-in-out infinite;"
                    onclick="window.hpmRestartRequired('${window._hesc(pkg.name)}')"
                    title="${_ti('Restart required to activate this package', 'Riavvio richiesto per attivare il pacchetto', 'Reinicio requerido para activar el paquete')}">
              <i class="fas fa-power-off" style="font-size:10px;margin-right:4px;"></i>${_ti('Restart', 'Riavvia', 'Reiniciar')}
            </button>`;
      } else {
        actions += `
            <button type="button"
                    class="btn btn-sm"
                    style="font-size:10px;padding:4px 10px;margin-left:4px; border:1px solid var(--border-color); color:var(--text-color); background:transparent;"
                    onclick="window.hpmHotReloadModule('${pkg.id}', '${window._hesc(pkg.name)}')"
                    title="${window.HPM_I18N?.hot_reload || _ti('Hot Reload','Hot Reload','Recarga en Caliente')}">
              <i class="fas fa-sync-alt" style="font-size:10px; opacity:0.8;"></i>
            </button>`;
      }
    }

    if (isRemovable) {
      actions += `
          <button type="button"
                  class="btn btn-sm btn-danger"
                  style="font-size:10px;padding:4px 10px;margin-left:4px;"
                  onclick="hpmConfirmUninstall('${pkg.id}','${window._hesc(pkg.name)}')"
                  title="${window.HPM_I18N?.uninstall || _ti('Uninstall','Disinstalla','Desinstalar')}">
            <i class="fas fa-trash-alt" style="font-size:10px;"></i>
          </button>`;
    } else {
      actions += `<span title="${window.HPM_I18N?.tooltip_builtin || _ti('Built-in module — cannot be removed','Modulo integrato — non rimovibile','Módulo integrado — no se puede eliminar')}"
                         style="font-size:10px;color:var(--muted);opacity:0.5;padding:0 4px;margin-left:4px;">
                     <i class="fas fa-lock"></i>
                   </span>`;
    }
  }

  const typeMeta = window.HPM_TYPE_META[pkg.type] || { label: pkg.type, color: '#6b7280' };

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
          <span style="font-size:9px;background:${typeMeta.color}15;color:${typeMeta.color};
                       padding:1px 5px;border-radius:3px;letter-spacing:.5px;border:1px solid ${typeMeta.color}33;">${typeMeta.label}</span>
          ${versionBadge}
        </div>
        ${pkg.description ? `
        <div style="font-size:0.75em;color:var(--muted);margin-top:4px;
                    display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;line-height:1.4;max-width:450px;">
          ${window._hesc(pkg.description)}
        </div>` : ''}
        ${(pkg.manifest_snapshot && pkg.manifest_snapshot.config_panel) ? `
        <div style="font-size:0.75em;margin-top:6px;">
            <a href="#${window._hesc(pkg.manifest_snapshot.config_panel.tab_id || pkg.id.replace('_', '-'))}" style="color:var(--accent);text-decoration:none;display:inline-flex;align-items:center;gap:5px;background:rgba(255,255,255,0.05);padding:3px 8px;border-radius:6px;border:1px solid rgba(255,255,255,0.1);">
                <i class="fas fa-cogs"></i>
                <span>${_ti('Configuration', 'Configurazione', 'Configuración')}: ${window._hesc(window.hpmGetHubCategoryLabel(pkg.manifest_snapshot.config_panel.category))} &rarr; ${window._hesc(pkg.manifest_snapshot.config_panel.tab_label || pkg.name)}</span>
            </a>
        </div>
        ` : ''}
        ${!isCore ? `
        <div style="font-size:0.68em;color:var(--muted);margin-top:2px;opacity:0.6;">
          ${pkg.author ? `by ${window._hesc(pkg.author)}` : ''}
          ${pkg.updated_at ? ` · ${_ti('Updated', 'Aggiornato', 'Actualizado')} ${pkg.updated_at.substring(0, 10)} ${pkg.updated_at.substring(11, 16)}` : (pkg.installed_at ? ` · ${_ti('Installed', 'Installato', 'Instalado')} ${pkg.installed_at.substring(0, 10)} ${pkg.installed_at.substring(11, 16)}` : '')}
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
