/**
 * config_core_utils.js
 * Shared low-level utilities: fetch helper, DOM helpers, system actions.
 * Must be loaded FIRST before other config_core_*.js files.
 * Depends on: nothing (standalone)
 */

/**
 * fetch() with a configurable timeout (default 30s).
 * On timeout returns a mock { ok: false } so callers don't break.
 */
async function fetchWithTimeout(resource, options = {}) {
  const { timeout = 30000 } = options;
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), timeout);
  try {
    const response = await fetch(resource, { ...options, signal: controller.signal });
    clearTimeout(id);
    return response;
  } catch (error) {
    clearTimeout(id);
    if (error.name === 'AbortError') {
        console.warn("Fetch aborted:", resource);
        return { ok: false, json: async () => ({ ok: false, error: 'Aborted' }) };
    }
    throw error;
  }
}

/** Updates the #save-msg element with colored text. */
function setSaveMsg(msg, type) {
  const el = document.getElementById('save-msg');
  if (!el) return;
  el.textContent = msg;
  el.style.color = type === 'ok' ? 'var(--green)' : type === 'err' ? 'var(--red)' : 'var(--muted)';
}

/** Sets the textContent of a span by ID. */
function setSpanText(id, text) {
  const el = document.getElementById(id);
  if (el) el.textContent = text;
}

/** HTML-escapes a string to prevent XSS in template literals. */
function escapeHtml(text) {
  const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
  return (text || '').replace(/[&<>"']/g, m => map[m]);
}

/** Sends a reboot command to the backend and reloads after 5s. */
async function rebootSystem() {
  const _ti = (en, it, es) => {
    const l = (document.documentElement.lang || 'en').toLowerCase();
    if (l.startsWith('it')) return it;
    if (l.startsWith('es')) return es;
    return en;
  };

  // Inject animation keyframes if missing
  if (!document.getElementById('sys-reboot-styles')) {
    const style = document.createElement('style');
    style.id = 'sys-reboot-styles';
    style.innerHTML = `
      @keyframes sysSpinSlow { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
    `;
    document.head.appendChild(style);
  }

  // ── Full-screen overlay ───────────────────────────────────────────────────
  const overlay = document.createElement('div');
  overlay.id = 'sys-reboot-overlay';
  overlay.style.cssText = `
    position:fixed;inset:0;z-index:99999;
    background:rgba(10,10,20,0.97);
    display:flex;flex-direction:column;
    align-items:center;justify-content:center;
    gap:20px;
  `;
  overlay.innerHTML = `
    <div style="text-align:center;">
      <div style="position:relative;width:72px;height:72px;margin:0 auto 20px;">
        <svg viewBox="0 0 72 72" style="width:72px;height:72px;animation:sysSpinSlow 2s linear infinite;">
          <circle cx="36" cy="36" r="32" fill="none" stroke="var(--accent)" stroke-width="4"
                  stroke-dasharray="150 52" stroke-linecap="round"/>
        </svg>
        <i class="fas fa-power-off" style="
          position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);
          font-size:22px;color:var(--accent);"></i>
      </div>
      <div style="font-size:1.25em;font-weight:700;color:#fff;letter-spacing:.5px;">
        ${_ti('Restarting Hecos…', 'Riavvio in corso…', 'Reiniciando Hecos…')}
      </div>
      <div id="sys-reboot-status" style="font-size:0.82em;color:rgba(255,255,255,0.45);margin-top:8px;">
        ${_ti('Sending restart command…', 'Invio comando di riavvio…', 'Enviando comando de reinicio…')}
      </div>
      <div style="margin-top:24px;width:220px;height:3px;background:rgba(255,255,255,0.08);border-radius:3px;overflow:hidden;">
        <div id="sys-reboot-bar" style="height:100%;width:0%;background:var(--accent);border-radius:3px;transition:width 0.4s ease;"></div>
      </div>
    </div>`;
  document.body.appendChild(overlay);

  const statusEl = document.getElementById('sys-reboot-status');
  const barEl    = document.getElementById('sys-reboot-bar');

  const setStatus = (msg, pct) => {
    if (statusEl) statusEl.textContent = msg;
    if (barEl) barEl.style.width = pct + '%';
  };

  // ── Send reboot command ───────────────────────────────────────────────────
  try {
    await fetch('/api/system/reboot', { method: 'POST' });
  } catch (_) { /* connection drop is expected */ }

  setStatus(
    _ti('Server is restarting…', 'Il server si sta riavviando…', 'El servidor se está reiniciando…'),
    30
  );

  // ── Poll until server responds ────────────────────────────────────────────
  await new Promise(r => setTimeout(r, 3000));

  let attempts = 0;
  const maxAttempts = 60; // 60 × 2s = 2 minutes max wait
  const poll = async () => {
    attempts++;
    const pct = Math.min(30 + Math.round((attempts / maxAttempts) * 65), 95);
    setStatus(
      _ti(`Waiting for server (${attempts})…`, `Attesa server (${attempts})…`, `Esperando servidor (${attempts})…`),
      pct
    );
    try {
      const res = await fetch('/hecos/heartbeat', { method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({type: 'restart_poll'})
      });
      if (res.ok) {
        setStatus(_ti('Reloading…', 'Ricaricamento…', 'Recargando…'), 100);
        await new Promise(r => setTimeout(r, 800));
        location.reload();
        return;
      }
    } catch (_) { }

    if (attempts < maxAttempts) {
      setTimeout(poll, 2000);
    } else {
      if (statusEl) statusEl.innerHTML =
        `<span style="color:#ef4444;">${_ti('Server took too long. Please refresh manually.', 'Il server ha impiegato troppo tempo. Aggiorna manualmente.', 'El servidor tardó demasiado. Actualice manualmente.')}</span>
         <br><br><button onclick="location.reload()" style="padding:8px 18px;background:#f59e0b;color:#000;border:none;border-radius:6px;cursor:pointer;font-weight:700;">
           ${_ti('Refresh', 'Aggiorna', 'Actualizar')}
         </button>`;
    }
  };

  setTimeout(poll, 2000);
}

window.fetchWithTimeout = fetchWithTimeout;
window.setSaveMsg       = setSaveMsg;
window.setSpanText      = setSpanText;
window.escapeHtml       = escapeHtml;
window.rebootSystem     = rebootSystem;
