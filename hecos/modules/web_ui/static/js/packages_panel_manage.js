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

window.hpmVerifyPackage = async function(id, name) {
  try {
    const _ti = (en, it, es) => { const l = (document.documentElement.lang||'en').toLowerCase(); if(l.startsWith('it')) return it; if(l.startsWith('es')) return es; return en; };
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

window.hpmShowDocs = async function(pkg_id, pkg_name) {
  try {
    const res = await fetch(`/api/packages/${pkg_id}/readme`);
    const data = await res.json();
    if (!data.ok) {
      if (window.showToast) window.showToast('Error: ' + data.error, 'error');
      else alert('Error: ' + data.error);
      return;
    }
    
    let htmlContent = data.content;
    try {
      if (typeof marked !== 'undefined') {
        htmlContent = marked.parse(data.content);
      } else if (window.marked && typeof window.marked.parse === 'function') {
        htmlContent = window.marked.parse(data.content);
      } else {
        htmlContent = `<pre style="white-space: pre-wrap; font-family: monospace; font-size: 13px;">${window._hesc(data.content)}</pre>`;
      }
    } catch(e) {
      htmlContent = `<pre style="white-space: pre-wrap; font-family: monospace; font-size: 13px;">${window._hesc(data.content)}</pre>`;
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


window.hpmShowCapabilities = async function(pkg_id, pkg_name) {
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

window._hpmSelectionMode = false;
window._hpmSelectedPackages = new Set();

window.hpmToggleSelectionMode = function() {
    window._hpmSelectionMode = !window._hpmSelectionMode;
    window._hpmSelectedPackages.clear();
    
    const toolbar = document.getElementById('hpm-selection-toolbar');
    const selectModeBtn = document.getElementById('hpm-btn-select-mode');
    
    if (toolbar) toolbar.style.display = window._hpmSelectionMode ? 'flex' : 'none';
    
    if (selectModeBtn) {
        if (window._hpmSelectionMode) {
            selectModeBtn.style.background = 'var(--accent)';
            selectModeBtn.style.color = '#fff';
        } else {
            selectModeBtn.style.background = '';
            selectModeBtn.style.color = '';
        }
    }
    
    const chkAll = document.getElementById('hpm-select-all');
    if (chkAll) chkAll.checked = false;
    
    window.hpmUpdateSelectionUI();
    if (typeof window.hpmRenderHierarchy === 'function') window.hpmRenderHierarchy();
};

window.hpmToggleSelectAll = function() {
    const chkAll = document.getElementById('hpm-select-all');
    const isChecked = chkAll ? chkAll.checked : false;
    
    window._hpmSelectedPackages.clear();
    if (isChecked && window._packages) {
        window._packages.forEach(pkg => {
            if (pkg.removable === true) {
                window._hpmSelectedPackages.add(pkg.id);
            }
        });
    }
    
    window.hpmUpdateSelectionUI();
    if (typeof window.hpmRenderHierarchy === 'function') window.hpmRenderHierarchy();
};

window.hpmTogglePackageSelection = function(pkgId) {
    if (window._hpmSelectedPackages.has(pkgId)) {
        window._hpmSelectedPackages.delete(pkgId);
    } else {
        window._hpmSelectedPackages.add(pkgId);
    }
    window.hpmUpdateSelectionUI();
};

window.hpmUpdateSelectionUI = function() {
    const countEl = document.getElementById('hpm-selected-count');
    const btnUninstall = document.getElementById('hpm-btn-uninstall-selected');
    const count = window._hpmSelectedPackages.size;
    const _ti = (en, it, es) => { const l = (document.documentElement.lang||'en').toLowerCase(); if(l.startsWith('it')) return it; if(l.startsWith('es')) return es; return en; };
    const uninstallStr = _ti('Uninstall', 'Disinstalla', 'Desinstalar');
    
    // Dynamic translations for toolbar buttons
    const lblSelectAll = document.getElementById('lbl-hpm-select-all');
    if (lblSelectAll) lblSelectAll.innerText = _ti('Select all', 'Seleziona tutti', 'Seleccionar todo');
    
    const btnCancel = document.getElementById('btn-hpm-cancel-sel');
    if (btnCancel) btnCancel.innerText = _ti('Cancel', 'Annulla', 'Cancelar');
    
    const btnMode = document.getElementById('hpm-btn-select-mode');
    if (btnMode) btnMode.title = _ti('Select multiple', 'Seleziona multipli', 'Seleccionar múltiples');

    if (countEl) countEl.innerText = count;
    
    if (btnUninstall) {
        if (count > 0) {
            btnUninstall.style.opacity = '1';
            btnUninstall.style.pointerEvents = 'auto';
            btnUninstall.innerHTML = `<i class="fas fa-trash" style="margin-right:6px;"></i> ${uninstallStr} (${count})`;
        } else {
            btnUninstall.style.opacity = '0.5';
            btnUninstall.style.pointerEvents = 'none';
            btnUninstall.innerHTML = `<i class="fas fa-trash" style="margin-right:6px;"></i> ${uninstallStr}`;
        }
    }
};

window.hpmUninstallSelected = function() {
    if (window._hpmSelectedPackages.size === 0) return;
    
    const count = window._hpmSelectedPackages.size;
    const _ti = (en, it, es) => { const l = (document.documentElement.lang||'en').toLowerCase(); if(l.startsWith('it')) return it; if(l.startsWith('es')) return es; return en; };
    
    const msgTemplate = _ti(
        `Are you sure you want to uninstall <b>{count} packages</b>?<br><br><span style="font-size:0.85em;color:var(--muted);">This operation cannot be undone.</span>`,
        `Sei sicuro di voler disinstallare <b>{count} pacchetti</b>?<br><br><span style="font-size:0.85em;color:var(--muted);">Questa operazione non è annullabile.</span>`,
        `¿Estás seguro de que deseas desinstalar <b>{count} paquetes</b>?<br><br><span style="font-size:0.85em;color:var(--muted);">Esta operación no se puede deshacer.</span>`
    );
    const msg = msgTemplate.replace('{count}', count);
    const title = _ti(`Uninstall ${count}`, `Disinstalla ${count}`, `Desinstalar ${count}`);
    
    window.hpmShowConfirm(msg, title, async () => {
        // Estrai gli id PRIMA di disabilitare la modalità, altrimenti si azzerano
        const ids = Array.from(window._hpmSelectedPackages);
        window.hpmToggleSelectionMode(); // esci dalla modalità selezione e azzera il set
        
        const baseMsg = `<i class="fas fa-trash fa-spin" style="margin-right:6px; color:#ef4444;"></i> ${_ti(`Uninstalling (${ids.length} packages)...`, `Disinstallazione in corso (${ids.length} pacchetti)...`, `Desinstalando (${ids.length} paquetes)...`)}`;
        let uninstallHtml = `
            <div id="hpm-uninstall-header" style="font-size:1.05em; font-weight:600; color:var(--text);">${baseMsg}</div>
            <div id="hpm-uninstall-logs" style="margin-top:12px; font-size:0.92em; color:var(--muted); font-family:monospace; text-align:left; background:rgba(0,0,0,0.25); border-radius:6px; padding:8px; border-left:2px solid #ef4444; max-height:150px; overflow-y:auto; display:none; word-break:break-all;"></div>
        `;
        window.hpmSetProgress(true, uninstallHtml, 30);
        
        const logListener = (e) => {
            const logsContainer = document.getElementById('hpm-uninstall-logs');
            const header = document.getElementById('hpm-uninstall-header');
            if (!logsContainer || !header) return;
            
            const step = e.detail.step || '';
            const msg = e.detail.message || '';
            
            if (step === 'pip_log' || step === 'pip_remove') {
                logsContainer.style.display = 'block';
                const div = document.createElement('div');
                div.textContent = msg;
                if (step === 'pip_remove') {
                    div.style.color = '#ef4444';
                    div.style.fontWeight = 'bold';
                    div.style.marginTop = '4px';
                    div.style.marginBottom = '2px';
                }
                logsContainer.appendChild(div);
                logsContainer.scrollTop = logsContainer.scrollHeight;
            } else if (msg) {
                header.innerHTML = `<i class="fas fa-trash fa-spin" style="margin-right:6px; color:#ef4444;"></i> ${msg}`;
            }
        };
        
        document.addEventListener('hpmProgressUpdate', logListener);
        
        try {
            const resp = await fetch('/api/packages/uninstall/batch', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ ids: ids })
            });
            const data = await resp.json();
            
            if (data.ok) {
                let extraHTML = `<div style="text-align:left; background:rgba(0,0,0,0.2); border-radius:8px; padding:10px; margin-top:12px; max-height:150px; overflow-y:auto; font-size:0.85em; border:1px solid rgba(255,255,255,0.05);">`;
                data.results.forEach(r => {
                    const icon = r.ok ? '<i class="fas fa-check" style="color:#10b981; margin-right:6px; width:14px;"></i>' : '<i class="fas fa-times" style="color:#ef4444; margin-right:6px; width:14px;"></i>';
                    const removedMsg = r.ok ? `<span style="color:var(--muted)">${_ti('removed', 'rimosso', 'eliminado')}</span>` : `<span style="color:#ef4444">${r.error || 'error'}</span>`;
                    extraHTML += `<div style="margin-bottom:4px; display:flex; justify-content:space-between;">
                        <span style="color:var(--text);">${icon}${r.id}</span>
                        ${removedMsg}
                    </div>`;
                });
                extraHTML += `</div>`;

                if (data.succeeded > 0) {
                    const sound = localStorage.getItem('hpm_install_sound') || 'success.mp3';
                    if (sound !== 'none') {
                        if (sound.startsWith('custom|')) {
                            const path = sound.substring(7);
                            new Audio('/api/local_file?path=' + encodeURIComponent(path)).play().catch(() => {});
                        } else {
                            new Audio(`/static/sounds/${sound}`).play().catch(() => {});
                        }
                    }
                }

                const lblHint = `<div style="font-size:0.75em;color:var(--muted);margin-top:15px;opacity:0.6;font-weight:normal;">${_ti('Double click anywhere to close', 'Fai doppio clic per chiudere', 'Haz doble clic para cerrar')}</div>`;
                const lblSuccess = data.failed === 0 
                    ? _ti('Batch uninstall completed!', 'Disinstallazione batch completata!', '¡Desinstalación por lotes completada!')
                    : _ti('Completed with some errors', 'Completato con alcuni errori', 'Completado con algunos errores');
                
                const mainIconColor = data.failed === 0 ? '#10b981' : (data.succeeded > 0 ? '#f59e0b' : '#ef4444');
                const mainIcon = data.failed === 0 ? 'fa-check-circle' : (data.succeeded > 0 ? 'fa-exclamation-circle' : 'fa-times-circle');

                window.hpmSetProgress(true, `
                  <div style="text-align:center; padding: 10px 0;">
                      <i class="fas ${mainIcon}" style="margin-right:6px; color:${mainIconColor}; font-size:1.5em; margin-bottom:8px; display:block;"></i> 
                      <b style="font-size:1.1em; color:var(--text)">${lblSuccess}</b>
                      <div style="font-size:0.85em; color:var(--muted); margin-top:4px;">${data.succeeded} ${_ti('removed', 'rimossi', 'eliminados')} • ${data.failed} ${_ti('failed', 'falliti', 'fallidos')}</div>
                      ${extraHTML}
                      ${lblHint}
                  </div>`, 100);
                
                const container = document.getElementById('hpm-install-progress');
                if (container) {
                    container.ondblclick = () => window.hpmSetProgress(false);
                    container.style.cursor = 'default';
                }

                if (typeof window.hpmLoadPackages === 'function') window.hpmLoadPackages();
                if (typeof window.hpmRefreshConfigHub === 'function') window.hpmRefreshConfigHub();
                if (typeof window.loadWidgetsPanel === 'function') window.loadWidgetsPanel();
            } else {
                window.hpmSetProgress(false);
                if (window.showToast) window.showToast(`Batch uninstall error: ${data.error}`, 'error');
            }
        } catch (err) {
            window.hpmSetProgress(false);
            if (window.showToast) window.showToast(`Network error: ${err.message}`, 'error');
        } finally {
            document.removeEventListener('hpmProgressUpdate', logListener);
        }
    });
};

window.hpmHotReloadModule = async function(pkg_id, name) {
    const _ti = (en, it, es) => { const l = (document.documentElement.lang||'en').toLowerCase(); if(l.startsWith('it')) return it; if(l.startsWith('es')) return es; return en; };
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
