/**
 * packages_panel.js
 * ─────────────────────────────────────────────────────────────────────────────
 * Orchestrator for Hecos Package Manager Frontend
 */

window.hpmInit = function () {
  window.hpmSwitchTab('packages');
  // Attempt to update counts for loaded panels
  setTimeout(() => {
    if (document.getElementById('tab-plugins')) {
      const builtinCount = document.querySelectorAll('#tab-plugins .toggle-row, #tab-plugins .plugin-card, #tab-plugins [data-plugin]').length;
      if (builtinCount > 0) window.hpmUpdateCount('builtin', builtinCount);
    }
    if (document.getElementById('tab-widgets')) {
      const widgetCount = document.querySelectorAll('#tab-widgets .toggle-row, #tab-widgets .widget-card, #tab-widgets [data-widget]').length;
      if (widgetCount > 0) window.hpmUpdateCount('widgets', widgetCount);
    }
  }, 1000);
};

window.hpmUpdateCount = function(tabId, count) {
  const el = document.getElementById(`hpm-cnt-${tabId}`);
  if (el) {
    el.textContent = `(${count})`;
  }
  localStorage.setItem(`hpm-cache-cnt-${tabId}`, count);
};

window.hpmSwitchTab = async function(tabId) {
  // Update buttons
  const btnPackages = document.getElementById('hpm-tab-btn-packages');
  const btnBuiltin  = document.getElementById('hpm-tab-btn-builtin');
  const btnWidgets  = document.getElementById('hpm-tab-btn-widgets');
  const btnStore    = document.getElementById('hpm-tab-btn-store');

  [btnPackages, btnBuiltin, btnWidgets, btnStore].forEach(b => b && b.classList.remove('active'));
  const activeBtn = document.getElementById(`hpm-tab-btn-${tabId}`);
  if (activeBtn) activeBtn.classList.add('active');

  // Update panes
  document.getElementById('hpm-pane-packages').style.display = tabId === 'packages' ? 'block' : 'none';
  document.getElementById('hpm-pane-builtin').style.display  = tabId === 'builtin'  ? 'block' : 'none';
  const widgetsPane = document.getElementById('hpm-pane-widgets');
  if (widgetsPane) widgetsPane.style.display = tabId === 'widgets' ? 'block' : 'none';
  const storePane = document.getElementById('hpm-pane-store');
  if (storePane) storePane.style.display = tabId === 'store' ? 'block' : 'none';

  // ── Content loading per tab ────────────────────────────────────────────────
  if (tabId === 'packages') {
    if (typeof window.hpmLoadPackages === 'function') window.hpmLoadPackages();

  } else if (tabId === 'builtin') {
    const builtinContainer = document.getElementById('hpm-builtin-container');
    const existingTab = document.getElementById('tab-plugins');

    if (existingTab && existingTab.parentElement !== builtinContainer) {
      builtinContainer.innerHTML = '';
      builtinContainer.appendChild(existingTab);
      existingTab.classList.remove('panel');
      existingTab.style.display = 'block';
      existingTab.classList.add('active');
      if (typeof window.populatePlugins === 'function') window.populatePlugins();
      
      setTimeout(() => {
        const builtinCount = document.querySelectorAll('#tab-plugins .toggle-row, #tab-plugins .plugin-card, #tab-plugins [data-plugin]').length;
        if (builtinCount > 0) window.hpmUpdateCount('builtin', builtinCount);
      }, 500);
      
    } else if (!existingTab && builtinContainer && builtinContainer.innerHTML.trim() === '') {
      try {
        if (typeof window._loadPanel === 'function') {
          await window._loadPanel('plugins');
          const loadedTab = document.getElementById('tab-plugins');
          if (loadedTab) {
            builtinContainer.innerHTML = '';
            builtinContainer.appendChild(loadedTab);
            loadedTab.classList.remove('panel');
            loadedTab.style.display = 'block';
            loadedTab.classList.add('active');
            
            setTimeout(() => {
              const builtinCount = document.querySelectorAll('#tab-plugins .toggle-row, #tab-plugins .plugin-card, #tab-plugins [data-plugin]').length;
              if (builtinCount > 0) window.hpmUpdateCount('builtin', builtinCount);
            }, 500);
          }
        } else {
          throw new Error('_loadPanel function not found');
        }
      } catch (err) {
        builtinContainer.innerHTML = `<div style="color:var(--danger);padding:20px;">Failed to load built-in modules: ${err.message}</div>`;
      }
    }

  } else if (tabId === 'widgets') {
    const widgetsContainer = document.getElementById('hpm-widgets-container');
    const existingWidgetsTab = document.getElementById('tab-widgets');

    if (existingWidgetsTab && existingWidgetsTab.parentElement !== widgetsContainer) {
      widgetsContainer.innerHTML = '';
      widgetsContainer.appendChild(existingWidgetsTab);
      existingWidgetsTab.classList.remove('panel');
      existingWidgetsTab.style.display = 'block';
      existingWidgetsTab.classList.add('active');
      
      setTimeout(() => {
        const widgetCount = document.querySelectorAll('#tab-widgets .toggle-row, #tab-widgets .widget-card, #tab-widgets [data-widget]').length;
        if (widgetCount > 0) window.hpmUpdateCount('widgets', widgetCount);
      }, 500);
      
    } else if (!existingWidgetsTab && widgetsContainer && widgetsContainer.innerHTML.trim() === '') {
      try {
        if (typeof window._loadPanel === 'function') {
          await window._loadPanel('widgets');
          const loadedWidgetsTab = document.getElementById('tab-widgets');
          if (loadedWidgetsTab) {
            widgetsContainer.innerHTML = '';
            widgetsContainer.appendChild(loadedWidgetsTab);
            loadedWidgetsTab.classList.remove('panel');
            loadedWidgetsTab.style.display = 'block';
            loadedWidgetsTab.classList.add('active');
            
            setTimeout(() => {
              const widgetCount = document.querySelectorAll('#tab-widgets .toggle-row, #tab-widgets .widget-card, #tab-widgets [data-widget]').length;
              if (widgetCount > 0) window.hpmUpdateCount('widgets', widgetCount);
            }, 500);
          }
        } else {
          throw new Error('_loadPanel function not found');
        }
      } catch (err) {
        widgetsContainer.innerHTML = `<div style="color:var(--danger);padding:20px;">Failed to load Widget Manager: ${err.message}</div>`;
      }
    }
  } else if (tabId === 'store') {
    if (typeof window.hpmStoreInit === 'function') {
      if (!window.HPM_STORE_STATE || !window.HPM_STORE_STATE.catalog) {
        window.hpmStoreInit();
      }
    }
  }
};


