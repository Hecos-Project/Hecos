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
  core_module: { label: 'Core',        icon: 'fa-microchip',         color: '#66fcf1' },
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
window.hpmStoreLoad = async function (forceRefresh = false) {
  _hpmStoreShowLoading();
  try {
    const url = `/api/hpm/store/catalog${forceRefresh ? '?refresh=1' : ''}`;
    const resp = await fetch(url);
    const data = await resp.json();
    if (!data.ok) throw new Error(data.error || 'Unknown error');

    const catalog = data.catalog;
    window.HPM_STORE_STATE.catalog = catalog;
    window.HPM_STORE_STATE.filtered = catalog.packages || [];
    if (data.offline) _hpmStoreShowBanner('⚠️ Offline mode — showing cached catalog', 'warning');
    _hpmStoreBuildTypeFilters(catalog.packages || []);
    _hpmStoreApplyFilters();
  } catch (err) {
    _hpmStoreShowError(err.message);
  }
};

// ── Filtering & Search ────────────────────────────────────────────────────────
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
        <input id="hpm-store-search" type="text" placeholder="Search modules…"
               name="hpm_store_search_q" autocomplete="off" autocorrect="off" autocapitalize="off"
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
function _hpmStoreBuildDetailModal() {
  const closeLabel = _t('Close', 'Chiudi', 'Cerrar');
  return `
    <div id="hpm-store-detail-modal"
         style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.85);z-index:9999;
                align-items:flex-start;justify-content:center;padding:24px;overflow-y:auto;"
         onclick="if(event.target===this)this.style.display='none'">
      <div style="background:var(--bg2);border:1px solid var(--border-color);border-radius:20px;
                  max-width:800px;width:100%;margin:auto;box-shadow:0 32px 80px rgba(0,0,0,.75);
                  position:relative;overflow:hidden;">

        <!-- Accent band -->
        <div id="hpm-detail-band" style="height:5px;background:linear-gradient(90deg,var(--accent),#7c3aed);"></div>

        <!-- Close X -->
        <button onclick="document.getElementById('hpm-store-detail-modal').style.display='none'"
                style="position:absolute;top:14px;right:14px;background:rgba(255,255,255,.08);border:none;
                       border-radius:50%;width:32px;height:32px;color:var(--text);font-size:1em;cursor:pointer;
                       display:flex;align-items:center;justify-content:center;z-index:2;transition:background .2s;"
                onmouseover="this.style.background='rgba(255,255,255,.18)'"
                onmouseout="this.style.background='rgba(255,255,255,.08)'">
          <i class="fas fa-times"></i>
        </button>

        <!-- Package meta header -->
        <div id="hpm-detail-header" style="padding:24px 28px 0;"></div>

        <!-- Image carousel -->
        <div id="hpm-detail-carousel-wrap" style="display:none;padding:18px 28px 0;">
          <div style="position:relative;border-radius:12px;overflow:hidden;background:#060606;
                      border:1px solid rgba(255,255,255,0.08);aspect-ratio:16/9;">
            <img id="hpm-detail-carousel-img" src="" alt=""
                 style="width:100%;height:100%;object-fit:contain;display:block;cursor:zoom-in;"
                 onclick="window.open(this.src,'_blank')">
            <button id="hpm-carousel-prev" onclick="window._hpmCarouselStep(-1)"
                    style="display:none;position:absolute;left:10px;top:50%;transform:translateY(-50%);
                           background:rgba(0,0,0,.6);border:none;border-radius:50%;width:38px;height:38px;
                           color:#fff;font-size:1em;cursor:pointer;align-items:center;justify-content:center;
                           transition:background .2s;"
                    onmouseover="this.style.background='rgba(0,0,0,.9)'"
                    onmouseout="this.style.background='rgba(0,0,0,.6)'">
              <i class="fas fa-chevron-left"></i>
            </button>
            <button id="hpm-carousel-next" onclick="window._hpmCarouselStep(1)"
                    style="display:none;position:absolute;right:10px;top:50%;transform:translateY(-50%);
                           background:rgba(0,0,0,.6);border:none;border-radius:50%;width:38px;height:38px;
                           color:#fff;font-size:1em;cursor:pointer;align-items:center;justify-content:center;
                           transition:background .2s;"
                    onmouseover="this.style.background='rgba(0,0,0,.9)'"
                    onmouseout="this.style.background='rgba(0,0,0,.6)'">
              <i class="fas fa-chevron-right"></i>
            </button>
            <div id="hpm-carousel-counter"
                 style="display:none;position:absolute;bottom:10px;right:12px;background:rgba(0,0,0,.65);
                        color:#fff;font-size:0.72em;padding:3px 9px;border-radius:12px;
                        pointer-events:none;font-weight:600;letter-spacing:.4px;"></div>
          </div>
          <!-- Thumbnail strip -->
          <div id="hpm-carousel-thumbs" style="display:flex;gap:7px;margin-top:10px;overflow-x:auto;padding-bottom:4px;"></div>
        </div>

        <!-- README content -->
        <div style="padding:22px 28px 4px;">
          <div id="hpm-store-detail-content" style="color:var(--text);font-size:0.88em;line-height:1.75;"></div>
        </div>

        <!-- Footer -->
        <div style="padding:16px 28px 22px;border-top:1px solid var(--border-color);
                    display:flex;align-items:center;justify-content:flex-end;gap:10px;">
          <div id="hpm-detail-install-btn"></div>
          <button onclick="document.getElementById('hpm-store-detail-modal').style.display='none'"
                  class="btn btn-secondary" style="font-size:0.85em;">${closeLabel}</button>
        </div>
      </div>
    </div>`;
}

