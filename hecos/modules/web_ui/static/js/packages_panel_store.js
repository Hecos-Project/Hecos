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

const TYPE_META = {
  plugin:      { label: 'Plugin',      icon: 'fa-plug',         color: '#3b82f6' },
  extension:   { label: 'Extension',   icon: 'fa-puzzle-piece', color: '#45a29e' },
  app:         { label: 'App',         icon: 'fa-th-large',     color: '#8b5cf6' },
  widget:      { label: 'Widget',      icon: 'fa-expand-arrows-alt', color: '#f59e0b' },
  persona:     { label: 'Persona',     icon: 'fa-user-astronaut', color: '#ec4899' },
  theme:       { label: 'Theme',       icon: 'fa-palette',      color: '#10b981' },
  skill_pack:  { label: 'Skill Pack',  icon: 'fa-graduation-cap', color: '#f97316' },
  core_module: { label: 'Core',        icon: 'fa-microchip',    color: '#66fcf1' },
};

// ── Entry Point ───────────────────────────────────────────────────────────────

window.hpmStoreInit = async function () {
  const pane = document.getElementById('hpm-pane-store');
  if (!pane) return;

  // Render the skeleton UI
  pane.innerHTML = _hpmStoreBuildShell();

  // Wire up the search box
  const searchEl = document.getElementById('hpm-store-search');
  if (searchEl) {
    searchEl.addEventListener('input', (e) => {
      window.HPM_STORE_STATE.searchQuery = e.target.value.trim().toLowerCase();
      _hpmStoreApplyFilters();
    });
  }

  // Load catalog
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

    if (data.offline) {
      _hpmStoreShowBanner('⚠️ Offline mode — showing cached catalog', 'warning');
    }

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

  if (activeType !== 'all') {
    pkgs = pkgs.filter(p => p.type === activeType);
  }

  if (searchQuery) {
    pkgs = pkgs.filter(p => {
      const hay = [p.name, p.description, p.author, ...(p.tags || [])].join(' ').toLowerCase();
      return hay.includes(searchQuery);
    });
  }

  window.HPM_STORE_STATE.filtered = pkgs;
  _hpmStoreRenderGrid(pkgs);
}

// ── Rendering ─────────────────────────────────────────────────────────────────

