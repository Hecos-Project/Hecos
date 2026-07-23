/**
 * packages_panel_store.js
 * ─────────────────────────────────────────────────────────────────────────────
 * Hecos Package Store — Frontend Module
 * Handles: catalog loading, rendering, search/filter, detail modal, install via SSE
 */

// ── State ─────────────────────────────────────────────────────────────────────
window.HPM_STORE_STATE = window.HPM_STORE_STATE || {
  catalog: null,
  filtered: [],
  activeType: 'all',
  searchQuery: '',
};

// Carousel state for the detail modal
let _detailCarousel = { images: [], index: 0 };

const TYPE_META = {
  plugin:      { label: 'Plugin',      icon: 'fa-plug',              color: '#3b82f6' },
  extension:   { label: 'Extension',   icon: 'fa-puzzle-piece',      color: '#45a29e' },
  app:         { label: 'App',         icon: 'fa-th-large',          color: '#8b5cf6' },
  widget:      { label: 'Widget',      icon: 'fa-expand-arrows-alt', color: '#f59e0b' },
  persona:     { label: 'Persona',     icon: 'fa-user-astronaut',    color: '#ec4899' },
  theme:       { label: 'Theme',       icon: 'fa-palette',           color: '#10b981' },
  skill_pack:  { label: 'Skill Pack',  icon: 'fa-graduation-cap',    color: '#f97316' },
  core_module: { label: 'Core',        icon: 'fa-microchip',         color: '#ff4444' },
};

// ── i18n helper ───────────────────────────────────────────────────────────────
function _t(en, it, es) {
  const l = (document.documentElement.lang || 'en').toLowerCase();
  if (l.startsWith('it')) return it;
  if (l.startsWith('es')) return es;
  return en;
}

// ── Entry Point ───────────────────────────────────────────────────────────────
window.hpmStoreInit = async function () {
  const pane = document.getElementById('hpm-pane-store');
  if (!pane) return;
  pane.innerHTML = _hpmStoreBuildShell();

  const searchEl = document.getElementById('hpm-store-search');
  if (searchEl) {
    searchEl.addEventListener('input', (e) => {
      window.HPM_STORE_STATE.searchQuery = e.target.value.trim().toLowerCase();
      _hpmStoreApplyFilters();
    });
  }
  await window.hpmStoreLoad();
};

// ── Catalog Loading ───────────────────────────────────────────────────────────
window.hpmStoreSetTypeFilter = function (type) {
  window.HPM_STORE_STATE.activeType = type;
  document.querySelectorAll('.hpm-store-type-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.type === type);
  });
  _hpmStoreApplyFilters();
};

function _hpmStoreApplyFilters() {
  const { catalog, activeType, searchQuery } = window.HPM_STORE_STATE;
  if (!catalog) return;
  let pkgs = catalog.packages || [];
  if (activeType !== 'all') pkgs = pkgs.filter(p => p.type === activeType);
  if (searchQuery) {
    pkgs = pkgs.filter(p => {
      const hay = [p.name, p.description, p.author, ...(p.tags || [])].join(' ').toLowerCase();
      return hay.includes(searchQuery);
    });
  }
  window.HPM_STORE_STATE.filtered = pkgs;
  _hpmStoreRenderGrid(pkgs);
}

