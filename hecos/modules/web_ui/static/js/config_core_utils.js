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

window.fetchWithTimeout = fetchWithTimeout;
window.setSaveMsg       = setSaveMsg;
window.setSpanText      = setSpanText;
window.escapeHtml       = escapeHtml;
window.rebootSystem     = rebootSystem;
