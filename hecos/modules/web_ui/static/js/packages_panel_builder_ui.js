window.builderViewMode = 'wall';
window.builderSelectMode = false;
window.builderSelectedPackages = new Set();
window.builderCollapsedCategories = new Set();
window.builderActiveCategoryFilters = new Set();

window.builderRefreshSources = async function() {
    const grid = document.getElementById('builder-sources-grid');
    if (!grid) return;
    grid.innerHTML = '<div style="color:var(--muted); padding:16px; text-align:center;"><i class="fas fa-circle-notch fa-spin"></i> Scanning local sources...</div>';
    window.builderLog('Scanning local workspace for packages...', 'info');
    
    try {
        const baseDir = document.getElementById('builder-sources-root') ? document.getElementById('builder-sources-root').value : '';
        const resp = await fetch('/api/hpm/builder/scan-sources', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ base_dir: baseDir })
        });
        const data = await resp.json();
        
        if (data && data.ok) {
            window.builderSourcesData = data.sources;
            window.builderLog(`Found ${data.sources.length} packages in local sources.`, 'success');
            
            // We now use builderRenderFilters which gets called by builderRenderGrid
            if (!window.builderCategoryFiltersInitialized) {
                const uniqueTypes = new Set(data.sources.map(s => s.type || 'other'));
                uniqueTypes.forEach(t => window.builderActiveCategoryFilters.add(t));
                window.builderCategoryFiltersInitialized = true;
            }
            
            window.builderRenderGrid();
        } else {
            grid.innerHTML = `<div style="color:#ef4444; padding:16px;">Scan Error: ${data ? data.error : "Unknown"}</div>`;
        }
    } catch (e) {
        console.error(e);
        window.builderLog('An unexpected error occurred: ' + e.message, 'error');
        grid.innerHTML = '<div style="color:#ef4444; padding:16px;">Connection Error</div>';
    }
};


window.builderRenderFilters = function() {
    const catContainer = document.getElementById('builder-category-filters');
    if (!catContainer || !window.builderSourcesData) return;
    
    const uniqueTypes = new Set(window.builderSourcesData.map(s => s.type || 'other'));
    let html = '';
    
    // Toggle All Button (styled as a pill)
    const isAllChecked = (window.builderActiveCategoryFilters.size === uniqueTypes.size);
    html += `
        <button class="hpm-cat-btn filter-btn ${isAllChecked ? 'active' : ''}" 
                onclick="window.builderToggleAllFilters()"
                style="display:inline-flex;align-items:center;gap:6px;font-size:0.95em; padding:6px 14px; margin-bottom:5px;">
            <i class="fas fa-layer-group"></i> All 
            <span class="badge" style="background:rgba(255,255,255,0.1);padding:1px 6px;border-radius:10px;font-size:0.9em; padding:2px 8px;margin-left:4px;">${window.builderSourcesData.length}</span>
        </button>
    `;
    
    // Sort categories
    const sortedMeta = window.HPM_TYPE_META ? Object.entries(window.HPM_TYPE_META).sort((a, b) => (a[1].order || 99) - (b[1].order || 99)) : [];
    const orderedTypes = sortedMeta.map(m => m[0]);
    uniqueTypes.forEach(t => {
        if (!orderedTypes.includes(t)) orderedTypes.push(t);
    });
    
    orderedTypes.forEach(catId => {
        if (!uniqueTypes.has(catId)) return;
        const meta = window.HPM_TYPE_META && window.HPM_TYPE_META[catId] ? window.HPM_TYPE_META[catId] : { label: catId, color: '#6b7280', icon: 'fa-cube' };
        const count = window.builderSourcesData.filter(s => (s.type || 'other') === catId).length;
        if (count > 0) {
            const isActive = window.builderActiveCategoryFilters.has(catId);
            html += `
                <button class="hpm-cat-btn filter-btn ${isActive ? 'active' : ''}" 
                        onclick="window.builderToggleCategoryFilter('${catId}')"
                        style="display:inline-flex;align-items:center;gap:6px;font-size:0.95em; padding:6px 14px; margin-bottom:5px;">
                    <i class="fas ${meta.icon}" style="color:${meta.color};"></i> ${meta.label}
                    <span style="background:rgba(255,255,255,0.1);padding:1px 6px;border-radius:10px;font-size:0.9em; padding:2px 8px;">${count}</span>
                </button>`;
        }
    });
    
    catContainer.innerHTML = html;
};

