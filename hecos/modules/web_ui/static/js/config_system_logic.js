/**
 * Hecos WebUI - System Configuration Logic
 * Handles logging, proxy testing, and system diagnostics.
 */

function populateSystemUI() {
    const c = cfg;
    const slg = c.logging || {};
    setVal('log-level', slg.level || 'INFO');
    setVal('log-type', slg.message_types || 'both');
    setVal('log-dest', slg.destination || 'console');
    setCheck('log-error-beeps', slg.ui_error_beeps ?? true);

    const sys = c.system || {};
    setCheck('sys-fastboot', sys.fast_boot ?? false);
    setCheck('sys-flask-debug', sys.flask_debug ?? false);
    setCheck('sys-check-local-backend', sys.check_local_backend_on_boot ?? false);
    setCheck('sys-sdk-enabled', sys.sdk_enabled === true);  // default OFF
    setVal('sys-language', c.language || 'en');

    // Input History
    const ihist = c.input_history || {};
    setCheck('ihistory-enabled', ihist.enabled ?? true);
    setCheck('ihistory-persist', ihist.persist ?? true);
    setCheck('ihistory-deduplicate', ihist.deduplicate ?? true);
    setVal('ihistory-max-entries', ihist.max_entries ?? 200);
    
    // HTTPS and WebUI config
    const webUiPlug = (c.plugins || {}).WEB_UI || {};
    setCheck('webui-https-enabled', webUiPlug.https_enabled ?? false);

    // Dashboard config
    const dsb = (c.plugins || {}).DASHBOARD || {};
    setCheck('sys-console-telemetry', dsb.console_telemetry_enabled ?? true);
    setCheck('sys-track-cpu', dsb.console_telemetry_cpu ?? false);
    setCheck('sys-track-ram', dsb.console_telemetry_ram ?? false);
    setCheck('sys-track-vram', dsb.console_telemetry_vram ?? false);
    setCheck('wui-control-room-panel', webUiPlug.control_room_panel ?? true);
    setCheck('wui-control-room-home', webUiPlug.control_room_home ?? true);

    const sysNet = (c.plugins || {}).SYS_NET || {};
    setCheck('sys-proxy-enabled', sysNet.proxy_enabled ?? false);
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

    // RAG Vector Memory fields
    const rag = cog.rag || {};
    setCheck('cog-rag-enabled',      rag.enabled ?? false);
    setCheck('cog-rag-auto-ingest',  rag.auto_ingest_history ?? false);
    setVal('cog-rag-embedder-model', rag.embedder_model || 'all-MiniLM-L6-v2');
    setVal('cog-rag-top-k',          rag.top_k ?? 5);
    setVal('cog-rag-chunk-size',     rag.chunk_size ?? 512);
    setVal('cog-rag-threshold',      rag.similarity_threshold ?? 0.3);

    loadMemoryStatus();
    if (typeof loadRagStatus === 'function') loadRagStatus();
    
    // Auto-init one log window if it doesn't exist - SEQ AFTER REFRSH
    initLogsTab();
}

async function initLogsTab() {
    await refreshLogFiles();
    if (activeLogWindows.length === 0) {
        addLogWindow('LIVE', 'BOTH');
    }
}