window.hpmLoadPackages = async function (forceRefresh = false) {
  const grid = document.getElementById('hpm-packages-grid');
  if (!grid) return;

  // ── Stale-while-revalidate: show cached data immediately ─────────────────
  if (window._packages && window._packages.length > 0 && !forceRefresh) {
    // Render what we have right now — zero latency
    if (typeof window.hpmRenderHierarchy === 'function') {
      grid.innerHTML = window.hpmRenderHierarchy(window._packages);
    }
    window.hpmUpdateCount('packages', window._packages.length);

    // Then silently re-fetch in background and update only if changed
    try {
      const resp  = await fetch('/api/packages/all');
      const data  = await resp.json();
      if (!data.ok) return;
      const fresh = JSON.stringify(data.packages || []);
      const stale = JSON.stringify(window._packages);
      if (fresh !== stale) {
        window._packages = data.packages || [];
        window.hpmUpdateCount('packages', window._packages.length);
        if (typeof window.hpmRenderHierarchy === 'function') {
          grid.innerHTML = window.hpmRenderHierarchy(window._packages);
        }
        _hpmCheckUpdatesBackground(window._packages);
      }
    } catch (_) { /* silent — keep showing stale */ }
    return;
  }
  // ─────────────────────────────────────────────────────────────────────────

  // First load (no cache) — show spinner
  grid.innerHTML = `
    <div style="text-align:center;padding:30px;color:var(--muted);">
      <i class="fas fa-spinner fa-spin" style="font-size: 1.5em;"></i>
    </div>`;

  try {
    const resp = await fetch('/api/packages/all');
    const data = await resp.json();
    if (!data.ok) throw new Error(data.error || 'Unknown error');

    const packages = data.packages || [];
    window._packages = packages;

    window.hpmUpdateCount('packages', packages.length);

    if (packages.length === 0) {
      grid.innerHTML = `
        <div style="text-align:center;padding:40px;color:var(--muted);">
          <i class="fas fa-box-open" style="font-size:2em;margin-bottom:10px;display:block;opacity:0.4;"></i>
          <div style="font-size:0.9em;">${window.HPM_I18N?.no_modules || 'No modules found.'}</div>
        </div>`;
      return;
    }

    if (typeof window.hpmRenderHierarchy === 'function') {
      grid.innerHTML = window.hpmRenderHierarchy(packages);
    }

    _hpmCheckUpdatesBackground(packages);

  } catch (err) {
    grid.innerHTML = `
      <div style="color:var(--danger,#ef4444);padding:16px;text-align:center;font-size:0.85em;">
        <i class="fas fa-exclamation-triangle" style="margin-right:6px;"></i>
        ${window.HPM_I18N?.failed_load || 'Failed to load modules:'} ${err.message}
      </div>`;
  }
};