// ── Carousel logic ────────────────────────────────────────────────────────────
window._hpmCarouselStep = function (dir) {
  const imgs = _detailCarousel.images;
  if (!imgs.length) return;
  _detailCarousel.index = (_detailCarousel.index + dir + imgs.length) % imgs.length;
  _hpmCarouselRender();
};

window._hpmCarouselGoto = function (i) {
  _detailCarousel.index = i;
  _hpmCarouselRender();
};

function _hpmCarouselRender() {
  const { images, index } = _detailCarousel;
  const img     = document.getElementById('hpm-detail-carousel-img');
  const counter = document.getElementById('hpm-carousel-counter');
  const prev    = document.getElementById('hpm-carousel-prev');
  const next    = document.getElementById('hpm-carousel-next');
  const thumbs  = document.getElementById('hpm-carousel-thumbs');
  if (!img) return;

  img.src = images[index];
  const multi = images.length > 1;

  if (counter) { counter.textContent = `${index + 1} / ${images.length}`; counter.style.display = multi ? 'block' : 'none'; }
  if (prev)    { prev.style.display  = multi ? 'flex' : 'none'; }
  if (next)    { next.style.display  = multi ? 'flex' : 'none'; }

  if (thumbs) {
    if (multi) {
      thumbs.innerHTML = images.map((src, i) => `
        <img src="${_hesc(src)}" onclick="window._hpmCarouselGoto(${i})"
             style="width:74px;height:46px;object-fit:cover;border-radius:6px;cursor:pointer;flex-shrink:0;
                    border:2px solid ${i === index ? 'var(--accent)' : 'rgba(255,255,255,.12)'};
                    opacity:${i === index ? '1' : '0.5'};transition:opacity .2s,border-color .2s;"
             onerror="this.style.display='none'">`).join('');
    } else {
      thumbs.innerHTML = '';
    }
  }
}

