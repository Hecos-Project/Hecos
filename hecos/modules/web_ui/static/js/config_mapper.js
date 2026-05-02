// config_mapper.js
// Extracts DOM mapping and Payload Building from config_core.js

const RESTART_FIELDS = [
  'sys-https-enabled'
];

/**
 * Utility to populate a <select> element
 */
function populateSelect(id, list, currentValue, isFilenameOnly = false) {
  const el = document.getElementById(id);
  if (!el) return;
  
  // Clear existing
  el.innerHTML = '';
  
  // Convert object to array [ { "id": "val", "name": "val" / "key" } ]
  let items = list;
  if (list && typeof list === 'object' && !Array.isArray(list)) {
      items = Object.entries(list).map(([k, v]) => ({ 
          id: v, 
          name: k.match(/^\d+$/) ? String(v).replace('.yaml', '') : k 
      }));
  }

  // Basic validation
  if (!items || (Array.isArray(items) && items.length === 0)) {
    if (typeof isInitialLoading !== 'undefined' && isInitialLoading) {
      const opt = document.createElement('option');
      opt.textContent = "Loading...";
      opt.disabled = true;
      el.appendChild(opt);
    }
    return;
  }
  
  let cleanValue = currentValue;
  if (isFilenameOnly && currentValue && (currentValue.includes('\\') || currentValue.includes('/'))) {
    cleanValue = currentValue.split(/[\\/]/).pop();
  }

  const itemsArr = Array.isArray(items) ? items : [items];
  itemsArr.forEach(item => {
    const opt = document.createElement('option');
    
    let val, text;
    if (typeof item === 'object' && item !== null) {
        val = item.id || item.value || '';
        text = item.name || item.text || val;
    } else {
        val = item;
        text = item;
    }

    const shortText = (isFilenameOnly && (text.includes('\\') || text.includes('/'))) ? text.split(/[\\/]/).pop() : text;
    const shortVal = (isFilenameOnly && (val.includes('\\') || val.includes('/'))) ? val.split(/[\\/]/).pop() : val;
    
    opt.value = val;
    opt.textContent = shortText;
    
    // Improved selection logic: exact match or filename match
    if (cleanValue) {
        if (val === cleanValue || shortVal === cleanValue || val.toLowerCase() === cleanValue.toLowerCase() || shortVal.toLowerCase() === cleanValue.toLowerCase()) {
            opt.selected = true;
        }
    }
    el.appendChild(opt);
  });

  // Final fallback force selection
  if (cleanValue && !el.value) {
      for (let i = 0; i < el.options.length; i++) {
          if (el.options[i].value.toLowerCase().includes(cleanValue.toLowerCase().replace('.yaml',''))) {
              el.selectedIndex = i;
              break;
          }
      }
  }
}

function setVal(id, val) { const el = document.getElementById(id); if (el) el.value = val; }
function setCheck(id, val) { const el = document.getElementById(id); if (el) el.checked = val; }
function getV(id) { const el = document.getElementById(id); return el ? el.value : ''; }
function getC(id) { const el = document.getElementById(id); return el ? el.checked : false; }