/**
 * Checks the store catalog for updates.
 * @param {Array}   packages     - The currently loaded packages array
 * @param {boolean} showFeedback - If true, shows toasts and button spinner (manual call)
 */
async function _hpmCheckUpdatesBackground(packages, showFeedback = false) {
  const checkBtn = document.querySelector('button[onclick*="hpmCheckUpdates"]');

  if (showFeedback && checkBtn) {
    checkBtn.disabled = true;
    checkBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
    checkBtn.title = window.HPM_I18N?.btn_checking || 'Checking…';
  }

  try {
    // Force a fresh catalog fetch when called manually, use cache otherwise
    const url = showFeedback ? '/api/hpm/store/catalog?refresh=1' : '/api/hpm/store/catalog';
    const resp = await fetch(url);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();
    if (!data.ok || !data.catalog) throw new Error(data.error || 'Invalid catalog');

    const catalogPkgs = data.catalog.packages || [];
    window.hpmUpdateCount('store', catalogPkgs.length);
    const catalogMap = {};
    catalogPkgs.forEach(p => { catalogMap[p.id] = p.version; });

    let updatesFound = 0;

    packages.forEach(pkg => {
      const catalogVersion = catalogMap[pkg.id];
      if (!catalogVersion || pkg.version === 'built-in') return;

      const hasUpdate = catalogVersion !== pkg.version;
      pkg.update_available = hasUpdate;
      pkg.catalog_version = catalogVersion;

      if (hasUpdate) {
        updatesFound++;
        // Inject update badge into the already-rendered card
        const card = document.getElementById(`hpm-pkg-${pkg.id}`);
        if (card && !card.querySelector('.hpm-update-badge')) {
          const actionsDiv = card.querySelector('.hpm-card-actions');
          if (actionsDiv) {
            const badge = document.createElement('button');
            badge.className = 'hpm-update-badge btn btn-sm';
            badge.title = `Update to v${catalogVersion}`;
            badge.style.cssText = `
              background:linear-gradient(135deg,#f59e0b,#d97706);
              color:#fff;border:none;border-radius:6px;
              padding:4px 9px;font-size:10px;font-weight:700;
              cursor:pointer;margin-right:4px;display:inline-flex;
              align-items:center;gap:4px;`;
            badge.innerHTML = `<i class="fas fa-arrow-up"></i> v${catalogVersion}`;
            badge.onclick = () => {
              if (typeof window.hpmSwitchTab === 'function') {
                window.hpmSwitchTab('store');
                setTimeout(() => {
                  const catalogPkg = catalogPkgs.find(p => p.id === pkg.id);
                  if (catalogPkg && typeof window.hpmStoreInstall === 'function') {
                    window.hpmStoreInstall(catalogPkg.id, catalogPkg.download_url, catalogPkg.name);
                  }
                }, 800);
              }
            };
            actionsDiv.prepend(badge);
          }
        }
      }
    });

    // ── Update the Store tab button badge ────────────────────────────────────
    const storeBtn = document.getElementById('hpm-tab-btn-store');
    if (storeBtn) {
      // Remove old NEW badge or update count
      storeBtn.querySelectorAll('span').forEach(s => s.remove());
      if (updatesFound > 0) {
        const updateBadge = document.createElement('span');
        updateBadge.className = 'hpm-update-count';
        updateBadge.style.cssText = `
          position:absolute;top:-6px;right:-6px;
          background:#f59e0b;color:#000;
          font-size:0.55em;font-weight:800;padding:2px 5px;
          border-radius:6px;letter-spacing:.5px;`;
        updateBadge.textContent = updatesFound;
        storeBtn.appendChild(updateBadge);
      }
    }

    // ── Feedback toast (only on manual call) ─────────────────────────────────
    if (showFeedback) {
      if (updatesFound > 0) {
        const names = packages
          .filter(p => p.update_available)
          .map(p => p.name)
          .join(', ');
        const availStr = updatesFound === 1 
            ? (window.HPM_I18N?.update_avail_single || 'update available')
            : (window.HPM_I18N?.update_avail_plural || 'updates available');
        _hpmShowUpdateToast(
          `⬆️ ${updatesFound} ${availStr}: ${names}`,
          'update'
        );
      } else {
        _hpmShowUpdateToast(window.HPM_I18N?.update_all_ok || 'All modules are up to date!', 'ok');
      }
    }

  } catch (e) {
    console.debug('[HPM] Update check failed:', e.message);
    if (showFeedback) {
      _hpmShowUpdateToast(window.HPM_I18N?.update_offline || 'Cannot contact the Store. Check your connection.', 'warn');
    }
  } finally {
    // Restore button
    if (showFeedback && checkBtn) {
      checkBtn.disabled = false;
      checkBtn.innerHTML = '<i class="fas fa-arrow-circle-up"></i>';
      checkBtn.title = window.HPM_I18N?.btn_check_updates || 'Check for updates';
    }
  }
}

