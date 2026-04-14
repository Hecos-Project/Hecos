/**
 * Zentra Core WebUI - System Configuration Logic
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
    setVal('sys-language', c.language || 'en');
    
    // HTTPS config
    const webUiPlug = (c.plugins || {}).WEB_UI || {};
    setCheck('sys-https-enabled', webUiPlug.https_enabled ?? false);

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
    
    loadMemoryStatus();
    
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
    const proxyEl = document.getElementById('sys-proxy-url');
    return {
        logging: {
            level: document.getElementById('log-level').value,
            destination: document.getElementById('log-dest').value,
            message_types: document.getElementById('log-type').value,
            ui_error_beeps: document.getElementById('log-error-beeps')?.checked ?? true
        },
        system: {
            fast_boot: document.getElementById('sys-fastboot').checked,
            flask_debug: document.getElementById('sys-flask-debug').checked
        },
        language: document.getElementById('sys-language').value,
        cognition: {
            memory_enabled:          document.getElementById('cog-memory-enabled').checked,
            episodic_memory:         document.getElementById('cog-episodic').checked,
            clear_on_restart:        document.getElementById('cog-clear-restart').checked,
            include_identity_context:document.getElementById('cog-identity').checked,
            include_self_awareness:  document.getElementById('cog-awareness').checked,
            max_history_messages:    parseInt(document.getElementById('cog-max-history').value) || 20
        },
        plugins: {
            SYS_NET: {
                proxy_url: proxyEl ? proxyEl.value.trim() : ""
            },
            WEB_UI: {
                https_enabled: document.getElementById('sys-https-enabled')?.checked || false
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

// Exports for Global Scope
window.populateSystemUI = populateSystemUI;
window.buildSystemPayload = buildSystemPayload;
window.startLogStream = startLogStream;
window.addLogWindow = addLogWindow;
window.removeLogWindow = removeLogWindow;
window.updateWindowSource = updateWindowSource;
window.updateWindowLevel = updateWindowLevel;
window.updateLogGridLayout = updateLogGridLayout;
window.clearWindow = clearWindow;
window.clearAllLogWindows = clearAllLogWindows;
window.loadMemoryStatus = loadMemoryStatus;
window.clearMemoryHistory = clearMemoryHistory;
window.refreshModels = refreshModels;
window.refreshLogFiles = refreshLogFiles;