// ── Shell ─────────────────────────────────────────────────────────────────────
function _hpmStoreBuildShell() {
  return `
    <div id="hpm-store-offline-banner" style="display:none;"></div>
    <div style="display:flex;align-items:center;gap:12px;margin-bottom:18px;flex-wrap:wrap;">
      <div style="position:relative;flex:1;min-width:220px;">
        <i class="fas fa-search" style="position:absolute;left:12px;top:50%;transform:translateY(-50%);color:var(--muted);font-size:13px;pointer-events:none;"></i>
        <input id="hpm-store-search" type="search" placeholder="Search modules…"
               name="hpm_store_search_q_nope" autocomplete="off" autocorrect="off" autocapitalize="off" spellcheck="false" data-lpignore="true" data-1p-ignore="true"
               style="width:100%;box-sizing:border-box;background:var(--bg2);border:1px solid var(--border-color);
                      border-radius:10px;padding:9px 12px 9px 34px;color:var(--text);font-size:0.88em;outline:none;transition:border-color .2s;"
               onfocus="this.style.borderColor='var(--accent)'"
               onblur="this.style.borderColor='var(--border-color)'">
      </div>
      <button class="btn btn-sm btn-outline" onclick="window.hpmStoreLoad(true)" title="Force refresh catalog">
        <i class="fas fa-sync-alt"></i>
      </button>
    </div>
    <div id="hpm-store-type-filters" style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:20px;"></div>
    <div id="hpm-store-grid" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:14px;">
      <div style="text-align:center;padding:50px;color:var(--muted);grid-column:1/-1;">
        <i class="fas fa-spinner fa-spin" style="font-size:1.8em;opacity:.4;"></i>
      </div>
    </div>
    ${_hpmStoreBuildDetailModal()}
    ${_hpmStoreBuildProgressModal()}`;
}

// ── Type Filters ──────────────────────────────────────────────────────────────
function _hpmStoreBuildTypeFilters(packages) {
  const container = document.getElementById('hpm-store-type-filters');
  if (!container) return;
  const types = ['all', ...new Set(packages.map(p => p.type))];
  const counts = {};
  packages.forEach(p => { counts[p.type] = (counts[p.type] || 0) + 1; });
  container.innerHTML = types.map(type => {
    const meta = TYPE_META[type] || { label: type, icon: 'fa-cube', color: '#6b7280' };
    const count = type === 'all' ? packages.length : (counts[type] || 0);
    const isActive = window.HPM_STORE_STATE.activeType === type;
    return `
      <button class="hpm-store-type-btn filter-btn ${isActive ? 'active' : ''}"
              data-type="${type}" onclick="window.hpmStoreSetTypeFilter('${type}')"
              style="display:inline-flex;align-items:center;gap:6px;font-size:0.8em;">
        ${type !== 'all' ? `<i class="fas ${meta.icon}" style="color:${meta.color};"></i>` : '<i class="fas fa-border-all"></i>'}
        ${type === 'all' ? 'All' : meta.label}
        <span style="background:rgba(255,255,255,0.1);padding:1px 6px;border-radius:10px;font-size:0.85em;">${count}</span>
      </button>`;
  }).join('');
}

// ── Card Grid ─────────────────────────────────────────────────────────────────
function _hpmStoreRenderGrid(packages) {
  const grid = document.getElementById('hpm-store-grid');
  if (!grid) return;
  if (packages.length === 0) {
    grid.innerHTML = `
      <div style="text-align:center;padding:50px;color:var(--muted);grid-column:1/-1;">
        <i class="fas fa-box-open" style="font-size:2.5em;opacity:.3;display:block;margin-bottom:12px;"></i>
        <div style="font-size:0.9em;">No modules found.</div>
      </div>`;
    return;
  }
  grid.innerHTML = packages.map(pkg => _hpmStoreRenderCard(pkg)).join('');
}

