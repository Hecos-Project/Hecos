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
  const btnPackages  = document.getElementById('hpm-tab-btn-packages');
  const btnBuiltin   = document.getElementById('hpm-tab-btn-builtin');
  const btnWidgets   = document.getElementById('hpm-tab-btn-widgets');
  const btnStore     = document.getElementById('hpm-tab-btn-store');
  const btnLibraries = document.getElementById('hpm-tab-btn-libraries');

  [btnPackages, btnBuiltin, btnWidgets, btnStore, btnLibraries].forEach(b => b && b.classList.remove('active'));
  const activeBtn = document.getElementById(`hpm-tab-btn-${tabId}`);
  if (activeBtn) activeBtn.classList.add('active');

  // Update panes
  document.getElementById('hpm-pane-packages').style.display = tabId === 'packages' ? 'block' : 'none';
  document.getElementById('hpm-pane-builtin').style.display  = tabId === 'builtin'  ? 'block' : 'none';
  const widgetsPane = document.getElementById('hpm-pane-widgets');
  if (widgetsPane) widgetsPane.style.display = tabId === 'widgets' ? 'block' : 'none';
  const storePane = document.getElementById('hpm-pane-store');
  if (storePane) storePane.style.display = tabId === 'store' ? 'block' : 'none';
  const librariesPane = document.getElementById('hpm-pane-libraries');
  if (librariesPane) librariesPane.style.display = tabId === 'libraries' ? 'block' : 'none';

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
  } else if (tabId === 'libraries') {
    const listEl = document.getElementById('hpm-libraries-list');
    if (!listEl) return;
    fetch('/api/packages/all')
      .then(r => r.ok ? r.json() : null)
      .then(data => {
        if (!data || !data.packages) return;
        const libs = data.packages.filter(p => p.type === 'library');
        window.hpmUpdateCount('libraries', libs.length);
        if (libs.length === 0) {
          listEl.innerHTML = `<div style="text-align:center;padding:40px 20px;color:var(--muted);"><i class="fas fa-book-open" style="font-size:1.6em;margin-bottom:10px;display:block;"></i>No libraries installed yet.</div>`;
          return;
        }
        listEl.innerHTML = libs.map(p => `
          <div style="background:var(--bg2);border:1px solid var(--border-color);border-radius:10px;padding:14px 16px;display:flex;align-items:center;gap:14px;">
            <div style="width:36px;height:36px;background:linear-gradient(135deg,#7c3aed,#4f46e5);border-radius:8px;display:flex;align-items:center;justify-content:center;flex-shrink:0;">
              <i class="fas fa-book" style="color:#fff;font-size:1em;"></i>
            </div>
            <div style="flex:1;min-width:0;">
              <div style="font-weight:600;color:var(--text);font-size:0.95em;">${p.name || p.id}</div>
              <div style="font-size:0.78em;color:var(--muted);margin-top:2px;">${p.description || ''}</div>
            </div>
            <div style="flex-shrink:0;">
              <span style="font-size:0.75em;background:rgba(139,92,246,0.15);color:#8b5cf6;padding:3px 8px;border-radius:6px;font-weight:600;">v${p.version || '?'}</span>
            </div>
          </div>`).join('');
      })
      .catch(() => {
        listEl.innerHTML = `<div style="color:var(--danger);padding:20px;">Failed to load libraries.</div>`;
      });
  }
};
