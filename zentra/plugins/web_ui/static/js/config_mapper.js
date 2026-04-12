// config_mapper.js
// Extracts DOM mapping and Payload Building from config_core.js

const RESTART_FIELDS = [
  'system-port',
  'system-api-port',
  'sys-https-enabled'
];

/**
 * Utility to populate a <select> element
 */
function populateSelect(id, list, currentValue, isFilenameOnly = false) {
  const el = document.getElementById(id);
  if (!el) return;
  el.innerHTML = '';
  if (!Array.isArray(list)) list = [];
  
  let cleanValue = currentValue;
  if (isFilenameOnly && currentValue && (currentValue.includes('\\') || currentValue.includes('/'))) {
    cleanValue = currentValue.split(/[\\/]/).pop();
  }

  list.forEach(item => {
    const opt = document.createElement('option');
    const shortItem = (isFilenameOnly && (item.includes('\\') || item.includes('/'))) ? item.split(/[\\/]/).pop() : item;
    
    opt.value = item;
    opt.textContent = shortItem;
    if (cleanValue && (item === cleanValue || item.endsWith(cleanValue))) opt.selected = true;
    el.appendChild(opt);
  });
}

function setVal(id, val) { const el = document.getElementById(id); if (el) el.value = val; }
function setCheck(id, val) { const el = document.getElementById(id); if (el) el.checked = val; }

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
      setVal('key-'+p, prov[p]?.api_key || '');
      setVal('models-'+p, (prov[p]?.models || []).join('\n'));
    });

    const rm = c.routing_engine || {};
    setVal('route-mode', rm.mode || 'auto');
    setVal('route-models', rm.legacy_models || '');

    populateSelect('ia-personality', sysOptions.personalities || [], c.ai?.active_personality, true);
    setVal('ia-avatar-size', c.ai?.avatar_size || 'medium');
    setVal('ia-instructions', c.ai?.special_instructions || '');
    setCheck('ia-save-instructions', c.ai?.save_special_instructions || false);

    setCheck('ia-roleplay-mode', c.ai?.roleplay_mode || false);
    setVal('ia-roleplay-disclaimer', c.ai?.roleplay_disclaimer || '');
    
    // Load the avatar preview for the currently selected persona
    if (typeof window.loadPersonaAvatar === 'function') {
        const personaEl = document.getElementById('ia-personality');
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
    setCheck('fl-ast', fi.remove_asterisks ?? false);
    setCheck('fl-tonde', fi.remove_round_brackets ?? false);
    setCheck('fl-quadre', fi.remove_square_brackets ?? false);

    // 2. Audio Module Dispatch
    if (typeof populateAudioUI === 'function') populateAudioUI();

    // 3. System Module Dispatch
    if (typeof populateSystemUI === 'function') populateSystemUI();

    // 4. Media Module Dispatch
    if (typeof populateMediaUI === 'function') populateMediaUI();
    
    // 5. Drive Module Dispatch
    populateDriveUI();

    // 6. Remote Triggers Dispatch
    populateRemoteTriggersUI();

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
  const I18N = window.I18N || {};
  const descs = {
    DASHBOARD:   I18N.plugin_desc_dashboard,
    FILE_MANAGER:I18N.plugin_desc_file,
    HELP:        I18N.plugin_desc_help,
    MEDIA:       I18N.plugin_desc_media,
    ROLEPLAY:    I18N.plugin_desc_roleplay,
    SYSTEM:      I18N.plugin_desc_system,
    WEB:         I18N.plugin_desc_web,
    WEBCAM:      I18N.plugin_desc_webcam,
    WEB_UI:      I18N.plugin_desc_webui,
    IMAGE_GEN:   'Generazione Immagini AI (Pollinations)',
    DRIVE:       I18N.webui_conf_plugin_desc_drive || 'Gestore File HTTP (Zentra Drive)',
    REMOTE_TRIGGERS: 'PTT via Media Keys (iPhone), Bluetooth & Webhooks',
    MCP_BRIDGE:  'Universal Protocol Hub (Connect external AI tools via MCP)'
  };
  let html = '';
  for (const [tag, pCfg] of Object.entries(plugins)) {
    const on = pCfg.enabled !== false;
    const lazyOn = pCfg.lazy_load === true;
    html += `<div class="plugin-row">
      <div><div class="plugin-name">${tag} <label style="font-size:10px; color:var(--muted); margin-left:10px; cursor:pointer;" title="Abilita Lazy Loading"><input type="checkbox" data-plugin-lazy="${tag}" ${lazyOn?'checked':''} style="vertical-align:middle"> Lazy</label></div>${descs[tag] ? `<div class="plugin-desc">${descs[tag]}</div>` : ''}</div>
      <label class="switch"><input type="checkbox" data-plugin="${tag}" ${on?'checked':''}><span class="slider"></span></label>
    </div>`;
  }
  cont.innerHTML = html || `<p style="color:var(--muted)">${I18N.no_plugins || 'No plugins'}</p>`;
}

