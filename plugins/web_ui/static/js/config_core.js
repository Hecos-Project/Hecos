/**
 * Zentra Core WebUI - Core Configuration Logic
 * Handles initialization, global state, and shared utilities.
 */

let cfg = {};
let sysOptions = {};
let audioDevices = null;
let audioConfig = null;
let mediaConfig = null;
let isInitialLoading = false;


const I18N = window.I18N || {};

/**
 * Tab switching logic
 */
function showTab(name) {
  document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  const panel = document.getElementById('tab-' + name);
  if (panel) panel.classList.add('active');
  if (event && event.target && event.target.classList.contains('tab')) {
    event.target.classList.add('active');
  }
}

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

/**
 * Master Initialization
 */
async function initAll() {
  isInitialLoading = true;
  console.log("Initializing Configuration...");
  const start = Date.now();
  setSaveMsg(I18N.msg_loading || 'Loading...', 'muted');

  try {
    const [rOpts, rCfg, rAudio, rAudioCfg, rMediaCfg] = await Promise.all([
      fetch('/zentra/options'),
      fetch('/zentra/config'),
      fetch('/api/audio/devices'),
      fetch('/api/audio/config'),
      fetch('/zentra/api/config/media')
    ]);
    
    sysOptions = await rOpts.json();
    cfg = await rCfg.json();
    
    try {
        const acData = await rAudioCfg.json();
        if (acData.ok) audioConfig = acData.config;
    } catch(e) { console.warn("Could not load audio config:", e); }
    
    try {
        mediaConfig = await rMediaCfg.json();
    } catch(e) { console.warn("Could not load media config:", e); }
    
    try {
        const adData = await rAudio.json();
        if (adData.ok) audioDevices = adData;
    } catch(e) { console.warn("Could not load audio devices array:", e); }
    
    console.log("Config loaded in " + (Date.now() - start) + "ms");
    populateUI();
    
    const now = new Date().toLocaleTimeString();
    setSaveMsg((I18N.msg_synced || 'Synced') + ' (' + now + ')', 'ok');
    console.log("UI populated in total " + (Date.now() - start) + "ms");
    isInitialLoading = false;
    setTimeout(() => { if (document.getElementById('save-msg').textContent.includes(now)) setSaveMsg('', ''); }, 5000);

  } catch(e) {
    console.error("Init error:", e);
    setSaveMsg((I18N.msg_err || 'Error') + ': ' + e, 'err');
  }
}

/**
 * Dispatches UI population to all modules
 */
function populateUI() {
  try {
    const c = cfg;
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
    setVal('ia-instructions', c.ai?.special_instructions || '');
    setCheck('ia-save-instructions', c.ai?.save_special_instructions || false);

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

    renderPlugins(c.plugins || {});
    console.log("UI Populated successfully.");
  } catch (err) {
    console.error("UI Population failed:", err);
  }
}

function setVal(id, val) { const el = document.getElementById(id); if (el) el.value = val; }
function setCheck(id, val) { const el = document.getElementById(id); if (el) el.checked = val; }

function renderPlugins(plugins) {
  const cont = document.getElementById('plugin-list');
  if (!cont) return;
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
    IMAGE_GEN:   'Generazione Immagini AI (Pollinations)'
  };
  let html = '';
  for (const [tag, pCfg] of Object.entries(plugins)) {
    const on = pCfg.enabled !== false;
    html += `<div class="plugin-row">
      <div><div class="plugin-name">${tag}</div>${descs[tag] ? `<div class="plugin-desc">${descs[tag]}</div>` : ''}</div>
      <label class="switch"><input type="checkbox" data-plugin="${tag}" ${on?'checked':''} onchange="saveConfig(true)"><span class="slider"></span></label>
    </div>`;
  }
  cont.innerHTML = html || `<p style="color:var(--muted)">${I18N.no_plugins || 'No plugins'}</p>`;
}

async function saveConfig(silent = false) {
  if (isInitialLoading) return;
  if (!silent) setSaveMsg(I18N.msg_saving || 'Saving...', 'muted');
  try {
    const payload = buildPayload();

    const audioPayload = (typeof buildAudioPayload === 'function') ? buildAudioPayload() : {};
    const mediaPayload = (typeof buildMediaPayload === 'function') ? buildMediaPayload() : {};
    
    const [resCfg, resAud, resMed] = await Promise.all([
        fetch('/zentra/config', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        }),
        fetch('/api/audio/config', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(audioPayload)
        }),
        fetch('/zentra/api/config/media', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(mediaPayload)
        })
    ]);
    
    const data = await resCfg.json();
    const audData = await resAud.json();
    const medData = await resMed.json();
    
    if (data.ok && audData.ok && medData.ok) {
      if (!silent) {
          setSaveMsg(I18N.msg_saved || 'Saved', 'ok');
          setTimeout(() => location.reload(), 1500);
      }
    } else {
      setSaveMsg('Error saving config.', 'err');
    }
  } catch (e) {
    setSaveMsg('Fetch error: ' + e, 'err');
  }
}

