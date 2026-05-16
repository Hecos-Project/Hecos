/**
 * config_mapper_plugins.js
 * Plugin Manager rendering and live state sync.
 * Depends on: config_mapper_utils.js
 */

function renderPlugins(plugins) {
  const cont = document.getElementById('plugin-list');
  if (!cont) return;
  const hub  = window.CONFIG_HUB;
  if (!hub) return;
  const I18N = window.I18N || {};

  let coreCount = 0, pluginCount = 0, extensionCount = 0;
  hub.modules.forEach(m => {
    if (!m.pluginTag || m.id === 'plugins') return;
    if (m.isExtension) extensionCount++;
    else if (m.isCore) coreCount++;
    else pluginCount++;
  });

  let htmlCore = `<details open style="margin-bottom:10px;">
    <summary style="cursor:pointer; margin-bottom:12px; padding-bottom:8px; border-bottom:1px solid rgba(102,252,241,0.2); user-select:none; display:flex; align-items:center; gap:10px;">
      <strong style="color:var(--cyan);font-size:11px;opacity:0.8;letter-spacing:1px;text-transform:uppercase;">Hecos Module Manager (Level 1)</strong>
      <span class="p-tag core">CORE</span>
      <span style="margin-left:auto; font-size:10px; color:var(--muted); font-weight:800; background:rgba(255,255,255,0.05); padding:2px 8px; border-radius:10px;">${coreCount}</span>
    </summary>`;

  let htmlPlugins = `<details open style="margin-top:25px; margin-bottom:10px;">
    <summary style="cursor:pointer; margin-bottom:12px; padding-bottom:8px; border-bottom:1px solid rgba(102,252,241,0.2); user-select:none; display:flex; align-items:center; gap:10px;">
      <strong style="color:var(--cyan);font-size:11px;opacity:0.8;letter-spacing:1px;text-transform:uppercase;">Native Plugins &amp; Extensions (Level 2 &amp; 3)</strong>
      <span class="p-tag plugin">PLUGIN</span>
      <span class="p-tag extension">EXT</span>
      <span style="margin-left:auto; font-size:10px; color:var(--muted); font-weight:800; background:rgba(255,255,255,0.05); padding:2px 8px; border-radius:10px;">${pluginCount + extensionCount}</span>
    </summary>`;

  let addedCore = false, addedPlugins = false;

  hub.modules.forEach(m => {
    if (!m.pluginTag || m.id === 'plugins' || m.isExtension) return;

    const tag  = m.pluginTag;
    const pCfg = plugins[tag] || { enabled: true };
    const on   = pCfg.enabled !== false;
    const lazyOn = pCfg.lazy_load === true;
    const name = window.t ? window.t(m.label) : m.label;
    const descKey = 'webui_desc_' + tag.toLowerCase();
    const desc = (window.t && window.t(descKey) !== descKey) ? window.t(descKey) : (I18N['plugin_desc_' + tag.toLowerCase()] || name);
    const icon = m.icon || '🧩';
    const mType = m.isCore ? 'core_module' : (pCfg.module_type || 'plugin');

    const disableLazy    = ['REMINDER','CALENDAR','WEB_UI','MCP_BRIDGE','DASHBOARD'].includes(tag);
    const disableEnabled = ['WEB_UI'].includes(tag);

    let badges = `<span class="p-tag">${tag}</span>`;
    badges += mType === 'core_module'
      ? ` <span class="p-tag core" style="font-size:9px;">CORE</span>`
      : ` <span class="p-tag plugin" style="font-size:9px;">PLUGIN</span>`;

    let rowHtml = `<div class="plugin-row">
      <div class="plugin-info-main">
        <span class="p-icon">${icon}</span>
        <div class="plugin-meta">
          <div class="plugin-name">${name} ${badges}
            ${disableLazy ? '' : `<label class="lazy-label"><input type="checkbox" data-plugin-lazy="${tag}" ${lazyOn?'checked':''}> Lazy</label>`}
          </div>
          <div class="plugin-desc">${desc}</div>
        </div>
      </div>
      <label class="switch" ${disableEnabled ? 'style="visibility:hidden;pointer-events:none;"' : ''}><input type="checkbox" data-plugin="${tag}" ${on?'checked':''} ${disableEnabled?'disabled':''}><span class="slider"></span></label>
    </div>`;

    // Child extensions
    hub.modules.forEach(child => {
      if (!child.isExtension || child.parentPluginTag !== tag) return;
      const childTag  = child.pluginTag;
      const extId     = childTag.replace(tag + '_', '').toLowerCase();
      const extCfg    = (pCfg.extensions || {})[extId] || {};
      const extOn     = extCfg.enabled !== false;
      const childName = window.t ? window.t(child.label) : child.label;
      const childDescKey = 'webui_desc_' + childTag.toLowerCase();
      const childDesc = (window.t && window.t(childDescKey) !== childDescKey) ? window.t(childDescKey) : childName;
      const childIcon = child.icon || '🧩';
      const dimStyle  = !on ? 'opacity:0.4; pointer-events:none;' : '';

      rowHtml += `<div class="plugin-row plugin-row-extension" style="margin-left:28px; border-left:2px solid rgba(102,252,241,0.15); padding-left:12px; ${dimStyle}">
        <div class="plugin-info-main">
          <span class="p-icon" style="font-size:14px;">└─ ${childIcon}</span>
          <div class="plugin-meta">
            <div class="plugin-name" style="font-size:12px;">${childName}
              <span class="p-tag" style="font-size:9px; opacity:0.6;">${childTag}</span>
              <span class="p-tag" style="font-size:9px; background:rgba(69,162,158,0.2); color:#45a29e; border-color:#45a29e;">EXT</span>
            </div>
            <div class="plugin-desc" style="font-size:11px; opacity:0.7;">${childDesc}</div>
          </div>
        </div>
        <label class="switch is-small"><input type="checkbox"
          data-extension="true" data-parent="${tag}" data-ext-id="${extId}"
          ${extOn?'checked':''} ${!on?'disabled':''}
        ><span class="slider"></span></label>
      </div>`;
    });

    if (mType === 'core_module') { htmlCore += rowHtml; addedCore = true; }
    else { htmlPlugins += rowHtml; addedPlugins = true; }
  });

  if (addedCore)    htmlCore    += '</details>';
  if (addedPlugins) htmlPlugins += '</details>';

  let html = '';
  if (addedCore)    html += htmlCore;
  if (addedPlugins) html += htmlPlugins;
  cont.innerHTML = html || `<p style="color:var(--muted)">${I18N.no_plugins || 'No modules discovered'}</p>`;

  // Wire parent toggles
  cont.querySelectorAll('[data-plugin]').forEach(parentCb => {
    parentCb.addEventListener('change', function() {
      const parentTag = this.dataset.plugin;
      syncPluginStateToMemory(parentTag, this.checked);
      cont.querySelectorAll(`[data-extension="true"][data-parent="${parentTag}"]`).forEach(childCb => {
        childCb.disabled = !this.checked;
        const row = childCb.closest('.plugin-row-extension');
        if (row) {
          row.style.opacity = this.checked ? '' : '0.4';
          row.style.pointerEvents = this.checked ? '' : 'none';
        }
      });
    });
  });

  // Wire extension toggles
  cont.querySelectorAll('[data-extension="true"]').forEach(extCb => {
    extCb.addEventListener('change', function() {
      syncPluginStateToMemory(this.dataset.parent, this.checked, this.dataset.extId);
    });
  });
}

