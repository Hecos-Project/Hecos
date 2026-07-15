  window.populateBrowserUI = function() {
      const bCfg = window.cfg?.plugins?.BROWSER || {};
      const mode = bCfg.browser_engine_mode || 'cdp_mode';
      
      const browserEl = document.getElementById('browser-enabled');
      if (browserEl) browserEl.checked = bCfg.enabled ?? true;
      
      const emApp = document.getElementById('em-app');
      if(emApp && mode === 'app_mode') emApp.checked = true;
      const emCdp = document.getElementById('em-cdp');
      if(emCdp && mode === 'cdp_mode') emCdp.checked = true;
      
      const aCfg = window.cfg?.plugins?.AUTOMATION || {};
      const autoEnabled = aCfg.enabled ?? false;
      const autoEl = document.getElementById('automation-enabled');
      if (autoEl) autoEl.checked = autoEnabled;

      const cdpPort = document.getElementById('browser-cdp-port');
      if (cdpPort) cdpPort.value = bCfg.cdp_port || 9222;
      
      const headless = document.getElementById('browser-headless');
      if (headless) headless.checked = bCfg.headless ?? true;
      
      const blockAds = document.getElementById('browser-block-ads');
      if (blockAds) blockAds.checked = bCfg.block_ads ?? true;
      
      const startup = document.getElementById('browser-startup-url');
      if (startup) startup.value = bCfg.startup_url || '';
      
      const engine = document.getElementById('browser-engine');
      if (engine) engine.value = bCfg.browser_type || 'chromium';
  };

  /**
   * Helper to update in-memory config and trigger a silent save to disk.
   */
  window.updateConfig = function(path, val) {
      console.log(`[Config] Updating ${path} to`, val);
      // Update local window.cfg object so buildPayload picks it up
      const keys = path.split('.');
      let obj = window.cfg;
      for (let i = 0; i < keys.length - 1; i++) {
          obj[keys[i]] = obj[keys[i]] || {};
          obj = obj[keys[i]];
      }
      obj[keys[keys.length - 1]] = val;
      
      // Call global saveConfig if available (silent mode)
      if (typeof saveConfig === 'function') {
          saveConfig(true); 
      }
  };

  async function launchCdpBrowser() {
      if (!confirm("A new instance of Chrome/Edge will be launched with debugging enabled. Do you want to proceed?")) return;
      try {
          const r = await fetch('/api/browser/launch_external', { method: 'POST' });
          const d = await r.json();
          if (d.ok) alert(window.t('webui_diag_done') + ": " + d.message);
          else alert(window.t('webui_diag_error') + ": " + d.error);
      } catch(e) {
          alert(window.t('webui_diag_error') + ": " + e.message);
      }
  }
