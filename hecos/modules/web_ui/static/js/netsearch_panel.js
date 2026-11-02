/**
 * netsearch_panel.js
 * Central Hub panel logic for Hecos Net Search System App.
 * Manages Net Search settings, Tor network status, and Resilient Search Endpoints, Nodes & Fallbacks.
 */
(function () {
  let _endpointsLoading = false;

  function _notify(msg, type = 'info') {
    if (typeof window.showToast === 'function') {
      window.showToast(msg, type);
    } else {
      console.log(`[NetSearch] [${type}] ${msg}`);
    }
  }

  function _ensureSearchEndpoints(cb) {
    if (window.SearchEndpoints) {
      return cb(window.SearchEndpoints);
    }
    // Try to load search_endpoints.js dynamically if not present
    let script = document.querySelector('script[src*="search_endpoints.js"]');
    if (!script) {
      script = document.createElement('script');
      script.src = '/hpm_plugin/net_search/web/static/js/search/search_endpoints.js';
      script.onload = () => {
        if (window.SearchEndpoints) cb(window.SearchEndpoints);
      };
      document.head.appendChild(script);
    } else {
      setTimeout(() => _ensureSearchEndpoints(cb), 100);
    }
  }

  window.updateNetSearchConfig = async function (keyPath, value) {
    try {
      const parts = keyPath.split('.');
      const payload = {};
      let curr = payload;
      for (let i = 0; i < parts.length - 1; i++) {
        curr[parts[i]] = {};
        curr = curr[parts[i]];
      }
      curr[parts[parts.length - 1]] = value;

      const res = await fetch('/hecos/api/plugins/net_search/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      }).then(r => r.json());

      if (res.ok) {
        _notify('Net Search setting saved', 'success');
        if (keyPath === 'tor.onion_action') {
          const a = document.getElementById('search-tor-onion-action');
          const b = document.getElementById('endp-tor-onion-action');
          if (a) a.value = value;
          if (b) b.value = value;
        } else if (keyPath === 'tor.tor_browser_path') {
          const a = document.getElementById('search-tor-browser-path');
          const b = document.getElementById('endp-tor-browser-path');
          if (a) a.value = value;
          if (b) b.value = value;
        }
      } else {
        _notify('Failed to save Net Search setting: ' + (res.error || 'Unknown'), 'error');
      }
    } catch (e) {
      console.error('[NetSearchPanel] update error:', e);
    }
  };

  window.loadNetSearchPanelConfig = async function () {
    if (_endpointsLoading) return;
    _endpointsLoading = true;
    try {
      // 1. Fetch plugin config
      const cfgRes = await fetch('/hecos/api/plugins/net_search/config').then(r => r.json()).catch(() => null);
      const cfg = (cfgRes && cfgRes.config) ? cfgRes.config : {};

      // Master switch
      const masterSw = document.getElementById('search-master-enabled');
      if (masterSw) masterSw.checked = cfg.enabled !== false;

      // Privacy Shield (Local-Only Mode)
      const localOnlySw = document.getElementById('search-local-only-enabled');
      if (localOnlySw) localOnlySw.checked = cfg.local_only === true;

      // Tor settings
      const tor = cfg.tor || {};
      const torSw = document.getElementById('search-tor-enabled');
      if (torSw) torSw.checked = tor.enabled !== false;
      const socksInput = document.getElementById('search-tor-socks-port');
      if (socksInput) socksInput.value = tor.socks_port || 9055;
      const ctrlInput = document.getElementById('search-tor-control-port');
      if (ctrlInput) ctrlInput.value = tor.control_port || 9056;
      const onionAct = document.getElementById('search-tor-onion-action');
      if (onionAct) onionAct.value = tor.onion_action || 'hecos_viewer';
      const endpOnionAct = document.getElementById('endp-tor-onion-action');
      if (endpOnionAct) endpOnionAct.value = tor.onion_action || 'hecos_viewer';

      const torPath = document.getElementById('search-tor-browser-path');
      if (torPath) torPath.value = tor.tor_browser_path || '';
      const endpTorPath = document.getElementById('endp-tor-browser-path');
      if (endpTorPath) endpTorPath.value = tor.tor_browser_path || '';

      // SearXNG settings
      const sx = cfg.searxng || {};
      const sxSw = document.getElementById('search-searxng-enabled');
      if (sxSw) sxSw.checked = sx.enabled !== false;
      const sxUrl = document.getElementById('search-searxng-url');
      if (sxUrl) sxUrl.value = sx.url || 'http://127.0.0.1:8888';

      // Defaults
      const timeoutInput = document.getElementById('search-timeout');
      if (timeoutInput) timeoutInput.value = cfg.timeout || 10;
      const limitInput = document.getElementById('search-limit');
      if (limitInput) limitInput.value = cfg.limit || 25;

      // Check Tor status badge
      window.checkTorStatusBadge();

      // 2. Fetch endpoints and populate full card editor
      const epRes = await fetch('/api/hsearch/endpoints').then(r => r.json()).catch(() => null);
      if (epRes && epRes.ok && epRes.endpoints) {
        _ensureSearchEndpoints((SE) => {
          window.renderNetSearchEndpointsUI(epRes.endpoints, tor);
        });
      }
    } catch (err) {
      console.warn('[NetSearchPanel] load error:', err);
    } finally {
      _endpointsLoading = false;
    }
  };

  window.renderNetSearchEndpointsUI = function (ep, torCfg = {}) {
    _ensureSearchEndpoints((SE) => {
      const sx = ep.searxng || {};
      const ahmia = ep.dark_ahmia || {};
      const torch = ep.dark_torch || {};
      const haystak = ep.dark_haystak || {};
      const onionland = ep.dark_onionland || {};
      const excavator = ep.dark_excavator || {};
      const phobos = ep.dark_phobos || {};
      const tor66 = ep.dark_tor66 || {};
      const daniel = ep.dark_danieltore || {};
      const archives = ep.archives || {};
      const customTorEngines = Array.isArray(ep.custom_onion_engines) ? ep.custom_onion_engines : [];
      const customNodes = Array.isArray(ep.custom_nodes) ? ep.custom_nodes : [];
      const fallbacks = Array.isArray(sx.fallbacks) ? sx.fallbacks : [];

      // 1. Populate SearXNG local daemon
      const localWrap = document.getElementById('endp-searxng-local-wrap');
      if (localWrap) {
        const localInst = sx.local_instance || SE.decomposeUrl(sx.local_url || 'http://127.0.0.1:8888', 'SearXNG Local Daemon', 'http');
        localInst.id = 'endp_sx_local';
        localWrap.innerHTML = SE.renderCard(localInst, {
          typeBadge: 'LOCAL DAEMON',
          isDeletable: false,
          key: 'searxng_local',
          category: 'searxng'
        });
      }

      // 1b. Populate SearXNG Aggregated Engines
      const enginesWrap = document.getElementById('endp-searxng-engines-wrap');
      const sxEngines = Array.isArray(sx.engines) ? sx.engines : [];
      if (enginesWrap) {
        enginesWrap.innerHTML = '';
        sxEngines.forEach(eng => {
          SE.addSearxngEngine('endp-searxng-engines-wrap', eng);
        });
        window.updateSearxngEnginesCount();
      }

      // 2. Populate SearXNG fallbacks
      const fbWrap = document.getElementById('endp-searxng-fallbacks-wrap');
      if (fbWrap) {
        fbWrap.innerHTML = '';
        fallbacks.forEach(f => {
          const item = (typeof f === 'string') ? SE.decomposeUrl(f, '', 'https') : f;
          SE.addEndpoint('endp-searxng-fallbacks-wrap', item, {
            typeBadge: 'SEARXNG MIRROR',
            isDeletable: true,
            key: 'searxng_fallback',
            category: 'searxng'
          });
        });
      }

      // 3. Populate Dark Web Built-in Engines
      const torWrap = document.getElementById('endp-tor-engines-wrap');
      if (torWrap) {
        torWrap.innerHTML = '';
        const torEnginesDef = [
          {
            key: 'ahmia_onion',
            badge: 'TOR ONION',
            data: ahmia.onion || SE.decomposeUrl(ahmia.onion_url || 'http://juhanurmihxlp77nkq76byazcldy2hlmovfu2epvl5ankdibsot4csyd.onion', 'Ahmia (.onion)', 'http')
          },
          {
            key: 'ahmia_clear',
            badge: 'CLEARNET GATEWAY',
            data: ahmia.clearnet || SE.decomposeUrl(ahmia.clearnet_url || 'https://ahmia.fi', 'Ahmia Clearnet Gateway', 'https')
          },
          {
            key: 'ddg_onion',
            badge: 'TOR ONION',
            data: torch.ddg || SE.decomposeUrl(torch.ddg_onion || 'https://duckduckgogg42xjoc72x3sjasowoarfbgcmvfimaftt6twagswzczad.onion/html/', 'DuckDuckGo (.onion)', 'https')
          },
          {
            key: 'torch_onion',
            badge: 'TOR ONION',
            data: torch.torch || SE.decomposeUrl(torch.torch_onion || 'http://xmh57jrknzkhv6y3ls3ubitzfqnkrwxhopf5aygthi7d6rplyvk3noyd.onion/cgi-bin/omega/omega', 'Torch (.onion)', 'http')
          },
          {
            key: 'haystak_onion',
            badge: 'TOR ONION',
            data: haystak.onion || SE.decomposeUrl(haystak.onion_url || 'http://haystak5njsmn2hqkewecpaxetahtwhsbsa64jom2k22z5afxhnpxfid.onion', 'Haystak (.onion)', 'http')
          },
          {
            key: 'onionland_clear',
            badge: 'CLEARNET GATEWAY',
            data: onionland.clearnet || SE.decomposeUrl(onionland.clearnet_url || 'https://onionsearchengine.com/search.php', 'Onion Search Engine', 'https')
          },
          {
            key: 'excavator_onion',
            badge: 'TOR ONION',
            data: excavator.onion || SE.decomposeUrl(excavator.onion_url || 'http://2fd6cemt4gmccflhm6imvdfvli3nf7zn6rfrwpsy7uhxrgbypvwf5fad.onion/search', 'Excavator (.onion)', 'http')
          },
          {
            key: 'phobos_onion',
            badge: 'TOR ONION',
            data: phobos.onion || SE.decomposeUrl(phobos.onion_url || 'http://phobosxilamwcg75xt22id7aywkzol6q6rfl2flipcqoc4e4ahima5id.onion/search', 'Phobos (.onion)', 'http')
          },
          {
            key: 'tor66_onion',
            badge: 'TOR ONION',
            data: tor66.onion || SE.decomposeUrl(tor66.onion_url || 'http://tor66sewebgixwhcqfnp5inzp5x5uohhdy3kvtnyfxc2e5mxiuh34iid.onion/search', 'Tor66 (.onion)', 'http')
          },
          {
            key: 'daniel_onion',
            badge: 'TOR ONION',
            data: daniel.onion || SE.decomposeUrl(daniel.onion_url || 'http://tordexu73joywapk2txdr54jed4imqledpcvcuf75qsas2gwdgksvnyd.onion/search', 'TorDex Directory (.onion)', 'http')
          }
        ];

        torEnginesDef.forEach(ted => {
          ted.data.id = 'endp_' + ted.key;
          torWrap.insertAdjacentHTML('beforeend', SE.renderCard(ted.data, {
            typeBadge: ted.badge,
            isDeletable: false,
            key: ted.key,
            category: 'tor'
          }));
        });

        // Add custom tor engines
        customTorEngines.forEach(cte => {
          SE.addEndpoint('endp-tor-engines-wrap', cte, {
            typeBadge: 'CUSTOM TOR',
            isDeletable: true,
            key: 'custom_tor',
            category: 'tor'
          });
        });
      }

      // 4. Archives
      const archInput = document.getElementById('endp-archive-org');
      if (archInput) archInput.value = archives.archive_org || 'https://archive.org/advancedsearch.php';
      const wikiInput = document.getElementById('endp-wikimedia');
      if (wikiInput) wikiInput.value = archives.wikimedia_commons || 'https://commons.wikimedia.org/w/api.php';

      // 5. Populate Custom Nodes
      const customWrap = document.getElementById('endp-custom-nodes-wrap');
      if (customWrap) {
        customWrap.innerHTML = '';
        customNodes.forEach(cn => {
          SE.addEndpoint('endp-custom-nodes-wrap', cn, {
            typeBadge: 'CUSTOM NODE',
            isDeletable: true,
            key: 'custom_node',
            category: 'custom'
          });
        });
      }

      // 6. Update counts on section badges
      const fbCount = document.getElementById('badge-searxng-fallbacks-count');
      if (fbCount) fbCount.textContent = `${fallbacks.length} Mirrors`;

      const torCount = document.getElementById('badge-tor-engines-count');
      if (torCount) {
        const totalTor = 10 + customTorEngines.length;
        torCount.textContent = `${totalTor} Engines`;
      }

      const customCount = document.getElementById('badge-custom-nodes-count');
      if (customCount) customCount.textContent = `${customNodes.length} Nodes`;
    });
  };

  window.toggleEndpointSection = function (triggerEl, bodyId, forceExpand) {
    const body = document.getElementById(bodyId);
    if (!body) return;
    const isCurrentlyHidden = (body.style.display === 'none');
    const shouldShow = (typeof forceExpand === 'boolean') ? forceExpand : isCurrentlyHidden;

    body.style.display = shouldShow ? '' : 'none';

    // Find corresponding toggle button in the group
    const group = body.closest('.endpoint-group');
    const btn = group ? group.querySelector('.btn-group-toggle') : null;
    if (btn) {
      btn.innerHTML = shouldShow ? '<i class="fas fa-minus"></i>' : '<i class="fas fa-plus"></i>';
      btn.title = shouldShow ? 'Collapse Section (-)' : 'Expand Section (+)';
      btn.setAttribute('aria-expanded', shouldShow ? 'true' : 'false');
    }
  };

  window.toggleAllEndpointSections = function (expand = true) {
    const groups = document.querySelectorAll('#netsearch-endpoints-manager-container .endpoint-group');
    groups.forEach(g => {
      const body = g.querySelector('.endpoint-group-body');
      const btn = g.querySelector('.btn-group-toggle');
      if (body) {
        body.style.display = expand ? '' : 'none';
        if (btn) {
          btn.innerHTML = expand ? '<i class="fas fa-minus"></i>' : '<i class="fas fa-plus"></i>';
          btn.title = expand ? 'Collapse Section (-)' : 'Expand Section (+)';
          btn.setAttribute('aria-expanded', expand ? 'true' : 'false');
        }
      }
    });
  };

  window.checkTorStatusBadge = async function () {
    const badge = document.getElementById('tor-cfg-status-badge');
    if (!badge) return;
    try {
      const res = await fetch('/api/hsearch/tor_status').then(r => r.json());
      if (res.ok && res.tor_online) {
        badge.textContent = `Online (Port ${res.tor_port || 9055})`;
        badge.style.background = 'rgba(16, 185, 129, 0.15)';
        badge.style.color = '#34d399';
      } else {
        badge.textContent = 'Offline';
        badge.style.background = 'rgba(239, 68, 68, 0.15)';
        badge.style.color = '#f87171';
      }
    } catch (e) {
      badge.textContent = 'Check failed';
    }
  };

  window.torNewCircuit = async function () {
    try {
      const res = await fetch('/api/hsearch/tor_newnym', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: '{}'
      }).then(r => r.json());
      if (res.ok) {
        _notify('New Tor identity (circuit) requested successfully!', 'success');
        window.checkTorStatusBadge();
      } else {
        _notify('Tor circuit request: ' + (res.message || res.error || 'Failed to switch identity'), 'warning');
      }
    } catch (e) {
      _notify('Error requesting new Tor circuit: ' + e.message, 'error');
    }
  };

  window.syncTorActionFromEndpoints = function (val) {
    const topSel = document.getElementById('search-tor-onion-action');
    if (topSel) topSel.value = val;
    window.updateNetSearchConfig('tor.onion_action', val);
  };

  window.syncTorPathFromEndpoints = function (val) {
    const topPath = document.getElementById('search-tor-browser-path');
    if (topPath) topPath.value = val;
    window.updateNetSearchConfig('tor.tor_browser_path', val);
  };

  window.detectTorBrowserPath = async function () {
    try {
      const res = await fetch('/api/hsearch/detect_tor_browser').then(r => r.json());
      if (res.ok && res.path) {
        const input = document.getElementById('search-tor-browser-path');
        if (input) input.value = res.path;
        const endpInput = document.getElementById('endp-tor-browser-path');
        if (endpInput) endpInput.value = res.path;
        window.updateNetSearchConfig('tor.tor_browser_path', res.path);
        _notify('Tor Browser detected: ' + res.path, 'success');
      } else {
        _notify('Tor Browser could not be detected automatically.', 'warning');
      }
    } catch (e) {
      _notify('Detection error: ' + e, 'error');
    }
  };
  window.autoDetectTorBrowser = window.detectTorBrowserPath;

  window.addSearxngFallbackNode = function () {
    window.toggleEndpointSection(null, 'endp-searxng-fallbacks-body', true);
    _ensureSearchEndpoints((SE) => {
      SE.addEndpoint('endp-searxng-fallbacks-wrap', {
        name: 'Custom Fallback Node',
        protocol: 'https',
        host: '',
        port: '',
        path: '',
        enabled: true
      }, {
        typeBadge: 'SEARXNG MIRROR',
        isDeletable: true,
        key: 'searxng_fallback',
        category: 'searxng'
      });
    });
  };

  window.addCustomTorEngineNode = function () {
    window.toggleEndpointSection(null, 'endp-tor-engines-body', true);
    _ensureSearchEndpoints((SE) => {
      SE.addEndpoint('endp-tor-engines-wrap', {
        name: 'Custom Onion Engine',
        protocol: 'http',
        host: '',
        port: '',
        path: '/search?q={q}',
        enabled: true
      }, {
        typeBadge: 'CUSTOM TOR',
        isDeletable: true,
        key: 'custom_tor',
        category: 'tor'
      });
    });
  };

  window.addCustomSearchNode = function () {
    window.toggleEndpointSection(null, 'endp-custom-nodes-body', true);
    _ensureSearchEndpoints((SE) => {
      SE.addEndpoint('endp-custom-nodes-wrap', {
        name: 'Custom Search Node',
        protocol: 'https',
        host: '',
        port: '',
        path: '',
        enabled: true
      }, {
        typeBadge: 'CUSTOM NODE',
        isDeletable: true,
        key: 'custom_node',
        category: 'custom'
      });
    });
  };

  window.updateSearxngEnginesCount = function () {
    const countBadge = document.getElementById('badge-searxng-engines-count');
    if (!countBadge) return;
    const cards = document.querySelectorAll('#endp-searxng-engines-wrap .searxng-engine-card');
    let active = 0;
    cards.forEach(c => {
      if (c.querySelector('.engine-enabled-checkbox')?.checked) active++;
    });
    countBadge.textContent = `${cards.length} Engines (${active} Active)`;
  };

  window.addSearxngEngineNode = function (presetData) {
    window.toggleEndpointSection(null, 'endp-searxng-engines-body', true);
    _ensureSearchEndpoints((SE) => {
      SE.addSearxngEngine('endp-searxng-engines-wrap', presetData || {
        name: '',
        label: '',
        category: 'general',
        enabled: true
      });
    });
  };

  window.quickAddSearxngEngine = function (name, label, category) {
    window.toggleEndpointSection(null, 'endp-searxng-engines-body', true);
    // Check if engine with this name already exists in wrap
    const existing = document.querySelector(`#endp-searxng-engines-wrap .searxng-engine-card input.engine-name-input[value="${name}"]`);
    if (existing) {
      const card = existing.closest('.searxng-engine-card');
      const cb = card.querySelector('.engine-enabled-checkbox');
      if (cb && !cb.checked) {
        cb.checked = true;
        _ensureSearchEndpoints(SE => SE.syncEngineCard(card.dataset.id));
        _notify(`Activated existing engine: ${label}`, 'info');
      } else {
        _notify(`Engine ${label} is already configured and active.`, 'info');
      }
      card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      return;
    }
    window.addSearxngEngineNode({ name, label, category, enabled: true });
    _notify(`Added ${label} to aggregated engines. Click 'Save Endpoints' to apply.`, 'success');
  };

  window.saveEndpointsFromUI = async function () {
    _ensureSearchEndpoints(async (SE) => {
      // 1. SearXNG local
      const localCard = document.querySelector('#endp-searxng-local-wrap .endpoint-card');
      const localItem = SE.collectCard(localCard);

      // 1b. SearXNG aggregated engines
      const engineCards = document.querySelectorAll('#endp-searxng-engines-wrap .searxng-engine-card');
      const sxEngines = [];
      engineCards.forEach(c => {
        const item = SE.collectSearxngEngineCard(c);
        if (item && item.name) sxEngines.push(item);
      });

      // 2. SearXNG fallbacks
      const fallbackCards = document.querySelectorAll('#endp-searxng-fallbacks-wrap .endpoint-card');
      const fallbacks = [];
      fallbackCards.forEach(c => {
        const item = SE.collectCard(c);
        if (item && (item.host || item.url)) fallbacks.push(item);
      });

      // 3. Built-in Tor engines by key
      function getTorItem(key) {
        const card = document.querySelector(`#endp-tor-engines-wrap .endpoint-card[data-key="${key}"]`);
        return SE.collectCard(card);
      }

      const ahmiaOnion = getTorItem('ahmia_onion');
      const ahmiaClear = getTorItem('ahmia_clear');
      const ddgOnion = getTorItem('ddg_onion');
      const torchOnion = getTorItem('torch_onion');
      const haystakOnion = getTorItem('haystak_onion');
      const onionlandClear = getTorItem('onionland_clear');
      const excavatorOnion = getTorItem('excavator_onion');
      const phobosOnion = getTorItem('phobos_onion');
      const tor66Onion = getTorItem('tor66_onion');
      const danielOnion = getTorItem('daniel_onion');

      // Custom Tor engines
      const customTorCards = document.querySelectorAll('#endp-tor-engines-wrap .endpoint-card[data-key="custom_tor"]');
      const customTorEngines = [];
      customTorCards.forEach(c => {
        const item = SE.collectCard(c);
        if (item && (item.host || item.url)) {
          customTorEngines.push({
            name: item.name || 'Custom Onion',
            onion_url: item.url,
            protocol: item.protocol,
            host: item.host,
            port: item.port,
            path: item.path,
            search_template: item.path || '/search?q={q}',
            enabled: item.enabled,
            use_api_key: item.use_api_key,
            api_key: item.api_key
          });
        }
      });

      // 4. Custom Nodes
      const customNodeCards = document.querySelectorAll('#endp-custom-nodes-wrap .endpoint-card');
      const customNodes = [];
      customNodeCards.forEach(c => {
        const item = SE.collectCard(c);
        if (item && (item.host || item.url)) customNodes.push(item);
      });

      // 5. Archives
      const archiveOrg = (document.getElementById('endp-archive-org')?.value || '').trim();
      const wikimedia = (document.getElementById('endp-wikimedia')?.value || '').trim();

      const payload = {
        searxng: {
          local_instance: localItem,
          local_url: localItem?.url || 'http://127.0.0.1:8888',
          fallbacks: fallbacks,
          engines: sxEngines
        },
        dark_ahmia: {
          onion: ahmiaOnion,
          onion_url: ahmiaOnion?.url || '',
          clearnet: ahmiaClear,
          clearnet_url: ahmiaClear?.url || ''
        },
        dark_torch: {
          torch: torchOnion,
          torch_onion: torchOnion?.url || '',
          ddg: ddgOnion,
          ddg_onion: ddgOnion?.url || ''
        },
        dark_haystak: {
          onion: haystakOnion,
          onion_url: haystakOnion?.url || ''
        },
        dark_onionland: {
          clearnet: onionlandClear,
          clearnet_url: onionlandClear?.url || ''
        },
        dark_excavator: {
          onion: excavatorOnion,
          onion_url: excavatorOnion?.url || ''
        },
        dark_phobos: {
          onion: phobosOnion,
          onion_url: phobosOnion?.url || ''
        },
        dark_tor66: {
          onion: tor66Onion,
          onion_url: tor66Onion?.url || ''
        },
        dark_danieltore: {
          onion: danielOnion,
          onion_url: danielOnion?.url || ''
        },
        archives: {
          archive_org: archiveOrg || 'https://archive.org/advancedsearch.php',
          wikimedia_commons: wikimedia || 'https://commons.wikimedia.org/w/api.php'
        },
        custom_nodes: customNodes,
        custom_onion_engines: customTorEngines
      };

      try {
        const res = await fetch('/api/hsearch/endpoints', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        }).then(r => r.json());

        if (res.ok) {
          _notify('Search endpoints saved successfully!', 'success');
          // Also persist primary SearXNG URL if modified
          if (localItem && localItem.url) {
            window.updateNetSearchConfig('searxng.url', localItem.url);
          }
          // Also persist Tor onion action and Tor browser path if present
          const curAction = document.getElementById('endp-tor-onion-action')?.value || document.getElementById('search-tor-onion-action')?.value;
          if (curAction) window.updateNetSearchConfig('tor.onion_action', curAction);
          const curPath = (document.getElementById('endp-tor-browser-path')?.value || document.getElementById('search-tor-browser-path')?.value || '').trim();
          if (curPath) window.updateNetSearchConfig('tor.tor_browser_path', curPath);
        } else {
          _notify('Failed to save endpoints: ' + (res.error || 'Unknown error'), 'error');
        }
      } catch (e) {
        _notify('Error saving endpoints: ' + e.message, 'error');
      }
    });
  };

  window.resetEndpointsFromUI = async function () {
    if (!confirm('Reset all search endpoints and fallback pools to factory defaults?')) return;
    try {
      const res = await fetch('/api/hsearch/endpoints/reset', { method: 'POST' }).then(r => r.json());
      if (res.ok) {
        _notify('Endpoints reset to factory defaults', 'success');
        window.loadNetSearchPanelConfig();
      } else {
        _notify('Reset failed: ' + (res.error || 'Unknown error'), 'error');
      }
    } catch (e) {
      _notify('Error resetting endpoints: ' + e.message, 'error');
    }
  };

  window.reloadNetSearchEndpoints = function () {
    window.loadNetSearchPanelConfig();
  };

  window.populateNetSearchPanelUI = window.loadNetSearchPanelConfig;

  // React to hashchange (Central Hub navigation)
  window.addEventListener('hashchange', () => {
    if (window.location.hash === '#netsearch' || window.location.hash === '#tab-netsearch') {
      window.loadNetSearchPanelConfig();
    }
  });

  // Run on DOM ready or immediate if already loaded
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', window.loadNetSearchPanelConfig);
  } else {
    window.loadNetSearchPanelConfig();
  }
})();
