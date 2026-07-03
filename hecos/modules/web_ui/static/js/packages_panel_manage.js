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

window.hpmConfirmUninstall = function (id, name) {
  const msgTemplate = window.HPM_I18N?.confirm_uninstall || 'Are you sure you want to uninstall the package \'%s\'?';
  const msg = msgTemplate.replace('%s', name);
  
  window.hpmShowConfirm(msg, window.HPM_I18N?.uninstall || 'Uninstall', () => {
    window.hpmUninstall(id, name);
  });
};

window.hpmUninstall = async function(id, name) {
  const card = document.getElementById(`hpm-pkg-${id}`);
  if (card) { card.style.opacity = '0.4'; card.style.pointerEvents = 'none'; }

  const _ti = (en, it, es) => { const l = (document.documentElement.lang||'en').toLowerCase(); if(l.startsWith('it')) return it; if(l.startsWith('es')) return es; return en; };
  const lblUninst = _ti('Uninstalling...', 'Disinstallazione in corso...', 'Desinstalando...');
  
  if (typeof window.hpmSetProgress === 'function') {
      window.hpmSetProgress(true, `<i class="fas fa-trash fa-spin" style="margin-right:6px; color:#ef4444;"></i> ${lblUninst}`, 50);
  }

  try {
    const resp = await fetch(`/api/packages/${id}`, { method: 'DELETE' });
    const data = await resp.json();

    if (data.ok) {
      const lblSuccess = _ti('Uninstalled successfully!', 'Disinstallato con successo!', '¡Desinstalado con éxito!');
      const lblHint = _ti('Double click anywhere to close', 'Fai doppio clic per chiudere', 'Haz doble clic para cerrar');
      const hintHTML = `<div style="font-size:0.75em;color:var(--muted);margin-top:15px;opacity:0.6;font-weight:normal;">${lblHint}</div>`;

      if (typeof window.hpmSetProgress === 'function') {
          window.hpmSetProgress(true, `<div style="text-align:center; padding: 10px 0;"><i class="fas fa-check-circle" style="margin-right:6px; color:#10b981; font-size:1.5em; margin-bottom:8px; display:block;"></i> <b style="font-size:1.1em; color:var(--text)">${lblSuccess}</b>${hintHTML}</div>`, 100);
          
          const container = document.getElementById('hpm-install-progress');
          if (container) {
              container.ondblclick = () => window.hpmSetProgress(false);
              container.style.cursor = 'default';
          }
      } else {
          if (window.showToast) window.showToast(`Package uninstalled.`);
      }
      
      if (typeof window.hpmLoadPackages === 'function') window.hpmLoadPackages();
      if (typeof window.hpmRefreshConfigHub === 'function') window.hpmRefreshConfigHub();
      if (typeof window.loadWidgetsPanel === 'function') window.loadWidgetsPanel();
    } else {
      if (typeof window.hpmSetProgress === 'function') window.hpmSetProgress(false);
      if (window.showToast) window.showToast(`Uninstall failed: ${data.error}`, 'error');
      if (card) { card.style.opacity = '1'; card.style.pointerEvents = ''; }
    }
  } catch (err) {
    if (typeof window.hpmSetProgress === 'function') window.hpmSetProgress(false);
    if (window.showToast) window.showToast(`${err.message}`, 'error');
    if (card) { card.style.opacity = '1'; card.style.pointerEvents = ''; }
  }
};

window.hpmInjectTab = function(installResult) {
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

window.hpmRemoveTab = function(pkg_id) {
  document.querySelectorAll(`.hpm-injected[data-panel="${pkg_id}"]`).forEach(el => el.remove());
};

window.hpmShowCapabilities = async function(pkg_id, pkg_name) {
  try {
    const res = await fetch(`/hecos/api/packages/${pkg_id}/capabilities`);
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

    if (c.syscall_notes || c.notes) {
      html += `<div style="margin-top:15px; padding:10px; background:var(--bg2); border-radius:6px; border:1px solid var(--border-color);">`;
      if (c.syscall_notes) html += `<div style="margin-bottom:6px;"><strong>Syscalls:</strong> <span style="color:var(--muted);">${c.syscall_notes}</span></div>`;
      if (c.notes) html += `<div><strong>Notes:</strong> <span style="color:var(--muted);">${c.notes}</span></div>`;
      html += `</div>`;
    }

    html += `</div>`;

    if (typeof Swal !== 'undefined') {
      Swal.fire({
        title: 'Module Capabilities',
        html: html,
        icon: 'info',
        background: 'var(--bg1)',
        color: 'var(--text)',
        confirmButtonColor: '#3b82f6',
        confirmButtonText: 'Close',
        customClass: {
          popup: 'hecos-swal-popup'
        }
      });
    } else {
      alert(`Capabilities for ${c.name}:\n\nType: ${c.type}\nTools: ${c.llm_tools.join(', ')}\nCommands: ${c.slash_commands.join(', ')}`);
    }

  } catch (err) {
    if (window.showToast) window.showToast('Network error: ' + err.message, 'error');
  }
};
