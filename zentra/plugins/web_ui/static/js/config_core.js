/**
 * Zentra Core WebUI - Core Configuration Logic
 * Handles initialization, global state, and shared utilities.
 */

// Use window objects to share state with config_mapper.js
window.cfg = {};
window.sysOptions = {};
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
  
  // Call specific load functions when switching to their respective tabs
  if (name === 'users') {
      if (typeof loadMyProfile === 'function') loadMyProfile();
      if (typeof loadUsersData === 'function') loadUsersData();
  }
}

async function fetchWithTimeout(resource, options = {}) {
  const { timeout = 10000 } = options;
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), timeout);
  try {
    const response = await fetch(resource, { ...options, signal: controller.signal });
    clearTimeout(id);
    return response;
  } catch (error) {
    clearTimeout(id);
    throw error;
  }
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
      fetchWithTimeout('/zentra/options'),
      fetchWithTimeout('/zentra/config'),
      fetchWithTimeout('/api/audio/devices'),
      fetchWithTimeout('/api/audio/config'),
      fetchWithTimeout('/zentra/api/config/media')
    ]);
    
    sysOptions = await rOpts.json();
    cfg = await rCfg.json();
    
    // Assign to window for config_mapper.js access
    window.cfg = cfg;
    window.sysOptions = sysOptions;
    
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

// (Mapping logic extracted to config_mapper.js)

async function saveConfig(silent = false) {
  if (isInitialLoading) return;
  if (!silent) setSaveMsg(I18N.msg_saving || 'Saving...', 'muted');
  try {
    const payload = buildPayload();
    payload._force_restart = !silent;

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

// (Payload builder extracted to config_mapper.js)

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

window.showTab = showTab;
window.initAll = initAll;
window.saveConfig = saveConfig;
window.refreshStatus = refreshStatus;
window.rebootSystem = rebootSystem;
// window.populateSelect, window.populateUI moved to config_mapper
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

