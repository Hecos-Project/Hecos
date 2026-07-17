/**
 * packages_panel_manage.js
 * ─────────────────────────────────────────────────────────────────────────────
 * Manage logic for Hecos Package Manager (Status, Uninstall)
 */

window.hpmSetStatus = async function (id, status, skipRender = false) {
  try {
    const res = await fetch(`/api/packages/${id}/status`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status })
    });
    const data = await res.json();
    if (!data.ok) {
      if (window.showToast) window.showToast('Error: ' + data.error, 'error');
      return;
    }
    if (window.showToast) window.showToast(`Package ${status}`);

    const isEnabled = (status === 'installed');
    const pkgTag = data.tag;

    // ── Update window.cfg in memory so the hub filters correctly ──────────
    if (pkgTag && window.cfg && window.cfg.plugins) {
      if (!window.cfg.plugins[pkgTag]) window.cfg.plugins[pkgTag] = {};
      window.cfg.plugins[pkgTag].enabled = isEnabled;
    }

    // ── Refresh the config hub (add/remove the panel tab instantly) ────────
    const evictId = isEnabled ? null : (data.panel_id || null);
    if (typeof window.hpmRefreshConfigHub === 'function') {
      window.hpmRefreshConfigHub(evictId);
    } else if (typeof window.renderConfigHub === 'function') {
      window.renderConfigHub(window.viewMode);
    }

    // ── For builtin legacy plugins also save config ─────────────────────
    if (window._packages) {
        const pkg = window._packages.find(x => x.id === id);
        if (pkg && pkg.version === 'built-in') {
            if (typeof window.saveConfig === 'function') {
                window.saveConfig(true).then(() => {
                    if (typeof window.renderConfigHub === 'function') window.renderConfigHub(window.viewMode);
                });
            }
        }

        // Broadcast widget state change to update Control Room dynamically
        const hpmChannel = new BroadcastChannel('hecos_widgets');
        hpmChannel.postMessage({ type: 'widgets_reload_request' });

        if (typeof window.loadWidgetsPanel === 'function') window.loadWidgetsPanel();

        if (!skipRender) {
          if (pkg) {
            pkg.status = status;
            if (typeof window.hpmRenderHierarchy === 'function') window.hpmRenderHierarchy();
          }
        }
    }
  } catch (err) {
    if (window.showToast) window.showToast('Network error', 'error');
  }
};

