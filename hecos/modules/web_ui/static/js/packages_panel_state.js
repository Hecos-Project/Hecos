/**
 * packages_panel_state.js
 * ─────────────────────────────────────────────────────────────────────────────
 * State and Filters for Hecos Package Manager Frontend
 */

window.HPM_STATE = {
    viewMode: localStorage.getItem('hpm_view_mode') || 'list',
    activeCategory: 'all',
    activeType: 'all',
    currentPage: 1,
    pageSize: 50, // Will be overridden by settings later
    paginationEnabled: false,
    filteredPackages: []
};

// ── UI Interactions ──────────────────────────────────────────────────────────

window.hpmSetViewMode = function(mode) {
    window.HPM_STATE.viewMode = mode;
    localStorage.setItem('hpm_view_mode', mode);
    
    // Update buttons
    document.getElementById('view-hpm-list')?.classList.toggle('active', mode === 'list');
    document.getElementById('view-hpm-wall')?.classList.toggle('active', mode === 'wall');
    
    // Toggle containers
    const gridList = document.getElementById('hpm-packages-grid');
    const gridWall = document.getElementById('hpm-packages-wall');
    if (gridList) gridList.style.display = mode === 'list' ? 'grid' : 'none';
    if (gridWall) gridWall.style.display = mode === 'wall' ? 'grid' : 'none';
    
    // Selection toolbar only makes sense in list mode
    const selBtn = document.getElementById('hpm-btn-select-mode');
    if (selBtn) selBtn.style.display = mode === 'list' ? 'inline-block' : 'none';
    
    // Hide batch toolbar if switching to wall
    if (mode === 'wall' && window._hpmSelectionMode) {
        window.hpmToggleSelectionMode(); // cancel selection
    }
    
    window.hpmRenderHierarchy();
};

window.hpmSetCategoryFilter = function(catId) {
    window.HPM_STATE.activeCategory = catId;
    document.querySelectorAll('.hpm-cat-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.cat === catId);
    });
    window.hpmApplyFilters();
};

window.hpmSetTypeFilter = function(typeId) {
    window.HPM_STATE.activeType = typeId;
    document.querySelectorAll('.hpm-type-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.type === typeId);
    });
    window.hpmApplyFilters();
};

window.hpmApplyFilters = function() {
    const packages = window._packages || [];
    let filtered = packages;
    
    // Search query
    const searchInput = document.getElementById('hpm-search-input');
    const q = searchInput ? searchInput.value.trim().toLowerCase() : '';
    
    if (q) {
        filtered = filtered.filter(pkg => {
            return (pkg.name || '').toLowerCase().includes(q) ||
                   (pkg.description || '').toLowerCase().includes(q) ||
                   (pkg.author || '').toLowerCase().includes(q) ||
                   (pkg.tag || '').toLowerCase().includes(q);
        });
    }
    
    // Category
    if (window.HPM_STATE.activeCategory !== 'all') {
        filtered = filtered.filter(pkg => window.hpmGetCategory(pkg) === window.HPM_STATE.activeCategory);
    }
    
    // Type
    if (window.HPM_STATE.activeType !== 'all') {
        filtered = filtered.filter(pkg => (pkg.type || '').toLowerCase() === window.HPM_STATE.activeType);
    }
    
    window.HPM_STATE.filteredPackages = filtered;
    window.HPM_STATE.currentPage = 1; // reset to first page on filter change
    
    window.hpmRenderHierarchy();
};

window.hpmGoToPage = function(delta, relative = true) {
    if (!window.HPM_STATE.paginationEnabled) return;
    
    let target = relative ? window.HPM_STATE.currentPage + delta : delta;
    const totalPages = Math.ceil(window.HPM_STATE.filteredPackages.length / window.HPM_STATE.pageSize);
    
    if (target < 1) target = 1;
    if (target > totalPages) target = totalPages;
    
    if (target !== window.HPM_STATE.currentPage) {
        window.HPM_STATE.currentPage = target;
        window.hpmRenderHierarchy();
    }
};

window.hpmRenderPagination = function(totalItems) {
    const pagEl = document.getElementById('hpm-pagination');
    if (!pagEl) return;
    
    const totalPages = Math.ceil(totalItems / window.HPM_STATE.pageSize);
    
    if (totalPages > 1) {
        pagEl.style.display = 'flex';
        const infoEl = document.getElementById('hpm-page-info');
        if (infoEl) infoEl.textContent = `Page ${window.HPM_STATE.currentPage} of ${totalPages}`;
        
        const prevBtn = document.getElementById('hpm-page-prev');
        if (prevBtn) prevBtn.disabled = window.HPM_STATE.currentPage === 1;
        
        const nextBtn = document.getElementById('hpm-page-next');
        if (nextBtn) nextBtn.disabled = window.HPM_STATE.currentPage === totalPages;
    } else {
        pagEl.style.display = 'none';
    }
};

window.hpmRenderFilterBars = function() {
    const packages = window._packages || [];
    
    // Category Filters
    // Category Filters (Now based on HPM_TYPE_META since we group by Type)
    const catContainer = document.getElementById('hpm-category-filters');
    if (catContainer && window.HPM_TYPE_META) {
        // Count per category (which is type now)
        const counts = { 'all': packages.length };
        packages.forEach(p => {
            const cat = window.hpmGetCategory(p);
            counts[cat] = (counts[cat] || 0) + 1;
        });
        
        let html = `
            <button class="hpm-cat-btn filter-btn ${window.HPM_STATE.activeCategory === 'all' ? 'active' : ''}" 
                    data-cat="all" onclick="window.hpmSetCategoryFilter('all')">
                <i class="fas fa-layer-group"></i> All 
                <span class="badge" style="background:rgba(255,255,255,0.1);padding:1px 6px;border-radius:10px;font-size:0.85em;margin-left:4px;">${counts['all']}</span>
            </button>`;
            
        // Sort by order
        const sortedMeta = Object.entries(window.HPM_TYPE_META).sort((a, b) => (a[1].order || 99) - (b[1].order || 99));

        for (const [catId, meta] of sortedMeta) {
            const count = counts[catId] || 0;
            if (count > 0) {
                const isActive = window.HPM_STATE.activeCategory === catId;
                html += `
                    <button class="hpm-cat-btn filter-btn ${isActive ? 'active' : ''}" 
                            data-cat="${catId}" onclick="window.hpmSetCategoryFilter('${catId}')"
                            style="display:inline-flex;align-items:center;gap:6px;font-size:0.8em;">
                        <i class="fas ${meta.icon}" style="color:${meta.color};"></i> ${meta.label}
                        <span style="background:rgba(255,255,255,0.1);padding:1px 6px;border-radius:10px;font-size:0.85em;">${count}</span>
                    </button>`;
            }
        }
        catContainer.innerHTML = html;
    }
    
    // Type Filters - Removed since it's the primary grouping now
    const typeContainer = document.getElementById('hpm-type-filters');
    if (typeContainer) typeContainer.style.display = 'none';
};
