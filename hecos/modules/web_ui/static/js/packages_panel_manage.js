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
    
    // Only trigger saveConfig for builtin legacy plugins, not for HPM packages.
    // HPM backend directly modifies the config when disabling packages.
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

  try {
    const resp = await fetch(`/api/packages/${id}`, { method: 'DELETE' });
    const data = await resp.json();

    if (data.ok) {
      if (window.showToast) window.showToast(`Package uninstalled.`);
      if (typeof window.hpmLoadPackages === 'function') window.hpmLoadPackages();
      if (typeof window.hpmRefreshConfigHub === 'function') window.hpmRefreshConfigHub();
      if (typeof window.loadWidgetsPanel === 'function') window.loadWidgetsPanel();
    } else {
      if (window.showToast) window.showToast(`Uninstall failed: ${data.error}`, 'error');
      if (card) { card.style.opacity = '1'; card.style.pointerEvents = ''; }
    }
  } catch (err) {
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