window.hpmShowConfirm = function(msgHtml, confirmBtnText, onConfirm) {
  const modal = document.getElementById('hpm-confirm-modal');
  const textEl = document.getElementById('hpm-confirm-modal-text');
  const yesBtn = document.getElementById('hpm-confirm-modal-yes');
  
  if (modal && textEl && yesBtn) {
    textEl.innerHTML = msgHtml;
    yesBtn.innerHTML = confirmBtnText;
    modal.style.display = 'flex';
    yesBtn.onclick = function() {
      modal.style.display = 'none';
      onConfirm();
    };
  } else {
    // Fallback if modal is missing from DOM
    const plainMsg = msgHtml.replace(/<[^>]+>/g, '').replace(/&#39;/g, "'").replace(/&quot;/g, '"');
    if (!confirm(plainMsg)) return;
    onConfirm();
  }
};

/**
 * hpmShowMessage — mostra un messaggio informativo nel modal HPM esistente.
 * @param {string} title   - Titolo del modal
 * @param {string} msgHtml - Contenuto HTML del messaggio
 * @param {string} type    - 'success' | 'error' | 'info' (default)
 */
window.hpmShowMessage = function(title, msgHtml, type) {
  const modal   = document.getElementById('hpm-info-modal');
  const titleEl = document.getElementById('hpm-info-modal-title');
  const textEl  = document.getElementById('hpm-info-modal-text');

  if (modal && titleEl && textEl) {
    // Icona colorata in base al tipo
    const iconMap = {
      success: '<i class="fas fa-check-circle" style="color:#22c55e; margin-right:8px;"></i>',
      error:   '<i class="fas fa-times-circle" style="color:#ef4444; margin-right:8px;"></i>',
      info:    '<i class="fas fa-info-circle"  style="color:#3b82f6; margin-right:8px;"></i>',
    };
    const icon = iconMap[type] || iconMap.info;
    titleEl.innerHTML = icon + window._hesc(title);
    textEl.innerHTML  = msgHtml;
    modal.style.display = 'flex';
  } else {
    // Fallback senza DOM
    const plainMsg = msgHtml.replace(/<[^>]+>/g, '');
    alert(title + '\n\n' + plainMsg);
  }
};

/**
 * hpmRestartRequired — shown when a newly installed package needs a full restart.
 * Shows a confirmation modal, then triggers the system reboot and waits for the
 * server to come back up, auto-reloading the page when it does.
 */
window.hpmRestartRequired = function(pkgName) {
  const _ti = (en, it, es) => {
    const l = (document.documentElement.lang || 'en').toLowerCase();
    if (l.startsWith('it')) return it;
    if (l.startsWith('es')) return es;
    return en;
  };

  const title   = _ti('Restart Required', 'Riavvio Necessario', 'Reinicio Necesario');
  const bodyMsg = _ti(
    `<b>${pkgName}</b> has been installed but requires a <b>full restart</b> to register its API routes and activate all features.`,
    `<b>${pkgName}</b> è stato installato ma richiede un <b>riavvio completo</b> per registrare le rotte API e attivare tutte le funzionalità.`,
    `<b>${pkgName}</b> ha sido instalado pero requiere un <b>reinicio completo</b> para registrar sus rutas API y activar todas las funciones.`
  );
  const btnText = _ti('Restart Now', 'Riavvia Ora', 'Reiniciar Ahora');
  const laterText = _ti('Later', 'Più tardi', 'Más tarde');

  window.hpmShowConfirm(
    `<div style="text-align:center;">
       <i class="fas fa-power-off" style="font-size:2em;color:#f59e0b;margin-bottom:14px;display:block;"></i>
       <b style="font-size:1.1em;color:var(--text);">${title}</b>
       <p style="margin-top:12px;font-size:0.9em;color:var(--muted);line-height:1.5;">${bodyMsg}</p>
       <div style="font-size:0.78em;color:var(--muted);opacity:0.6;margin-top:8px;">
         ${_ti('Hecos will restart in the background and reload automatically.', 'Hecos si riavvierà in background e si ricaricherà automaticamente.', 'Hecos se reiniciará en segundo plano y se recargará automáticamente.')}
       </div>
     </div>`,
    btnText,
    () => window._hpmDoRestart()
  );
};

window._hpmDoRestart = async function() {
  const _ti = (en, it, es) => {
    const l = (document.documentElement.lang || 'en').toLowerCase();
    if (l.startsWith('it')) return it;
    if (l.startsWith('es')) return es;
    return en;
  };

  // ── Full-screen overlay ───────────────────────────────────────────────────
  const overlay = document.createElement('div');
  overlay.id = 'hpm-restart-overlay';
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
        <svg viewBox="0 0 72 72" style="width:72px;height:72px;animation:hpmSpinSlow 2s linear infinite;">
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
      <div id="hpm-restart-status" style="font-size:0.82em;color:rgba(255,255,255,0.45);margin-top:8px;">
        ${_ti('Sending restart command…', 'Invio comando di riavvio…', 'Enviando comando de reinicio…')}
      </div>
      <div style="margin-top:24px;width:220px;height:3px;background:rgba(255,255,255,0.08);border-radius:3px;overflow:hidden;">
        <div id="hpm-restart-bar" style="height:100%;width:0%;background:var(--accent);border-radius:3px;transition:width 0.4s ease;"></div>
      </div>
    </div>`;
  document.body.appendChild(overlay);

  const statusEl = document.getElementById('hpm-restart-status');
  const barEl    = document.getElementById('hpm-restart-bar');

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
  // Wait at least 3s before first poll (give the process time to die & restart)
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
        // Server is back up!
        setStatus(_ti('Reloading…', 'Ricaricamento…', 'Recargando…'), 100);
        await new Promise(r => setTimeout(r, 800));
        location.reload();
        return;
      }
    } catch (_) { /* server still down — keep polling */ }

    if (attempts < maxAttempts) {
      setTimeout(poll, 2000);
    } else {
      // Timeout — prompt manual reload
      if (statusEl) statusEl.innerHTML =
        `<span style="color:#ef4444;">${_ti('Server took too long. Please refresh manually.', 'Il server ha impiegato troppo tempo. Aggiorna manualmente.', 'El servidor tardó demasiado. Actualice manualmente.')}</span>
         <br><br><button onclick="location.reload()" style="padding:8px 18px;background:#f59e0b;color:#000;border:none;border-radius:6px;cursor:pointer;font-weight:700;">
           ${_ti('Refresh', 'Aggiorna', 'Actualizar')}
         </button>`;
    }
  };

  setTimeout(poll, 2000);
};


