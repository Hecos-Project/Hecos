/**
 * packages_panel_store_sources.js
 * ─────────────────────────────────────────────────────────────────────────────
 * Hecos Package Manager — Store Sources Manager
 * Gestisce la UI per aggiungere/rimuovere/abilitare store URL multipli.
 * Si aggancia al pannello Store tramite #hpm-store-sources-panel.
 */

// ── State ──────────────────────────────────────────────────────────────────────
window._hpmStores = [];
window._hpmStoresLoaded = false;

// ── Load stores from backend ───────────────────────────────────────────────────
window.hpmStoresLoad = async function () {
  try {
    const res = await fetch('/api/hpm/store/stores');
    const data = await res.json();
    if (!data.ok) throw new Error(data.error || 'Unknown error');
    window._hpmStores = data.stores || [];
    window._hpmStoresLoaded = true;
    _hpmStoresRender();
    _hpmStoresUpdateDropdown();
  } catch (e) {
    console.warn('[HPM:Stores] Failed to load stores:', e);
    window._hpmStores = [{ name: 'Hecos Official Store', url: 'https://hecos-project.github.io/store/index.json', enabled: true }];
    _hpmStoresRender();
    _hpmStoresUpdateDropdown();
  }
};

// ── Add a store ────────────────────────────────────────────────────────────────
window.hpmStoresAdd = async function () {
  const urlEl  = document.getElementById('hpm-store-add-url');
  const nameEl = document.getElementById('hpm-store-add-name');
  const url    = (urlEl ? urlEl.value : '').trim();
  const name   = (nameEl ? nameEl.value : '').trim();

  if (!url) {
    window.showToast && window.showToast('Insert a store URL first.', 'warning');
    return;
  }

  const btn = document.getElementById('hpm-store-add-btn');
  if (btn) { btn.disabled = true; btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>'; }

  try {
    const res  = await fetch('/api/hpm/store/stores', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url, name: name || url }),
    });
    const data = await res.json();
    if (!data.ok) {
      window.showToast && window.showToast(data.error || 'Failed to add store.', 'error');
      return;
    }
    window._hpmStores = data.stores || [];
    if (urlEl)  urlEl.value  = '';
    if (nameEl) nameEl.value = '';
    _hpmStoresRender();
    _hpmStoresUpdateDropdown();
    window.showToast && window.showToast('Store added! Refreshing catalog...', 'success');
    // Force catalog refresh to include the new store
    window.hpmStoreLoad && window.hpmStoreLoad(true);
  } catch (e) {
    window.showToast && window.showToast('Network error: ' + e, 'error');
  } finally {
    if (btn) { btn.disabled = false; btn.innerHTML = '<i class="fas fa-plus"></i> Add'; }
  }
};