function _hpmStoreBuildShell() {
  return `
    <div id="hpm-store-offline-banner" style="display:none;"></div>

    <!-- Header bar -->
    <div style="display:flex; align-items:center; gap:12px; margin-bottom:18px; flex-wrap:wrap;">
      <div style="position:relative; flex:1; min-width:220px;">
        <i class="fas fa-search" style="position:absolute;left:12px;top:50%;transform:translateY(-50%);color:var(--muted);font-size:13px;pointer-events:none;"></i>
        <input id="hpm-store-search" type="text" placeholder="Search modules…"
               style="width:100%;box-sizing:border-box;background:var(--bg2);border:1px solid var(--border-color);
                      border-radius:10px;padding:9px 12px 9px 34px;color:var(--text);font-size:0.88em;outline:none;
                      transition:border-color .2s;"
               onfocus="this.style.borderColor='var(--accent)'"
               onblur="this.style.borderColor='var(--border-color)'">
      </div>
      <button class="btn btn-sm btn-outline" onclick="window.hpmStoreLoad(true)" title="Force refresh catalog">
        <i class="fas fa-sync-alt"></i>
      </button>
    </div>

    <!-- Type filter pills -->
    <div id="hpm-store-type-filters" style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:20px;"></div>

    <!-- Package grid -->
    <div id="hpm-store-grid" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:14px;">
      <div style="text-align:center;padding:50px;color:var(--muted);grid-column:1/-1;">
        <i class="fas fa-spinner fa-spin" style="font-size:1.8em;opacity:.4;"></i>
      </div>
    </div>

    <!-- Detail Modal -->
    ${_hpmStoreBuildDetailModal()}
    <!-- Install Progress Modal -->
    ${_hpmStoreBuildProgressModal()}
  `;
}

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
              data-type="${type}"
              onclick="window.hpmStoreSetTypeFilter('${type}')"
              style="display:inline-flex;align-items:center;gap:6px;font-size:0.8em;">
        ${type !== 'all' ? `<i class="fas ${meta.icon}" style="color:${meta.color};"></i>` : '<i class="fas fa-border-all"></i>'}
        ${type === 'all' ? 'All' : meta.label}
        <span style="background:rgba(255,255,255,0.1);padding:1px 6px;border-radius:10px;font-size:0.85em;">${count}</span>
      </button>`;
  }).join('');
}

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

  const actionBtn = pkg.installed
    ? pkg.update_available
      ? `<button onclick="window.hpmStoreInstall('${pkg.id}','${pkg.download_url}','${pkg.name}')"
                style="background:linear-gradient(135deg,#f59e0b,#d97706);color:#fff;border:none;
                       border-radius:8px;padding:7px 14px;font-size:0.78em;font-weight:700;cursor:pointer;">
           <i class="fas fa-arrow-up" style="margin-right:4px;"></i> Update to v${pkg.version}
         </button>`
      : `<span style="display:inline-flex;align-items:center;gap:5px;font-size:0.8em;
                      color:#10b981;background:rgba(16,185,129,.12);padding:6px 12px;border-radius:8px;font-weight:600;">
           <i class="fas fa-check-circle"></i> Installed
         </span>`
    : `<button onclick="window.hpmStoreInstall('${pkg.id}','${pkg.download_url}','${pkg.name}')"
              style="background:linear-gradient(135deg,var(--accent),var(--accent2,#7c3aed));color:#fff;
                     border:none;border-radius:8px;padding:7px 14px;font-size:0.78em;font-weight:700;cursor:pointer;
                     transition:opacity .2s;" onmouseover="this.style.opacity='.85'" onmouseout="this.style.opacity='1'">
         <i class="fas fa-download" style="margin-right:4px;"></i> Install
       </button>`;

  const fallbackIcon = 'https://raw.githubusercontent.com/Hecos-Project/Hecos-Packages/main/Hecos_module_Image_preview_square.png';
  const fallbackScreenshot = 'https://raw.githubusercontent.com/Hecos-Project/Hecos-Packages/main/Hecos_module_Image_preview.png';

  const finalIconUrl = pkg.icon_url || fallbackIcon;
  const customIconHtml = `<img src="${_hesc(finalIconUrl)}" style="width:100%;height:100%;object-fit:cover;border-radius:12px;" onerror="this.outerHTML='<i class=\\'fas ${icon}\\' style=\\'color:${meta.color};font-size:18px;\\'></i>'">`;

  const finalScreenshotUrl = (pkg.screenshots && pkg.screenshots.length > 0) ? pkg.screenshots[0] : fallbackScreenshot;
  const screenshotHtml = `<div style="width:100%; height:130px; margin-top:10px; border-radius:8px; overflow:hidden; border:1px solid rgba(255,255,255,0.05); background:rgba(0,0,0,0.15); display:flex; align-items:center; justify-content:center;">
         <img src="${_hesc(finalScreenshotUrl)}" style="width:100%; height:100%; object-fit:contain; padding:12px; box-sizing:border-box; cursor:zoom-in; transition:transform 0.3s ease;" 
              onmouseover="this.style.transform='scale(1.08)'" onmouseout="this.style.transform='scale(1)'"
              onclick="window.open(this.src, '_blank')" loading="lazy" onerror="this.parentElement.style.display='none'">
       </div>`;

  return `
    <div class="hpm-store-card" style="background:var(--bg2);border:1px solid var(--border-color);
         border-radius:14px;padding:18px;display:flex;flex-direction:column;gap:14px;
         transition:border-color .2s,box-shadow .2s;cursor:default;"
         onmouseover="this.style.borderColor='${meta.color}55';this.style.boxShadow='0 4px 20px ${meta.color}22';"
         onmouseout="this.style.borderColor='var(--border-color)';this.style.boxShadow='none';">

      <!-- Card Header -->
      <div style="display:flex;align-items:flex-start;gap:13px;">
        <div style="width:44px;height:44px;border-radius:12px;flex-shrink:0;
                    background:${meta.color}20;display:flex;align-items:center;justify-content:center;overflow:hidden;">
          ${customIconHtml}
        </div>
        <div style="flex:1;min-width:0;">
          <div style="font-weight:700;color:var(--text);font-size:0.95em;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">
            ${_hesc(pkg.name)}
          </div>
          <div style="display:flex;align-items:center;gap:6px;margin-top:3px;flex-wrap:wrap;">
            <span style="font-size:0.7em;font-weight:700;letter-spacing:.6px;text-transform:uppercase;
                         color:${meta.color};background:${meta.color}18;padding:2px 7px;border-radius:5px;">
              ${meta.label}
            </span>
            <span style="font-size:0.72em;color:var(--muted);">v${_hesc(pkg.version)}</span>
            ${sizeFmt ? `<span style="font-size:0.7em;color:var(--muted);">${sizeFmt}</span>` : ''}
          </div>
        </div>
      </div>
      
      ${screenshotHtml}

      <!-- Description -->
      <div style="font-size:0.8em;color:var(--muted);line-height:1.5;
                  display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;">
        ${_hesc(pkg.description || 'No description available.')}
      </div>

      <!-- Tags -->
      ${pkg.tags && pkg.tags.length ? `
        <div style="display:flex;gap:5px;flex-wrap:wrap;">
          ${pkg.tags.slice(0, 4).map(t =>
            `<span style="font-size:0.68em;background:rgba(255,255,255,.06);color:var(--muted);
                          padding:2px 7px;border-radius:5px;">#${_hesc(t)}</span>`).join('')}
        </div>` : ''}

      <!-- Footer: author + action -->
      <div style="display:flex;align-items:center;justify-content:space-between;margin-top:auto;padding-top:4px;
                  border-top:1px solid var(--border-color);">
        <div style="font-size:0.72em;color:var(--muted);">
          <i class="fas fa-user" style="margin-right:4px;opacity:.5;"></i>${_hesc(pkg.author || 'Unknown')}
        </div>
        ${actionBtn}
      </div>
    </div>`;
}

