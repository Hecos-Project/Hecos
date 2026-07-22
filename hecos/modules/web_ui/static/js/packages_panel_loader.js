/**
 * packages_panel_loader.js
 * ─────────────────────────────────────────────────────────────────────────────
 * Data loading logic for Hecos Package Manager Frontend
 */

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

    // Load pagination setting if available, otherwise default to 50
    const pageSizeSetting = localStorage.getItem('hpm_page_size');
    window.HPM_STATE.pageSize = pageSizeSetting ? parseInt(pageSizeSetting) : 50;
    window.HPM_STATE.paginationEnabled = window._packages.length > window.HPM_STATE.pageSize;
    
    window.HPM_STATE.filteredPackages = [...window._packages];
    
    // Set initial view mode based on saved state
    window.hpmSetViewMode(window.HPM_STATE.viewMode);
    
    // Render filter bars
    window.hpmRenderFilterBars();

    if (typeof window.hpmRenderHierarchy === 'function') {
      window.hpmApplyFilters(); // This will call hpmRenderHierarchy with filters and pagination
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