function populateUI() {
  try {
    const c = window.cfg;
    const sysOptions = window.sysOptions;
    // 1. LLM & Routing (Core)
    const bt = c.backend?.type || 'ollama';
    const btEl = document.getElementById('backend-type');
    if (btEl) {
        btEl.value = bt;
        btEl.dispatchEvent(new Event('change'));
    }
    populateSelect('cloud-model', sysOptions.all_cloud || [], c.backend?.cloud?.model);
    populateSelect('ollama-model', sysOptions.ollama_models || [], c.backend?.ollama?.model);

    setVal('cloud-temp', c.backend?.cloud?.temperature ?? 0.7);
    setVal('ollama-temp', c.backend?.ollama?.temperature ?? 0.3);
    setVal('ollama-gpu', c.backend?.ollama?.num_gpu ?? 25);
    setVal('ollama-predict', c.backend?.ollama?.num_predict ?? 250);
    setVal('ollama-ctx', c.backend?.ollama?.num_ctx ?? 4096);
    setVal('ollama-top-p', c.backend?.ollama?.top_p ?? 0.9);
    setVal('ollama-repeat', c.backend?.ollama?.repeat_penalty ?? 1.1);
    
    setVal('kobold-url', c.backend?.kobold?.url || 'http://localhost:5001');
    setVal('kobold-model', c.backend?.kobold?.model || '');
    setVal('kobold-temp', c.backend?.kobold?.temperature ?? 0.8);
    setVal('kobold-max', c.backend?.kobold?.max_length ?? 512);
    setVal('kobold-top-p', c.backend?.kobold?.top_p ?? 0.92);
    setVal('kobold-rep', c.backend?.kobold?.rep_pen ?? 1.1);

    const llm = c.llm || {};
    setCheck('llm-allow-cloud', llm.allow_cloud ?? true);
    setCheck('llm-debug', llm.debug_llm ?? true);
    const prov = llm.providers || {};
    ['openai','anthropic','groq','gemini'].forEach(p => {

      setVal('models-'+p, (prov[p]?.models || []).join('\n'));
    });

    const rm = c.routing_engine || {};
    setVal('route-mode', rm.mode || 'auto');
    setVal('route-models', rm.legacy_models || '');

    populateSelect('ia-personality-main', sysOptions.personalities || [], c.ai?.active_personality, true);
    const ai = c.ai || {};
    const instrEl  = document.getElementById('ia-instructions');
    const safetyEl = document.getElementById('ia-safety-instructions');
    const saveInstEl = document.getElementById('ia-save-instructions');
    
    if (instrEl) instrEl.value = ai.special_instructions || '';
    if (safetyEl) safetyEl.value = ai.safety_instructions || '';
    if (saveInstEl) saveInstEl.checked = ai.save_special_instructions || false;
    setCheck('ia-enable-safety-instructions', ai.enable_safety_instructions ?? true);
    setVal('ia-avatar-size', c.ai?.avatar_size || 'medium');


    
    // Load the avatar preview for the currently selected persona
    if (typeof window.loadPersonaAvatar === 'function') {
        const personaEl = document.getElementById('ia-personality-main');
        if (personaEl && personaEl.value) {
            window.loadPersonaAvatar(personaEl.value);
        }
    }


    const br = c.bridge || {};
    setCheck('br-processor', br.use_processor ?? false);
    setCheck('br-think-tags', br.remove_think_tags ?? true);
    setCheck('br-debug', br.debug_log ?? true);
    setCheck('br-tools', br.enable_tools ?? true);
    setCheck('br-voice-stt', br.webui_voice_stt ?? true);
    setCheck('br-voice-enabled', br.webui_voice_enabled ?? false);
    setVal('br-delay', br.chunk_delay_ms ?? 0);

    const fi = c.filters || {};
    // Backward compatibility: boolean to string handled in python, but UI might get bools if cache wasn't cleared
    setVal('fl-ast', fi.remove_asterisks === true ? 'both' : fi.remove_asterisks === false ? 'none' : fi.remove_asterisks || 'both');
    setVal('fl-tonde', fi.remove_round_brackets === true ? 'both' : fi.remove_round_brackets === false ? 'none' : fi.remove_round_brackets || 'voice');
    setVal('fl-quadre', fi.remove_square_brackets === true ? 'both' : fi.remove_square_brackets === false ? 'none' : fi.remove_square_brackets || 'none');
    
    if (window.HecosTextFilters) {
        window.HecosTextFilters.populate(fi.custom_filters || []);
    }

    // 2. Audio Module Dispatch
    if (typeof populateAudioUI === 'function') populateAudioUI();

    // 3. System Module Dispatch
    if (typeof populateSystemUI === 'function') populateSystemUI();

    // 4. Media & Image Gen Dispatch
    if (typeof populateMediaUI === 'function') populateMediaUI();
        
    // 5. Drive Module Dispatch
    populateDriveUI();

    // 6. Remote Triggers Dispatch
    populateRemoteTriggersUI();
    
    // 7. Privacy & WebUI Dispatch

    populatePrivacyUI();
    populateWebUIConfig();

    // Sync Dashboard specialized toggles
    const dsb = c.plugins?.DASHBOARD || {};
    setCheck('dashboard-webui-enabled', dsb.webui_dashboard_enabled ?? true);
    setCheck('telemetry-webui-enabled', dsb.webui_telemetry_enabled ?? true);
    setCheck('dashboard-console-enabled', dsb.console_dashboard_enabled ?? true);
    setCheck('telemetry-console-enabled', dsb.console_telemetry_enabled ?? true);

    // Sync all standalone plugin toggles
    document.querySelectorAll('[data-plugin]').forEach(cb => {
        const tag = cb.dataset.plugin;
        if (c.plugins && c.plugins[tag]) {
            cb.checked = c.plugins[tag].enabled !== false;
        }
    });

    renderPlugins(c.plugins || {});
    initRestartIndicators();
    console.log("UI Populated successfully.");
  } catch (err) {
    console.error("UI Population failed:", err);
  }
}