// ── "Read More" / Detail show ─────────────────────────────────────────────────
window.hpmStoreShowReadMe = async function (pkgId) {
  const pkgs = window.HPM_STORE_STATE.catalog?.packages || [];
  const pkg = pkgs.find(p => p.id === pkgId);
  if (!pkg) return;

  const meta   = TYPE_META[pkg.type] || { label: pkg.type, icon: 'fa-cube', color: '#6b7280' };
  const modal  = document.getElementById('hpm-store-detail-modal');
  const content = document.getElementById('hpm-store-detail-content');
  const headerEl = document.getElementById('hpm-detail-header');
  const band   = document.getElementById('hpm-detail-band');
  const carouselWrap = document.getElementById('hpm-detail-carousel-wrap');
  const installBtn = document.getElementById('hpm-detail-install-btn');

  // Accent colour band
  if (band) band.style.background = `linear-gradient(90deg,${meta.color},${meta.color}88)`;

  // ── Package Header ────────────────────────────────────────────────────────
  const sizeFmt = pkg.size_bytes ? `${(pkg.size_bytes / 1024).toFixed(1)} KB` : '';
  const fallbackIcon = 'https://raw.githubusercontent.com/Hecos-Project/Hecos-Packages/main/Hecos_module_Image_preview_square.png';
  const iconUrl = pkg.icon_url || fallbackIcon;
  const icon = pkg.fa_icon || 'fa-cube';

  if (headerEl) headerEl.innerHTML = `
    <div style="display:flex;align-items:flex-start;gap:18px;">
      <div style="width:60px;height:60px;border-radius:16px;flex-shrink:0;background:${meta.color}18;
                  display:flex;align-items:center;justify-content:center;overflow:hidden;
                  border:1px solid ${meta.color}33;">
        <img src="${_hesc(iconUrl)}" style="width:100%;height:100%;object-fit:cover;"
             onerror="this.outerHTML='<i class=\\'fas ${icon}\\' style=\\'font-size:24px;color:${meta.color};\\'></i>'">
      </div>
      <div style="flex:1;min-width:0;">
        <div style="font-size:1.2em;font-weight:800;color:var(--text);line-height:1.2;">${_hesc(pkg.name)}</div>
        <div style="display:flex;align-items:center;gap:8px;margin-top:7px;flex-wrap:wrap;">
          <span style="font-size:0.7em;font-weight:700;letter-spacing:.6px;text-transform:uppercase;
                       color:${meta.color};background:${meta.color}18;padding:2px 8px;border-radius:5px;">
            <i class="fas ${meta.icon}" style="margin-right:4px;"></i>${meta.label}
          </span>
          <span style="font-size:0.75em;color:var(--muted);">v${_hesc(pkg.version)}</span>
          ${sizeFmt ? `<span style="font-size:0.72em;color:var(--muted);"><i class="fas fa-weight-hanging" style="margin-right:3px;opacity:.4;"></i>${sizeFmt}</span>` : ''}
          <span style="font-size:0.72em;color:var(--muted);"><i class="fas fa-user" style="margin-right:3px;opacity:.4;"></i>${_hesc(pkg.author || 'Unknown')}</span>
        </div>
        ${pkg.description ? `<div style="font-size:0.83em;color:var(--muted);margin-top:9px;line-height:1.55;">${_hesc(pkg.description)}</div>` : ''}
        ${pkg.tags && pkg.tags.length ? `
          <div style="display:flex;gap:5px;flex-wrap:wrap;margin-top:8px;">
            ${pkg.tags.map(t => `<span style="font-size:0.67em;background:rgba(255,255,255,.07);color:var(--muted);padding:2px 7px;border-radius:5px;">#${_hesc(t)}</span>`).join('')}
          </div>` : ''}
      </div>
    </div>`;

  // ── Footer Install Button ─────────────────────────────────────────────────
  if (installBtn) {
    if (!pkg.installed) {
      installBtn.innerHTML = `
        <button onclick="document.getElementById('hpm-store-detail-modal').style.display='none';window.hpmStoreInstall('${pkg.id}','${pkg.download_url}','${pkg.name}')"
                style="background:linear-gradient(135deg,var(--accent),#7c3aed);color:#fff;border:none;
                       border-radius:8px;padding:8px 20px;font-size:0.85em;font-weight:700;cursor:pointer;">
          <i class="fas fa-download" style="margin-right:6px;"></i>Install</button>`;
    } else if (pkg.update_available) {
      installBtn.innerHTML = `
        <button onclick="document.getElementById('hpm-store-detail-modal').style.display='none';window.hpmStoreInstall('${pkg.id}','${pkg.download_url}','${pkg.name}')"
                style="background:linear-gradient(135deg,#f59e0b,#d97706);color:#fff;border:none;
                       border-radius:8px;padding:8px 20px;font-size:0.85em;font-weight:700;cursor:pointer;">
          <i class="fas fa-arrow-up" style="margin-right:6px;"></i>Update to v${pkg.version}</button>`;
    } else {
      installBtn.innerHTML = `
        <span style="display:inline-flex;align-items:center;gap:6px;font-size:0.82em;color:#10b981;
                     background:rgba(16,185,129,.12);padding:7px 14px;border-radius:8px;font-weight:600;">
          <i class="fas fa-check-circle"></i> Installed</span>`;
    }
  }

  // ── Carousel ──────────────────────────────────────────────────────────────
  const fallbackShot = 'https://raw.githubusercontent.com/Hecos-Project/Hecos-Packages/main/Hecos_module_Image_preview.png';
  const screenshots  = (pkg.screenshots && pkg.screenshots.length > 0) ? pkg.screenshots : [fallbackShot];
  _detailCarousel    = { images: screenshots, index: 0 };
  if (carouselWrap) {
    carouselWrap.style.display = 'block';
    _hpmCarouselRender();
  }

  // ── Show modal + spinner ──────────────────────────────────────────────────
  modal.style.display = 'flex';
  content.innerHTML   = '<div style="text-align:center;padding:30px;"><i class="fas fa-spinner fa-spin fa-2x" style="opacity:.35;"></i></div>';

  // ── Fetch README ──────────────────────────────────────────────────────────
  let mdText = null;
  try {
    if (pkg.readme_url) {
      const res = await fetch(pkg.readme_url);
      if (res.ok) mdText = await res.text();
    }
    if (!mdText) {
      const fallbackReadme = `https://raw.githubusercontent.com/Hecos-Project/Hecos-Packages/main/${pkg.id}_src/README.md`;
      const res = await fetch(fallbackReadme);
      if (res.ok) mdText = await res.text();
    }
  } catch (e) {
    console.error('[HPM Store] Failed to fetch README', e);
  }

  if (mdText) {
    if (typeof marked !== 'undefined') {
      content.innerHTML = `
        <div class="hpm-readme-body" style="--hpm-c:${meta.color};">
          ${marked.parse(mdText)}
        </div>
        <style>
          .hpm-readme-body h1,.hpm-readme-body h2,.hpm-readme-body h3{color:var(--text);margin:1.1em 0 .4em;font-weight:700;}
          .hpm-readme-body h1{font-size:1.3em;}
          .hpm-readme-body h2{font-size:1.1em;border-bottom:1px solid var(--border-color);padding-bottom:.35em;}
          .hpm-readme-body h3{font-size:1em;}
          .hpm-readme-body a{color:var(--hpm-c);text-decoration:none;}
          .hpm-readme-body a:hover{text-decoration:underline;}
          .hpm-readme-body code{background:rgba(255,255,255,.09);padding:2px 6px;border-radius:4px;font-size:0.85em;font-family:monospace;}
          .hpm-readme-body pre{background:rgba(0,0,0,.4);border:1px solid var(--border-color);border-radius:10px;padding:16px;overflow-x:auto;margin:12px 0;}
          .hpm-readme-body pre code{background:none;padding:0;}
          .hpm-readme-body blockquote{border-left:3px solid var(--hpm-c);margin:0 0 0 4px;padding:4px 14px;color:var(--muted);font-style:italic;}
          .hpm-readme-body img{max-width:100%;border-radius:10px;margin:6px 0;}
          .hpm-readme-body table{width:100%;border-collapse:collapse;font-size:0.85em;margin:10px 0;}
          .hpm-readme-body th,.hpm-readme-body td{border:1px solid var(--border-color);padding:7px 10px;}
          .hpm-readme-body th{background:rgba(255,255,255,.06);font-weight:700;}
          .hpm-readme-body hr{border:none;border-top:1px solid var(--border-color);margin:16px 0;}
          .hpm-readme-body ul,.hpm-readme-body ol{padding-left:20px;margin:6px 0;}
          .hpm-readme-body li{margin:3px 0;}
        </style>`;
    } else {
      content.innerHTML = `<pre style="white-space:pre-wrap;font-family:inherit;font-size:0.87em;line-height:1.6;">${_hesc(mdText)}</pre>`;
    }
  } else {
    // ── Rich empty state ──────────────────────────────────────────────────
    const noDocTitle = _t('No documentation available', 'Nessuna documentazione disponibile', 'Sin documentación disponible');
    const noDocSub   = _t(
      'You can still install this module and explore its features directly.',
      'Puoi comunque installare questo modulo ed esplorarne le funzionalità.',
      'Aún puedes instalar este módulo y explorar sus funciones.'
    );
    const githubLabel = _t('View on GitHub', 'Vedi su GitHub', 'Ver en GitHub');
    content.innerHTML = `
      <div style="text-align:center;padding:36px 20px;">
        <div style="width:64px;height:64px;border-radius:50%;background:${meta.color}12;display:inline-flex;
                    align-items:center;justify-content:center;margin-bottom:16px;border:1px solid ${meta.color}25;">
          <i class="fas fa-file-alt" style="font-size:1.6em;color:${meta.color};opacity:.6;"></i>
        </div>
        <div style="font-weight:700;font-size:1.05em;color:var(--text);margin-bottom:8px;">${noDocTitle}</div>
        <div style="font-size:0.83em;color:var(--muted);line-height:1.6;max-width:380px;margin:0 auto;">${noDocSub}</div>
        ${pkg.homepage_url ? `
          <a href="${_hesc(pkg.homepage_url)}" target="_blank" rel="noopener"
             style="display:inline-flex;align-items:center;gap:7px;margin-top:20px;
                    color:${meta.color};font-size:0.83em;font-weight:600;text-decoration:none;
                    border:1px solid ${meta.color}44;padding:7px 16px;border-radius:8px;
                    transition:background .2s;" onmouseover="this.style.background='${meta.color}18'"
             onmouseout="this.style.background='transparent'">
            <i class="fas fa-external-link-alt"></i>${githubLabel}
          </a>` : ''}
      </div>`;
  }
};