// ── Detail Modal ──────────────────────────────────────────────────────────────

function _hpmStoreBuildDetailModal() {
  return `
    <div id="hpm-store-detail-modal" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.8);
         z-index:9999;align-items:center;justify-content:center;padding:20px;">
      <div style="background:var(--bg2);border:1px solid var(--border-color);border-radius:16px;
                  max-width:560px;width:100%;max-height:80vh;overflow-y:auto;padding:28px;
                  box-shadow:0 20px 60px rgba(0,0,0,.6);">
        <div id="hpm-store-detail-content"></div>
        <div style="margin-top:20px;text-align:right;">
          <button onclick="document.getElementById('hpm-store-detail-modal').style.display='none'"
                  class="btn btn-secondary">Close</button>
        </div>
      </div>
    </div>`;
}

function _hpmStoreBuildProgressModal() {
  return `
    <div id="hpm-store-progress-modal" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.85);
         z-index:10000;align-items:center;justify-content:center;padding:20px;">
      <div style="background:var(--bg2);border:1px solid var(--border-color);border-radius:16px;
                  max-width:420px;width:100%;padding:32px;text-align:center;box-shadow:0 20px 60px rgba(0,0,0,.6);">
        <div id="hpm-store-progress-icon" style="font-size:2.5em;margin-bottom:16px;">
          <i class="fas fa-download" style="color:var(--accent);animation:pulse 1.5s infinite;"></i>
        </div>
        <div id="hpm-store-progress-title" style="font-weight:700;font-size:1.1em;margin-bottom:8px;color:var(--text);">
          Installing…
        </div>
        <div style="background:var(--border-color);border-radius:6px;height:6px;overflow:hidden;margin:14px 0;">
          <div id="hpm-store-progress-bar"
               style="height:100%;width:0%;background:linear-gradient(90deg,var(--accent),var(--accent2,#7c3aed));
                      border-radius:6px;transition:width .4s ease;"></div>
        </div>
        <div id="hpm-store-progress-msg" style="font-size:0.82em;color:var(--muted);min-height:1.4em;"></div>
      </div>
    </div>`;
}