function initRestartIndicators() {
  console.log("[CONFIG] Initializing Restart Indicators for:", RESTART_FIELDS);
  RESTART_FIELDS.forEach(id => {
    const el = document.getElementById(id);
    if (!el) {
      console.warn("[CONFIG] Element not found for restart indicator:", id);
      return;
    }

    // Create badge if not exists
    let badge = document.getElementById('badge-' + id);
    if (!badge) {
      badge = document.createElement('span');
      badge.id = 'badge-' + id;
      badge.className = 'restart-badge';
      badge.textContent = 'Restart Required';
      
      // Smart placement
      const parentField = el.closest('.field');
      const parentToggle = el.closest('.toggle-row');
      
      if (parentField) {
        const label = parentField.querySelector('label');
        if (label) label.appendChild(badge);
        else parentField.appendChild(badge);
      } else if (parentToggle) {
        const info = parentToggle.querySelector('.toggle-info');
        if (info) info.appendChild(badge);
        else parentToggle.appendChild(badge);
      } else {
        el.parentElement.appendChild(badge);
      }
    }

    const initialValue = el.type === 'checkbox' ? el.checked : el.value;
    console.debug(`[CONFIG] Monitoring ${id}, initial:`, initialValue);

    const check = () => {
      const current = el.type === 'checkbox' ? el.checked : el.value;
      if (current !== initialValue) {
        badge.classList.add('visible');
      } else {
        badge.classList.remove('visible');
      }
    };

    el.addEventListener('change', check);
    el.addEventListener('input', check);
  });
}

