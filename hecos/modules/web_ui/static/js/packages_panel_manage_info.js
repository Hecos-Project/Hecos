/**
 * packages_panel_manage.js
 * ─────────────────────────────────────────────────────────────────────────────
 * Manage logic for Hecos Package Manager (Status, Uninstall)
 */

window.hpmVerifyPackage = async function (id, name) {
  try {
    const _ti = (en, it, es) => { const l = (document.documentElement.lang || 'en').toLowerCase(); if (l.startsWith('it')) return it; if (l.startsWith('es')) return es; return en; };
    const lblVerifying = _ti('Verifying...', 'Verifica in corso...', 'Verificando...');
    if (typeof window.hpmSetProgress === 'function') window.hpmSetProgress(true, lblVerifying, 100);

    const res = await fetch(`/api/packages/${id}/verify`);
    const data = await res.json();

    if (typeof window.hpmSetProgress === 'function') window.hpmSetProgress(false);

    if (data.ok) {
      const lblHint = _ti('Double click anywhere to close', 'Fai doppio clic per chiudere', 'Haz doble clic para cerrar');
      const hintHTML = `<div style="font-size:0.75em;color:var(--muted);margin-top:15px;opacity:0.6;font-weight:normal;">${lblHint}</div>`;

      let htmlContent = '';

      if (data.status === 'valid') {
        const title = _ti('Verification Passed', 'Verifica Superata', 'Verificación Superada');
        const msg = _ti(`All files for package <b>${name}</b> are intact.`, `Tutti i file del pacchetto <b>${name}</b> sono integri.`, `Todos los archivos del paquete <b>${name}</b> están intactos.`);
        htmlContent = `<div style="text-align:center; padding: 10px 0;">
          <i class="fas fa-check-circle" style="margin-right:6px; color:#10b981; font-size:1.5em; margin-bottom:8px; display:block;"></i>
          <b style="font-size:1.1em; color:var(--text)">${title}</b>
          <div style="font-size:0.9em; color:var(--muted); margin-top:8px;">${msg}</div>
          ${hintHTML}
        </div>`;
      } else if (data.status === 'unverified') {
        const title = _ti('Cannot Verify', 'Impossibile Verificare', 'No se puede verificar');
        htmlContent = `<div style="text-align:center; padding: 10px 0;">
          <i class="fas fa-info-circle" style="margin-right:6px; color:#3b82f6; font-size:1.5em; margin-bottom:8px; display:block;"></i>
          <b style="font-size:1.1em; color:var(--text)">${title}</b>
          <div style="font-size:0.9em; color:var(--muted); margin-top:8px;">${data.message}</div>
          ${hintHTML}
        </div>`;
      } else {
        const title = _ti('Verification Failed', 'Verifica Fallita', 'Verificación Fallida');
        let msg = _ti(`Package <b>${name}</b> has missing or modified files:`, `Il pacchetto <b>${name}</b> ha file mancanti o modificati:`, `El paquete <b>${name}</b> tiene archivos faltantes o modificados:`);
        msg += `<div style="max-height:120px; overflow-y:auto; font-size:0.85em; text-align:left; background:rgba(0,0,0,0.2); padding:8px; border-radius:6px; margin-top:10px; border:1px solid rgba(255,255,255,0.05);">`;
        if (data.missing_files && data.missing_files.length) {
          msg += `<strong style="color:#ef4444;">Missing:</strong><br>${data.missing_files.join('<br>')}<br><br>`;
        }
        if (data.modified_files && data.modified_files.length) {
          msg += `<strong style="color:#f59e0b;">Modified:</strong><br>${data.modified_files.join('<br>')}`;
        }
        msg += `</div>`;

        htmlContent = `<div style="text-align:center; padding: 10px 0;">
          <i class="fas fa-exclamation-triangle" style="margin-right:6px; color:#ef4444; font-size:1.5em; margin-bottom:8px; display:block;"></i>
          <b style="font-size:1.1em; color:var(--text)">${title}</b>
          <div style="font-size:0.9em; color:var(--muted); margin-top:8px;">${msg}</div>
          ${hintHTML}
        </div>`;
      }

      if (typeof window.hpmSetProgress === 'function') {
        window.hpmSetProgress(true, htmlContent, 100);
        const container = document.getElementById('hpm-install-progress');
        if (container) {
          container.ondblclick = () => window.hpmSetProgress(false);
          container.style.cursor = 'default';
        }
      }
    } else {
      if (window.showToast) window.showToast(`Verify error: ${data.error}`, 'error');
    }
  } catch (err) {
    if (typeof window.hpmSetProgress === 'function') window.hpmSetProgress(false);
    if (window.showToast) window.showToast(`${err.message}`, 'error');
  }
};

