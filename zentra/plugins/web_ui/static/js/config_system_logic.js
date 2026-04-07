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

    setVal('web-log-level', slg.web_level || 'BOTH');
    setVal('web-log-max', slg.web_max_history || 500);
    setCheck('web-log-autoscroll', slg.web_autoscroll !== false);
    setCheck('web-log-split', slg.web_split === true);
    toggleLogSplit();

    const sys = c.system || {};
    setCheck('sys-fastboot', sys.fast_boot ?? false);
    setCheck('sys-flask-debug', sys.flask_debug ?? false);
    setVal('sys-plugin-sources', (sys.plugin_sources || []).join('\n'));
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
}

function buildSystemPayload() {
    const proxyEl = document.getElementById('sys-proxy-url');
    return {
        logging: {
            level: document.getElementById('log-level').value,
            destination: document.getElementById('log-dest').value,
            message_types: document.getElementById('log-type').value,
            web_level: document.getElementById('web-log-level').value,
            web_max_history: parseInt(document.getElementById('web-log-max').value),
            web_autoscroll: document.getElementById('web-log-autoscroll').checked,
            web_split: document.getElementById('web-log-split').checked
        },
        system: {
            fast_boot: document.getElementById('sys-fastboot').checked,
            flask_debug: document.getElementById('sys-flask-debug').checked,
            plugin_sources: document.getElementById('sys-plugin-sources').value.trim().split('\n').map(s=>s.trim()).filter(Boolean)
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

// Exports for Global Scope
window.populateSystemUI = populateSystemUI;
window.buildSystemPayload = buildSystemPayload;
window.startLogStream = startLogStream;
window.toggleLogSplit = toggleLogSplit;
window.clearLogConsole = clearLogConsole;
window.loadMemoryStatus = loadMemoryStatus;
window.clearMemoryHistory = clearMemoryHistory;
window.refreshModels = refreshModels;