// ── Progress Modal ────────────────────────────────────────────────────────────
function _hpmStoreBuildProgressModal() {
  return `
    <div id="hpm-store-progress-modal" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.85);
         z-index:10000;align-items:center;justify-content:center;padding:20px;"
         ondblclick="this.style.display='none'">
      <div style="background:var(--bg2);border:1px solid var(--border-color);border-radius:16px;
                  max-width:420px;width:100%;padding:32px;text-align:center;box-shadow:0 20px 60px rgba(0,0,0,.6);cursor:default;">
        <div id="hpm-store-progress-icon" style="font-size:2.5em;margin-bottom:16px;">
          <i class="fas fa-download" style="color:var(--accent);animation:pulse 1.5s infinite;"></i>
        </div>
        <div id="hpm-store-progress-title" style="font-weight:700;font-size:1.1em;margin-bottom:8px;color:var(--text);">Installing…</div>
        <div style="background:var(--border-color);border-radius:6px;height:6px;overflow:hidden;margin:14px 0;">
          <div id="hpm-store-progress-bar"
               style="height:100%;width:0%;background:linear-gradient(90deg,var(--accent),var(--accent2,#7c3aed));
                      border-radius:6px;transition:width .4s ease;"></div>
        </div>
        <div id="hpm-store-progress-msg" style="font-size:0.82em;color:var(--muted);min-height:1.4em;"></div>
        <div id="hpm-store-progress-hint" style="display:none;font-size:0.75em;color:var(--muted);margin-top:20px;opacity:0.6;">
          ${_t('Double click anywhere to close', 'Fai doppio clic per chiudere', 'Haz doble clic para cerrar')}
        </div>
      </div>
    </div>`;
}