// ── Install via SSE ───────────────────────────────────────────────────────────

window.hpmStoreInstall = async function (pkgId, downloadUrl, pkgName) {
  const modal = document.getElementById('hpm-store-progress-modal');
  const bar = document.getElementById('hpm-store-progress-bar');
  const msg = document.getElementById('hpm-store-progress-msg');
  const title = document.getElementById('hpm-store-progress-title');
  const icon = document.getElementById('hpm-store-progress-icon');

  if (!modal) return;

  // Reset and show modal
  modal.style.display = 'flex';
  bar.style.width = '10%';
  title.textContent = `Installing ${pkgName}…`;
  msg.textContent = 'Connecting to store…';
  icon.innerHTML = '<i class="fas fa-download" style="color:var(--accent);"></i>';

  const allowUnsigned = document.getElementById('hpm-allow-unsigned')?.checked || false;

  try {
    const resp = await fetch('/api/hpm/store/install', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id: pkgId, download_url: downloadUrl, allow_unsigned: allowUnsigned }),
    });

    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      const lines = buffer.split('\n');
      buffer = lines.pop(); // keep incomplete line

      let event = null;
      let dataStr = null;
      for (const line of lines) {
        if (line.startsWith('event: ')) event = line.slice(7).trim();
        if (line.startsWith('data: ')) dataStr = line.slice(6).trim();
        if (event && dataStr) {
          try {
            const payload = JSON.parse(dataStr);
            _hpmStoreHandleSSE(event, payload, bar, msg, title, icon, modal, pkgId);
          } catch {}
          event = null; dataStr = null;
        }
      }
    }
  } catch (err) {
    msg.textContent = `Error: ${err.message}`;
    icon.innerHTML = '<i class="fas fa-times-circle" style="color:#ef4444;"></i>';
    setTimeout(() => { modal.style.display = 'none'; }, 3000);
  }
};

function _hpmStoreHandleSSE(event, payload, bar, msg, title, icon, modal, pkgId) {
  if (event === 'progress') {
    const step = payload.step || '';
    msg.textContent = payload.message || '';
    bar.style.width = step === 'download' ? '40%' : '75%';
  } else if (event === 'done') {
    bar.style.width = '100%';
    msg.textContent = payload.message || 'Done!';
    icon.innerHTML = '<i class="fas fa-check-circle" style="color:#10b981;"></i>';
    title.textContent = 'Installed Successfully!';
    setTimeout(() => {
      modal.style.display = 'none';
      // Refresh catalog to show "Installed" badge
      window.hpmStoreLoad();
      // Also refresh the local package list
      if (typeof window.hpmLoadPackages === 'function') window.hpmLoadPackages();
    }, 1800);
  } else if (event === 'error') {
    bar.style.width = '100%';
    bar.style.background = '#ef4444';
    msg.textContent = payload.message || 'Installation failed.';
    icon.innerHTML = '<i class="fas fa-times-circle" style="color:#ef4444;"></i>';
    title.textContent = 'Installation Failed';
    setTimeout(() => {
      modal.style.display = 'none';
      bar.style.background = '';
    }, 4000);
  }
}

// ── UI Utilities ──────────────────────────────────────────────────────────────

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
  banner.innerHTML = `<div style="background:${color}18;border:1px solid ${color}44;color:${color};
                                  border-radius:8px;padding:10px 14px;font-size:0.82em;margin-bottom:14px;">
    <i class="fas fa-wifi" style="margin-right:6px;"></i>${_hesc(text)}
  </div>`;
  banner.style.display = 'block';
}