window.builderToggleCategoryFilter = function(catId) {
    if (window.builderActiveCategoryFilters.has(catId)) {
        window.builderActiveCategoryFilters.delete(catId);
    } else {
        window.builderActiveCategoryFilters.add(catId);
    }
    window.builderRenderGrid();
};

window.builderToggleAllFilters = function() {
    const uniqueTypes = new Set(window.builderSourcesData.map(s => s.type || 'other'));
    if (window.builderActiveCategoryFilters.size === uniqueTypes.size) {
        window.builderActiveCategoryFilters.clear();
    } else {
        uniqueTypes.forEach(t => window.builderActiveCategoryFilters.add(t));
    }
    window.builderRenderGrid();
};

window.builderRenderGrid = function() {
    try {
        const grid = document.getElementById('builder-sources-grid');
        if (!grid) return;
    
    // Update toolbar UI
    document.querySelectorAll('.builder-view-btn').forEach(b => b.style.background = 'transparent');
    const activeBtn = document.getElementById('builder-view-btn-' + window.builderViewMode);
    if (activeBtn) activeBtn.style.background = 'rgba(255,255,255,0.1)';
    
    const batchBtn = document.getElementById('builder-btn-batch');
    const multiBtn = document.getElementById('builder-btn-multiselect');
    if (window.builderSelectMode) {
        multiBtn.style.background = 'var(--accent)';
        multiBtn.style.color = '#000';
        batchBtn.style.display = 'inline-block';
        document.getElementById('builder-batch-count').innerText = window.builderSelectedPackages.size;
    } else {
        multiBtn.style.background = '';
        multiBtn.style.color = '';
        batchBtn.style.display = 'none';
        window.builderSelectedPackages.clear();
    }
    
    const searchInput = document.getElementById('builder-search-input');
    const query = searchInput ? searchInput.value.toLowerCase().trim() : '';
    
    window.builderRenderFilters();

    // Filter data
    const filtered = window.builderSourcesData.filter(src => {
        const type = src.type || 'other';
        if (!window.builderActiveCategoryFilters.has(type)) return false;
        if (query) {
            const matchesName = src.name && src.name.toLowerCase().includes(query);
            const matchesPath = src.rel_path && src.rel_path.toLowerCase().includes(query);
            if (!matchesName && !matchesPath) return false;
        }
        return true;
    });
    
    grid.innerHTML = '';
    if (filtered.length === 0) {
        grid.innerHTML = '<div style="color:var(--muted); padding:16px; text-align:center;">No sources match your filters.</div>';
        return;
    }
    
    const baseDir = document.getElementById('builder-sources-root') ? document.getElementById('builder-sources-root').value : '';
    
    const groups = {};
    filtered.forEach(src => {
        const type = src.type || 'other';
        if (!groups[type]) groups[type] = [];
        groups[type].push(src);
    });
    
    for (const [type, pkgs] of Object.entries(groups)) {
        const typeMeta = window.HPM_TYPE_META ? (window.HPM_TYPE_META[type] || { label: type, color: '#6b7280', icon: 'fa-cube' }) : { label: type, color: '#6b7280', icon: 'fa-cube' };
        
        const isCollapsed = window.builderCollapsedCategories.has(type);
        const header = document.createElement('div');
        header.style = `cursor:pointer; display:flex; align-items:center; gap:10px; padding:10px 14px; border-radius:10px; background:var(--bg2); border:1px solid var(--border-color); user-select:none; margin-top:16px; margin-bottom:12px;`;
        header.onclick = (e) => { if (e.target.tagName !== 'BUTTON' && !e.target.closest('button')) window.builderToggleCategory(type); };
        
        header.innerHTML = `
            <span class="cat-toggle" style="font-size:14px;color:var(--muted);width:16px;text-align:center;">${isCollapsed ? '⊕' : '⊖'}</span>
            <span style="font-size:10px;font-weight:800;letter-spacing:1.2px; text-transform:uppercase;color:${typeMeta.color};"><i class="fas ${typeMeta.icon}"></i> ${typeMeta.label}</span>
            <div style="margin-left:auto; display:flex; align-items:center; gap:8px;">
                <button class="btn btn-sm btn-secondary" title="Build all in this category" style="padding:2px 8px; font-size:9px;" onclick="window.builderExecuteBatchBuildCat('${type}')"><i class="fas fa-hammer"></i> Build Cat</button>
                <span style="font-size:10px;color:var(--muted); background:rgba(255,255,255,0.05);padding:2px 8px;border-radius:10px;">${pkgs.length}</span>
            </div>
        `;
        grid.appendChild(header);
        
        if (isCollapsed) continue;
        
        const groupGrid = document.createElement('div');
        if (window.builderViewMode === 'wall') {
            groupGrid.style = 'display:grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 12px;';
        } else {
            groupGrid.style = 'display:flex; flex-direction:column; gap:6px;';
        }
        
        pkgs.forEach(src => {
            let d = baseDir;
            if (!d.endsWith("\\\\") && !d.endsWith("/")) d += "\\\\";
            const absolutePath = d + src.rel_path;
            
            const isSelected = window.builderSelectedPackages.has(absolutePath);
            const currentDir = document.getElementById('builder-source-dir').value;
            const isActive = currentDir === absolutePath;
            
            const cardId = 'builder-card-' + src.rel_path.replace(/[^a-zA-Z0-9]/g, '-');
            const card = document.createElement('div');
            card.className = window.builderViewMode === 'wall' ? 'hpm-wall-card' : 'hpm-list-card';
            card.id = cardId;
            card.style.cursor = 'pointer';
            
            if (window.builderViewMode === 'wall') {
                card.style.padding = '10px';
                card.style.gap = '8px';
                
                if (isActive && !window.builderSelectMode) {
                    card.style.borderColor = 'var(--accent)';
                    card.style.boxShadow = '0 0 10px rgba(102,252,241,0.15)';
                }
                if (isSelected) {
                    card.style.borderColor = 'var(--accent)';
                    card.style.background = 'rgba(102,252,241,0.1)';
                }
                
                const imgUrl = '/api/local_file?path=' + encodeURIComponent(absolutePath + '\\\\preview_1.png');
                const fallbackImg = 'https://raw.githubusercontent.com/Hecos-Project/Hecos-Packages/main/Hecos_module_Image_preview.png';
                
                card.innerHTML = `
                  <div style="position:absolute; top:8px; right:8px; display:${window.builderSelectMode ? 'block' : 'none'}; z-index:10;">
                      <i class="fas ${isSelected ? 'fa-check-square' : 'fa-square'}" style="color:${isSelected ? 'var(--accent)' : 'var(--muted)'}; font-size:18px; background:#000; border-radius:2px;"></i>
                  </div>
                  <div style="display:flex;align-items:flex-start;gap:8px;">
                    <div style="width:32px;height:32px;border-radius:6px;flex-shrink:0;background:${typeMeta.color}20;display:flex;align-items:center;justify-content:center;">
                      <i class="fas ${typeMeta.icon}" style="color:${typeMeta.color};font-size:14px;"></i>
                    </div>
                    <div style="flex:1;min-width:0;">
                      <div style="font-weight:700;font-size:0.9em; padding:2px 8px;color:var(--text);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;" title="${src.name}">${src.name}</div>
                      <div style="display:flex;align-items:center;gap:5px;flex-wrap:wrap;">
                        <span style="font-size:0.75em;color:var(--muted);">v${src.version}</span>
                      </div>
                    </div>
                  </div>
                  <div style="width:100%;aspect-ratio:16/9;border-radius:6px;overflow:hidden;border:1px solid rgba(255,255,255,0.08);background:#050505;display:flex;align-items:center;justify-content:center;margin-top:4px;position:relative;">
                    <img src="${imgUrl}" onerror="this.src='${fallbackImg}'" style="width:100%;height:100%;object-fit:cover;padding:2px;box-sizing:border-box;transition:transform .3s;" onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'">
                  </div>
                `;
            } else {
                // List view
                card.style.display = 'flex';
                card.style.alignItems = 'center';
                card.style.gap = '10px';
                card.style.padding = '8px 12px';
                card.style.background = 'rgba(255,255,255,0.02)';
                card.style.border = '1px solid rgba(255,255,255,0.05)';
                card.style.borderRadius = '6px';
                
                if (isActive && !window.builderSelectMode) card.style.borderColor = 'var(--accent)';
                if (isSelected) {
                    card.style.borderColor = 'var(--accent)';
                    card.style.background = 'rgba(102,252,241,0.1)';
                }
                
                card.innerHTML = `
                  <div style="display:${window.builderSelectMode ? 'block' : 'none'}; margin-right:5px;">
                      <i class="fas ${isSelected ? 'fa-check-square' : 'fa-square'}" style="color:${isSelected ? 'var(--accent)' : 'var(--muted)'}; font-size:16px;"></i>
                  </div>
                  <div style="width:28px;height:28px;border-radius:6px;flex-shrink:0;background:${typeMeta.color}20;display:flex;align-items:center;justify-content:center;">
                      <i class="fas ${typeMeta.icon}" style="color:${typeMeta.color};font-size:12px;"></i>
                  </div>
                  <div style="flex:1;min-width:0;display:flex;align-items:center;gap:10px;">
                      <div style="font-weight:700;font-size:0.9em;color:var(--text);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;width:250px;" title="${src.name}">${src.name}</div>
                      <span style="font-size:0.95em; padding:6px 14px;color:var(--muted);width:80px;">v${src.version}</span>
                      <span style="font-size:0.95em; padding:6px 14px;color:var(--muted);flex:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${src.rel_path}</span>
                  </div>
                `;
                
                card.onmouseover = () => card.style.background = isSelected ? 'rgba(102,252,241,0.2)' : 'rgba(255,255,255,0.06)';
                card.onmouseout = () => card.style.background = isSelected ? 'rgba(102,252,241,0.1)' : 'rgba(255,255,255,0.02)';
            }
            
            card.onclick = () => {
                if (window.builderSelectMode) {
                    if (isSelected) window.builderSelectedPackages.delete(absolutePath);
                    else window.builderSelectedPackages.add(absolutePath);
                    window.builderRenderGrid();
                } else {
                    document.getElementById('builder-source-dir').value = absolutePath;
                    window.builderLoadManifest();
                    window.builderRenderGrid();
                }
            };
            
            groupGrid.appendChild(card);
        });
        grid.appendChild(groupGrid);
    }
    } catch (e) {
        window.builderLog("Error in renderGrid: " + e.message, "error");
        console.error(e);
    }
};

