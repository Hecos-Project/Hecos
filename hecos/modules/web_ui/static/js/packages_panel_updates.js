/**
 * packages_panel_updates.js
 * ─────────────────────────────────────────────────────────────────────────────
 * Update checking and notification logic for Hecos Package Manager
 */

/**
 * Checks the store catalog for updates.
 * @param {Array}   packages     - The currently loaded packages array
 * @param {boolean} showFeedback - If true, shows toasts and button spinner (manual call)
 */
window._hpmCheckUpdatesBackground = async function (packages, showFeedback = false) {
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
};

/** Tiny inline toast shown below the packages header — auto-dismisses after 4s */
window._hpmShowUpdateToast = function (msg, type) {
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
};

// ── Public API ────────────────────────────────────────────────────────────────
// Called automatically (silent) or manually from the button (with feedback)
window.hpmCheckUpdates = function(packages, manual = true) {
  if (!packages && window._packages) packages = window._packages;
  if (!packages || packages.length === 0) {
    if (manual) window._hpmShowUpdateToast(window.HPM_I18N?.update_no_modules || 'No modules loaded. Refresh the list first.', 'warn');
    return;
  }
  window._hpmCheckUpdatesBackground(packages, manual);
};