function buildPayload() {
  const out = JSON.parse(JSON.stringify(cfg));
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
    out.ai.special_instructions = document.getElementById('ia-instructions').value;
    out.ai.save_special_instructions = document.getElementById('ia-save-instructions').checked;

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
    }

    document.querySelectorAll('[data-plugin]').forEach(cb => {
      const tag = cb.dataset.plugin;
      out.plugins[tag] = out.plugins[tag] || {};
      out.plugins[tag].enabled = cb.checked;
    });

  } catch (err) { console.error("buildPayload err:", err); }


  return out;
}

function setSaveMsg(msg, type) {
  const el = document.getElementById('save-msg');
  if (!el) return;
  el.textContent = msg;
  el.style.color = type === 'ok' ? 'var(--green)' : type === 'err' ? 'var(--red)' : 'var(--muted)';
}

async function refreshStatus() {
  try {
    const r = await fetch('/zentra/status');
    const d = await r.json();
    setSpanText('s-backend', d.backend || '—');
    setSpanText('s-model', d.model || '—');
    setSpanText('s-bridge', d.bridge || '—');
    setSpanText('s-mic', d.mic || '—');
    setSpanText('s-tts', d.tts || '—');
    setSpanText('s-config', d.config || '—');
    setSpanText('hdr-model', d.model || (I18N.offline || 'Offline'));
    
    const m = document.getElementById('s-model');
    if (m) m.className = 'stat-val ' + (d.model && d.model !== '—' ? 'val-ok' : 'val-warn');
  } catch(e) {
    setSpanText('hdr-model', I18N.offline || 'Offline');
  }
}

function setSpanText(id, text) { const el = document.getElementById(id); if (el) el.textContent = text; }

async function rebootSystem() {
  setSaveMsg('Rebooting...', 'err');
  try {
    const res = await fetch("/api/system/reboot", { method: "POST" });
    if (res.ok) {
       console.log("Reboot command sent.");
       setTimeout(() => { location.reload(); }, 5000);
    } else {
       const err = await res.json();
       setSaveMsg("Reboot error: " + (err.error || "Unknown"), 'err');
    }
  } catch (e) {
    setSaveMsg("Network error during reboot", 'err');
  }
}

function escapeHtml(text) {
  const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
  return (text || '').replace(/[&<>"']/g, m => map[m]);
}

// Global Exports
window.showTab = showTab;
window.initAll = initAll;
window.saveConfig = saveConfig;
window.refreshStatus = refreshStatus;
window.rebootSystem = rebootSystem;
window.populateSelect = populateSelect;
// --- Event Listeners (Global/Core) ---

// Listen for global checkbox/select changes for auto-saving
document.addEventListener('change', (e) => {
  if (e.target.type === 'checkbox' || e.target.tagName === 'SELECT') {
    // Sync Image Gen enabled status between different UI locations
    if (e.target.id === 'igen-enabled') {
        const other = document.querySelector('[data-plugin="IMAGE_GEN"]');
        if (other) other.checked = e.target.checked;
    } else if (e.target.dataset.plugin === 'IMAGE_GEN') {
        const other = document.getElementById('igen-enabled');
        if (other) other.checked = e.target.checked;
    }
    
    // Auto-stop voice if toggle is turned off
    if (e.target.id === 'sys-voice-status' && !e.target.checked) {
       if (typeof stopVoice === 'function') stopVoice();
    }
    
    saveConfig(true);
  }
});

// Handle Backend Type card switching
document.addEventListener('DOMContentLoaded', () => {
    const backendTypeEl = document.getElementById('backend-type');
    if (backendTypeEl) {
        backendTypeEl.addEventListener('change', function() {
          const v = this.value;
          const cardCloud = document.getElementById('card-cloud');
          const cardOllama = document.getElementById('card-ollama');
          const cardKobold = document.getElementById('card-kobold');
          if (cardCloud) cardCloud.style.display  = v === 'cloud'  ? '' : 'none';
          if (cardOllama) cardOllama.style.display = v === 'ollama' ? '' : 'none';
          if (cardKobold) cardKobold.style.display = v === 'kobold' ? '' : 'none';
        });
    }
});

window.setVal = setVal;
window.setCheck = setCheck;