window.builderSetView = function(mode) {
    window.builderViewMode = mode;
    window.builderRenderGrid();
};

window.builderToggleSelectMode = function() {
    window.builderSelectMode = !window.builderSelectMode;
    if (!window.builderSelectMode) window.builderSelectedPackages.clear();
    window.builderRenderGrid();
};

window.builderToggleCategory = function(type) {
    if (window.builderCollapsedCategories.has(type)) {
        window.builderCollapsedCategories.delete(type);
    } else {
        window.builderCollapsedCategories.add(type);
    }
    window.builderRenderGrid();
};

window.builderToggleAllCategories = function(expand) {
    if (expand) {
        window.builderCollapsedCategories.clear();
    } else {
        if (window.builderSourcesData) {
            window.builderSourcesData.forEach(s => window.builderCollapsedCategories.add(s.type || 'other'));
        }
    }
    window.builderRenderGrid();
};

window.builderExecuteBatchActions = function() {
    if (window.builderSelectedPackages.size === 0) return;
    const paths = Array.from(window.builderSelectedPackages);
    
    let html = `<div style="padding:15px; text-align:center; max-width:400px; margin:0 auto;">
        <h4 style="margin-bottom:15px; font-weight:800; text-transform:uppercase;">Batch Actions <span style="font-size:0.7em; color:var(--muted)">(${paths.length} packages)</span></h4>
        <p style="color:var(--muted); margin-bottom:20px; font-size:0.9em;">Select an action to perform on all selected packages.</p>
        
        <div style="display:grid; grid-template-columns:1fr; gap:10px;">
            <button class="btn btn-primary" onclick="window.builderExecuteBatchBuildReal()" title="Compile all selected packages to .hpkg" style="padding:10px; font-weight:bold;">
                <i class="fas fa-hammer"></i> Build ${paths.length} Packages
            </button>
            <button class="btn btn-secondary" onclick="window.builderExecuteBatchActionLoop('dev-sync')" title="Compile and install directly to Hecos" style="padding:10px;">
                <i class="fas fa-sync"></i> Build & Install (Dev Sync)
            </button>
            <button class="btn btn-secondary" onclick="window.builderExecuteBatchActionLoop('capabilities')" title="Regenerate capabilities automatically" style="padding:10px;">
                <i class="fas fa-shield-alt"></i> Regenerate Capabilities
            </button>
            <button class="btn btn-secondary" onclick="window.builderExecuteBatchActionLoop('inspect')" title="Run security & structure inspection" style="padding:10px;">
                <i class="fas fa-search"></i> Inspect Packages
            </button>
            <button class="btn btn-secondary" onclick="window.builderExecuteBatchActionLoop('view-caps')" title="View all capabilities across selected packages" style="padding:10px;">
                <i class="fas fa-list-ul"></i> View Capabilities Report
            </button>
        </div>
    </div>`;
    
    _builderModal(html, true); // true = closeable
};