window.hpmInjectTab = function (installResult) {
  if (!installResult.config_panel) return;
  const { tab_id, tab_label, tab_icon } = installResult.config_panel;
  if (!tab_id) return;
  if (document.querySelector(`[data-panel="${tab_id}"]`)) return;
  const nav = document.querySelector('#config-sidebar-nav, .config-nav, .sidebar-nav');
  if (!nav) return;
  const li = document.createElement('li');
  li.setAttribute('data-panel', tab_id);
  li.className = 'nav-item hpm-injected';
  li.innerHTML = `
    <button class="nav-btn" onclick="showTab('${tab_id}')">
      <i class="fas ${tab_icon || 'fa-cube'}" style="margin-right:6px;"></i>
      ${window._hesc(tab_label || tab_id)}
    </button>`;
  nav.appendChild(li);
};

window.hpmRemoveTab = function (pkg_id) {
  document.querySelectorAll(`.hpm-injected[data-panel="${pkg_id}"]`).forEach(el => el.remove());
};

window.hpmShowDocs = async function (pkg_id, pkg_name) {
  try {
    const res = await fetch(`/api/packages/${pkg_id}/readme`);
    const data = await res.json();
    let htmlContent = '';
    if (!data.ok) {
      htmlContent = `
        <div style="text-align: center; padding: 40px 20px; background: var(--bg-card, #1e1e1e); border-radius: 8px; border: 1px dashed var(--border-color, #444); margin-top: 20px;">
            <i class="fas fa-file-alt" style="font-size: 48px; color: var(--muted, #888); margin-bottom: 16px;"></i>
            <h3 style="margin: 0 0 10px 0; color: var(--text-color, #fff);">No Documentation Available</h3>
            <p style="margin: 0; color: var(--muted, #888);">This package does not include a README or documentation guide.</p>
        </div>
      `;
    } else {
      htmlContent = data.content;
      try {
        if (typeof marked !== 'undefined') {
          htmlContent = marked.parse(data.content);
        } else if (window.marked && typeof window.marked.parse === 'function') {
          htmlContent = window.marked.parse(data.content);
        } else {
          htmlContent = `<pre style="white-space: pre-wrap; font-family: monospace; font-size: 13px;">${window._hesc(data.content)}</pre>`;
        }
      } catch (e) {
        htmlContent = `<pre style="white-space: pre-wrap; font-family: monospace; font-size: 13px;">${window._hesc(data.content)}</pre>`;
      }
    }

    let html = `
      <div style="text-align:left; font-size:14px; line-height:1.6; max-height: 70vh; overflow-y: auto; padding-right: 10px;" class="markdown-body">
        ${htmlContent}
      </div>
    `;

    const modal = document.getElementById('hpm-info-modal');
    const textEl = document.getElementById('hpm-info-modal-text');
    const titleEl = document.getElementById('hpm-info-modal-title');
    if (modal && textEl) {
      if (titleEl) titleEl.innerHTML = `<i class="fas fa-book" style="color:#10b981; margin-right:8px;"></i>Documentation: ${pkg_name}`;
      textEl.innerHTML = html;
      modal.style.display = 'flex';
    } else {
      console.log(data.content);
      alert("Manual loaded in console (modal not found)");
    }
  } catch (err) {
    console.error(err);
    if (window.showToast) window.showToast('Network error while fetching documentation.', 'error');
  }
};