// ── Install via SSE ───────────────────────────────────────────────────────────
window.hpmStoreInstall = async function (pkgId, downloadUrl, pkgName) {
  const modal = document.getElementById('hpm-store-progress-modal');
  const bar   = document.getElementById('hpm-store-progress-bar');
  const msg   = document.getElementById('hpm-store-progress-msg');
  const title = document.getElementById('hpm-store-progress-title');
  const icon  = document.getElementById('hpm-store-progress-icon');
  if (!modal) return;

  modal.style.display = 'flex';
  bar.style.width = '10%';
  bar.style.background = '';
  title.textContent = `Installing ${pkgName}…`;
  msg.textContent   = 'Connecting to store…';
  icon.innerHTML    = '<i class="fas fa-download" style="color:var(--accent);"></i>';

  const allowUnsigned = document.getElementById('hpm-allow-unsigned')?.checked || false;

  try {
    const resp = await fetch('/api/hpm/store/install', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id: pkgId, download_url: downloadUrl, allow_unsigned: allowUnsigned }),
    });

    const reader  = resp.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop();
      let event = null, dataStr = null;
      for (const line of lines) {
        if (line.startsWith('event: ')) event   = line.slice(7).trim();
        if (line.startsWith('data: '))  dataStr = line.slice(6).trim();
        if (event && dataStr) {
          try { _hpmStoreHandleSSE(event, JSON.parse(dataStr), bar, msg, title, icon, modal, pkgId); } catch {}
          event = null; dataStr = null;
        }
      }
    }
  } catch (err) {
    msg.textContent = `Error: ${err.message}`;
    icon.innerHTML  = '<i class="fas fa-times-circle" style="color:#ef4444;"></i>';
    setTimeout(() => { modal.style.display = 'none'; }, 3000);
  }
};