window.builderExecuteBatchActionLoop = async function(action) {
    const paths = Array.from(window.builderSelectedPackages);
    let successCount = 0;
    let failCount = 0;
    let combinedReport = [];
    
    _builderModal(`<div style="padding:20px; text-align:center;">
        <i class="fas fa-circle-notch fa-spin fa-2x"></i><br><br>
        <span id="batch-progress-text">Processing 0 / ${paths.length}...</span>
    </div>`, false);
    
    for (let i = 0; i < paths.length; i++) {
        const path = paths[i];
        document.getElementById('batch-progress-text').innerText = `Processing ${i+1} / ${paths.length}...`;
        
        try {
            if (action === 'dev-sync') {
                const resp = await fetch('/api/hpm/builder/dev-sync', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ src_dir: path }) });
                const data = await resp.json();
                if (data.ok) successCount++; else failCount++;
            } 
            else if (action === 'capabilities') {
                const resp = await fetch('/api/hpm/builder/capabilities', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ src_dir: path }) });
                const data = await resp.json();
                if (data.ok) successCount++; else failCount++;
            }
            else if (action === 'inspect') {
                const resp = await fetch('/api/hpm/builder/inspect', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ src_dir: path }) });
                const data = await resp.json();
                if (data.ok) successCount++; else failCount++;
            }
            else if (action === 'view-caps') {
                const resp = await fetch('/api/hpm/builder/load', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ src_dir: path }) });
                const data = await resp.json();
                if (data.ok && data.manifest) {
                    const caps = data.manifest.capabilities || {};
                    const capsList = Object.keys(caps).map(k => `&bull; <span style="color:var(--accent)">${k}</span>: <span style="color:var(--muted)">${caps[k]}</span>`).join('<br>');
                    combinedReport.push(`<div style="margin-bottom:10px;"><b style="font-size:1.1em; color:var(--text);">${data.manifest.name || data.manifest.id}</b><div style="padding-left:10px; margin-top:5px;">${capsList || '<i style="color:var(--muted)">- No capabilities required</i>'}</div></div>`);
                    successCount++;
                } else {
                    failCount++;
                }
            }
        } catch(e) {
            failCount++;
        }
    }
    
    if (action === 'view-caps') {
        const html = `<div style="padding:15px; max-height:60vh; overflow-y:auto; text-align:left; font-size:0.9em; line-height:1.4;">
            <h4 style="margin-bottom:15px; text-transform:uppercase; font-weight:800;">Capabilities Report <span style="color:var(--muted); font-size:0.7em;">(${paths.length} packages)</span></h4>
            <div style="background:rgba(255,255,255,0.02); padding:15px; border-radius:8px; border:1px solid rgba(255,255,255,0.05);">
                ${combinedReport.join('<hr style="border-color:rgba(255,255,255,0.05); margin:15px 0;">')}
            </div>
            <div style="text-align:center; margin-top:20px;">
                <button class="btn btn-primary" onclick="_builderModal(false)">Close Report</button>
            </div>
        </div>`;
        _builderModal(html, true);
    } else {
        _builderModal(false);
        window.builderLog(`Batch ${action} complete. Success: ${successCount}, Failed: ${failCount}`, failCount > 0 ? 'warn' : 'success');
        window.builderToggleSelectMode(); // disable selection mode
        window.builderRefreshSources(); // Refresh UI
    }
};

