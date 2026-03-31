let cfg = {};
let sysOptions = {};
let audioDevices = null;
let audioConfig = null;
let mediaConfig = null;

const I18N = window.I18N || {};

function showTab(name) {
  document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.getElementById('tab-' + name).classList.add('active');
  if (event && event.target) event.target.classList.add('active');
}

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

async function initAll() {
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
    setTimeout(() => { if (document.getElementById('save-msg').textContent.includes(now)) setSaveMsg('', ''); }, 5000);
  } catch(e) {
    console.error("Init error:", e);
    setSaveMsg((I18N.msg_err || 'Error') + ': ' + e, 'err');
  }
}

function populateUI() {
  try {
    const c = cfg;
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
    setVal('key-openai', prov.openai?.api_key || '');
    setVal('key-anthropic', prov.anthropic?.api_key || '');
    setVal('key-groq', prov.groq?.api_key || '');
    setVal('key-gemini', prov.gemini?.api_key || '');
    setVal('models-openai', (prov.openai?.models || []).join('\n'));
    setVal('models-anthropic', (prov.anthropic?.models || []).join('\n'));
    setVal('models-groq', (prov.groq?.models || []).join('\n'));
    setVal('models-gemini', (prov.gemini?.models || []).join('\n'));

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

    setCheck('sys-mic-status', (audioConfig || {}).listening_status ?? false);
    setCheck('sys-voice-status', (audioConfig || {}).voice_status ?? false);
    
    setVal('stt-source', (audioConfig || {}).stt_source || 'system');
    setVal('tts-destination', (audioConfig || {}).tts_destination || 'web');

    const v = audioConfig || {};
    setVal('v-piper', v.piper_path || '');
    const curOnnx = (v.onnx_model || '').split('\\').pop().split('/').pop();
    populateSelect('v-onnx-model', sysOptions.piper_voices || [], curOnnx, true);
    setVal('v-speed', v.speed ?? 1.2);
    setVal('v-noise', v.noise_scale ?? 0.817);
    setVal('v-noisew', v.noise_w ?? 0.9);
    setVal('v-silence', v.sentence_silence ?? 0.1);

    const a = audioConfig || {};
    setVal('a-threshold', a.energy_threshold ?? 450);
    setVal('a-timeout', a.silence_timeout ?? 5);
    setVal('a-limit', a.phrase_limit ?? 15);

    if (audioDevices) {
        const inSel = document.getElementById('audio-input-device');
        const outSel = document.getElementById('audio-output-device');
        if (inSel) {
            inSel.innerHTML = '';
            (audioDevices.input_devices || []).forEach(d => {
                const opt = document.createElement('option');
                opt.value = d.index;
                opt.textContent = `${d.index}: ${d.name}`;
                if (d.index === audioDevices.selected_input_index) opt.selected = true;
                inSel.appendChild(opt);
            });
        }
        if (outSel) {
            outSel.innerHTML = '';
            (audioDevices.output_devices || []).forEach(d => {
                const opt = document.createElement('option');
                opt.value = d.index;
                opt.textContent = `${d.index}: ${d.name}`;
                if (d.index === audioDevices.selected_output_index) opt.selected = true;
                outSel.appendChild(opt);
            });
        }
    }

    const slg = c.logging || {};
    setVal('log-level', slg.level || 'INFO');
    setVal('log-type', slg.message_types || 'both');
    setVal('log-dest', slg.destination || 'console');

    setVal('web-log-level', slg.web_level || 'BOTH');
    setVal('web-log-max', slg.web_max_history || 500);
    setCheck('web-log-autoscroll', slg.web_autoscroll !== false);
    setCheck('web-log-split', slg.web_split === true);
    toggleLogSplit();

    const sys = c.system || {};
    setCheck('sys-fastboot', sys.fast_boot ?? false);
    setCheck('sys-flask-debug', sys.flask_debug ?? false);
    setVal('sys-language', c.language || 'en');

    const sysNet = (c.plugins || {}).SYS_NET || {};
    if (typeof restoreProxyFields === 'function') {
      restoreProxyFields(sysNet.proxy_url || '');
    } else {
      setVal('sys-proxy-url', sysNet.proxy_url || '');
    }

    const cog = c.cognition || {};
    setCheck('cog-memory-enabled', cog.memory_enabled ?? true);
    setCheck('cog-episodic', cog.episodic_memory ?? true);
    setCheck('cog-clear-restart', cog.clear_on_restart ?? false);
    setCheck('cog-identity', cog.include_identity_context ?? true);
    setCheck('cog-awareness', cog.include_self_awareness ?? true);
    setVal('cog-max-history', cog.max_history_messages ?? 20);

    const igen = (mediaConfig && mediaConfig.image_gen) ? mediaConfig.image_gen : {};

    // --- Dynamic Image Providers Population ---
    const imgProvSelect = document.getElementById('igen-provider');
    if (imgProvSelect && c.llm && c.llm.providers) {
        imgProvSelect.innerHTML = '';
        const globalProviders = Object.keys(c.llm.providers);
        globalProviders.push("ollama");
        const extraImageProviders = ["pollinations", "airforce", "stability", "gemini_native"];
        
        // Merge without duplicates
        const allSet = new Set([...globalProviders, ...extraImageProviders]);
        
        const labels = {
            "pollinations": "Pollinations.ai (Free)",
            "airforce": "Airforce API (Free/Experimental)",
            "gemini": "Google Gemini Imagen",
            "gemini_native": "Google Gemini (Studio Multi-Modality)",
            "openai": "OpenAI DALL-E",
            "stability": "Stability.ai",
            "groq": "Groq (Testo - Non supporta immagini)",
            "anthropic": "Anthropic (Testo - Non supporta immagini)",
            "ollama": "Ollama (Testo - Non supporta immagini)",
            "lmstudio": "LM Studio (Testo - Non supporta immagini)"
        };

        allSet.forEach(prov => {
            const opt = document.createElement('option');
            opt.value = prov;
            opt.textContent = labels[prov] || (prov.charAt(0).toUpperCase() + prov.slice(1));
            imgProvSelect.appendChild(opt);
        });
    }

    setCheck('igen-enabled', igen.enabled !== false);
    setVal('igen-provider', igen.provider || 'pollinations');
    setVal('igen-width', igen.width  || 1024);
    setVal('igen-height', igen.height || 1024);
    setCheck('igen-nologo', igen.nologo ?? true);
    setVal('igen-apikey', igen.api_key || '');
    refreshImageModels(igen.model || 'flux');
    onProviderChanged();

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
    out.backend.ollama.temperature    = parseFloat(document.getElementById('ollama-temp').value) || 0.7;
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

  out.logging = {
    level: document.getElementById('log-level').value,
    destination: document.getElementById('log-dest').value,
    message_types: document.getElementById('log-type').value,
    web_level: document.getElementById('web-log-level').value,
    web_max_history: parseInt(document.getElementById('web-log-max').value),
    web_autoscroll: document.getElementById('web-log-autoscroll').checked,
    web_split: document.getElementById('web-log-split').checked
  };

  out.system = out.system || {};
  out.system.fast_boot = document.getElementById('sys-fastboot').checked;
  out.system.flask_debug = document.getElementById('sys-flask-debug').checked;
  out.language  = document.getElementById('sys-language').value;

  out.cognition = {
    memory_enabled:          document.getElementById('cog-memory-enabled').checked,
    episodic_memory:         document.getElementById('cog-episodic').checked,
    clear_on_restart:        document.getElementById('cog-clear-restart').checked,
    include_identity_context:document.getElementById('cog-identity').checked,
    include_self_awareness:  document.getElementById('cog-awareness').checked,
    max_history_messages:    parseInt(document.getElementById('cog-max-history').value) || 20
  };

  document.querySelectorAll('[data-plugin]').forEach(cb => {
    const tag = cb.dataset.plugin;
    out.plugins[tag] = out.plugins[tag] || {};
    out.plugins[tag].enabled = cb.checked;
  });

  const proxyEl = document.getElementById('sys-proxy-url');
  if (proxyEl) {
    out.plugins['SYS_NET'] = out.plugins['SYS_NET'] || {};
    out.plugins['SYS_NET'].proxy_url = proxyEl.value.trim();
  }

  } catch (err) { console.error("buildPayload err:", err); }

  return out;
}