function renderPlugins(plugins) {
  const cont = document.getElementById('plugin-list');
  if (!cont) return;
  const hub = window.CONFIG_HUB;
  const I18N = window.I18N || {};
  const descs = {
    DASHBOARD:   I18N.plugin_desc_dashboard,
    FILE_MANAGER:I18N.plugin_desc_file,
    HELP:        I18N.plugin_desc_help,
    MEDIA:       I18N.plugin_desc_media,

    SYSTEM:      I18N.plugin_desc_system,
    WEB:         I18N.plugin_desc_web,
    WEBCAM:      I18N.plugin_desc_webcam,
    WEB_UI:      I18N.plugin_desc_webui,
    IMAGE_GEN:   window.t ? window.t('webui_desc_igen') : 'AI Image Generation (Pollinations/Flux)',
    DRIVE:       window.t ? window.t('webui_desc_drive') : 'HTTP File Manager (Hecos Drive)',
    REMOTE_TRIGGERS: window.t ? window.t('webui_desc_triggers') : 'Remote PTT & Media Keys',
    MCP_BRIDGE:  window.t ? window.t('webui_desc_mcp') : 'Universal MCP Bridge',
    DRIVE_EDITOR: window.t ? window.t('webui_desc_editor') : 'Integrated Code Editor'
  };

  // Count categories for headers
  let coreCount = 0;
  let pluginCount = 0;
  let extensionCount = 0;

  hub.modules.forEach(m => {
    if (!m.pluginTag || m.id === 'plugins') return;
    if (m.isExtension) {
        extensionCount++;
    } else if (m.isCore) {
        coreCount++;
    } else {
        pluginCount++;
    }
  });

  let htmlCore = `<details open style="margin-bottom:10px;">
    <summary style="cursor:pointer; margin-bottom:12px; padding-bottom:8px; border-bottom:1px solid rgba(102,252,241,0.2); user-select:none; display:flex; align-items:center; gap:10px;">
      <strong style="color:var(--cyan);font-size:11px;opacity:0.8;letter-spacing:1px;text-transform:uppercase;">Core Modules (Level 1)</strong>
      <span class="p-tag core">CORE</span>
      <span style="margin-left:auto; font-size:10px; color:var(--muted); font-weight:800; background:rgba(255,255,255,0.05); padding:2px 8px; border-radius:10px;">${coreCount}</span>
    </summary>`;

  let htmlPlugins = `<details open style="margin-top:25px; margin-bottom:10px;">
    <summary style="cursor:pointer; margin-bottom:12px; padding-bottom:8px; border-bottom:1px solid rgba(102,252,241,0.2); user-select:none; display:flex; align-items:center; gap:10px;">
      <strong style="color:var(--cyan);font-size:11px;opacity:0.8;letter-spacing:1px;text-transform:uppercase;">Native Plugins & Extensions (Level 2 & 3)</strong>
      <span class="p-tag plugin">PLUGIN</span>
      <span class="p-tag extension">EXT</span>
      <span style="margin-left:auto; font-size:10px; color:var(--muted); font-weight:800; background:rgba(255,255,255,0.05); padding:2px 8px; border-radius:10px;">${pluginCount + extensionCount}</span>
    </summary>`;
  let addedCore = false;
  let addedPlugins = false;
  
  // Group 1: Native & Static Modules from Hub
  hub.modules.forEach(m => {
    if (!m.pluginTag || m.id === 'plugins') return;
    
    if (m.isExtension) return; // handled below, under parent

    const tag = m.pluginTag;
    const pCfg = plugins[tag] || { enabled: true };
    const on = pCfg.enabled !== false;
    const lazyOn = pCfg.lazy_load === true;
    const name = t(m.label);
    const descKey = 'webui_desc_' + tag.toLowerCase().replace(/_/g, '_');
    const desc = t(descKey) !== descKey ? t(descKey) : (I18N['plugin_desc_' + tag.toLowerCase()] || name);
    const icon = m.icon || '🧩';
    const mType = m.isCore ? 'core_module' : (pCfg.module_type || 'plugin');

    let badges = `<span class="p-tag">${tag}</span>`;
    if (mType === 'core_module') {
        badges += ` <span class="p-tag core" style="font-size:9px;">CORE</span>`;
    } else {
        badges += ` <span class="p-tag plugin" style="font-size:9px;">PLUGIN</span>`;
    }

    let rowHtml = `<div class="plugin-row">
      <div class="plugin-info-main">
        <span class="p-icon">${icon}</span>
        <div class="plugin-meta">
          <div class="plugin-name">${name} ${badges}
            <label class="lazy-label"><input type="checkbox" data-plugin-lazy="${tag}" ${lazyOn?'checked':''}> Lazy</label>
          </div>
          <div class="plugin-desc">${desc}</div>
        </div>
      </div>
      <label class="switch"><input type="checkbox" data-plugin="${tag}" ${on?'checked':''}><span class="slider"></span></label>
    </div>`;

    // Render child extensions of this plugin
    hub.modules.forEach(child => {
      if (!child.isExtension || child.parentPluginTag !== tag) return;

      const childTag = child.pluginTag;
      const extId = childTag.replace(tag + '_', '').toLowerCase();
      const extCfg = (pCfg.extensions || {})[extId] || {};
      const extOn = extCfg.enabled !== false;
      const childName = t(child.label);
      const childDescKey = 'webui_desc_' + childTag.toLowerCase().replace(/_/g, '_');
      const childDesc = t(childDescKey) !== childDescKey ? t(childDescKey) : childName;
      const childIcon = child.icon || '🧩';
      const disabledAttr = !on ? 'disabled' : '';
      const dimStyle = !on ? 'opacity:0.4; pointer-events:none;' : '';

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
          data-extension="true"
          data-parent="${tag}"
          data-ext-id="${extId}"
          ${extOn?'checked':''}
          ${disabledAttr}
        ><span class="slider"></span></label>
      </div>`;
    });
    
    if (mType === 'core_module') {
        htmlCore += rowHtml;
        addedCore = true;
    } else {
        htmlPlugins += rowHtml;
        addedPlugins = true;
    }
  });

  if (addedCore) htmlCore += '</details>';
  if (addedPlugins) htmlPlugins += '</details>';

  let html = '';
  if (addedCore) html += htmlCore;
  if (addedPlugins) html += htmlPlugins;

  cont.innerHTML = html || `<p style="color:var(--muted)">${I18N.no_plugins || 'No modules discovered'}</p>`;

  // Wire up parent toggles: cascade to children + live-update window.cfg + re-render tabs
  cont.querySelectorAll('[data-plugin]').forEach(parentCb => {
    parentCb.addEventListener('change', function() {
      const parentTag = this.dataset.plugin;
      const isOn = this.checked;

      // 1. Update live memory → triggers tab visibility refresh
      syncPluginStateToMemory(parentTag, isOn);

      // 2. Cascade visual disable to extension rows
      cont.querySelectorAll(`[data-extension="true"][data-parent="${parentTag}"]`).forEach(childCb => {
        childCb.disabled = !isOn;
        const row = childCb.closest('.plugin-row-extension');
        if (row) {
          row.style.opacity = isOn ? '' : '0.4';
          row.style.pointerEvents = isOn ? '' : 'none';
        }
      });
    });
  });

  // Wire up extension toggles: live-update window.cfg + re-render tabs
  cont.querySelectorAll('[data-extension="true"]').forEach(extCb => {
    extCb.addEventListener('change', function() {
      const parentTag = this.dataset.parent;
      const extId = this.dataset.extId;
      syncPluginStateToMemory(parentTag, this.checked, extId);
    });
  });
}


/**
 * Syncs a plugin/extension toggle change immediately into window.cfg
 * then re-renders the Hub so tabs appear/disappear without waiting for save.
 */
function syncPluginStateToMemory(tag, enabled, extId = null) {
    if (!window.cfg.plugins) window.cfg.plugins = {};
    window.cfg.plugins[tag] = window.cfg.plugins[tag] || {};

    if (extId) {
        // Extension state: plugins[parentTag].extensions[extId].enabled
        window.cfg.plugins[tag].extensions = window.cfg.plugins[tag].extensions || {};
        window.cfg.plugins[tag].extensions[extId] = window.cfg.plugins[tag].extensions[extId] || {};
        window.cfg.plugins[tag].extensions[extId].enabled = enabled;
    } else {
        // Parent plugin state
        window.cfg.plugins[tag].enabled = enabled;
    }

    if (typeof renderConfigHub === 'function') renderConfigHub();
}

function buildPayload() {
  const out = JSON.parse(JSON.stringify(window.cfg));
  out.backend        = out.backend        || {};
  out.backend.cloud  = out.backend.cloud  || {};
  out.backend.ollama = out.backend.ollama || {};
  out.backend.kobold = out.backend.kobold || {};

  try {
    out.backend.type                  = getV('backend-type') || 'cloud';
    out.backend.cloud.model           = getV('cloud-model');
    out.backend.cloud.temperature     = parseFloat(getV('cloud-temp')) || 0.7;
    out.backend.ollama.model          = getV('ollama-model');
    out.backend.ollama.temperature    = parseFloat(getV('ollama-temp')) || 0.3;
    out.backend.ollama.num_gpu        = parseInt(getV('ollama-gpu')) || 33;
    out.backend.ollama.num_predict    = parseInt(getV('ollama-predict')) || 1024;
    out.backend.ollama.num_ctx        = parseInt(getV('ollama-ctx')) || 4096;
    out.backend.ollama.top_p          = parseFloat(getV('ollama-top-p')) || 0.95;
    out.backend.ollama.repeat_penalty = parseFloat(getV('ollama-repeat')) || 1.1;
    out.backend.kobold.url            = getV('kobold-url');
    out.backend.kobold.model          = getV('kobold-model');
    out.backend.kobold.temperature    = parseFloat(getV('kobold-temp')) || 0.7;
    out.backend.kobold.max_length     = parseInt(getV('kobold-max')) || 512;
    out.backend.kobold.top_p          = parseFloat(getV('kobold-top-p')) || 0.95;
    out.backend.kobold.rep_pen        = parseFloat(getV('kobold-rep')) || 1.1;

    out.llm = out.llm || {};
    out.llm.allow_cloud = getC('llm-allow-cloud');
    out.llm.debug_llm = getC('llm-debug');
    out.llm.providers = out.llm.providers || {};
    ['openai','anthropic','groq','gemini'].forEach(p => {
      out.llm.providers[p] = out.llm.providers[p] || {};
      const rawM = getV('models-'+p).trim();
      if (rawM) out.llm.providers[p].models = rawM.split('\n').map(s=>s.trim()).filter(Boolean);
    });

    out.routing_engine = out.routing_engine || {};
    out.routing_engine.mode       = getV('route-mode') || 'auto';
    out.routing_engine.legacy_models = getV('route-models');

    out.ai = out.ai || {};
    const personaEl = document.getElementById('ia-personality-main');
                      
    if (personaEl) {
        out.ai.active_personality = personaEl.value;
    } else {
        // Urgent search for ANY select with personality
        const emergency = document.querySelector('select[id*="personality"]');
        if (emergency) {
            out.ai.active_personality = emergency.value;
        } else if (window.cfg && window.cfg.ai && window.cfg.ai.active_personality) {
            out.ai.active_personality = window.cfg.ai.active_personality;
        } else {
            out.ai.active_personality = 'Hecos_System_Soul.yaml';
        }
    }
    
    out.ai.avatar_size = getV('ia-avatar-size');
    out.ai.special_instructions      = getV('ia-instructions');
    out.ai.safety_instructions       = getV('ia-safety-instructions');
    out.ai.save_special_instructions = getC('ia-save-instructions');
    out.ai.enable_safety_instructions= getC('ia-enable-safety-instructions');
    out.ai.avatar_size               = getV('ia-avatar-size');
    out.privacy.default_mode = getV('pr-default-mode') || 'normal';
    out.privacy.auto_wipe_enabled = getC('pr-auto-wipe');
    out.privacy.incognito_shortcut = getC('pr-incognito-shortcut');

    out.bridge = out.bridge || {};
    out.bridge.use_processor        = getC('br-processor');
    out.bridge.remove_think_tags    = getC('br-think-tags');
    out.bridge.debug_log             = getC('br-debug');
    out.bridge.enable_tools         = getC('br-tools');
    out.bridge.webui_voice_stt        = getC('br-voice-stt');
    out.bridge.webui_voice_enabled = getC('br-voice-enabled');
    out.bridge.chunk_delay_ms      = parseInt(getV('br-delay')) || 0;

    out.filters = out.filters || {};
    out.filters.remove_asterisks       = getV('fl-ast');
    out.filters.remove_round_brackets  = getV('fl-tonde');
    out.filters.remove_square_brackets = getV('fl-quadre');
    
    if (window.HecosTextFilters) {
        out.filters.custom_filters = window.HecosTextFilters.extract();
    }

    // Dispatch to System Logic for its part of the payload
    if (typeof buildSystemPayload === 'function') {
        const sysPart = buildSystemPayload();
        out.logging = sysPart.logging;
        out.system = sysPart.system;
        out.language = sysPart.language;
        out.cognition = sysPart.cognition;
        
        // Handle SYS_NET Proxy via System Logic payload
        if (sysPart.plugins && sysPart.plugins.SYS_NET) {
           out.plugins['SYS_NET'] = out.plugins['SYS_NET'] || {};
           out.plugins['SYS_NET'].proxy_url = sysPart.plugins.SYS_NET.proxy_url;
        }
        
        // Handle WEB_UI HTTPS settings
        if (sysPart.plugins && sysPart.plugins.WEB_UI) {
           out.plugins['WEB_UI'] = out.plugins['WEB_UI'] || {};
           out.plugins['WEB_UI'].https_enabled = sysPart.plugins.WEB_UI.https_enabled;
        }
    }

    // Drive Plugin Payload
    const drivePart = buildDrivePayload();
    if (drivePart && drivePart.plugins && drivePart.plugins.DRIVE) {
        out.plugins['DRIVE'] = out.plugins['DRIVE'] || {};
        Object.assign(out.plugins['DRIVE'], drivePart.plugins.DRIVE);
    }

    document.querySelectorAll('[data-plugin]').forEach(cb => {
      const tag = cb.dataset.plugin;
      out.plugins[tag] = out.plugins[tag] || {};
      out.plugins[tag].enabled = cb.checked;
    });

    // Extension toggles: save as plugins[parentTag].extensions[extId].enabled
    document.querySelectorAll('[data-extension="true"]').forEach(cb => {
      const parentTag = cb.dataset.parent;
      const extId = cb.dataset.extId;
      if (!parentTag || !extId) return;
      out.plugins[parentTag] = out.plugins[parentTag] || {};
      out.plugins[parentTag].extensions = out.plugins[parentTag].extensions || {};
      out.plugins[parentTag].extensions[extId] = out.plugins[parentTag].extensions[extId] || {};
      out.plugins[parentTag].extensions[extId].enabled = cb.checked;
    });

    // Dashboard specialized toggles extraction
    if (document.getElementById('dashboard-webui-enabled')) {
        out.plugins['DASHBOARD'] = out.plugins['DASHBOARD'] || {};
        out.plugins['DASHBOARD'].webui_dashboard_enabled = getC('dashboard-webui-enabled');
        out.plugins['DASHBOARD'].webui_telemetry_enabled = getC('telemetry-webui-enabled');
        out.plugins['DASHBOARD'].console_dashboard_enabled = getC('dashboard-console-enabled');
        out.plugins['DASHBOARD'].console_telemetry_enabled = getC('telemetry-console-enabled');
    }

    // Remote Triggers Payload Part
    const rtPart = buildRemoteTriggersPayload();
    if (rtPart && rtPart.plugins && rtPart.plugins.REMOTE_TRIGGERS) {
        out.plugins['REMOTE_TRIGGERS'] = out.plugins['REMOTE_TRIGGERS'] || {};
        out.plugins['REMOTE_TRIGGERS'].settings = rtPart.plugins.REMOTE_TRIGGERS.settings;
    }


    const webuiPart = buildWebUIPayload();
    if (webuiPart.plugins && webuiPart.plugins.WEB_UI) {
        out.plugins['WEB_UI'] = out.plugins['WEB_UI'] || {};
        Object.assign(out.plugins['WEB_UI'], webuiPart.plugins.WEB_UI);
    }

    document.querySelectorAll('[data-plugin-lazy]').forEach(cb => {
      const tag = cb.dataset.pluginLazy;
      if (out.plugins[tag]) {
        out.plugins[tag].lazy_load = cb.checked;
      }
    });

    console.log("[PERSISTENCE-TRACE] buildPayload - FINAL AI BLOCK:", JSON.stringify(out.ai));
  } catch (err) { console.error("buildPayload err:", err); }

  return out;
}

function populateDriveUI() {
    const c = window.cfg;
    if (!c || !c.plugins || !c.plugins.DRIVE) return;
    const d = c.plugins.DRIVE;
    setVal('drive-root-dir', d.root_dir || '');
    setVal('drive-max-upload-mb', d.max_upload_mb ?? 100);
    setVal('drive-allowed-ext', d.allowed_extensions || '');

    const exts = d.extensions || {};
    
    // Editor
    const ed = exts.editor || {};
    setCheck('drive-editor-autosave', ed.autosave ?? false);
    setVal('drive-editor-autosave-interval', ed.autosave_interval ?? 30);
    setCheck('drive-editor-confirm-close', ed.confirm_close ?? true);
    setCheck('drive-editor-backup', ed.backup_on_save ?? false);
    setVal('drive-editor-theme', ed.theme || 'vs-dark');
    setVal('drive-editor-tab-size', ed.tab_size ?? 4);
    setCheck('drive-editor-line-numbers', ed.line_numbers ?? true);
    setCheck('drive-editor-word-wrap', ed.word_wrap ?? false);
    setCheck('drive-editor-minimap', ed.minimap ?? true);
    setVal('drive-editor-max-file-mb', ed.max_file_mb ?? 10);
    setVal('drive-editor-readonly-ext', ed.readonly_ext || '');

    // Media Viewer
    const mv = exts.media_viewer || {};
    setVal('drive-viewer-default-zoom', mv.default_zoom || 'fit');
    setCheck('drive-viewer-show-exif', mv.show_exif ?? false);
    setCheck('drive-viewer-slideshow', mv.slideshow ?? false);
    setVal('drive-viewer-slideshow-interval', mv.slideshow_interval ?? 5);
    setCheck('drive-viewer-video-autoplay', mv.video_autoplay ?? false);
    setCheck('drive-viewer-video-loop', mv.video_loop ?? false);
    setCheck('drive-viewer-video-controls', mv.video_controls ?? true);
    setCheck('drive-viewer-audio-autoplay', mv.audio_autoplay ?? false);
    setCheck('drive-viewer-audio-waveform', mv.audio_waveform ?? true);
    setVal('drive-viewer-image-ext', mv.image_ext || 'jpg,jpeg,png,gif,webp,svg,bmp,ico');
    setVal('drive-viewer-video-ext', mv.video_ext || 'mp4,webm,mkv,avi,mov');
    setVal('drive-viewer-audio-ext', mv.audio_ext || 'mp3,ogg,wav,flac,aac,m4a');
}

function buildDrivePayload() {
    const rootEl = document.getElementById('drive-root-dir');
    if (!rootEl) return {}; // Not in DOM
    const c = window.cfg && window.cfg.plugins && window.cfg.plugins.DRIVE ? window.cfg.plugins.DRIVE : {};
    const exts = c.extensions || {};
    const newExts = JSON.parse(JSON.stringify(exts));

    if (document.getElementById('drive-editor-theme')) {
        newExts.editor = Object.assign({}, newExts.editor, {
            autosave: document.getElementById('drive-editor-autosave').checked,
            autosave_interval: parseInt(document.getElementById('drive-editor-autosave-interval').value) || 30,
            confirm_close: document.getElementById('drive-editor-confirm-close').checked,
            backup_on_save: document.getElementById('drive-editor-backup').checked,
            theme: document.getElementById('drive-editor-theme').value || 'vs-dark',
            tab_size: parseInt(document.getElementById('drive-editor-tab-size').value) || 4,
            line_numbers: document.getElementById('drive-editor-line-numbers').checked,
            word_wrap: document.getElementById('drive-editor-word-wrap').checked,
            minimap: document.getElementById('drive-editor-minimap').checked,
            max_file_mb: parseInt(document.getElementById('drive-editor-max-file-mb').value) || 10,
            readonly_ext: document.getElementById('drive-editor-readonly-ext').value
        });
    }

    if (document.getElementById('drive-viewer-default-zoom')) {
        newExts.media_viewer = Object.assign({}, newExts.media_viewer, {
            default_zoom: document.getElementById('drive-viewer-default-zoom').value || 'fit',
            show_exif: document.getElementById('drive-viewer-show-exif').checked,
            slideshow: document.getElementById('drive-viewer-slideshow').checked,
            slideshow_interval: parseInt(document.getElementById('drive-viewer-slideshow-interval').value) || 5,
            video_autoplay: document.getElementById('drive-viewer-video-autoplay').checked,
            video_loop: document.getElementById('drive-viewer-video-loop').checked,
            video_controls: document.getElementById('drive-viewer-video-controls').checked,
            audio_autoplay: document.getElementById('drive-viewer-audio-autoplay').checked,
            audio_waveform: document.getElementById('drive-viewer-audio-waveform').checked,
            image_ext: document.getElementById('drive-viewer-image-ext').value,
            video_ext: document.getElementById('drive-viewer-video-ext').value,
            audio_ext: document.getElementById('drive-viewer-audio-ext').value
        });
    }

    return {
        plugins: {
            DRIVE: {
                root_dir: rootEl.value.trim(),
                max_upload_mb: parseInt(document.getElementById('drive-max-upload-mb').value) || 100,
                allowed_extensions: document.getElementById('drive-allowed-ext').value.trim(),
                extensions: newExts
            }
        }
    };
}

function populateRemoteTriggersUI() {
    const c = window.cfg;
    if (!c || !c.plugins || !c.plugins.REMOTE_TRIGGERS) return;
    const settings = c.plugins.REMOTE_TRIGGERS.settings || {};
    setCheck('rt-enable-mediasession', settings.enable_mediasession ?? true);
    setCheck('rt-enable-volume-keys', settings.enable_volume_keys ?? true);
    setCheck('rt-enable-volume-loop', settings.enable_volume_loop ?? false);
    setCheck('rt-feedback-sounds', settings.feedback_sounds ?? true);
    setCheck('rt-visual-indicator', settings.visual_indicator ?? true);
}

function buildRemoteTriggersPayload() {
    const el = document.getElementById('rt-enable-mediasession');
    if (!el) return {};
    return {
        plugins: {
            REMOTE_TRIGGERS: {
                settings: {
                    enable_mediasession: document.getElementById('rt-enable-mediasession').checked,
                    enable_volume_keys: document.getElementById('rt-enable-volume-keys').checked,
                    enable_volume_loop: document.getElementById('rt-enable-volume-loop').checked,
                    feedback_sounds: document.getElementById('rt-feedback-sounds').checked,
                    visual_indicator: document.getElementById('rt-visual-indicator').checked
                }
            }
        }
    };
}



function populateWebUIConfig() {
    const c = window.cfg;
    if (!c || !c.plugins || !c.plugins.WEB_UI) return;
    const w = c.plugins.WEB_UI;
    setVal('webui-port', w.port || 8080);
    setVal('webui-api-port', w.api_port || 5000);
    setCheck('webui-force-login', w.force_login ?? true);
}

function buildWebUIPayload() {
    const el = document.getElementById('webui-port');
    if (!el) return {};
    return {
        plugins: {
            WEB_UI: {
                port: parseInt(el.value) || 8080,
                api_port: parseInt(document.getElementById('webui-api-port').value) || 5000,
                force_login: document.getElementById('webui-force-login').checked
            }
        }
    };
}

function isRestartNeeded() {
  return document.querySelectorAll('.restart-badge.visible').length > 0;
}


function populatePrivacyUI() {
    const c = window.cfg;
    if (!c || !c.privacy) return;
    setVal('pr-default-mode', c.privacy.default_mode || 'normal');
    setCheck('pr-auto-wipe', c.privacy.auto_wipe_enabled ?? false);
    setCheck('pr-incognito-shortcut', c.privacy.incognito_shortcut ?? true);
}

// Global Exports
window.populateSelect = populateSelect;
window.populateUI = populateUI;
window.setVal = setVal;
window.setCheck = setCheck;
window.renderPlugins = renderPlugins;
window.buildPayload = buildPayload;
window.isRestartNeeded = isRestartNeeded;
window.populatePrivacyUI = populatePrivacyUI;

window.saveDsb = function(key, val) {
    if (!window.cfg.plugins) window.cfg.plugins = {};
    if (!window.cfg.plugins.DASHBOARD) window.cfg.plugins.DASHBOARD = {};
    window.cfg.plugins.DASHBOARD[key] = val;
    
    // Trigger immediate UI update (hiding/showing status bar/telemetry)
    if (typeof window.refreshStatus === 'function') window.refreshStatus();
    
    // We let the global change listener in config_core.js handle the actual saveConfig(true)
};

// --- CUSTOM TEXT FILTERS HANDLER ---
window.HecosTextFilters = {
    populate: function(filters) {
        const container = document.getElementById('custom-filters-container');
        if (!container) return;
        container.innerHTML = '';
        if (Array.isArray(filters)) {
            filters.forEach(f => this.addPlaceholderRow(f.find, f.replace, f.target));
        }
    },
    extract: function() {
        const container = document.getElementById('custom-filters-container');
        if (!container) return [];
        const results = [];
        container.querySelectorAll('.custom-filter-row').forEach(row => {
            const find = row.querySelector('.cf-find').value;
            if (!find) return;
            const replace = row.querySelector('.cf-replace').value || '';
            const target = row.querySelector('.cf-target').value || 'both';
            results.push({ find, replace, target });
        });
        return results;
    },
    removeRow: function(btn) {
        if (!btn || !btn.parentElement) return;
        btn.parentElement.remove();
        // Trigger auto-save immediately
        if (typeof window.saveConfig === 'function') {
            window.saveConfig(true);
        }
    },
    addPlaceholderRow: function(find = '', replace = '', target = 'both') {
        const container = document.getElementById('custom-filters-container');
        if (!container) return;
        const div = document.createElement('div');
        div.className = 'custom-filter-row';
        div.style.display = 'flex';
        div.style.gap = '8px';
        div.style.alignItems = 'center';
        
        div.innerHTML = `
            <input type="text" class="config-input cf-find" placeholder="Find..." value="${find.replace(/"/g, '&quot;')}" style="flex: 2; padding:4px 8px; font-size:12px;">
            <input type="text" class="config-input cf-replace" placeholder="Replace..." value="${replace.replace(/"/g, '&quot;')}" style="flex: 2; padding:4px 8px; font-size:12px;">
            <select class="config-input cf-target" style="flex: 1.5; padding:4px 8px; font-size:12px;">
                <option value="both" ${target === 'both' ? 'selected' : ''}>Voice & Text</option>
                <option value="voice" ${target === 'voice' ? 'selected' : ''}>Voice Only</option>
                <option value="text" ${target === 'text' ? 'selected' : ''}>Text Only</option>
            </select>
            <button type="button" class="btn" onclick="HecosTextFilters.removeRow(this)" style="padding: 4px 8px; font-size: 10px; background: rgba(255,50,50,0.2); color:#ff5555;">X</button>
        `;
        container.appendChild(div);
    }
};