function _hpmStoreHandleSSE(event, payload, bar, msg, title, icon, modal) {
  if (event === 'progress') {
    msg.textContent    = payload.message || '';
    bar.style.width    = payload.step === 'download' ? '40%' : '75%';
  } else if (event === 'done') {
    bar.style.width    = '100%';
    msg.textContent    = payload.message || _t('Done!', 'Fatto!', '¡Hecho!');
    icon.innerHTML     = '<i class="fas fa-check-circle" style="color:#10b981;"></i>';
    title.textContent  = _t('Installed Successfully!', 'Installato con successo!', '¡Instalado con éxito!');
    
    const hintEl = document.getElementById('hpm-store-progress-hint');
    if (hintEl) hintEl.style.display = 'block';

    let extraHTML = '';
    if (payload.install_path) {
        const lblPath = _t('Installed in:', 'Installato in:', 'Instalado en:');
        extraHTML += `<div style="margin-top:12px; font-size: 0.95em; color: var(--text);">${lblPath}<br><code style="display:inline-block; margin-top:4px; color:var(--accent); background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); padding: 4px 8px; border-radius: 6px;">${payload.install_path}</code></div>`;
    }
    if (payload.config_panel) {
        const lblCfg = _t('Available in the Configuration menu', 'Disponibile nel menu Configurazione', 'Disponible en el menú Configuración');
        extraHTML += `<div style="margin-top:8px; font-size: 0.85em; color: var(--muted);"><i class="fas fa-cogs" style="margin-right:4px;"></i>${lblCfg}</div>`;
    }
    if (extraHTML) {
        msg.innerHTML = (payload.message || _t('Done!', 'Fatto!', '¡Hecho!')) + extraHTML;
    }

    const sound = localStorage.getItem('hpm_install_sound') || 'success.mp3';
    if (sound !== 'none') {
        if (sound.startsWith('custom|')) {
            const path = sound.substring(7);
            new Audio('/api/local_file?path=' + encodeURIComponent(path)).play().catch(() => {});
        } else {
            new Audio(`/static/sounds/${sound}`).play().catch(() => {});
        }
    }

    // Refresh store without closing modal automatically
    window.hpmStoreLoad();
    if (typeof window.hpmLoadPackages === 'function') window.hpmLoadPackages();
    if (typeof window.hpmRefreshConfigHub === 'function') window.hpmRefreshConfigHub();
  } else if (event === 'error') {
    bar.style.width    = '100%';
    bar.style.background = '#ef4444';
    msg.textContent    = payload.message || 'Installation failed.';
    icon.innerHTML     = '<i class="fas fa-times-circle" style="color:#ef4444;"></i>';
    title.textContent  = 'Installation Failed';
    setTimeout(() => { modal.style.display = 'none'; bar.style.background = ''; }, 4000);
  }
}

// ── Utilities ─────────────────────────────────────────────────────────────────
function _hesc(s) {
  return String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

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
