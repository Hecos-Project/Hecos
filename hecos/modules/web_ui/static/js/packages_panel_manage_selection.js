/**
 * packages_panel_manage.js
 * ─────────────────────────────────────────────────────────────────────────────
 * Manage logic for Hecos Package Manager (Status, Uninstall)
 */

window._hpmSelectionMode = false;
window._hpmSelectedPackages = new Set();

window.hpmToggleSelectionMode = function() {
    window._hpmSelectionMode = !window._hpmSelectionMode;
    window._hpmSelectedPackages.clear();
    
    const toolbar = document.getElementById('hpm-selection-toolbar');
    const selectModeBtn = document.getElementById('hpm-btn-select-mode');
    
    if (toolbar) toolbar.style.display = window._hpmSelectionMode ? 'flex' : 'none';
    
    if (selectModeBtn) {
        if (window._hpmSelectionMode) {
            selectModeBtn.style.background = 'var(--accent)';
            selectModeBtn.style.color = '#fff';
        } else {
            selectModeBtn.style.background = '';
            selectModeBtn.style.color = '';
        }
    }
    
    const chkAll = document.getElementById('hpm-select-all');
    if (chkAll) chkAll.checked = false;
    
    window.hpmUpdateSelectionUI();
    if (typeof window.hpmRenderHierarchy === 'function') window.hpmRenderHierarchy();
};

window.hpmToggleSelectAll = function() {
    const chkAll = document.getElementById('hpm-select-all');
    const isChecked = chkAll ? chkAll.checked : false;
    
    window._hpmSelectedPackages.clear();
    if (isChecked && window._packages) {
        window._packages.forEach(pkg => {
            if (pkg.removable === true) {
                window._hpmSelectedPackages.add(pkg.id);
            }
        });
    }
    
    window.hpmUpdateSelectionUI();
    if (typeof window.hpmRenderHierarchy === 'function') window.hpmRenderHierarchy();
};

window.hpmTogglePackageSelection = function(pkgId) {
    if (window._hpmSelectedPackages.has(pkgId)) {
        window._hpmSelectedPackages.delete(pkgId);
    } else {
        window._hpmSelectedPackages.add(pkgId);
    }
    window.hpmUpdateSelectionUI();
};

window.hpmUpdateSelectionUI = function() {
    const countEl = document.getElementById('hpm-selected-count');
    const btnUninstall = document.getElementById('hpm-btn-uninstall-selected');
    const count = window._hpmSelectedPackages.size;
    const _ti = (en, it, es) => { const l = (document.documentElement.lang||'en').toLowerCase(); if(l.startsWith('it')) return it; if(l.startsWith('es')) return es; return en; };
    const uninstallStr = _ti('Uninstall', 'Disinstalla', 'Desinstalar');
    
    // Dynamic translations for toolbar buttons
    const lblSelectAll = document.getElementById('lbl-hpm-select-all');
    if (lblSelectAll) lblSelectAll.innerText = _ti('Select all', 'Seleziona tutti', 'Seleccionar todo');
    
    const btnCancel = document.getElementById('btn-hpm-cancel-sel');
    if (btnCancel) btnCancel.innerText = _ti('Cancel', 'Annulla', 'Cancelar');
    
    const btnMode = document.getElementById('hpm-btn-select-mode');
    if (btnMode) btnMode.title = _ti('Select multiple', 'Seleziona multipli', 'Seleccionar múltiples');

    if (countEl) countEl.innerText = count;
    
    if (btnUninstall) {
        if (count > 0) {
            btnUninstall.style.opacity = '1';
            btnUninstall.style.pointerEvents = 'auto';
            btnUninstall.innerHTML = `<i class="fas fa-trash" style="margin-right:6px;"></i> ${uninstallStr} (${count})`;
        } else {
            btnUninstall.style.opacity = '0.5';
            btnUninstall.style.pointerEvents = 'none';
            btnUninstall.innerHTML = `<i class="fas fa-trash" style="margin-right:6px;"></i> ${uninstallStr}`;
        }
    }
};