function buildPayload() {
  const out = JSON.parse(JSON.stringify(window.cfg));
  out.backend        = out.backend        || {};
  out.backend.cloud  = out.backend.cloud  || {};
  out.backend.ollama = out.backend.ollama || {};
  out.backend.kobold = out.backend.kobold || {};

  try {
    out.backend.type                  = document.getElementById('backend-type').value;
    out.backend.cloud.model           = document.getElementById('cloud-model').value;
    out.backend.cloud.temperature     = parseFloat(document.getElementById('cloud-temp').value) || 0.7;
    out.backend.ollama.model          = document.getElementById('ollama-model').value;
    out.backend.ollama.temperature    = parseFloat(document.getElementById('ollama-temp').value) || 0.3;
    out.backend.ollama.num_gpu        = parseInt(document.getElementById('ollama-gpu').value) || 33;
    out.backend.ollama.num_predict    = parseInt(document.getElementById('ollama-predict').value) || 1024;
    out.backend.ollama.num_ctx        = parseInt(document.getElementById('ollama-ctx').value) || 4096;
    out.backend.ollama.top_p          = parseFloat(document.getElementById('ollama-top-p').value) || 0.95;
    out.backend.ollama.repeat_penalty = parseFloat(document.getElementById('ollama-repeat').value) || 1.1;
    out.backend.kobold.url            = document.getElementById('kobold-url').value;
    out.backend.kobold.model          = document.getElementById('kobold-model').value;
    out.backend.kobold.temperature    = parseFloat(document.getElementById('kobold-temp').value) || 0.7;
    out.backend.kobold.max_length     = parseInt(document.getElementById('kobold-max').value) || 512;
    out.backend.kobold.top_p          = parseFloat(document.getElementById('kobold-top-p').value) || 0.95;
    out.backend.kobold.rep_pen        = parseFloat(document.getElementById('kobold-rep').value) || 1.1;

    out.llm = out.llm || {};
    out.llm.allow_cloud = document.getElementById('llm-allow-cloud').checked;
    out.llm.debug_llm = document.getElementById('llm-debug').checked;
    out.llm.providers = out.llm.providers || {};
    ['openai','anthropic','groq','gemini'].forEach(p => {
      out.llm.providers[p] = out.llm.providers[p] || {};
      const k = document.getElementById('key-'+p).value.trim();
      if (k) out.llm.providers[p].api_key = k;
      const rawM = document.getElementById('models-'+p).value.trim();
      if (rawM) out.llm.providers[p].models = rawM.split('\n').map(s=>s.trim()).filter(Boolean);
    });

    out.routing_engine = out.routing_engine || {};
    out.routing_engine.mode       = document.getElementById('route-mode').value;
    out.routing_engine.legacy_models = document.getElementById('route-models').value;

    out.ai = out.ai || {};
    out.ai.active_personality = document.getElementById('ia-personality').value;
    out.ai.avatar_size = document.getElementById('ia-avatar-size').value;
    out.ai.special_instructions = document.getElementById('ia-instructions').value;
    out.ai.save_special_instructions = document.getElementById('ia-save-instructions').checked;
    out.ai.roleplay_mode = document.getElementById('ia-roleplay-mode').checked;
    out.ai.roleplay_disclaimer = document.getElementById('ia-roleplay-disclaimer').value;

    out.bridge = out.bridge || {};
    out.bridge.use_processor        = document.getElementById('br-processor').checked;
    out.bridge.remove_think_tags    = document.getElementById('br-think-tags').checked;
    out.bridge.debug_log             = document.getElementById('br-debug').checked;
    out.bridge.enable_tools         = document.getElementById('br-tools').checked;
    out.bridge.webui_voice_stt        = document.getElementById('br-voice-stt').checked;
    out.bridge.webui_voice_enabled = document.getElementById('br-voice-enabled').checked;
    out.bridge.chunk_delay_ms      = parseInt(document.getElementById('br-delay').value);

    out.filters = out.filters || {};
    out.filters.remove_asterisks       = document.getElementById('fl-ast').checked;
    out.filters.remove_round_brackets  = document.getElementById('fl-tonde').checked;
    out.filters.remove_square_brackets = document.getElementById('fl-quadre').checked;

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

    // Remote Triggers Payload Part
    const rtPart = buildRemoteTriggersPayload();
    if (rtPart && rtPart.plugins && rtPart.plugins.REMOTE_TRIGGERS) {
        out.plugins['REMOTE_TRIGGERS'] = out.plugins['REMOTE_TRIGGERS'] || {};
        out.plugins['REMOTE_TRIGGERS'].settings = rtPart.plugins.REMOTE_TRIGGERS.settings;
    }

    document.querySelectorAll('[data-plugin-lazy]').forEach(cb => {
      const tag = cb.dataset.pluginLazy;
      if (out.plugins[tag]) {
        out.plugins[tag].lazy_load = cb.checked;
      }
    });

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
}

function buildDrivePayload() {
    const rootEl = document.getElementById('drive-root-dir');
    if (!rootEl) return {}; // Not in DOM
    return {
        plugins: {
            DRIVE: {
                root_dir: rootEl.value.trim(),
                max_upload_mb: parseInt(document.getElementById('drive-max-upload-mb').value) || 100,
                allowed_extensions: document.getElementById('drive-allowed-ext').value.trim()
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

function isRestartNeeded() {
  return document.querySelectorAll('.restart-badge.visible').length > 0;
}

// Global Exports
window.populateSelect = populateSelect;
window.populateUI = populateUI;
window.setVal = setVal;
window.setCheck = setCheck;
window.renderPlugins = renderPlugins;
window.buildPayload = buildPayload;
window.isRestartNeeded = isRestartNeeded;