async function loadMemoryStatus() {
  try {
    const r = await fetch('/api/memory/status');
    const d = await r.json();
    const el = document.getElementById('mem-status-text');
    if (!el) return;
    if (d.ok) {
      const cog = d.cognition || {};
      el.innerHTML = `💬 Messages stored: <strong>${d.total_messages}</strong><br>` +
        `Memory: <strong>${cog.memory_enabled ? 'ON ✅' : 'OFF ❌'}</strong> | ` +
        `Episodic: <strong>${cog.episodic_memory ? 'ON ✅' : 'OFF ❌'}</strong> | ` +
        `Max context: <strong>${cog.max_history_messages}</strong> msgs`;
    } else {
      el.textContent = 'Error: ' + d.error;
    }
  } catch(e) {
    const el = document.getElementById('mem-status-text');
    if (el) el.textContent = 'Error: ' + e.message;
  }
}

async function clearMemoryHistory() {
  const range = document.getElementById('clear-range').value;
  const label = range === 'all' ? 'ALL history' : `history older than ${range} day(s)`;
  
  if (!confirm(`Warning: You are about to delete ${label}. This cannot be undone. Continue?`)) return;
  
  try {
    const r = await fetch('/api/memory/clear', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ days: range })
    });
    const d = await r.json();
    if (d.ok) { 
      alert('✅ ' + d.message); 
      loadMemoryStatus(); 
    }
    else {
      alert('❌ Error: ' + d.error);
    }
  } catch(e) { 
    alert('❌ Error: ' + e.message); 
  }
}

