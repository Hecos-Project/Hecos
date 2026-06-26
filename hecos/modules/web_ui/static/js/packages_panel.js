/**
 * packages_panel.js
 * ─────────────────────────────────────────────────────────────────────────────
 * Orchestrator for Hecos Package Manager Frontend
 */

window.hpmInit = function () {
  window.hpmSwitchTab('packages');
};

window.hpmSwitchTab = async function(tabId) {
  // Update buttons
  const btnPackages = document.getElementById('hpm-tab-btn-packages');
  const btnBuiltin  = document.getElementById('hpm-tab-btn-builtin');
  const btnWidgets  = document.getElementById('hpm-tab-btn-widgets');
  const btnStore    = document.getElementById('hpm-tab-btn-store');

  [btnPackages, btnBuiltin, btnWidgets, btnStore].forEach(b => b && b.classList.remove('active'));
  const activeBtn = document.getElementById(`hpm-tab-btn-${tabId}`);
  if (activeBtn) activeBtn.classList.add('active');

  // Update panes
  document.getElementById('hpm-pane-packages').style.display = tabId === 'packages' ? 'block' : 'none';
  document.getElementById('hpm-pane-builtin').style.display  = tabId === 'builtin'  ? 'block' : 'none';
  const widgetsPane = document.getElementById('hpm-pane-widgets');
  if (widgetsPane) widgetsPane.style.display = tabId === 'widgets' ? 'block' : 'none';
  const storePane = document.getElementById('hpm-pane-store');
  if (storePane) storePane.style.display = tabId === 'store' ? 'block' : 'none';

  // ── Content loading per tab ────────────────────────────────────────────────
  if (tabId === 'packages') {
    if (typeof window.hpmLoadPackages === 'function') window.hpmLoadPackages();

  } else if (tabId === 'builtin') {
    const builtinContainer = document.getElementById('hpm-builtin-container');
    const existingTab = document.getElementById('tab-plugins');

    if (existingTab && existingTab.parentElement !== builtinContainer) {
      builtinContainer.innerHTML = '';
      builtinContainer.appendChild(existingTab);
      existingTab.classList.remove('panel');
      existingTab.style.display = 'block';
      existingTab.classList.add('active');
      if (typeof window.populatePlugins === 'function') window.populatePlugins();
    } else if (!existingTab && builtinContainer && builtinContainer.innerHTML.trim() === '') {
      try {
        if (typeof window._loadPanel === 'function') {
          await window._loadPanel('plugins');
          const loadedTab = document.getElementById('tab-plugins');
          if (loadedTab) {
            builtinContainer.innerHTML = '';
            builtinContainer.appendChild(loadedTab);
            loadedTab.classList.remove('panel');
            loadedTab.style.display = 'block';
            loadedTab.classList.add('active');
          }
        } else {
          throw new Error('_loadPanel function not found');
        }
      } catch (err) {
        builtinContainer.innerHTML = `<div style="color:var(--danger);padding:20px;">Failed to load built-in modules: ${err.message}</div>`;
      }
    }

  } else if (tabId === 'widgets') {
    const widgetsContainer = document.getElementById('hpm-widgets-container');
    const existingWidgetsTab = document.getElementById('tab-widgets');

    if (existingWidgetsTab && existingWidgetsTab.parentElement !== widgetsContainer) {
      widgetsContainer.innerHTML = '';
      widgetsContainer.appendChild(existingWidgetsTab);
      existingWidgetsTab.classList.remove('panel');
      existingWidgetsTab.style.display = 'block';
      existingWidgetsTab.classList.add('active');
    } else if (!existingWidgetsTab && widgetsContainer && widgetsContainer.innerHTML.trim() === '') {
      try {
        if (typeof window._loadPanel === 'function') {
          await window._loadPanel('widgets');
          const loadedWidgetsTab = document.getElementById('tab-widgets');
          if (loadedWidgetsTab) {
            widgetsContainer.innerHTML = '';
            widgetsContainer.appendChild(loadedWidgetsTab);
            loadedWidgetsTab.classList.remove('panel');
            loadedWidgetsTab.style.display = 'block';
            loadedWidgetsTab.classList.add('active');
          }
        } else {
          throw new Error('_loadPanel function not found');
        }
      } catch (err) {
        widgetsContainer.innerHTML = `<div style="color:var(--danger);padding:20px;">Failed to load Widget Manager: ${err.message}</div>`;
      }
    }
  } else if (tabId === 'store') {
    if (typeof window.hpmStoreInit === 'function') {
      if (!window.HPM_STORE_STATE || !window.HPM_STORE_STATE.catalog) {
        window.hpmStoreInit();
      }
    }
  }
};


window.hpmLoadPackages = async function () {
  const grid = document.getElementById('hpm-packages-grid');
  if (!grid) return;

  grid.innerHTML = `
    <div style="text-align:center;padding:30px;color:var(--muted);">
      <i class="fas fa-spinner fa-spin" style="font-size: 1.5em;"></i>
    </div>`;

  try {
    const resp = await fetch('/api/packages/all');
    const data = await resp.json();
    if (!data.ok) throw new Error(data.error || 'Unknown error');

    const packages = data.packages || [];
    window._packages = packages; // Store globally for toggle and uninstall logic
    
    if (packages.length === 0) {
      grid.innerHTML = `
        <div style="text-align:center;padding:40px;color:var(--muted);">
          <i class="fas fa-box-open" style="font-size:2em;margin-bottom:10px;display:block;opacity:0.4;"></i>
          <div style="font-size:0.9em;">${window.HPM_I18N?.no_modules || 'No modules found.'}</div>
        </div>`;
      return;
    }

    if (typeof window.hpmRenderHierarchy === 'function') {
        grid.innerHTML = window.hpmRenderHierarchy(packages);
    }

  } catch (err) {
    grid.innerHTML = `
      <div style="color:var(--danger,#ef4444);padding:16px;text-align:center;font-size:0.85em;">
        <i class="fas fa-exclamation-triangle" style="margin-right:6px;"></i>
        ${window.HPM_I18N?.failed_load || 'Failed to load modules:'} ${err.message}
      </div>`;
  }
};

// ── Auto-init ─────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', window.hpmInit);
if (document.readyState !== 'loading') {
  window.hpmInit();
}