window.builderExecuteBatchBuildReal = async function() {
    _builderModal('<div style="padding:20px; text-align:center;"><i class="fas fa-circle-notch fa-spin fa-2x"></i><br><br>Batch building... Check console.</div>', false);
    
    const paths = Array.from(window.builderSelectedPackages);
    const packages = [];
    paths.forEach(p => {
        const parts = p.split('\\\\');
        packages.push(parts[parts.length - 1]);
    });
    
    try {
        const baseDir = document.getElementById('builder-sources-root') ? document.getElementById('builder-sources-root').value : '';
        const outDir = document.getElementById('builder-dest-root') ? document.getElementById('builder-dest-root').value : '';
        const resp = await fetch('/api/hpm/builder/batch-build', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ packages: packages, base_dir: baseDir, out_dir: outDir })
        });
        const data = await resp.json();
        
        _builderModal(false);
        if (data.ok) {
            window.builderLog(`Batch build complete. Success: ${data.success_count}, Failed: ${data.fail_count}`, 'success');
            window.builderToggleSelectMode();
        } else {
            window.builderLog(`Batch build failed: ${data.error}`, 'error');
        }
    } catch(e) {
        _builderModal(false);
        window.builderLog(`Batch build exception: ${e}`, 'error');
    }
};

window.builderExecuteBatchBuildCat = function(type) {
    if (!window.builderSourcesData) return;
    const pkgs = window.builderSourcesData.filter(s => (s.type || 'other') === type);
    window.builderSelectMode = true;
    window.builderSelectedPackages.clear();
    
    const baseDir = document.getElementById('builder-sources-root') ? document.getElementById('builder-sources-root').value : '';
    
    pkgs.forEach(src => {
        let d = baseDir;
        if (!d.endsWith("\\\\") && !d.endsWith("/")) d += "\\\\";
        window.builderSelectedPackages.add(d + src.rel_path);
    });
    window.builderRenderGrid();
};