function buildAudioPayload() {
    const obj = {};
    obj.listening_status = document.getElementById('sys-mic-status').checked;
    obj.voice_status     = document.getElementById('sys-voice-status').checked;
    
    obj.piper_path       = document.getElementById('v-piper').value;
    const pdir = sysOptions.piper_dir || 'C:\\piper';
    const sel  = document.getElementById('v-onnx-model').value;
    obj.onnx_model       = (sel.includes('\\') || sel.includes('/')) ? sel : pdir + '\\' + sel;
    
    obj.speed            = parseFloat(document.getElementById('v-speed').value);
    obj.noise_scale      = parseFloat(document.getElementById('v-noise').value);
    obj.noise_w          = parseFloat(document.getElementById('v-noisew').value);
    obj.sentence_silence = parseFloat(document.getElementById('v-silence').value);
    
    obj.energy_threshold = parseInt(document.getElementById('a-threshold').value) || 450;
    obj.silence_timeout  = parseInt(document.getElementById('a-timeout').value) || 5;
    obj.phrase_limit     = parseInt(document.getElementById('a-limit').value) || 15;
    
    obj.stt_source = document.getElementById('stt-source').value;
    obj.tts_destination = document.getElementById('tts-destination').value;
    
    const inSel = document.getElementById('audio-input-device');
    const outSel = document.getElementById('audio-output-device');
    if (inSel && inSel.value !== "") {
        obj.input_device_index = parseInt(inSel.value);
        let txt = inSel.options[inSel.selectedIndex]?.text || '';
        obj.input_device_name = txt.includes(':') ? txt.split(': ').slice(1).join(': ') : txt;
    }
    if (outSel && outSel.value !== "") {
        obj.output_device_index = parseInt(outSel.value);
        let txt = outSel.options[outSel.selectedIndex]?.text || '';
        obj.output_device_name = txt.includes(':') ? txt.split(': ').slice(1).join(': ') : txt;
    }
    
    return obj;
}