/** Tiny inline toast shown below the packages header — auto-dismisses after 4s */
function _hpmShowUpdateToast(msg, type) {
  // Remove any previous toast
  document.getElementById('hpm-update-toast')?.remove();

  const colors = {
    ok:     { bg: 'rgba(16,185,129,.12)', border: '#10b981', text: '#10b981' },
    update: { bg: 'rgba(245,158,11,.12)', border: '#f59e0b', text: '#f59e0b' },
    warn:   { bg: 'rgba(239,68,68,.1)',   border: '#ef4444', text: '#ef4444' },
  };
  const c = colors[type] || colors.ok;

  const toast = document.createElement('div');
  toast.id = 'hpm-update-toast';
  toast.style.cssText = `
    margin-top:10px;padding:10px 16px;border-radius:10px;
    background:${c.bg};border:1px solid ${c.border};
    color:${c.text};font-size:0.83em;font-weight:600;
    display:flex;align-items:center;justify-content:space-between;
    animation:fadeIn .2s ease;`;
  toast.innerHTML = `
    <span>${msg}</span>
    <button onclick="this.parentElement.remove()"
            style="background:none;border:none;color:${c.text};cursor:pointer;font-size:14px;padding:0 0 0 10px;opacity:.7;">✕</button>`;

  // Insert after the packages card header (before the grid)
  const grid = document.getElementById('hpm-packages-grid');
  if (grid && grid.parentElement) {
    grid.parentElement.insertBefore(toast, grid);
  }

  // Auto-dismiss after 5s
  setTimeout(() => toast.remove(), 5000);
}

// ── Public API ────────────────────────────────────────────────────────────────
// Called automatically (silent) or manually from the button (with feedback)
window.hpmCheckUpdates = function(packages, manual = true) {
  if (!packages && window._packages) packages = window._packages;
  if (!packages || packages.length === 0) {
    if (manual) _hpmShowUpdateToast(window.HPM_I18N?.update_no_modules || 'No modules loaded. Refresh the list first.', 'warn');
    return;
  }
  _hpmCheckUpdatesBackground(packages, manual);
};




// ── Auto-init ─────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', window.hpmInit);
if (document.readyState !== 'loading') {
  window.hpmInit();
}
