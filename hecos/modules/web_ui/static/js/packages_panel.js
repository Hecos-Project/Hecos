/**
 * packages_panel.js
 * ─────────────────────────────────────────────────────────────────────────────
 * Orchestrator for Hecos Package Manager Frontend
 */

window.hpmInit = function () {
  window.hpmSwitchTab('packages');
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


window.hpmLoadPackages = async function () {
  const grid = document.getElementById('hpm-packages-grid');
  if (!grid) return;

  grid.innerHTML = `
    <div style="text-align:center;padding:30px;color:var(--muted);">
      <i class="fas fa-spinner fa-spin" style="font-size: 1.5em;"></i>
    </div>`;

  try {
    const resp = await fetch('/api/packages/all');
    const data = await resp.json();
    if (!data.ok) throw new Error(data.error || 'Unknown error');

    const packages = data.packages || [];
    window._packages = packages; // Store globally for toggle and uninstall logic
    
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

    // Silently check for updates in background (non-blocking)
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
 * Silently checks the store catalog for updates and patches the rendered cards.
 * Does NOT block the initial render.
 */
async function _hpmCheckUpdatesBackground(packages) {
  try {
    // Use cached catalog if available, or fetch a fresh one
    const url = '/api/hpm/store/catalog';
    const resp = await fetch(url);
    if (!resp.ok) return;
    const data = await resp.json();
    if (!data.ok || !data.catalog) return;

    const catalogPkgs = data.catalog.packages || [];
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
        // Inject a small update badge into the already-rendered card
        const card = document.getElementById(`hpm-pkg-${pkg.id}`);
        if (card && !card.querySelector('.hpm-update-badge')) {
          const actionsDiv = card.querySelector('div[style*="flex-shrink:0"]');
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
              // Switch to Store tab and trigger install
              if (typeof window.hpmSwitchTab === 'function') {
                window.hpmSwitchTab('store');
                // Wait for store to init then install
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

    // Update the Store tab button badge
    if (updatesFound > 0) {
      const storeBtn = document.getElementById('hpm-tab-btn-store');
      if (storeBtn) {
        const existingBadge = storeBtn.querySelector('.hpm-update-count');
        if (!existingBadge) {
          const updateBadge = document.createElement('span');
          updateBadge.className = 'hpm-update-count';
          updateBadge.style.cssText = `
            position:absolute;top:-6px;right:-6px;
            background:#f59e0b;color:#000;
            font-size:0.55em;font-weight:800;padding:2px 5px;
            border-radius:6px;letter-spacing:.5px;`;
          updateBadge.textContent = updatesFound;
          storeBtn.querySelector('span')?.remove(); // Remove "NEW" badge
          storeBtn.appendChild(updateBadge);
        } else {
          existingBadge.textContent = updatesFound;
        }
      }
    }
  } catch (e) {
    // Silently fail — store might be offline
    console.debug('[HPM] Update check failed (offline?):', e.message);
  }
}

window.hpmCheckUpdates = _hpmCheckUpdatesBackground;


// ── Auto-init ─────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', window.hpmInit);
if (document.readyState !== 'loading') {
  window.hpmInit();
}
