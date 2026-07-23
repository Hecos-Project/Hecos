/**
 * packages_panel_render_hierarchy.js
 * ─────────────────────────────────────────────────────────────────────────────
 * Hierarchy and Filtering logic for Hecos Package Manager
 */

window.hpmToggleCategory = function (catLvl) {
  const isCollapsed = window.HPM_UI_STATE.collapsedCategories.includes(catLvl);
  if (isCollapsed) {
    window.HPM_UI_STATE.collapsedCategories = window.HPM_UI_STATE.collapsedCategories.filter(c => c !== catLvl);
  } else {
    window.HPM_UI_STATE.collapsedCategories.push(catLvl);
  }
  window.hpmRenderHierarchy();
};

window.hpmToggleAllCategories = function (expand) {
  if (expand) {
    window.HPM_UI_STATE.collapsedCategories = [];
  } else {
    window.HPM_UI_STATE.collapsedCategories = Object.keys(window.HPM_TYPE_META);
  }
  window.hpmRenderHierarchy();
};

window.hpmFilterPackages = function (q) {
  if (q === undefined) {
    const input = document.getElementById('hpm-search-input');
    q = input ? input.value : '';
  }

  const clearBtn = document.getElementById('hpm-search-clear');
  if (clearBtn) clearBtn.style.display = q ? 'block' : 'none';

  q = (q || '').trim().toLowerCase();

  const packages = window._packages || [];
  if (!q) {
    window.hpmRenderHierarchy(packages);
    return;
  }

  const filtered = packages.filter(pkg => {
    return (pkg.name || '').toLowerCase().includes(q) ||
      (pkg.description || '').toLowerCase().includes(q) ||
      (pkg.author || '').toLowerCase().includes(q) ||
      (pkg.tag || '').toLowerCase().includes(q);
  });

  if (window.HPM_STATE && typeof window.hpmGoToPage === 'function') {
    window.HPM_STATE.currentPage = 1;
    window.HPM_STATE.filteredPackages = filtered;
    window.hpmRenderHierarchy();
  } else {
    window.hpmRenderHierarchy(filtered);
  }
};

window.hpmRenderHierarchy = function (packagesList) {
  let packages = packagesList || (window.HPM_STATE ? window.HPM_STATE.filteredPackages : window._packages) || [];
  if (!Array.isArray(packages)) packages = [];

  const totalCountEl = document.getElementById('hpm-total-count');
  if (totalCountEl) totalCountEl.textContent = packages.length;

  const viewMode = localStorage.getItem('hpm_view_mode') || 'list';

  let displayPackages = packages;
  if (window.HPM_STATE && window.HPM_STATE.paginationEnabled && window.HPM_STATE.pageSize > 0) {
    const startIdx = ((window.HPM_STATE.currentPage || 1) - 1) * window.HPM_STATE.pageSize;
    displayPackages = packages.slice(startIdx, startIdx + window.HPM_STATE.pageSize);

    if (typeof window.hpmRenderPagination === 'function') {
      window.hpmRenderPagination(packages.length);
    }
  } else {
    const pagEl = document.getElementById('hpm-pagination');
    if (pagEl) pagEl.style.display = 'none';
  }

  let listHtml = '';
  let wallHtml = '';

  const categoriesToIterate = window.HPM_TYPE_META || { other: { label: 'Other', icon: 'fa-cube', color: '#6b7280', order: 9 } };
  const sortedCatEntries = Object.entries(categoriesToIterate).sort((a, b) => (a[1].order || 99) - (b[1].order || 99));

  if (displayPackages.length > 0) {
    for (const [catId, meta] of sortedCatEntries) {
      const group = displayPackages.filter(p => window.hpmGetCategory(p) === catId);
      if (group.length === 0) continue;

      let isCollapsed = window.HPM_UI_STATE.collapsedCategories.includes(catId);

      listHtml += `
        <div class="category-group ${isCollapsed ? 'collapsed' : ''}" style="margin-bottom:12px;">
          <div class="category-header" onclick="hpmToggleCategory('${catId}')"
               style="cursor:pointer;display:flex;align-items:center;gap:10px;
                      padding:10px 14px;border-radius:10px;
                      background:var(--bg2);border:1px solid var(--border-color);
                      user-select:none;">
            <span class="cat-toggle" style="font-size:14px;color:var(--muted);width:16px;text-align:center;">${isCollapsed ? '⊕' : '⊖'}</span>
            <span style="font-size:10px;font-weight:800;letter-spacing:1.2px;
                         text-transform:uppercase;color:${meta.color};"><i class="fas ${meta.icon}"></i> ${meta.label}</span>
            <span style="margin-left:auto;font-size:10px;color:var(--muted);
                         background:rgba(255,255,255,0.05);padding:2px 8px;border-radius:10px;">
              ${group.length}
            </span>
          </div>
          <div class="category-content" style="${isCollapsed ? 'display:none;' : 'display:grid;gap:6px;margin-top:8px;padding:0 2px;'}">
            ${group.map(pkg => window.hpmRenderRow(pkg, meta)).join('')}
          </div>
        </div>`;

      wallHtml += group.map(pkg => window.hpmRenderWallCard(pkg, meta)).join('');
    }
  }

  const gridList = document.getElementById('hpm-packages-grid');
  const gridWall = document.getElementById('hpm-packages-wall');

  const isNone = window.HPM_STATE && window.HPM_STATE.activeCategory === 'none';
  const emptyText = isNone 
      ? (window.HPM_I18N?.select_category || window.hpm_ti('Select a category to view modules.', 'Seleziona una categoria per visualizzare i moduli.', 'Seleccione una categoría para ver los módulos.'))
      : (window.HPM_I18N?.no_modules || window.hpm_ti('No modules found.', 'Nessun modulo trovato.', 'No se encontraron módulos.'));

  const emptyMsg = `<div style="text-align:center;padding:40px;color:var(--muted);grid-column:1/-1;width:100%;">
                      <i class="fas ${isNone ? 'fa-hand-pointer' : 'fa-box-open'}" style="font-size:2em;margin-bottom:10px;display:block;opacity:0.4;"></i>
                      <div style="font-size:0.9em;">${emptyText}</div>
                    </div>`;

  if (gridList) gridList.innerHTML = listHtml || emptyMsg;
  if (gridWall) gridWall.innerHTML = wallHtml || emptyMsg;

  return listHtml || emptyMsg;
};
