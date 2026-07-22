/**
 * packages_panel_tabs.js
 * ─────────────────────────────────────────────────────────────────────────────
 * Tab switching and count updating logic for Hecos Package Manager
 */

window.hpmUpdateCount = function(tabId, count) {
  const el = document.getElementById(`hpm-cnt-${tabId}`);
  if (el) {
    el.textContent = `(${count})`;
  }
  localStorage.setItem(`hpm-cache-cnt-${tabId}`, count);
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
      // Already loaded — just re-attach and re-populate
      builtinContainer.innerHTML = '';
      builtinContainer.appendChild(existingTab);
      existingTab.classList.remove('panel');
      existingTab.style.display = 'block';
      existingTab.classList.add('active');
      if (typeof window.populatePlugins === 'function') window.populatePlugins();
      else if (typeof populateUI === 'function') populateUI();

      setTimeout(() => {
        const builtinCount = document.querySelectorAll('#tab-plugins .toggle-row, #tab-plugins .plugin-card, #tab-plugins [data-plugin]').length;
        if (builtinCount > 0) window.hpmUpdateCount('builtin', builtinCount);
      }, 500);

    } else if (!existingTab && builtinContainer && builtinContainer.innerHTML.trim() === '') {
      // First open — show spinner while loading
      builtinContainer.innerHTML = `
        <div id="hpm-builtin-loading" style="text-align:center;padding:40px 20px;color:var(--muted);">
          <i class="fas fa-spinner fa-spin" style="font-size:1.6em;margin-bottom:12px;display:block;"></i>
          <div style="font-size:0.85em;opacity:0.7;">Loading panel&hellip;</div>
        </div>`;
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

            // Wait for Phase2 scripts (config_mapper_plugins.js) if not yet ready
            const maxWait = 3000;
            const poll = 60;
            let elapsed = 0;
            await new Promise(resolve => {
              const check = () => {
                if (typeof renderPlugins === 'function' || elapsed >= maxWait) {
                  resolve();
                } else {
                  elapsed += poll;
                  setTimeout(check, poll);
                }
              };
              check();
            });

            if (typeof populateUI === 'function') populateUI();

            setTimeout(() => {
              const builtinCount = document.querySelectorAll('#tab-plugins .toggle-row, #tab-plugins .plugin-card, #tab-plugins [data-plugin]').length;
              if (builtinCount > 0) window.hpmUpdateCount('builtin', builtinCount);
            }, 600);
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
      
      setTimeout(() => {
        const widgetCount = document.querySelectorAll('#tab-widgets .toggle-row, #tab-widgets .widget-card, #tab-widgets [data-widget]').length;
        if (widgetCount > 0) window.hpmUpdateCount('widgets', widgetCount);
      }, 500);
      
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
            
            setTimeout(() => {
              // Use API count for accuracy; DOM may not be fully rendered yet
              fetch('/api/widgets').then(r => r.ok ? r.json() : null).then(data => {
                if (data && Array.isArray(data.widgets)) {
                  const count = data.widgets.filter(w => w.sidebar_widget !== false).length;
                  window.hpmUpdateCount('widgets', count);
                } else {
                  const widgetCount = document.querySelectorAll('#tab-widgets .widget-card').length;
                  if (widgetCount > 0) window.hpmUpdateCount('widgets', widgetCount);
                }
              }).catch(() => {
                const widgetCount = document.querySelectorAll('#tab-widgets .widget-card').length;
                if (widgetCount > 0) window.hpmUpdateCount('widgets', widgetCount);
              });
            }, 500);
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
