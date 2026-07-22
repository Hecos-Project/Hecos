/**
 * packages_panel_render_card.js
 * ─────────────────────────────────────────────────────────────────────────────
 * Wall Card Renderer for Hecos Package Manager
 */

window.hpmRenderWallCard = function (pkg, meta) {
  const _ti = window.hpm_ti;
  const isDisabled = pkg.status === 'disabled';
  const isBroken  = pkg.status === 'broken';
  const isRemovable = pkg.removable === true;
  const isCore  = pkg.level === 1;
  const isBuiltin = (pkg.version === 'built-in');

  const fallbackScreenshot = 'https://raw.githubusercontent.com/Hecos-Project/Hecos-Packages/main/Hecos_module_Image_preview.png';
  const screenshots = (pkg.screenshots && pkg.screenshots.length > 0) ? pkg.screenshots : [fallbackScreenshot];
  const hasMultiple = screenshots.length > 1;

  // Always use the type category icon (fa icon) — never custom icon_url for the small header icon
  const typeMeta = window.HPM_TYPE_META[pkg.type] || { label: pkg.type || 'Other', color: '#6b7280', icon: 'fa-cube' };
  const faIcon = pkg.fa_icon || typeMeta.icon || 'fa-cube';

  const statusDot = isBroken
    ? `<span style="width:8px;height:8px;border-radius:50%;background:#ef4444;position:absolute;top:10px;right:10px;box-shadow:0 0 6px #ef4444;z-index:2;" title="${_ti('Broken','Rotto','Roto')}"></span>`
    : isDisabled
      ? `<span style="width:8px;height:8px;border-radius:50%;background:#6b7280;position:absolute;top:10px;right:10px;z-index:2;" title="${_ti('Disabled','Disabilitato','Desactivado')}"></span>`
      : `<span style="width:8px;height:8px;border-radius:50%;background:#10b981;position:absolute;top:10px;right:10px;box-shadow:0 0 6px #10b981;z-index:2;" title="${_ti('Active','Attivo','Activo')}"></span>`;

  const disableLazy    = pkg.tag ? ['REMINDER','CALENDAR','WEB_UI','MCP_BRIDGE','DASHBOARD'].includes(pkg.tag.toUpperCase()) : false;
  const disableEnabled = pkg.tag ? ['WEB_UI'].includes(pkg.tag.toUpperCase()) : false;
  const isLazy = pkg.lazy_load === true;
  const hasConfig = !!(pkg.manifest_snapshot && pkg.manifest_snapshot.config_panel);

  // ── Shared button styles ────────────────────────────────────────────────────
  const btnActive   = 'font-size:11px;padding:5px 8px;background:var(--bg3);border:1px solid var(--border-color);color:var(--text);border-radius:6px;cursor:pointer;display:inline-flex;align-items:center;justify-content:center;transition:background .15s;flex:1;';
  const btnGhost    = 'font-size:11px;padding:5px 8px;background:transparent;border:1px solid rgba(255,255,255,0.07);color:var(--muted);border-radius:6px;cursor:default;display:inline-flex;align-items:center;justify-content:center;opacity:0.35;flex:1;';
  const btnDanger   = 'font-size:11px;padding:5px 8px;background:rgba(239,68,68,.1);border:1px solid rgba(239,68,68,.3);color:#ef4444;border-radius:6px;cursor:pointer;display:inline-flex;align-items:center;justify-content:center;transition:background .15s;flex:1;';
  const btnRestart  = 'font-size:11px;padding:5px 8px;background:linear-gradient(135deg,#f59e0b,#d97706);border:none;color:#fff;border-radius:6px;cursor:pointer;display:inline-flex;align-items:center;justify-content:center;animation:hpmPulse 2s ease-in-out infinite;flex:1;';

  // ── ROW 1 – Always-present action buttons (top) ────────────────────────────
  let row1 = '';

  // Capabilities
  row1 += `<button type="button" style="${btnActive}"
    onclick="event.stopPropagation();hpmShowCapabilities('${pkg.id}','${window._hesc(pkg.name)}')"
    title="${_ti('View Capabilities','Vedi Funzionalità','Ver Capacidades')}">
    <i class="fas fa-info-circle" style="color:#3b82f6;"></i>
  </button>`;

  // Docs (ghost for core)
  if (!isCore) {
    row1 += `<button type="button" style="${btnActive}"
      onclick="event.stopPropagation();hpmShowDocs('${pkg.id}','${window._hesc(pkg.name)}')"
      title="${window.HPM_I18N?.read_docs || _ti('Read Docs','Leggi Docs','Leer Documentación')}">
      <i class="fas fa-book" style="color:#10b981;"></i>
    </button>`;
  } else {
    row1 += `<span style="${btnGhost}" title="${_ti('Documentation not available for core modules','Non disponibile per moduli core','No disponible para módulos core')}">
      <i class="fas fa-book"></i>
    </span>`;
  }

  // Verify integrity
  row1 += `<button type="button" style="${btnActive}"
    onclick="event.stopPropagation();window.hpmVerifyPackage('${pkg.id}','${window._hesc(pkg.name)}')"
    title="${window.HPM_I18N?.verify || _ti('Verify Integrity','Verifica Integrità','Verificar Integridad')}">
    <i class="fas fa-check-double" style="opacity:.8;"></i>
  </button>`;

  // Hot reload / Restart (ghost if tag missing or broken/disabled)
  if (pkg.tag && !isDisabled && !isBroken) {
    if (pkg.requires_restart) {
      row1 += `<button type="button" style="${btnRestart}"
        onclick="event.stopPropagation();window.hpmRestartRequired('${window._hesc(pkg.name)}')"
        title="${_ti('Restart required to activate','Riavvio richiesto per attivare','Reinicio requerido para activar')}">
        <i class="fas fa-power-off"></i>
      </button>`;
    } else {
      row1 += `<button type="button" style="${btnActive}"
        onclick="event.stopPropagation();window.hpmHotReloadModule('${pkg.id}','${window._hesc(pkg.name)}')"
        title="${window.HPM_I18N?.hot_reload || _ti('Hot Reload','Hot Reload','Recarga en Caliente')}">
        <i class="fas fa-sync-alt" style="opacity:.8;"></i>
      </button>`;
    }
  } else {
    row1 += `<span style="${btnGhost}" title="${_ti('Hot Reload not available','Hot Reload non disponibile','Recarga no disponible')}">
      <i class="fas fa-sync-alt"></i>
    </span>`;
  }

  // Uninstall / Lock (always present, lock for built-ins)
  if (isRemovable) {
    row1 += `<button type="button" style="${btnDanger}"
      onclick="event.stopPropagation();hpmConfirmUninstall('${pkg.id}','${window._hesc(pkg.name)}')"
      title="${window.HPM_I18N?.uninstall || _ti('Uninstall','Disinstalla','Desinstalar')}">
      <i class="fas fa-trash-alt"></i>
    </button>`;
  } else {
    row1 += `<span style="${btnGhost}" title="${window.HPM_I18N?.tooltip_builtin || _ti('Built-in — cannot be removed','Integrato — non rimovibile','Integrado — no se puede eliminar')}">
      <i class="fas fa-lock"></i>
    </span>`;
  }

  // ── ROW 2 – Toggles + optional controls (bottom) ──────────────────────────

  // Left side: Lazy Load (ghost if disabled) + Config gear (ghost if missing)
  let lazyBtn = '';
  if (!disableLazy) {
    lazyBtn = `<label class="lazy-label no-autosave"
        title="${_ti('Lazy Load — start only when first needed','Lazy Load — avvia solo al primo utilizzo','Carga diferida — inicia solo cuando se necesita')}"
        style="font-size:10px;display:inline-flex;align-items:center;gap:3px;cursor:pointer;color:var(--muted);padding:5px 7px;background:var(--bg3);border:1px solid var(--border-color);border-radius:6px;" onclick="event.stopPropagation()">
      <input type="checkbox" onchange="hpmToggleLazy('${pkg.id}', ${isBuiltin}, this.checked)" ${isLazy ? 'checked' : ''} onclick="event.stopPropagation()">
      <i class="fas fa-feather" style="font-size:9px;"></i>
    </label>`;
  } else {
    lazyBtn = `<span style="${btnGhost};padding:5px 7px;flex:none;" title="${_ti('Lazy Load not available for this module type','Lazy Load non disponibile per questo tipo di modulo','Carga diferida no disponible para este tipo')}">
      <i class="fas fa-feather" style="font-size:9px;margin-right:2px;"></i>
    </span>`;
  }

  let cfgBtn = '';
  if (hasConfig) {
    const cfgCat   = window.hpmGetHubCategoryLabel(pkg.manifest_snapshot.config_panel.category);
    const cfgLabel = window._hesc(pkg.manifest_snapshot.config_panel.tab_label || pkg.name);
    const cfgId    = window._hesc(pkg.manifest_snapshot.config_panel.tab_id || pkg.id.replace('_','-'));
    cfgBtn = `<a href="#${cfgId}" onclick="event.stopPropagation()"
      style="${btnActive}flex:none;text-decoration:none;"
      title="${_ti('Configuration','Configurazione','Configuración')}: ${window._hesc(cfgCat)} → ${cfgLabel}">
      <i class="fas fa-cogs" style="color:var(--accent);"></i>
    </a>`;
  } else {
    cfgBtn = `<span style="${btnGhost};flex:none;" title="${_ti('No configuration panel for this module','Nessun pannello di configurazione','Sin panel de configuración')}">
      <i class="fas fa-cogs"></i>
    </span>`;
  }

  // Right side: Enable/Disable switch
  let switchHtml = '';
  if (!isBroken) {
    switchHtml = `<label class="switch no-autosave"
      ${disableEnabled ? 'style="visibility:hidden;pointer-events:none;"' : ''}
      title="${window.HPM_I18N?.enable || _ti('Enable / Disable','Abilita / Disabilita','Activar / Desactivar')}"
      onclick="event.stopPropagation()">
      <input type="checkbox" onchange="hpmToggleEnabled('${pkg.id}', ${isBuiltin}, this.checked)" ${!isDisabled ? 'checked' : ''} ${disableEnabled ? 'disabled' : ''} onclick="event.stopPropagation()">
      <span class="slider"></span>
    </label>`;
  }

  // The fallback chain: local preview.png → manifest screenshots[0] → default remote
  const fallbackSrc = window._hesc(screenshots[0]);

  return `
    <div class="hpm-wall-card ${isDisabled ? 'disabled' : ''}" id="hpm-pkg-wall-${pkg.id}"
         onclick="hpmShowCapabilities('${pkg.id}','${window._hesc(pkg.name)}')">
      ${statusDot}

      <!-- Header: fa-icon (always type category icon) + name + type badge -->
      <div style="display:flex;align-items:flex-start;gap:12px;">
        <div style="width:44px;height:44px;border-radius:12px;flex-shrink:0;background:${typeMeta.color}20;
                    display:flex;align-items:center;justify-content:center;overflow:hidden;">
          <i class="fas ${window._hesc(faIcon)}" style="color:${typeMeta.color};font-size:20px;"></i>
        </div>
        <div style="flex:1;min-width:0;padding-top:2px;">
          <div style="font-weight:700;font-size:0.95em;color:var(--text);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;" title="${window._hesc(pkg.name)}">
            ${window._hesc(pkg.name)}
          </div>
          <div style="display:flex;align-items:center;gap:5px;margin-top:3px;flex-wrap:wrap;">
            <span style="font-size:0.66em;font-weight:700;letter-spacing:.6px;text-transform:uppercase;
                         color:${typeMeta.color};background:${typeMeta.color}18;padding:2px 6px;
                         border-radius:4px;border:1px solid ${typeMeta.color}44;">${typeMeta.label}</span>
            <span style="font-size:0.7em;color:var(--muted);">v${window._hesc(pkg.version || '—')}</span>
          </div>
        </div>
      </div>

      <!-- Preview image 16:9: try local preview.png first, fallback to manifest screenshot, then hide -->
      <div style="width:100%;aspect-ratio:16/9;border-radius:8px;overflow:hidden;
                  border:1px solid rgba(255,255,255,0.08);background:#050505;
                  display:flex;align-items:center;justify-content:center;position:relative;">
        <img src="/hpm_plugin/${pkg.id}/preview.png"
             onerror="if(this.dataset.fb!='1'){this.dataset.fb='1';this.src='${fallbackSrc}';}else{this.parentElement.style.display='none';}"
             style="width:100%;height:100%;object-fit:contain;padding:6px;box-sizing:border-box;transition:transform .3s;"
             onmouseover="this.style.transform='scale(1.04)'" onmouseout="this.style.transform='scale(1)'"
             loading="lazy">
        ${hasMultiple ? `<div style="position:absolute;bottom:6px;right:8px;background:rgba(0,0,0,.65);color:#fff;font-size:0.65em;padding:2px 7px;border-radius:10px;pointer-events:none;font-weight:600;">1 / ${screenshots.length}</div>` : ''}
      </div>

      <!-- Description -->
      ${pkg.description ? `<div style="font-size:0.76em;color:var(--muted);line-height:1.45;
          display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;">
        ${window._hesc(pkg.description)}
      </div>` : ''}

      <!-- Footer: two rows of controls -->
      <div onclick="event.stopPropagation()" style="display:flex;flex-direction:column;gap:6px;margin-top:auto;">

        <!-- Row 1: always-present action buttons -->
        <div class="hpm-card-actions" style="display:flex;align-items:center;gap:4px;">
          ${row1}
        </div>

        <!-- Row 2: optional controls + enable toggle -->
        <div style="display:flex;align-items:center;justify-content:space-between;gap:6px;">
          <div style="display:flex;align-items:center;gap:4px;">
            ${lazyBtn}
            ${cfgBtn}
          </div>
          <div>
            ${switchHtml}
          </div>
        </div>

      </div>
    </div>
  `;
};