// ── Toggle enable/disable a store ─────────────────────────────────────────────
window.hpmStoresToggle = async function (idx) {
  const store = window._hpmStores[idx];
  if (!store) return;
  try {
    const res  = await fetch(`/api/hpm/store/stores/${idx}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ enabled: !store.enabled }),
    });
    const data = await res.json();
    if (!data.ok) { window.showToast && window.showToast(data.error || 'Failed', 'error'); return; }
    window._hpmStores = data.stores || [];
    _hpmStoresRender();
    _hpmStoresUpdateDropdown();
    window.hpmStoreLoad && window.hpmStoreLoad(true);
  } catch (e) {
    window.showToast && window.showToast('Network error: ' + e, 'error');
  }
};

// ── Remove a store ─────────────────────────────────────────────────────────────
window.hpmStoresRemove = async function (idx) {
  const store = window._hpmStores[idx];
  if (!store) return;
  if (!confirm(`Remove store "${store.name}"?\nThis will not delete any installed packages.`)) return;
  try {
    const res  = await fetch(`/api/hpm/store/stores/${idx}`, { method: 'DELETE' });
    const data = await res.json();
    if (!data.ok) { window.showToast && window.showToast(data.error || 'Failed', 'error'); return; }
    window._hpmStores = data.stores || [];
    _hpmStoresRender();
    _hpmStoresUpdateDropdown();
    window.showToast && window.showToast('Store removed.', 'success');
    window.hpmStoreLoad && window.hpmStoreLoad(true);
  } catch (e) {
    window.showToast && window.showToast('Network error: ' + e, 'error');
  }
};

// ── Render the sources list ────────────────────────────────────────────────────
function _hpmStoresRender() {
  const list = document.getElementById('hpm-stores-list');
  if (!list) return;

  const stores = window._hpmStores;
  if (!stores.length) {
    list.innerHTML = `<div style="color:var(--muted);font-size:0.8em;text-align:center;padding:10px;">
      No stores configured. Add a URL below.
    </div>`;
    return;
  }

  list.innerHTML = stores.map((s, i) => {
    const urlShort = s.url.length > 55 ? s.url.slice(0, 52) + '…' : s.url;
    const isDefault = s.url.includes('hecos-project.github.io');
    return `
      <div style="display:flex;align-items:center;gap:10px;padding:8px 10px;
                  background:var(--bg3);border-radius:8px;border:1px solid var(--border-color);
                  transition:border-color .2s;" id="hpm-store-row-${i}">
        <!-- Status dot -->
        <span title="${s.enabled ? 'Enabled' : 'Disabled'}"
              style="width:8px;height:8px;border-radius:50%;flex-shrink:0;
                     background:${s.enabled ? '#10b981' : '#6b7280'};
                     box-shadow:${s.enabled ? '0 0 6px #10b981' : 'none'};"></span>

        <!-- Name + URL -->
        <div style="flex:1;min-width:0;">
          <div style="font-size:0.82em;font-weight:600;color:var(--text);
                      white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">
            ${_hesc(s.name)}
            ${isDefault ? '<span style="font-size:0.7em;background:rgba(16,185,129,.15);color:#10b981;padding:1px 5px;border-radius:4px;margin-left:4px;">official</span>' : ''}
          </div>
          <div style="font-size:0.72em;color:var(--muted);white-space:nowrap;overflow:hidden;
                      text-overflow:ellipsis;" title="${_hesc(s.url)}">
            ${_hesc(urlShort)}
          </div>
        </div>

        <!-- Actions -->
        <button onclick="window.hpmStoresToggle(${i})"
                title="${s.enabled ? 'Disable' : 'Enable'} this store"
                style="background:${s.enabled ? 'rgba(16,185,129,.1)' : 'rgba(255,255,255,.06)'};
                       border:1px solid ${s.enabled ? '#10b98133' : 'var(--border-color)'};
                       color:${s.enabled ? '#10b981' : 'var(--muted)'};
                       border-radius:6px;padding:3px 8px;font-size:0.72em;cursor:pointer;
                       transition:all .2s;">
          ${s.enabled ? 'ON' : 'OFF'}
        </button>
        <button onclick="window.hpmStoresRemove(${i})"
                title="Remove store"
                ${isDefault ? 'disabled title="Cannot remove the official store"' : ''}
                style="background:${isDefault ? 'transparent' : 'rgba(239,68,68,.08)'};
                       border:1px solid ${isDefault ? 'transparent' : 'rgba(239,68,68,.2)'};
                       color:${isDefault ? 'var(--border-color)' : '#ef4444'};
                       border-radius:6px;padding:3px 8px;font-size:0.72em;
                       cursor:${isDefault ? 'default' : 'pointer'};transition:all .2s;">
          <i class="fas fa-times"></i>
        </button>
      </div>`;
  }).join('');
}

// ── Update the store filter dropdown in the catalog ────────────────────────────
function _hpmStoresUpdateDropdown() {
  const sel = document.getElementById('hpm-store-source-filter');
  if (!sel) return;

  const prev = sel.value;
  const stores = window._hpmStores;

  sel.innerHTML = `<option value="">All Stores (${stores.filter(s => s.enabled).length} active)</option>` +
    stores.map(s =>
      `<option value="${_hesc(s.url)}" ${!s.enabled ? 'disabled' : ''}>${_hesc(s.name)}${!s.enabled ? ' (off)' : ''}</option>`
    ).join('');

  // Restore previous selection if still valid
  if (prev && stores.some(s => s.url === prev)) sel.value = prev;
}

// ── Build the Store Sources panel HTML (injected into #hpm-pane-store) ─────────
window.hpmStoresBuildPanel = function () {
  return `
    <!-- ══ Store Sources ══════════════════════════════════════════════════ -->
    <details id="hpm-store-sources-panel"
             style="margin-bottom:16px;background:var(--bg2);border:1px solid var(--border-color);
                    border-radius:12px;overflow:hidden;">
      <summary style="cursor:pointer;padding:12px 16px;display:flex;align-items:center;
                      gap:10px;font-size:0.85em;font-weight:600;color:var(--text);
                      list-style:none;user-select:none;">
        <i class="fas fa-database" style="color:var(--accent);"></i>
        Store Sources
        <span id="hpm-stores-count-badge"
              style="background:rgba(255,255,255,.08);color:var(--muted);font-size:0.8em;
                     padding:1px 7px;border-radius:10px;margin-left:auto;"></span>
        <i class="fas fa-chevron-down" style="color:var(--muted);font-size:0.8em;
           transition:transform .2s;" id="hpm-store-src-chevron"></i>
      </summary>

      <div style="padding:0 16px 16px;">
        <!-- Store list -->
        <div id="hpm-stores-list" style="display:flex;flex-direction:column;gap:6px;margin-bottom:12px;">
          <div style="text-align:center;padding:12px;color:var(--muted);font-size:0.8em;">
            <i class="fas fa-spinner fa-spin"></i> Loading stores…
          </div>
        </div>

        <!-- Add store form -->
        <div style="background:var(--bg3);border-radius:8px;padding:10px 12px;
                    border:1px solid var(--border-color);">
          <div style="font-size:0.78em;font-weight:600;color:var(--muted);margin-bottom:8px;
                      text-transform:uppercase;letter-spacing:.5px;">
            <i class="fas fa-plus-circle" style="margin-right:5px;color:var(--accent);"></i>
            Add Store
          </div>
          <div style="display:flex;flex-direction:column;gap:6px;">
            <input id="hpm-store-add-url" type="url"
                   placeholder="https://example.com/store/index.json or C:/path/to/store/index.json"
                   autocomplete="off" spellcheck="false"
                   style="width:100%;box-sizing:border-box;background:var(--bg2);
                          border:1px solid var(--border-color);border-radius:8px;
                          padding:7px 10px;color:var(--text);font-size:0.82em;outline:none;"
                   onfocus="this.style.borderColor='var(--accent)'"
                   onblur="this.style.borderColor='var(--border-color)'"
                   onkeydown="if(event.key==='Enter') window.hpmStoresAdd()">
            <div style="display:flex;gap:6px;">
              <input id="hpm-store-add-name" type="text"
                     placeholder="Store name (optional)"
                     style="flex:1;background:var(--bg2);border:1px solid var(--border-color);
                            border-radius:8px;padding:6px 10px;color:var(--text);font-size:0.8em;outline:none;"
                     onfocus="this.style.borderColor='var(--accent)'"
                     onblur="this.style.borderColor='var(--border-color)'"
                     onkeydown="if(event.key==='Enter') window.hpmStoresAdd()">
              <button id="hpm-store-add-btn" onclick="window.hpmStoresAdd()"
                      style="background:linear-gradient(135deg,var(--accent),var(--accent2,#7c3aed));
                             color:#fff;border:none;border-radius:8px;padding:6px 16px;
                             font-size:0.8em;font-weight:700;cursor:pointer;white-space:nowrap;
                             transition:opacity .2s;"
                      onmouseover="this.style.opacity='.85'" onmouseout="this.style.opacity='1'">
                <i class="fas fa-plus"></i> Add
              </button>
            </div>
          </div>
        </div>
      </div>
    </details>

    <!-- Store Source Filter Dropdown -->
    <div style="display:flex;align-items:center;gap:8px;margin-bottom:14px;">
      <i class="fas fa-filter" style="color:var(--muted);font-size:0.85em;"></i>
      <select id="hpm-store-source-filter"
              style="background:var(--bg2);border:1px solid var(--border-color);
                     border-radius:8px;padding:5px 10px;color:var(--text);font-size:0.82em;
                     outline:none;cursor:pointer;transition:border-color .2s;"
              onfocus="this.style.borderColor='var(--accent)'"
              onblur="this.style.borderColor='var(--border-color)'"
              onchange="window.hpmStoreApplySourceFilter(this.value)">
        <option value="">All Stores</option>
      </select>
      <span id="hpm-store-source-filter-info"
            style="font-size:0.75em;color:var(--muted);"></span>
    </div>`;
};

// ── Apply source filter to catalog grid ───────────────────────────────────────
window.hpmStoreApplySourceFilter = function (storeUrl) {
  const state = window.HPM_STORE_STATE;
  if (!state) return;
  state._sourceFilter = storeUrl || '';
  // Trigger re-filter
  if (typeof _hpmStoreApplyFilters === 'function') _hpmStoreApplyFilters();
};

// ── Init: called when Store tab is activated ──────────────────────────────────
window.hpmStoresInit = async function () {
  // Sync badge counter after loading
  await window.hpmStoresLoad();
  const badge = document.getElementById('hpm-stores-count-badge');
  if (badge) {
    const enabled = window._hpmStores.filter(s => s.enabled).length;
    badge.textContent = `${enabled} / ${window._hpmStores.length}`;
  }

  // Animate chevron on details open/close
  const details = document.getElementById('hpm-store-sources-panel');
  const chevron = document.getElementById('hpm-store-src-chevron');
  if (details && chevron) {
    details.addEventListener('toggle', () => {
      chevron.style.transform = details.open ? 'rotate(180deg)' : '';
    });
  }
};

// ── HTML escape helper (may already exist in store_ui.js) ─────────────────────
if (typeof _hesc === 'undefined') {
  function _hesc(str) {
    return String(str || '').replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }
}