function _hpmStoreRenderCard(pkg) {
  const meta = TYPE_META[pkg.type] || { label: pkg.type, icon: 'fa-cube', color: '#6b7280' };
  const sizeFmt = pkg.size_bytes ? `${(pkg.size_bytes / 1024).toFixed(1)} KB` : '';
  const icon = pkg.fa_icon || 'fa-cube';
  const fallbackIcon = 'https://raw.githubusercontent.com/Hecos-Project/Hecos-Packages/main/Hecos_module_Image_preview_square.png';
  const fallbackScreenshot = 'https://raw.githubusercontent.com/Hecos-Project/Hecos-Packages/main/Hecos_module_Image_preview.png';
  const finalIconUrl = pkg.icon_url || fallbackIcon;
  const screenshots = (pkg.screenshots && pkg.screenshots.length > 0) ? pkg.screenshots : [fallbackScreenshot];
  const hasMultiple = screenshots.length > 1;

  const actionBtn = pkg.installed
    ? pkg.update_available
      ? `<button onclick="window.hpmStoreInstall('${pkg.id}','${pkg.download_url}','${pkg.name}')"
                style="background:linear-gradient(135deg,#f59e0b,#d97706);color:#fff;border:none;border-radius:8px;padding:7px 14px;font-size:0.78em;font-weight:700;cursor:pointer;">
           <i class="fas fa-arrow-up" style="margin-right:4px;"></i>Update to v${pkg.version}</button>`
      : `<span style="display:inline-flex;align-items:center;gap:5px;font-size:0.8em;color:#10b981;background:rgba(16,185,129,.12);padding:6px 12px;border-radius:8px;font-weight:600;">
           <i class="fas fa-check-circle"></i> Installed</span>`
    : `<button onclick="window.hpmStoreInstall('${pkg.id}','${pkg.download_url}','${pkg.name}')"
              style="background:linear-gradient(135deg,var(--accent),var(--accent2,#7c3aed));color:#fff;border:none;border-radius:8px;padding:7px 14px;font-size:0.78em;font-weight:700;cursor:pointer;transition:opacity .2s;"
              onmouseover="this.style.opacity='.85'" onmouseout="this.style.opacity='1'">
         <i class="fas fa-download" style="margin-right:4px;"></i>Install</button>`;

  const readMoreLabel = _t('Read more', 'Leggi di più', 'Leer más');

  return `
    <div class="hpm-store-card" style="background:var(--bg2);border:1px solid var(--border-color);border-radius:14px;
         padding:18px;display:flex;flex-direction:column;gap:14px;transition:border-color .2s,box-shadow .2s;"
         onmouseover="this.style.borderColor='${meta.color}55';this.style.boxShadow='0 4px 20px ${meta.color}22';"
         onmouseout="this.style.borderColor='var(--border-color)';this.style.boxShadow='none';">

      <!-- Header -->
      <div style="display:flex;align-items:flex-start;gap:13px;">
        <div style="width:44px;height:44px;border-radius:12px;flex-shrink:0;background:${meta.color}20;
                    display:flex;align-items:center;justify-content:center;overflow:hidden;">
          <img src="${_hesc(finalIconUrl)}" style="width:100%;height:100%;object-fit:cover;border-radius:12px;"
               onerror="this.outerHTML='<i class=\\'fas ${icon}\\' style=\\'color:${meta.color};font-size:18px;\\'></i>'">
        </div>
        <div style="flex:1;min-width:0;">
          <div style="font-weight:700;color:var(--text);font-size:0.95em;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${_hesc(pkg.name)}</div>
          <div style="display:flex;align-items:center;gap:6px;margin-top:3px;flex-wrap:wrap;">
            <span style="font-size:0.7em;font-weight:700;letter-spacing:.6px;text-transform:uppercase;color:${meta.color};background:${meta.color}18;padding:2px 7px;border-radius:5px;">${meta.label}</span>
            <span style="font-size:0.72em;color:var(--muted);">v${_hesc(pkg.version)}</span>
            ${sizeFmt ? `<span style="font-size:0.7em;color:var(--muted);">${sizeFmt}</span>` : ''}
          </div>
        </div>
      </div>

      <!-- Screenshot (first image + multi-counter badge) -->
      <div style="width:100%;aspect-ratio:16/9;border-radius:8px;overflow:hidden;border:1px solid rgba(255,255,255,0.08);
                  background:#050505;display:flex;align-items:center;justify-content:center;position:relative;cursor:pointer;"
           onclick="window.hpmStoreShowReadMe('${pkg.id}')">
        <img src="${_hesc(screenshots[0])}" style="width:100%;height:100%;object-fit:contain;padding:8px;box-sizing:border-box;
             transition:transform 0.3s ease;" onmouseover="this.style.transform='scale(1.04)'" onmouseout="this.style.transform='scale(1)'"
             loading="lazy" onerror="this.parentElement.style.display='none'">
        ${hasMultiple ? `<div style="position:absolute;bottom:7px;right:9px;background:rgba(0,0,0,.65);color:#fff;font-size:0.68em;padding:2px 8px;border-radius:10px;pointer-events:none;font-weight:600;">1 / ${screenshots.length}</div>` : ''}
      </div>

      <!-- Description -->
      <div style="font-size:0.8em;color:var(--muted);line-height:1.5;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;">
        ${_hesc(pkg.description || 'No description available.')}
      </div>
      <div style="margin-top:-6px;text-align:right;">
        <span onclick="window.hpmStoreShowReadMe('${pkg.id}')" style="font-size:0.75em;color:var(--accent);cursor:pointer;font-weight:600;">
          ${readMoreLabel} <i class="fas fa-chevron-right" style="font-size:0.8em;margin-left:2px;"></i>
        </span>
      </div>

      <!-- Tags -->
      ${pkg.tags && pkg.tags.length ? `
        <div style="display:flex;gap:5px;flex-wrap:wrap;">
          ${pkg.tags.slice(0, 4).map(t => `<span style="font-size:0.68em;background:rgba(255,255,255,.06);color:var(--muted);padding:2px 7px;border-radius:5px;">#${_hesc(t)}</span>`).join('')}
        </div>` : ''}

      <!-- Footer -->
      <div style="display:flex;align-items:center;justify-content:space-between;margin-top:auto;padding-top:4px;border-top:1px solid var(--border-color);">
        <div style="font-size:0.72em;color:var(--muted);">
          <i class="fas fa-user" style="margin-right:4px;opacity:.5;"></i>${_hesc(pkg.author || 'Unknown')}
        </div>
        ${actionBtn}
      </div>
    </div>`;
}