function buildSystemPayload() {
    const slg = window.cfg.logging || {};
    const sys = window.cfg.system || {};
    const sln = window.cfg.language || 'en';
    const cog = window.cfg.cognition || {};
    const ihist = window.cfg.input_history || {};
    const snet = window.cfg.plugins?.SYS_NET || {};
    const wui = window.cfg.plugins?.WEB_UI || {};

    return {
        logging: {
            level: getV('log-level', slg.level || 'INFO'),
            destination: getV('log-dest', slg.destination || 'console'),
            message_types: getV('log-type', slg.message_types || 'both'),
            ui_error_beeps: getC('log-error-beeps', slg.ui_error_beeps ?? true)
        },
        system: {
            fast_boot: getC('sys-fastboot', sys.fast_boot ?? false),
            flask_debug: getC('sys-flask-debug', sys.flask_debug ?? false),
            check_local_backend_on_boot: getC('sys-check-local-backend', sys.check_local_backend_on_boot ?? false),
            sdk_enabled: getC('sys-sdk-enabled', sys.sdk_enabled === true)
        },
        language: getV('sys-language', sln),
        cognition: {
            memory_enabled:          getC('cog-memory-enabled', cog.memory_enabled ?? true),
            episodic_memory:         getC('cog-episodic', cog.episodic_memory ?? true),
            clear_on_restart:        getC('cog-clear-restart', cog.clear_on_restart ?? false),
            include_identity_context:getC('cog-identity', cog.include_identity_context ?? true),
            include_self_awareness:  getC('cog-awareness', cog.include_self_awareness ?? true),
            max_history_messages:    parseInt(getV('cog-max-history', cog.max_history_messages)) || 20,
            rag: {
                enabled:              getC('cog-rag-enabled', (cog.rag||{}).enabled ?? false),
                auto_ingest_history:  getC('cog-rag-auto-ingest', (cog.rag||{}).auto_ingest_history ?? false),
                embedder:             'sentence_transformers',
                embedder_model:       getV('cog-rag-embedder-model', (cog.rag||{}).embedder_model || 'all-MiniLM-L6-v2'),
                top_k:                parseInt(getV('cog-rag-top-k', (cog.rag||{}).top_k)) || 5,
                chunk_size:           parseInt(getV('cog-rag-chunk-size', (cog.rag||{}).chunk_size)) || 512,
                chunk_overlap:        (cog.rag||{}).chunk_overlap ?? 64,
                similarity_threshold: parseFloat(getV('cog-rag-threshold', (cog.rag||{}).similarity_threshold)) || 0.3,
                persist_path:         (cog.rag||{}).persist_path || 'memory/vector_store'
            }
        },
        input_history: {
            enabled: getC('ihistory-enabled', ihist.enabled ?? true),
            persist: getC('ihistory-persist', ihist.persist ?? true),
            deduplicate: getC('ihistory-deduplicate', ihist.deduplicate ?? true),
            max_entries: parseInt(getV('ihistory-max-entries', ihist.max_entries)) || 200,
            scope: "per_user"
        },
        plugins: {
            DASHBOARD: {
                console_telemetry_enabled: getC('sys-console-telemetry', (window.cfg.plugins?.DASHBOARD?.console_telemetry_enabled ?? true)),
                console_telemetry_cpu: getC('sys-track-cpu', (window.cfg.plugins?.DASHBOARD?.console_telemetry_cpu ?? false)),
                console_telemetry_ram: getC('sys-track-ram', (window.cfg.plugins?.DASHBOARD?.console_telemetry_ram ?? false)),
                console_telemetry_vram: getC('sys-track-vram', (window.cfg.plugins?.DASHBOARD?.console_telemetry_vram ?? false))
            },
            SYS_NET: {
                proxy_enabled: getC('sys-proxy-enabled', snet.proxy_enabled ?? false),
                proxy_url: getV('sys-proxy-url', snet.proxy_url || "")
            },
            WEB_UI: {
                https_enabled: getC('webui-https-enabled', wui.https_enabled ?? false),
                control_room_panel: getC('wui-control-room-panel', wui.control_room_panel ?? true),
                control_room_home: getC('wui-control-room-home', wui.control_room_home ?? true)
            }
        }
    };
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

async function refreshModels() {
  const btn = event ? event.target : null;
  const oldTxt = btn ? btn.textContent : '';
  if (btn) { btn.textContent = '...'; btn.disabled = true; }
  try {
    await fetch('/api/models/refresh', {method:'POST'});
    
    // Clear front-end cache to force a real re-fetch from the updated backend
    window.sysOptions = {};
    
    if (typeof initAll === 'function') await initAll();
  } catch(e) {
    alert("Refresh failed: " + e);
  } finally {
    if (btn) { btn.textContent = oldTxt; btn.disabled = false; }
  }
}

function escapeHtml(text) {
  const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
  return (text || '').replace(/[&<>"']/g, m => map[m]);
}

window.clearInputHistory = async function() {
  if (!confirm("Are you sure you want to clear your input history?")) return;
  try {
    const r = await fetch('/api/input-history/clear', {method: 'POST'});
    const d = await r.json();
    if (d.ok) {
        alert("Input history cleared successfully.");
        if (window._inputHistory) window._inputHistory = [];
        if (window._inputHistoryCursor !== undefined) window._inputHistoryCursor = -1;
    } else {
        alert("Error clearing input history: " + (d.error || 'Unknown error'));
    }
  } catch(e) {
    alert("Error: " + e.message);
  }
};

// Exports for Global Scope
window.populateSystemUI = populateSystemUI;
window.buildSystemPayload = buildSystemPayload;
window.loadMemoryStatus = loadMemoryStatus;
window.clearMemoryHistory = clearMemoryHistory;
window.refreshModels = refreshModels;
// RAG functions (defined in config_memory.html script block)
if (typeof loadRagStatus    !== 'undefined') window.loadRagStatus    = loadRagStatus;
if (typeof ragIngestText    !== 'undefined') window.ragIngestText    = ragIngestText;
if (typeof ragIngestFile    !== 'undefined') window.ragIngestFile    = ragIngestFile;
if (typeof ragTestSearch    !== 'undefined') window.ragTestSearch    = ragTestSearch;
if (typeof ragWipe          !== 'undefined') window.ragWipe          = ragWipe;
if (typeof ragDeleteSource  !== 'undefined') window.ragDeleteSource  = ragDeleteSource;

// Safely bridge Log Engine functions if they exist
if (typeof startLogStream !== 'undefined') window.startLogStream = startLogStream;
if (typeof addLogWindow !== 'undefined') window.addLogWindow = addLogWindow;
if (typeof removeLogWindow !== 'undefined') window.removeLogWindow = removeLogWindow;
if (typeof updateWindowSource !== 'undefined') window.updateWindowSource = updateWindowSource;
if (typeof updateWindowLevel !== 'undefined') window.updateWindowLevel = updateWindowLevel;
if (typeof updateLogGridLayout !== 'undefined') window.updateLogGridLayout = updateLogGridLayout;
if (typeof clearWindow !== 'undefined') window.clearWindow = clearWindow;
if (typeof clearAllLogWindows !== 'undefined') window.clearAllLogWindows = clearAllLogWindows;
if (typeof refreshLogFiles !== 'undefined') window.refreshLogFiles = refreshLogFiles;