let currentTestAudio = null;
async function testVoice(mode) {
    const vTextEl = document.getElementById('v-test-text');
    const text = (vTextEl ? vTextEl.value : "") || "Test di Zentra Core, tutto funziona correttamente.";
    const sts = document.getElementById('v-test-status');
    const stopBtn = document.getElementById('v-test-stop');
    if (sts) sts.textContent = mode === 'web' ? "Generating..." : "Playing on console...";
    if(stopBtn) stopBtn.style.display = 'inline-block';
    
    try {
        const r = await fetch('/api/audio/test', {
            method: 'POST',
            body: JSON.stringify({ text: text, mode: mode })
        });
        const data = await r.json();
        if (data.ok) {
            if (mode === 'web' && data.url) {
                if (sts) sts.textContent = "Playing...";
                if (currentTestAudio) currentTestAudio.pause();
                currentTestAudio = new Audio(data.url);
                currentTestAudio.play();
                currentTestAudio.onended = () => { 
                    if (sts) sts.textContent = "Done."; 
                    if(stopBtn) stopBtn.style.display='none'; 
                    currentTestAudio = null;
                };
            } else {
                if (sts) sts.textContent = data.msg || "Done.";
                if(mode === 'console') {
                   setTimeout(() => { if(sts && sts.textContent!=="Generating...") if(stopBtn) stopBtn.style.display='none'; }, 8000);
                }
            }
        } else {
            if (sts) sts.textContent = "Error: " + data.error;
            if(stopBtn) stopBtn.style.display='none';
        }
    } catch(e) {
        if (sts) sts.textContent = "Request failed.";
        if(stopBtn) stopBtn.style.display='none';
    }
}

async function stopVoice() {
    if (currentTestAudio) {
        currentTestAudio.pause();
        currentTestAudio.src = "";
        currentTestAudio = null;
    }
    try { await fetch('/api/audio/stop', {method: 'POST'}); } catch(e) {}
    const stopBtn = document.getElementById('v-test-stop');
    if(stopBtn) stopBtn.style.display = 'none';
    const sts = document.getElementById('v-test-status');
    if(sts) sts.textContent = "Stopped.";
}

document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') stopVoice();
});

async function scanAudioDevices() {
    const sts = document.getElementById('audio-scan-status');
    if (sts) sts.textContent = "Scanning... (Wait for beep)";
    try {
        const r = await fetch('/api/audio/devices/scan', { method: 'POST' });
        const data = await r.json();
        if (data.ok) {
            if (sts) sts.textContent = `Done. Selected In: ${data.input_device_index}, Out: ${data.output_device_index}`;
            const rr = await fetch('/api/audio/devices');
            const rrData = await rr.json();
            if (rrData.ok) {
                audioDevices = rrData;
                populateUI();
            }
        } else {
            if (sts) sts.textContent = "Error: " + data.error;
        }
    } catch(e) {
        if (sts) sts.textContent = "Request failed.";
    }
}

async function applyAudioDevice() {
    const sts = document.getElementById('audio-scan-status');
    const inIdx = document.getElementById('audio-input-device').value;
    const outIdx = document.getElementById('audio-output-device').value;
    
    if (sts) sts.textContent = "Applying...";
    try {
        const r = await fetch('/api/audio/devices/select', {
            method: 'POST',
            body: JSON.stringify({ input_index: inIdx, output_index: outIdx })
        });
        const data = await r.json();
        if (data.ok) {
            if (sts) sts.textContent = "Saved to audio configuration.";
            setTimeout(() => { if(sts && sts.textContent.includes("Saved")) sts.textContent = ""; }, 3000);
        } else {
            if (sts) sts.textContent = "Error: " + data.error;
        }
    } catch(e) {
        if (sts) sts.textContent = "Request failed.";
    }
}

async function refreshModels() {
  const btn = event ? event.target : null;
  const oldTxt = btn ? btn.textContent : '';
  if (btn) { btn.textContent = '...'; btn.disabled = true; }
  try {
    await fetch('/api/models/refresh', {method:'POST'});
    await initAll();
  } catch(e) {
    alert("Refresh failed: " + e);
  } finally {
    if (btn) { btn.textContent = oldTxt; btn.disabled = false; }
  }
}

function buildMediaPayload() {
    return {
        image_gen: {
            enabled: document.getElementById('igen-enabled').checked,
            provider: document.getElementById('igen-provider').value,
            model: document.getElementById('igen-model').value,
            width: parseInt(document.getElementById('igen-width').value) || 1024,
            height: parseInt(document.getElementById('igen-height').value) || 1024,
            nologo: document.getElementById('igen-nologo').checked,
            api_key: document.getElementById('igen-apikey').value.trim()
        }
    };
}