// ── Detail Modal HTML skeleton ────────────────────────────────────────────────
function _hpmStoreShowLoading() {
  const grid = document.getElementById('hpm-store-grid');
  if (grid) grid.innerHTML = `
    <div style="text-align:center;padding:50px;color:var(--muted);grid-column:1/-1;">
      <i class="fas fa-spinner fa-spin" style="font-size:1.8em;opacity:.4;"></i>
      <div style="margin-top:10px;font-size:0.85em;">Loading catalog…</div>
    </div>`;
}

function _hpmStoreShowError(errMsg) {
  const grid = document.getElementById('hpm-store-grid');
  if (grid) grid.innerHTML = `
    <div style="text-align:center;padding:50px;color:var(--muted);grid-column:1/-1;">
      <i class="fas fa-exclamation-triangle" style="font-size:2em;color:#f59e0b;opacity:.7;display:block;margin-bottom:10px;"></i>
      <div style="font-size:0.85em;">Could not load store catalog.<br><span style="opacity:.6;">${_hesc(errMsg)}</span></div>
      <button onclick="window.hpmStoreLoad()" class="btn btn-sm btn-outline" style="margin-top:14px;">Retry</button>
    </div>`;
}

function _hpmStoreShowBanner(text, type) {
  const banner = document.getElementById('hpm-store-offline-banner');
  if (!banner) return;
  const color = type === 'warning' ? '#f59e0b' : 'var(--accent)';
  banner.innerHTML = `
    <div style="background:${color}18;border:1px solid ${color}44;color:${color};border-radius:8px;
                padding:10px 14px;font-size:0.82em;margin-bottom:14px;">
      <i class="fas fa-wifi" style="margin-right:6px;"></i>${_hesc(text)}
    </div>`;
  banner.style.display = 'block';
}

document.addEventListener('hpmProgressUpdate', (e) => {
    const modal = document.getElementById('hpm-store-progress-modal');
    if (modal && modal.style.display !== 'none') {
        const msg = document.getElementById('hpm-store-progress-msg');
        if (msg) msg.textContent = e.detail.message || e.detail.step || '';
    }
});