window.hpmShowCapabilities = async function (pkg_id, pkg_name) {
  try {
    const res = await fetch(`/api/packages/${pkg_id}/capabilities`);
    const data = await res.json();
    if (!data.ok) {
      if (window.showToast) window.showToast('Error: ' + data.error, 'error');
      return;
    }
    const c = data.card;

    // Format card as HTML
    let html = `
      <div style="text-align:left; font-size:13px; line-height:1.5;">
        <div style="margin-bottom:10px;">
          <span style="display:inline-block; padding:2px 6px; background:var(--bg3, #2a2a35); border-radius:4px; font-weight:bold; font-size:11px; margin-right:6px;">${c.type.toUpperCase()}</span>
          <span style="font-size:16px; font-weight:bold; color:var(--text);">${c.name} <span style="opacity:0.5;font-weight:normal;font-size:12px;">v${c.version}</span></span>
        </div>
        <p style="color:var(--muted); margin-bottom:15px; font-size:14px;">${c.description}</p>
        
        <table style="width:100%; border-collapse:collapse; margin-bottom:15px;">
          <tr style="border-bottom:1px solid var(--border-color);">
            <td style="padding:6px 0; color:var(--muted); width:40%;">Author</td>
            <td style="padding:6px 0; font-weight:500;">${c.author || 'Unknown'}</td>
          </tr>
          <tr style="border-bottom:1px solid var(--border-color);">
            <td style="padding:6px 0; color:var(--muted);">Has Widget</td>
            <td style="padding:6px 0;">${c.has_widget ? '<span style="color:#10b981;">Yes</span>' : 'No'}</td>
          </tr>
          <tr style="border-bottom:1px solid var(--border-color);">
            <td style="padding:6px 0; color:var(--muted);">Config Panel</td>
            <td style="padding:6px 0;">${c.has_config_panel ? '<span style="color:#10b981;">Yes</span>' : 'No'}</td>
          </tr>
          <tr style="border-bottom:1px solid var(--border-color);">
            <td style="padding:6px 0; color:var(--muted);">API Routes</td>
            <td style="padding:6px 0;">${c.has_api_routes ? '<span style="color:#10b981;">Yes</span>' : 'No'}</td>
          </tr>
          <tr style="border-bottom:1px solid var(--border-color);">
            <td style="padding:6px 0; color:var(--muted);">System Calls</td>
            <td style="padding:6px 0;">${c.has_system_calls ? '<span style="color:#10b981;">Yes</span>' : 'No'}</td>
          </tr>
        </table>
    `;

    if (c.llm_tools && c.llm_tools.length > 0) {
      html += `
        <div style="margin-bottom:10px;">
          <div style="font-weight:bold; margin-bottom:4px;">LLM Tools:</div>
          <div style="display:flex; flex-wrap:wrap; gap:5px;">
            ${c.llm_tools.map(t => `<span style="background:rgba(59,130,246,0.15); color:#3b82f6; padding:2px 6px; border-radius:4px; font-size:11px; border:1px solid rgba(59,130,246,0.3);">${t}</span>`).join('')}
          </div>
        </div>
      `;
    }

    if (c.slash_commands && c.slash_commands.length > 0) {
      html += `
        <div style="margin-bottom:10px;">
          <div style="font-weight:bold; margin-bottom:4px;">Slash Commands:</div>
          <div style="display:flex; flex-wrap:wrap; gap:5px;">
            ${c.slash_commands.map(cmd => `<span style="background:rgba(236,72,153,0.15); color:#ec4899; padding:2px 6px; border-radius:4px; font-size:11px; border:1px solid rgba(236,72,153,0.3);">${cmd}</span>`).join('')}
          </div>
        </div>
      `;
    }

    if (c.dependencies && c.dependencies.length > 0) {
      html += `
        <div style="margin-bottom:10px;">
          <div style="font-weight:bold; margin-bottom:4px; color:#60a5fa;">Dependencies (Hecos):</div>
          <div style="display:flex; flex-wrap:wrap; gap:5px;">
            ${c.dependencies.map(d => `<span style="background:rgba(59,130,246,0.15); color:#60a5fa; padding:2px 6px; border-radius:4px; font-size:11px; border:1px solid rgba(59,130,246,0.3);">${window._hesc ? window._hesc(d) : d}</span>`).join('')}
          </div>
        </div>
      `;
    }

    if (c.pip_requirements && c.pip_requirements.length > 0) {
      html += `
        <div style="margin-bottom:10px;">
          <div style="font-weight:bold; margin-bottom:4px; color:#fbbf24;">Dependencies (PIP):</div>
          <div style="display:flex; flex-wrap:wrap; gap:5px;">
            ${c.pip_requirements.map(p => {
        let clean = p.split('==')[0].split('>=')[0];
        return `<span style="background:rgba(245,158,11,0.15); color:#fbbf24; padding:2px 6px; border-radius:4px; font-size:11px; border:1px solid rgba(245,158,11,0.3);">${window._hesc ? window._hesc(clean) : clean}</span>`;
      }).join('')}
          </div>
        </div>
      `;
    }

    if (c.syscall_notes || c.notes) {
      html += `<div style="margin-top:15px; padding:10px; background:var(--bg2); border-radius:6px; border:1px solid var(--border-color);">`;
      if (c.syscall_notes) html += `<div style="margin-bottom:6px;"><strong>Syscalls:</strong> <span style="color:var(--muted);">${c.syscall_notes}</span></div>`;
      if (c.notes) html += `<div><strong>Notes:</strong> <span style="color:var(--muted);">${c.notes}</span></div>`;
      html += `</div>`;
    }

    html += `</div>`;

    const modal = document.getElementById('hpm-info-modal');
    const textEl = document.getElementById('hpm-info-modal-text');
    const titleEl = document.getElementById('hpm-info-modal-title');
    if (modal && textEl) {
      if (titleEl) titleEl.innerHTML = `<i class="fas fa-info-circle" style="color:#3b82f6; margin-right:8px;"></i>Module Capabilities`;
      textEl.innerHTML = html;
      modal.style.display = 'flex';
    } else {
      alert(`Capabilities for ${c.name}:\n\nType: ${c.type}\nTools: ${c.llm_tools.join(', ')}\nCommands: ${c.slash_commands.join(', ')}`);
    }

  } catch (err) {
    if (window.showToast) window.showToast('Network error: ' + err.message, 'error');
  }
};

window.hpmHotReloadModule = async function (pkg_id, name) {

  const _ti = (en, it, es) => { const l = (document.documentElement.lang || 'en').toLowerCase(); if (l.startsWith('it')) return it; if (l.startsWith('es')) return es; return en; };
  if (typeof window.hpmSetProgress === 'function') {
    window.hpmSetProgress(true, `<i class="fas fa-sync fa-spin" style="margin-right:6px; color:#3b82f6;"></i> ${_ti('Reloading module...', 'Ricaricamento modulo...', 'Recargando módulo...')}`, 50);
  }

  try {
    const resp = await fetch(`/api/packages/${pkg_id}/hot_reload_module`, { method: 'POST' });
    const data = await resp.json();
    if (typeof window.hpmSetProgress === 'function') window.hpmSetProgress(false);

    if (data.ok) {
      if (window.showToast) window.showToast(`Module ${name} hot-reloaded!`, 'success');
    } else {
      if (window.showToast) window.showToast(`Reload failed: ${data.error}`, 'error');
    }
  } catch (err) {
    if (typeof window.hpmSetProgress === 'function') window.hpmSetProgress(false);
    if (window.showToast) window.showToast(`Network error: ${err.message}`, 'error');
  }
};

