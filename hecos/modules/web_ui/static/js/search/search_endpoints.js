/**
 * search_endpoints.js
 * Modular Resilient Search Endpoints, Nodes & Fallbacks Manager for Hecos Deep Search.
 * Provides rich card rendering, automatic URL decomposition/composition,
 * protocol selection (including custom protocols), port configuration, and persistence.
 */
window.SearchEndpoints = (function () {

  function escapeHtml(str) {
    if (!str && str !== 0) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  function decomposeUrl(rawUrl, defaultName = '', defaultProto = 'https', useApiKey = false, apiKey = '') {
    if (!rawUrl) {
      return {
        name: defaultName,
        protocol: defaultProto,
        host: '',
        port: '',
        path: '',
        url: '',
        enabled: true,
        use_api_key: !!useApiKey,
        api_key: apiKey || ''
      };
    }
    const str = String(rawUrl).trim();
    let proto = defaultProto;
    let rest = str;

    if (str.includes('://')) {
      const parts = str.split('://');
      proto = parts[0].toLowerCase();
      rest = parts[1] || '';
    }

    let host = rest;
    let port = '';
    let path = '';

    if (rest.includes('/')) {
      const slashIdx = rest.indexOf('/');
      host = rest.substring(0, slashIdx);
      path = rest.substring(slashIdx);
    }

    if (host.includes(':')) {
      const colParts = host.split(':');
      host = colParts[0];
      port = colParts[1] || '';
    }

    const computed = buildUrl(proto, host, port, path);
    return {
      name: defaultName || host,
      protocol: proto,
      host: host,
      port: port,
      path: path,
      url: computed,
      enabled: true,
      use_api_key: !!useApiKey,
      api_key: apiKey || ''
    };
  }

  function buildUrl(proto, host, port, path) {
    const p = (proto || 'https').trim().replace(/[:/]/g, '').toLowerCase();
    const h = (host || '').trim().replace(/\/$/, '');
    if (!h) return '';
    let portStr = '';
    const pt = String(port || '').trim();
    if (pt && pt !== '80' && pt !== '443') {
      portStr = ':' + pt;
    }
    let pathStr = (path || '').trim();
    if (pathStr && !pathStr.startsWith('/')) {
      pathStr = '/' + pathStr;
    }
    return `${p}://${h}${portStr}${pathStr}`;
  }

  function renderCard(item, options = {}) {
    const id = item.id || ('ep_' + Math.random().toString(36).substr(2, 9));
    const name = item.name || '';
    let proto = (item.protocol || 'https').toLowerCase().replace(/[:/]/g, '');
    const host = item.host || '';
    const port = item.port || '';
    const path = item.path || '';
    const enabled = item.enabled !== false;
    const isDeletable = !!options.isDeletable;
    const typeBadge = options.typeBadge || 'NODE';
    const computedUrl = item.url || buildUrl(proto, host, port, path);
    const standardProtos = ['https', 'http', 'socks5', 'socks5h'];
    const isCustomProto = !standardProtos.includes(proto);
    const useApiKey = item.use_api_key === true;
    const apiKey = item.api_key || '';

    return `
      <div class="endpoint-card" id="card-${id}" data-id="${id}" data-key="${escapeHtml(options.key || '')}" data-category="${escapeHtml(options.category || 'general')}">
        <div class="endpoint-card-header">
          <div class="endpoint-card-title-group">
            <input type="text" class="endpoint-name-input" value="${escapeHtml(name)}" placeholder="Endpoint Name / Label" title="Custom name or label" oninput="window.SearchEndpoints.syncUrl('${id}')">
            <span class="badge-pill badge-neutral">${escapeHtml(typeBadge)}</span>
          </div>
          <div class="endpoint-card-actions">
            <label class="endpoint-toggle-label" title="Enable or disable this endpoint without deleting">
              <input type="checkbox" class="endpoint-enabled-checkbox" ${enabled ? 'checked' : ''} onchange="window.SearchEndpoints.syncUrl('${id}')">
              <span class="endpoint-toggle-text">${enabled ? 'Active' : 'Disabled'}</span>
            </label>
            ${isDeletable ? `
              <button type="button" class="btn-icon-del" onclick="this.closest('.endpoint-card').remove()" title="Delete this endpoint">
                <i class="fas fa-trash"></i>
              </button>
            ` : ''}
          </div>
        </div>

        <div class="endpoint-card-fields">
          <div class="endpoint-field-col proto-col">
            <label>Protocol</label>
            <div class="proto-input-wrap">
              <select class="endpoint-proto-select" onchange="window.SearchEndpoints.onProtoChange('${id}', this)">
                <option value="https" ${proto === 'https' ? 'selected' : ''}>https://</option>
                <option value="http" ${proto === 'http' ? 'selected' : ''}>http://</option>
                <option value="socks5" ${proto === 'socks5' ? 'selected' : ''}>socks5://</option>
                <option value="socks5h" ${proto === 'socks5h' ? 'selected' : ''}>socks5h://</option>
                <option value="custom" ${isCustomProto ? 'selected' : ''}>Custom...</option>
              </select>
              <input type="text" class="endpoint-proto-custom" value="${escapeHtml(isCustomProto ? proto : '')}" style="${isCustomProto ? '' : 'display:none;'}" placeholder="proto" oninput="window.SearchEndpoints.syncUrl('${id}')">
            </div>
          </div>

          <div class="endpoint-field-col host-col">
            <label>Host / Address / .onion</label>
            <input type="text" class="endpoint-host-input" value="${escapeHtml(host)}" placeholder="domain.com, IP or .onion" oninput="window.SearchEndpoints.onHostInput('${id}', this)">
          </div>

          <div class="endpoint-field-col port-col">
            <label>Port</label>
            <input type="text" class="endpoint-port-input" value="${escapeHtml(port)}" placeholder="Port (e.g. 443, 8080)" oninput="window.SearchEndpoints.syncUrl('${id}')">
          </div>

          <div class="endpoint-field-col path-col">
            <label>Path / Template</label>
            <input type="text" class="endpoint-path-input" value="${escapeHtml(path)}" placeholder="/search or /" oninput="window.SearchEndpoints.syncUrl('${id}')">
          </div>
        </div>

        <div class="endpoint-api-row">
          <label class="endpoint-api-toggle-label" title="Enable API Key / Token Authentication for this endpoint">
            <input type="checkbox" class="endpoint-api-toggle" ${useApiKey ? 'checked' : ''} onchange="window.SearchEndpoints.onApiKeyToggle('${id}', this)">
            <span class="endpoint-api-toggle-text"><i class="fas fa-key"></i> Use API Key</span>
          </label>
          <div class="endpoint-api-key-wrap" id="api-wrap-${id}" style="${useApiKey ? '' : 'display:none;'}">
            <div class="endpoint-api-input-group">
              <input type="password" class="endpoint-api-key-input" value="${escapeHtml(apiKey)}" placeholder="Enter API Token or Secret Key" title="API Key / Token for this search endpoint" oninput="window.SearchEndpoints.syncUrl('${id}')">
              <button type="button" class="btn-api-visibility" onclick="window.SearchEndpoints.toggleKeyVisibility('${id}')" title="Show / Hide API Key">
                <i class="fas fa-eye"></i>
              </button>
            </div>
          </div>
        </div>

        <div class="endpoint-preview-row">
          <span class="endpoint-preview-label"><i class="fas fa-link"></i> Full URL:</span>
          <code class="endpoint-preview-url" id="preview-${id}">${escapeHtml(computedUrl || '(Enter host to preview URL)')}</code>
        </div>
      </div>
    `;
  }

  function onProtoChange(id, select) {
    const card = document.getElementById(`card-${id}`);
    if (!card) return;
    const customInput = card.querySelector('.endpoint-proto-custom');
    if (customInput) {
      if (select.value === 'custom') {
        customInput.style.display = 'inline-block';
        customInput.focus();
      } else {
        customInput.style.display = 'none';
        customInput.value = '';
      }
    }
    syncUrl(id);
  }

  function onApiKeyToggle(id, checkbox) {
    const card = document.getElementById(`card-${id}`);
    if (!card) return;
    const wrap = document.getElementById(`api-wrap-${id}`);
    if (wrap) {
      if (checkbox.checked) {
        wrap.style.display = 'block';
        const input = wrap.querySelector('.endpoint-api-key-input');
        if (input) input.focus();
      } else {
        wrap.style.display = 'none';
      }
    }
    syncUrl(id);
  }

  function toggleKeyVisibility(id) {
    const card = document.getElementById(`card-${id}`);
    if (!card) return;
    const input = card.querySelector('.endpoint-api-key-input');
    const icon = card.querySelector('.btn-api-visibility i');
    if (!input) return;
    if (input.type === 'password') {
      input.type = 'text';
      if (icon) icon.className = 'fas fa-eye-slash';
    } else {
      input.type = 'password';
      if (icon) icon.className = 'fas fa-eye';
    }
  }

  function onHostInput(id, input) {
    const card = document.getElementById(`card-${id}`);
    if (!card) return;
    const val = input.value.trim();

    // If user pasted a full URL into the host field, auto-decompose it
    if (val.includes('://')) {
      const dec = decomposeUrl(val);
      const protoSelect = card.querySelector('.endpoint-proto-select');
      const protoCustom = card.querySelector('.endpoint-proto-custom');
      const portInput = card.querySelector('.endpoint-port-input');
      const pathInput = card.querySelector('.endpoint-path-input');

      if (['https', 'http', 'socks5', 'socks5h'].includes(dec.protocol)) {
        protoSelect.value = dec.protocol;
        protoCustom.style.display = 'none';
        protoCustom.value = '';
      } else {
        protoSelect.value = 'custom';
        protoCustom.style.display = 'inline-block';
        protoCustom.value = dec.protocol;
      }

      input.value = dec.host;
      if (dec.port && portInput) portInput.value = dec.port;
      if (dec.path && pathInput) pathInput.value = dec.path;
    }

    syncUrl(id);
  }

  function syncUrl(id) {
    const card = document.getElementById(`card-${id}`);
    if (!card) return '';
    const protoSelect = card.querySelector('.endpoint-proto-select');
    const protoCustom = card.querySelector('.endpoint-proto-custom');
    const hostInput = card.querySelector('.endpoint-host-input');
    const portInput = card.querySelector('.endpoint-port-input');
    const pathInput = card.querySelector('.endpoint-path-input');
    const preview = document.getElementById(`preview-${id}`);
    const toggleText = card.querySelector('.endpoint-toggle-text');
    const checkbox = card.querySelector('.endpoint-enabled-checkbox');

    if (toggleText && checkbox) {
      toggleText.innerText = checkbox.checked ? 'Active' : 'Disabled';
    }

    let proto = protoSelect ? protoSelect.value : 'https';
    if (proto === 'custom' && protoCustom) {
      proto = protoCustom.value.trim() || 'https';
    }
    const host = hostInput ? hostInput.value.trim() : '';
    const port = portInput ? portInput.value.trim() : '';
    const path = pathInput ? pathInput.value.trim() : '';

    const fullUrl = buildUrl(proto, host, port, path);
    if (preview) {
      preview.innerText = fullUrl || '(Enter host to preview URL)';
    }
    return fullUrl;
  }

  function collectCard(card) {
    if (!card) return null;
    const id = card.dataset.id;
    const key = card.dataset.key || '';
    const category = card.dataset.category || 'general';
    const name = card.querySelector('.endpoint-name-input')?.value.trim() || '';

    const protoSelect = card.querySelector('.endpoint-proto-select');
    const protoCustom = card.querySelector('.endpoint-proto-custom');
    let proto = protoSelect ? protoSelect.value : 'https';
    if (proto === 'custom' && protoCustom) {
      proto = protoCustom.value.trim() || 'https';
    }
    const host = card.querySelector('.endpoint-host-input')?.value.trim() || '';
    const port = card.querySelector('.endpoint-port-input')?.value.trim() || '';
    let path = card.querySelector('.endpoint-path-input')?.value.trim() || '';
    const enabled = card.querySelector('.endpoint-enabled-checkbox')?.checked ?? true;
    const useApiKey = card.querySelector('.endpoint-api-toggle')?.checked ?? false;
    const apiKey = card.querySelector('.endpoint-api-key-input')?.value.trim() || '';
    const url = buildUrl(proto, host, port, path);

    return { id, key, category, name, protocol: proto, host, port, path, url, enabled, use_api_key: useApiKey, api_key: apiKey };
  }

  function collectContainer(container) {
    if (!container) return [];
    const cards = container.querySelectorAll('.endpoint-card');
    const list = [];
    cards.forEach(c => {
      const item = collectCard(c);
      if (item) list.push(item);
    });
    return list;
  }

  function addEndpoint(containerId, defaultItem = {}, options = {}) {
    const wrap = document.getElementById(containerId);
    if (!wrap) return null;
    const id = defaultItem.id || ('ep_' + Math.random().toString(36).substr(2, 9));
    const item = {
      id: id,
      name: defaultItem.name || 'New Endpoint',
      protocol: defaultItem.protocol || 'https',
      host: defaultItem.host || '',
      port: defaultItem.port || '',
      path: defaultItem.path || '',
      url: defaultItem.url || '',
      enabled: defaultItem.enabled !== false,
      use_api_key: defaultItem.use_api_key === true,
      api_key: defaultItem.api_key || ''
    };
    const html = renderCard(item, { ...options, isDeletable: true });
    wrap.insertAdjacentHTML('beforeend', html);
    const added = document.getElementById(`card-${id}`);
    if (added) {
      const nameInp = added.querySelector('.endpoint-name-input');
      if (nameInp) nameInp.focus();
    }
    return id;
  }

  function renderSearxngEngineCard(item, options = {}) {
    const id = item.id || ('sx_eng_' + Math.random().toString(36).substr(2, 9));
    const name = item.name || item.id || '';
    const label = item.label || (name ? name.charAt(0).toUpperCase() + name.slice(1) : '');
    const category = item.category || 'general';
    const enabled = item.enabled !== false;

    return `
      <div class="endpoint-card searxng-engine-card" id="card-${id}" data-id="${id}" style="margin-bottom:8px; border-left:3px solid var(--accent-cyan, #06b6d4);">
        <div class="endpoint-card-header" style="align-items:center;">
          <div class="endpoint-card-title-group" style="flex:1; display:flex; gap:8px; align-items:center; flex-wrap:wrap;">
            <input type="text" class="engine-name-input" value="${escapeHtml(name)}" placeholder="Engine ID (e.g. bing, yandex)" style="font-family:monospace; font-weight:700; max-width:140px; padding:4px 8px; border-radius:6px; border:1px solid var(--border); background:var(--bg0); color:var(--text); font-size:11px;" title="SearXNG backend adapter name" oninput="window.SearchEndpoints.syncEngineCard('${id}')">
            <input type="text" class="engine-label-input" value="${escapeHtml(label)}" placeholder="Display Label (e.g. Bing Search)" style="flex:1; min-width:140px; padding:4px 8px; border-radius:6px; border:1px solid var(--border); background:var(--bg0); color:var(--text); font-size:11px;" title="Human-readable label" oninput="window.SearchEndpoints.syncEngineCard('${id}')">
            <select class="engine-category-select" style="padding:4px 8px; border-radius:6px; border:1px solid var(--border); background:var(--bg0); color:var(--text); font-size:11px;" onchange="window.SearchEndpoints.syncEngineCard('${id}')" title="Engine category">
              <option value="general" ${category === 'general' ? 'selected' : ''}>🌐 General (Web)</option>
              <option value="videos" ${category === 'videos' ? 'selected' : ''}>🎬 Videos (Media)</option>
              <option value="images" ${category === 'images' ? 'selected' : ''}>🖼️ Images</option>
              <option value="news" ${category === 'news' ? 'selected' : ''}>📰 News</option>
              <option value="files" ${category === 'files' ? 'selected' : ''}>📁 Files / Dorks</option>
              <option value="music" ${category === 'music' ? 'selected' : ''}>🎵 Music / Audio</option>
            </select>
          </div>
          <div class="endpoint-card-actions" style="display:flex; align-items:center; gap:8px;">
            <label class="endpoint-toggle-label" title="Enable or disable this engine without deleting" style="cursor:pointer;">
              <input type="checkbox" class="engine-enabled-checkbox" ${enabled ? 'checked' : ''} onchange="window.SearchEndpoints.syncEngineCard('${id}')">
              <span class="engine-toggle-text badge-pill ${enabled ? 'badge-ok' : 'badge-neutral'}" style="font-size:10px;">${enabled ? 'Active' : 'Disabled'}</span>
            </label>
            <button type="button" class="btn-icon-del" onclick="this.closest('.searxng-engine-card').remove(); if(typeof window.updateSearxngEnginesCount==='function') window.updateSearxngEnginesCount();" title="Remove this engine">
              <i class="fas fa-trash"></i>
            </button>
          </div>
        </div>
      </div>
    `;
  }

  function syncEngineCard(id) {
    const card = document.getElementById(`card-${id}`);
    if (!card) return;
    const checkbox = card.querySelector('.engine-enabled-checkbox');
    const toggleText = card.querySelector('.engine-toggle-text');
    if (checkbox && toggleText) {
      const isAct = checkbox.checked;
      toggleText.textContent = isAct ? 'Active' : 'Disabled';
      toggleText.className = `engine-toggle-text badge-pill ${isAct ? 'badge-ok' : 'badge-neutral'}`;
    }
    if (typeof window.updateSearxngEnginesCount === 'function') {
      window.updateSearxngEnginesCount();
    }
  }

  function collectSearxngEngineCard(card) {
    if (!card) return null;
    const id = card.dataset.id;
    const name = card.querySelector('.engine-name-input')?.value.trim().toLowerCase() || '';
    const label = card.querySelector('.engine-label-input')?.value.trim() || name;
    const category = card.querySelector('.engine-category-select')?.value || 'general';
    const enabled = card.querySelector('.engine-enabled-checkbox')?.checked ?? true;
    if (!name) return null;
    return { id, name, label, category, enabled };
  }

  function addSearxngEngine(containerId, defaultItem = {}) {
    const wrap = document.getElementById(containerId);
    if (!wrap) return null;
    const id = defaultItem.id || ('sx_eng_' + Math.random().toString(36).substr(2, 9));
    const item = {
      id: id,
      name: defaultItem.name || '',
      label: defaultItem.label || '',
      category: defaultItem.category || 'general',
      enabled: defaultItem.enabled !== false
    };
    const html = renderSearxngEngineCard(item);
    wrap.insertAdjacentHTML('beforeend', html);
    const added = document.getElementById(`card-${id}`);
    if (added && !item.name) {
      const nameInp = added.querySelector('.engine-name-input');
      if (nameInp) nameInp.focus();
    }
    if (typeof window.updateSearxngEnginesCount === 'function') {
      window.updateSearxngEnginesCount();
    }
    return id;
  }

  return {
    escapeHtml,
    decomposeUrl,
    buildUrl,
    renderCard,
    onProtoChange,
    onApiKeyToggle,
    toggleKeyVisibility,
    onHostInput,
    syncUrl,
    collectCard,
    collectContainer,
    addEndpoint,
    renderSearxngEngineCard,
    syncEngineCard,
    collectSearxngEngineCard,
    addSearxngEngine
  };
})();