// Initialize scanner automatically
setTimeout(() => {
    window.builderRefreshSources();
}, 500);

window._builderUpdateImages = function(dir, images) {
    const box = document.getElementById('builder-image-preview');
    const cnt = document.getElementById('builder-image-count');
    if (!box) return;
    
    if (images && images.length > 0) {
        if (cnt) cnt.innerText = images.length + (images.length === 1 ? " Image" : " Images");
        let d = dir;
        if (!d.endsWith("\\") && !d.endsWith("/")) d += "\\";
        const imgPath = d + images[0];
        box.innerHTML = `<img src="/api/local_file?path=${encodeURIComponent(imgPath)}&t=${Date.now()}" style="width:100%; height:100%; object-fit:cover;">`;
    } else {
        if (cnt) cnt.innerText = "0 Images";
        box.innerHTML = '<i class="fas fa-image" style="font-size:24px; color:var(--muted);"></i>';
    }
};


window.builderLoadManifest = async function() {
    const dir = document.getElementById('builder-source-dir').value;
    if (!dir) {
        document.getElementById('builder-editor-area').style.display = 'none';
        return; // Empty option selected
    }

    try {
        const response = await fetch('/api/hpm/builder/load', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ src_dir: dir })
        });
        const data = await response.json();
        
        if (!data.ok) {
            _builderModal(data.error || "Failed to load manifest.", true);
            return;
        }

        currentManifest = data.manifest;
        window.builderLog(`Loaded manifest for package: ${currentManifest.name || 'Unknown'} (${currentManifest.id || 'N/A'})`, 'info');

        const area = document.getElementById('builder-editor-area');
        area.style.display = 'flex';
        const empty = document.getElementById('builder-editor-empty');
        if(empty) empty.style.display = 'none';
        
        // Ensure values exist
        document.getElementById('builder-id').value = currentManifest.id || '';
        document.getElementById('builder-name').value = currentManifest.name || '';
        const v = currentManifest.version || '1.0.0';
        document.getElementById('builder-version').value = v;
        const vparts = v.split('.');
        document.getElementById('builder-version-major').value = parseInt(vparts[0]) || 0;
        document.getElementById('builder-version-minor').value = parseInt(vparts[1]) || 0;
        document.getElementById('builder-version-patch').value = parseInt(vparts[2]) || 0;
        document.getElementById('builder-author').value = currentManifest.author || '';
        document.getElementById('builder-type').value = currentManifest.type || '';
        document.getElementById('builder-license').value = currentManifest.license || '';
        document.getElementById('builder-date').value = currentManifest.date || '';
        const descEl = document.getElementById('builder-desc');
        descEl.value = currentManifest.description || '';
        setTimeout(() => {
            descEl.style.height = '';
            descEl.style.height = descEl.scrollHeight + 'px';
        }, 10);
        
        // Update images
        _builderUpdateImages(dir, data.images);
        
    } catch (e) {
        console.error(e);
        window.builderLog('An unexpected error occurred: ' + e.message, 'error');
        _builderModal("Error connecting to Hecos Backend: " + e.message, true);
    }
};

window.builderSyncVersion = function() {
    const major = document.getElementById('builder-version-major').value || '0';
    const minor = document.getElementById('builder-version-minor').value || '0';
    const patch = document.getElementById('builder-version-patch').value || '0';
    document.getElementById('builder-version').value = `${major}.${minor}.${patch}`;
};