async function saveConfig(silent = false) {
  if (!silent) setSaveMsg(I18N.msg_saving || 'Saving...', 'muted');
  try {
    const payload = buildPayload();
    const audioPayload = buildAudioPayload();
    const mediaPayload = buildMediaPayload();
    
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
      setSaveMsg('Error saving config/audio.', 'err');
    }
  } catch (e) {
    setSaveMsg('Fetch error: ' + e, 'err');
  }
}

let logEvtSource = null;
function startLogStream() {
    if (logEvtSource) return;
    const consoleEl = document.getElementById('log-console');
    const statusEl  = document.getElementById('log-status');
    
    if (consoleEl) consoleEl.innerHTML = '';
    if (statusEl) { statusEl.textContent = 'Active'; statusEl.className = 'val-ok'; }

    logEvtSource = new EventSource('/api/logs/stream');
    logEvtSource.onmessage = (e) => {
        const data = JSON.parse(e.data);
        const filterEl = document.getElementById('web-log-level');
        const filter = filterEl ? filterEl.value : 'BOTH';
        if (filter !== 'BOTH' && data.level !== filter) return;

        const line = document.createElement('div');
        line.className = 'log-line';
        
        let colorClass = 'lvl-INFO';
        if (data.text.includes('[DEBUG]')) colorClass = 'lvl-DEBUG';
        if (data.text.includes('[ERROR]')) colorClass = 'lvl-ERROR';
        if (data.text.includes('[WARNING]')) colorClass = 'lvl-WARN';

        line.innerHTML = `<span class="log-time">${data.time}</span><span class="log-lvl ${colorClass}">${data.level}</span><span class="log-text">${escapeHtml(data.text)}</span>`;
        
        let target = document.getElementById('log-console');
        const debugEl = document.getElementById('log-console-debug');
        const splitEl = document.getElementById('web-log-split');
        const isSplit = splitEl ? splitEl.checked : false;
        
        if (isSplit && data.level === 'DEBUG') target = debugEl;
        
        if (target) {
            target.appendChild(line);
            const mEl = document.getElementById('web-log-max');
            const m = mEl ? parseInt(mEl.value) : 500;
            const maxLines = isNaN(m) ? 500 : m;
            while (target.children.length > maxLines) target.removeChild(target.firstChild);
            
            const autoScEl = document.getElementById('web-log-autoscroll');
            if (autoScEl && autoScEl.checked) {
                target.scrollTop = target.scrollHeight;
            }
        }
    };
    logEvtSource.onerror = () => {
        if (statusEl) { statusEl.textContent = 'Disconnected (Reconnecting...)'; statusEl.className = 'val-err'; }
    };
}

function toggleLogSplit() {
    const splitEl = document.getElementById('web-log-split');
    const isSplit = splitEl ? splitEl.checked : false;
    const wrapper = document.getElementById('log-wrapper');
    const debugG  = document.getElementById('log-group-debug');
    const mainLog = document.getElementById('log-console');
    
    if (isSplit) {
        if (wrapper) wrapper.classList.add('split');
        if (debugG) debugG.style.display = 'flex';
        if (mainLog) mainLog.style.height = 'auto';
    } else {
        if (wrapper) wrapper.classList.remove('split');
        if (debugG) debugG.style.display = 'none';
        if (mainLog) mainLog.style.height = '500px';
    }
}

function clearLogConsole() {
    const c1 = document.getElementById('log-console');
    const c2 = document.getElementById('log-console-debug');
    if (c1) c1.innerHTML = '';
    if (c2) c2.innerHTML = '';
}