/**
 * Syncs a plugin/extension toggle directly into window.cfg and re-renders tabs.
 */
function syncPluginStateToMemory(tag, enabled, extId = null) {
    if (!window.cfg.plugins) window.cfg.plugins = {};
    window.cfg.plugins[tag] = window.cfg.plugins[tag] || {};

    if (extId) {
        window.cfg.plugins[tag].extensions = window.cfg.plugins[tag].extensions || {};
        window.cfg.plugins[tag].extensions[extId] = window.cfg.plugins[tag].extensions[extId] || {};
        window.cfg.plugins[tag].extensions[extId].enabled = enabled;
    } else {
        window.cfg.plugins[tag].enabled = enabled;
    }
    if (typeof renderConfigHub === 'function') renderConfigHub();
}

/**
 * Merges plugin toggles (enabled, extensions, lazy, dashboard, browser, automation)
 * into the `out` payload object.
 */
function buildPluginsPayload(out) {
    // Standalone plugin enabled toggles
    document.querySelectorAll('[data-plugin]').forEach(cb => {
        const tag = cb.dataset.plugin;
        out.plugins[tag] = out.plugins[tag] || {};
        out.plugins[tag].enabled = cb.checked;
    });

    // Browser engine mode (inline radio)
    out.plugins['BROWSER'] = out.plugins['BROWSER'] || {};
    const modeEl = document.querySelector('input[name="engine_mode"]:checked');
    if (modeEl) {
        out.plugins['BROWSER'].browser_engine_mode = modeEl.value;
    } else {
        out.plugins['BROWSER'].browser_engine_mode = out.plugins['BROWSER'].browser_engine_mode || 'playwright';
    }
    out.plugins['BROWSER'].cdp_port    = parseInt(getV('browser-cdp-port',    out.plugins['BROWSER'].cdp_port))    || 9222;
    out.plugins['BROWSER'].headless    = getC('browser-headless',    out.plugins['BROWSER'].headless);
    out.plugins['BROWSER'].block_ads   = getC('browser-block-ads',   out.plugins['BROWSER'].block_ads);
    out.plugins['BROWSER'].startup_url = getV('browser-startup-url', out.plugins['BROWSER'].startup_url);
    out.plugins['BROWSER'].browser_type = getV('browser-engine',     out.plugins['BROWSER'].browser_type) || 'chromium';

    // Automation
    out.plugins['AUTOMATION'] = out.plugins['AUTOMATION'] || {};
    out.plugins['AUTOMATION'].enabled = getC('automation-enabled');

    // Extension toggles
    document.querySelectorAll('[data-extension="true"]').forEach(cb => {
        const parentTag = cb.dataset.parent;
        const extId     = cb.dataset.extId;
        if (!parentTag || !extId) return;
        out.plugins[parentTag] = out.plugins[parentTag] || {};
        out.plugins[parentTag].extensions = out.plugins[parentTag].extensions || {};
        out.plugins[parentTag].extensions[extId] = out.plugins[parentTag].extensions[extId] || {};
        out.plugins[parentTag].extensions[extId].enabled = cb.checked;
    });

    // Lazy load toggles
    document.querySelectorAll('[data-plugin-lazy]').forEach(cb => {
        const tag = cb.dataset.pluginLazy;
        if (out.plugins[tag]) out.plugins[tag].lazy_load = cb.checked;
    });

    // Dashboard specialized toggles
    if (document.getElementById('dashboard-webui-enabled')) {
        out.plugins['DASHBOARD'] = out.plugins['DASHBOARD'] || {};
        out.plugins['DASHBOARD'].webui_dashboard_enabled    = getC('dashboard-webui-enabled');
        out.plugins['DASHBOARD'].webui_telemetry_enabled    = getC('telemetry-webui-enabled');
        out.plugins['DASHBOARD'].track_cpu                  = getC('track-cpu-enabled');
        out.plugins['DASHBOARD'].track_ram                  = getC('track-ram-enabled');
        out.plugins['DASHBOARD'].track_vram                 = getC('track-vram-enabled');
        out.plugins['DASHBOARD'].console_dashboard_enabled  = getC('dashboard-console-enabled');
        out.plugins['DASHBOARD'].console_telemetry_enabled  = getC('telemetry-console-enabled');
    }
}

window.renderPlugins            = renderPlugins;
window.syncPluginStateToMemory  = syncPluginStateToMemory;