function escapeHtml(text) {
  const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
  return text.replace(/[&<>"']/g, m => map[m]);
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

function onProviderChanged() {
  const provEl = document.getElementById('igen-provider');
  const provider = provEl ? provEl.value : 'pollinations';
  const keyRow  = document.getElementById('igen-apikey-row');
  const keyLbl  = document.getElementById('igen-apikey-label');
  
  const labels = {
    gemini:    'Gemini API Key (GEMINI_API_KEY)',
    openai:    'OpenAI API Key (OPENAI_API_KEY)',
    stability: 'Stability API Key (STABILITY_API_KEY)',
  };

  if (labels[provider]) {
    if (keyRow) keyRow.style.display = '';
    if (keyLbl) keyLbl.textContent   = labels[provider];
  } else {
    if (keyRow) keyRow.style.display = 'none';
  }
}

async function refreshImageModels(restoreValue) {
  const provEl = document.getElementById('igen-provider');
  const provider = provEl ? provEl.value : 'pollinations';
  const sel     = document.getElementById('igen-model');
  const status  = document.getElementById('igen-model-status');
  if (!sel) return;
  if (status) status.textContent = 'Loading...';
  try {
    const r = await fetch(`/zentra/api/media/models?provider=${encodeURIComponent(provider)}`);
    const d = await r.json();
    if (d.ok && Array.isArray(d.models) && d.models.length) {
      sel.innerHTML = '';
      d.models.forEach(m => {
        const opt = document.createElement('option');
        opt.value = m; opt.textContent = m;
        if (restoreValue && m === restoreValue) opt.selected = true;
        sel.appendChild(opt);
      });
      if (status) status.textContent = `${d.models.length} models`;
    } else {
      if (status) status.textContent = 'Using defaults';
    }
  } catch(e) {
    if (status) status.textContent = 'Could not fetch';
    console.warn('refreshImageModels error:', e);
  }
}

async function openMediaVault() {
  try {
    const res = await fetch('/zentra/api/media/open-folder', { method: 'POST' });
    if (!res.ok) alert('Impossibile aprire la cartella.');
  } catch(e) { console.error(e); }
}

async function clearMediaVault() {
  if (!confirm('Sei sicuro? Questa operazione ELIMINERÀ DEFINITIVAMENTE tutte le immagini salvate in locale.\n\nVuoi procedere?')) return;
  try {
    const res = await fetch('/zentra/api/media/clear', { method: 'POST' });
    const data = await res.json();
    if (data.ok) {
      alert(`Media Vault svuotato con successo.\nFile eliminati: ${data.deleted}`);
    } else {
      alert("Errore durante l'eliminazione: " + data.error);
    }
  } catch(e) {
    alert('Errore di connessione al server.');
  }
}

// Event Listeners
document.addEventListener('change', (e) => {
  if (e.target.type === 'checkbox' || e.target.tagName === 'SELECT') {
    if (e.target.id === 'igen-enabled') {
        const other = document.querySelector('[data-plugin="IMAGE_GEN"]');
        if (other) other.checked = e.target.checked;
    } else if (e.target.dataset.plugin === 'IMAGE_GEN') {
        const other = document.getElementById('igen-enabled');
        if (other) other.checked = e.target.checked;
    }

    if (e.target.id === 'sys-voice-status' && !e.target.checked) {
       stopVoice();
    }
    saveConfig(true);
  }
});

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

// Global functions for inline HTML calls
window.showTab = showTab;
window.initAll = initAll;
window.refreshStatus = refreshStatus;
window.saveConfig = saveConfig;
window.refreshModels = refreshModels;
window.loadMemoryStatus = loadMemoryStatus;
window.clearMemoryHistory = clearMemoryHistory;
window.scanAudioDevices = scanAudioDevices;
window.applyAudioDevice = applyAudioDevice;
window.testVoice = testVoice;
window.stopVoice = stopVoice;
window.clearLogConsole = clearLogConsole;
window.openMediaVault = openMediaVault;
window.clearMediaVault = clearMediaVault;
window.rebootSystem = rebootSystem;
window.onProviderChanged = onProviderChanged;
window.refreshImageModels = refreshImageModels;
window.startLogStream = startLogStream;
window.toggleLogSplit = toggleLogSplit;

initAll();
refreshStatus();
setInterval(refreshStatus, 3000);

setInterval(() => {
  fetch('/zentra/heartbeat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ type: 'config' })
  }).catch(() => {});
}, 5000);
