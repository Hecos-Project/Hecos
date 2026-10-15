// ── Repositories Management ──────────────────────────────────────────────────
window._hpmRepositories = window._hpmRepositories || [
  { name: 'Hecos Official', url: 'https://hecos-project.github.io/store/index.json' }
];
window._hpmActiveRepoUrl = window._hpmActiveRepoUrl || 'https://hecos-project.github.io/store/index.json';

window.hpmGetRepoLabel = function (repoOrUrl) {
  if (!repoOrUrl) return 'Default Repository';
  if (typeof repoOrUrl === 'object' && repoOrUrl !== null) {
    if (repoOrUrl.name && repoOrUrl.name.trim()) return repoOrUrl.name.trim();
    repoOrUrl = repoOrUrl.url || '';
  }

  const url = String(repoOrUrl).trim();
  // Check if known in window._hpmRepositories list
  if (Array.isArray(window._hpmRepositories)) {
    const match = window._hpmRepositories.find(r => (typeof r === 'object' ? r.url : r) === url);
    if (match && typeof match === 'object' && match.name && match.name.trim()) {
      return match.name.trim();
    }
  }

  if (url === 'https://hecos-project.github.io/store/index.json' || url.includes('Hecos-Packages')) {
    return 'Hecos Official';
  }

  // GitHub repository auto-name
  const ghMatch = url.match(/github\.com\/[^/]+\/([^/#?]+)/i) || url.match(/raw\.githubusercontent\.com\/[^/]+\/([^/#?]+)/i);
  if (ghMatch) {
    let repoName = ghMatch[1];
    if (repoName.endsWith('.git')) repoName = repoName.slice(0, -4);
    return repoName;
  }

  // Local path auto-name
  if (url.includes('\\') || url.includes('/')) {
    const parts = url.replace(/\\/g, '/').split('/').filter(Boolean);
    const last = parts[parts.length - 1];
    if (last && !last.endsWith('.json')) return last;
    if (parts.length > 1) {
      const prev = parts[parts.length - 2];
      if (prev && !['store', 'packages'].includes(prev.toLowerCase())) return prev;
    }
  }

  try {
    const u = new URL(url);
    const pathSnippet = u.pathname.length > 25 ? '...' + u.pathname.slice(-22) : u.pathname;
    return `${u.hostname}${pathSnippet}`;
  } catch (_) {
    return url.length > 35 ? url.slice(0, 15) + '...' + url.slice(-15) : url;
  }
};

window.hpmUpdateRepoNameDisplay = function (url) {
  const activeUrl = url || window._hpmActiveRepoUrl;
  const nameEl = document.getElementById('hpm-store-repo-name-text');
  const badgeEl = document.getElementById('hpm-store-active-repo-badge');
  const name = window.hpmGetRepoLabel(activeUrl);

  if (nameEl) {
    nameEl.textContent = name;
  }
  if (badgeEl) {
    badgeEl.title = `Active Repository: ${name}\nURL: ${activeUrl}`;
  }
};

window.hpmPopulateRepoSelect = function (selectId) {
  const el = typeof selectId === 'string' ? document.getElementById(selectId) : selectId;
  if (!el) return;
  const rawRepos = window._hpmRepositories || [];
  const repos = rawRepos.map((r, i) => {
    if (typeof r === 'object' && r !== null) {
      return { name: r.name || window.hpmGetRepoLabel(r.url), url: r.url };
    }
    return { name: window.hpmGetRepoLabel(r), url: String(r) };
  });

  const active = window._hpmActiveRepoUrl || (repos[0] ? repos[0].url : '');

  el.innerHTML = '';
  repos.forEach(repo => {
    const opt = document.createElement('option');
    opt.value = repo.url;
    opt.textContent = repo.url;
    opt.title = `${repo.name}\n${repo.url}`;
    if (repo.url === active) opt.selected = true;
    el.appendChild(opt);
  });

  // Badge displays the clean friendly name:
  window.hpmUpdateRepoNameDisplay(active);
};

window.hpmLoadRepositories = async function () {
  try {
    const resp = await fetch('/api/hpm/settings/repositories');
    if (!resp.ok) return;
    const data = await resp.json();
    if (data.ok && Array.isArray(data.repositories)) {
      window._hpmRepositories = data.repositories;
      const firstUrl = typeof data.repositories[0] === 'object' ? data.repositories[0].url : data.repositories[0];
      window._hpmActiveRepoUrl = data.active_repository || firstUrl || '';

      if (window.cfg) {
        window.cfg.hpm = window.cfg.hpm || {};
        window.cfg.hpm.repositories = data.repositories;
        window.cfg.hpm.store_catalog_url = window._hpmActiveRepoUrl;
      }

      // Update store select dropdown & active badge
      window.hpmPopulateRepoSelect('hpm-store-repo-select');
    }
  } catch (err) {
    console.warn('[HPM] Failed to load repositories:', err);
  }
};

window.hpmSelectRepository = async function (url) {
  if (!url) return;
  window._hpmActiveRepoUrl = url;

  // Immediately update badge display to reflect friendly name
  window.hpmUpdateRepoNameDisplay(url);

  // Sync store select element in DOM
  const sel = document.getElementById('hpm-store-repo-select');
  if (sel && sel.value !== url) sel.value = url;

  if (window.cfg) {
    window.cfg.hpm = window.cfg.hpm || {};
    window.cfg.hpm.store_catalog_url = url;
  }

  // Persist active repo to backend
  try {
    const res = await fetch('/api/hpm/settings/active_repository', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ active_repository: url }),
    });
    const resData = await res.json();
    if (resData && resData.ok && resData.active_repository) {
      window._hpmActiveRepoUrl = resData.active_repository;
      if (window.cfg && window.cfg.hpm) {
        window.cfg.hpm.store_catalog_url = resData.active_repository;
      }
    }
  } catch (e) {
    console.warn('[HPM] Failed to save active repository:', e);
  }

  // Reload store catalog from new repo if store is active or loaded
  if (typeof window.hpmStoreLoad === 'function') {
    await window.hpmStoreLoad(true, url);
  }
};

window.hpmStoreLoad = async function (forceRefresh = false, repoUrl = null) {
  _hpmStoreShowLoading();
  try {
    const activeRepo = repoUrl || window._hpmActiveRepoUrl;
    let url = `/api/hpm/store/catalog?refresh=${forceRefresh ? '1' : '0'}`;
    if (activeRepo) {
      url += `&repo_url=${encodeURIComponent(activeRepo)}`;
    }
    const resp = await fetch(url);
    const data = await resp.json();
    if (!data.ok) throw new Error(data.error || 'Unknown error');

    const catalog = data.catalog;
    window.HPM_STORE_STATE.catalog = catalog;
    window.HPM_STORE_STATE.loadedRepoUrl = activeRepo;
    window.HPM_STORE_STATE.filtered = catalog.packages || [];
    if (data.offline) _hpmStoreShowBanner('⚠️ Offline mode — showing cached catalog', 'warning');
    else if (typeof _hpmStoreHideBanner === 'function') _hpmStoreHideBanner();
    _hpmStoreBuildTypeFilters(catalog.packages || []);
    _hpmStoreApplyFilters();
    if (typeof window.hpmUpdateCount === 'function') {
      window.hpmUpdateCount('store', (catalog.packages || []).length);
    }
  } catch (err) {
    _hpmStoreShowError(err.message);
  }
};


// ── Filtering & Search ────────────────────────────────────────────────────────
window.hpmStoreInstall = async function (pkgId, downloadUrl, pkgName, skipDepsCheck = false) {
  await _doSingleInstall(pkgId, downloadUrl, pkgName, skipDepsCheck);
  if (window.hpmStoreReloadRemote) window.hpmStoreReloadRemote();
};

async function _doSingleInstall(pkgId, downloadUrl, pkgName, skipDepCheck = false) {
  const modal  = document.getElementById('hpm-store-progress-modal');
  const bar    = document.getElementById('hpm-store-progress-bar');
  const msg    = document.getElementById('hpm-store-progress-msg');
  const logEl  = document.getElementById('hpm-store-progress-log');
  const title  = document.getElementById('hpm-store-progress-title');
  const icon   = document.getElementById('hpm-store-progress-icon');
  if (!modal) return;

  modal.style.display = 'flex';
  modal.ondblclick = function() { this.style.display = 'none'; };
  bar.style.width = '10%';
  bar.style.background = '';
  title.textContent = `Installing ${pkgName}…`;
  msg.textContent   = 'Connecting to store…';
  if (logEl) logEl.textContent = '';
  icon.innerHTML    = '<i class="fas fa-download" style="color:var(--accent);"></i>';

  const allowUnsigned = document.getElementById('hpm-allow-unsigned')?.checked || false;

  try {
    const resp = await fetch('/api/hpm/store/install', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id: pkgId, download_url: downloadUrl, allow_unsigned: allowUnsigned, skip_dep_check: skipDepCheck }),
    });

    const reader  = resp.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop();
      let event = null, dataStr = null;
      for (const line of lines) {
        if (line.startsWith('event: ')) event   = line.slice(7).trim();
        if (line.startsWith('data: '))  dataStr = line.slice(6).trim();
        if (event && dataStr) {
          try { _hpmStoreHandleSSE(event, JSON.parse(dataStr), bar, msg, logEl, title, icon, modal, pkgId, downloadUrl, pkgName); } catch {}
          event = null; dataStr = null;
        }
      }
    }
  } catch (err) {
    msg.textContent = `Error: ${err.message}`;
    if (logEl) logEl.textContent = '';
    icon.innerHTML  = '<i class="fas fa-times-circle" style="color:#ef4444;"></i>';
    setTimeout(() => { modal.style.display = 'none'; }, 3000);
  }
};

function _hpmStoreHandleSSE(event, payload, bar, msg, logEl, title, icon, modal, pkgId, downloadUrl, pkgName) {
  if (event === 'progress') {
    if (payload.step === 'pip_log') {
        // Row 2 only — pip log lines scroll through without touching row 1
        if (logEl) logEl.textContent = payload.message || '';
    } else {
        // Row 1 — step label (download, install, validating…)
        msg.textContent = payload.message || '';
        bar.style.width = payload.step === 'download' ? '40%' : '75%';
        // Row 2 — clear pip log when a new major step begins
        if (logEl) logEl.textContent = '';
    }
  } else if (event === 'done') {
    bar.style.width    = '100%';
    msg.textContent    = payload.message || _t('Done!', 'Fatto!', '¡Hecho!');
    icon.innerHTML     = '<i class="fas fa-check-circle" style="color:#10b981;"></i>';
    title.textContent  = _t('Installed Successfully!', 'Installato con successo!', '¡Instalado con éxito!');
    
    const hintEl = document.getElementById('hpm-store-progress-hint');
    if (hintEl) hintEl.style.display = 'block';

    let extraHTML = '';
    if (payload.install_path) {
        const lblPath = _t('Installed in:', 'Installato in:', 'Instalado en:');
        extraHTML += `<div style="margin-top:12px; font-size: 1.05em; color: var(--text);">${lblPath}<br><code style="display:inline-block; margin-top:4px; color:var(--accent); background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); padding: 4px 8px; border-radius: 6px;">${payload.install_path}</code></div>`;
    }
    if (payload.config_panel) {
        const lblCfg = _t('Available in the Configuration menu', 'Disponibile nel menu Configurazione', 'Disponible en el menú Configuración');
        extraHTML += `<div style="margin-top:8px; font-size: 1em; color: var(--muted);"><i class="fas fa-cogs" style="margin-right:4px;"></i>${lblCfg}</div>`;
    }
    if (payload.pip_installed && payload.pip_installed.length > 0) {
        const lblPip = _t('Installed PIP dependencies:', 'Dipendenze PIP installate:', 'Dependencias PIP instaladas:');
        extraHTML += `<div style="margin-top:8px; font-size: 1em; color: var(--text);"><i class="fab fa-python" style="margin-right:4px;color:#f59e0b;"></i>${lblPip} <span style="color:var(--muted);">${payload.pip_installed.join(', ')}</span></div>`;
    }
    if (payload.pip_failures && payload.pip_failures.length > 0) {
        const lblPipFail = _t('Failed PIP dependencies:', 'Dipendenze PIP non installate:', 'Dependencias PIP fallidas:');
        extraHTML += `<div style="margin-top:4px; font-size: 1em; color: #ef4444;"><i class="fas fa-exclamation-triangle" style="margin-right:4px;"></i>${lblPipFail} <span>${payload.pip_failures.join(', ')}</span></div>`;
    }
    if (extraHTML) {
        msg.innerHTML = (payload.message || _t('Done!', 'Fatto!', '¡Hecho!')) + extraHTML;
    }

    const sound = localStorage.getItem('hpm_install_sound') || 'success.mp3';
    if (sound !== 'none') {
        if (sound.startsWith('custom|')) {
            const path = sound.substring(7);
            new Audio('/api/local_file?path=' + encodeURIComponent(path)).play().catch(() => {});
        } else {
            new Audio(`/static/sounds/${sound}`).play().catch(() => {});
        }
    }

    // ── Save NEW badge for Central Hub ──────────────────────────────────────
    if (payload.config_panel) {
        let newPanels = [];
        try { newPanels = JSON.parse(localStorage.getItem('hpm_new_panels') || '[]'); } catch(e) {}
        
        const tabId = payload.config_panel || payload.id;
        const pkgId = payload.id || '';
        for (const key of [tabId, pkgId]) {
            if (key && !newPanels.includes(key)) newPanels.push(key);
        }
        
        try { localStorage.setItem('hpm_new_panels', JSON.stringify(newPanels)); } catch(e) {}
    }
    // ────────────────────────────────────────────────────────────────────────

    // Refresh store without closing modal automatically
    window.hpmStoreLoad();
    if (typeof window.hpmLoadPackages === 'function') window.hpmLoadPackages();
    if (typeof window.hpmRefreshConfigHub === 'function') window.hpmRefreshConfigHub();

    // ── Show Restart prompt if backend routes need a fresh boot (Removed) ────
    if (payload.requires_restart && typeof window.hpmSignalRestartPending === 'function') {
      window.hpmSignalRestartPending();
    }
    // ────────────────────────────────────────────────────────────────────────
  } else if (event === 'error') {
    if (payload.missing_deps && payload.missing_deps.length > 0) {
      bar.style.width      = '100%';
      bar.style.background = '#f59e0b';
      icon.innerHTML       = '<i class="fas fa-exclamation-triangle" style="color:#f59e0b;animation:pulse 1.5s infinite;"></i>';
      title.textContent    = _t('Missing Dependencies', 'Dipendenze Mancanti', 'Dependencias Faltantes');
      
      const lblMissing = _t('Missing required modules:', 'Moduli richiesti mancanti:', 'Módulos requeridos faltantes:');
      const question = _t('Do you want to install them automatically?', 'Vuoi installarli automaticamente?', '¿Quieres instalarlos automáticamente?');
      
      msg.innerHTML = `
        <div style="font-size:1.05em; margin-bottom:12px; color:var(--text);">${question}</div>
        <div style="font-size:1em; color:var(--muted); margin-bottom:20px;">
          <i class="fas fa-box-open" style="margin-right:6px;"></i>${lblMissing} <b style="color:var(--text);">${payload.missing_deps.join(', ')}</b>
        </div>
        <div style="display:flex; gap:10px; justify-content:center;">
          <button id="hpm-dep-install-all" style="background:linear-gradient(135deg,var(--accent),var(--accent2,#7c3aed));color:#fff;border:none;padding:10px 18px;border-radius:8px;font-weight:700;cursor:pointer;flex:1;">
            <i class="fas fa-download" style="margin-right:6px;"></i> ${_t('Install All', 'Installa Tutto', 'Instalar Todo')}
          </button>
          <button id="hpm-dep-install-only" style="background:rgba(255,255,255,0.05);color:var(--text);border:1px solid rgba(255,255,255,0.1);padding:10px 18px;border-radius:8px;font-weight:600;cursor:pointer;flex:1;">
            ${_t('Install Only', 'Installa Solo', 'Instalar Solo')}
          </button>
        </div>
      `;
      
      modal.ondblclick = null;
      
      document.getElementById('hpm-dep-install-all').onclick = async () => {
        try {
          msg.innerHTML = `<div style="padding:10px;"><i class="fas fa-spinner fa-spin" style="margin-right:6px;"></i> ${_t('Resolving...', 'Risoluzione in corso...', 'Resolviendo...')}</div>`;
          const catResp = await fetch('/api/hpm/store/catalog?refresh=1');
          const catData = await catResp.json();
          if (catData && catData.catalog && catData.catalog.packages) {
            for (const d of payload.missing_deps) {
              const depPkg = catData.catalog.packages.find(p => p.id === d);
              if (depPkg) {
                await _doSingleInstall(depPkg.id, depPkg.download_url, depPkg.name);
              }
            }
            await _doSingleInstall(pkgId, downloadUrl, pkgName);
            if (window.hpmStoreReloadRemote) window.hpmStoreReloadRemote();
          }
        } catch(e) {
          msg.innerHTML = `<div style="color:#ef4444;"><i class="fas fa-times"></i> Error resolving dependencies</div>`;
        }
      };
      
      document.getElementById('hpm-dep-install-only').onclick = () => {
        _doSingleInstall(pkgId, downloadUrl, pkgName, true);
      };
      
      return;
    }

    bar.style.width    = '100%';
    bar.style.background = '#ef4444';
    icon.innerHTML     = '<i class="fas fa-times-circle" style="color:#ef4444;"></i>';
    title.textContent  = _t('Installation Failed', 'Installazione Fallita', 'Instalación Fallida');

    let errHTML = `<div>${_hesc(payload.message || 'Installation failed.')}</div>`;
    if (payload.missing_deps && payload.missing_deps.length > 0) {
        const lblMissing = _t('Missing modules:', 'Moduli mancanti:', 'Módulos faltantes:');
        errHTML += `<div style="margin-top:8px;font-size:1em;"><i class="fas fa-box-open" style="margin-right:4px;"></i>${lblMissing} <span style="color:var(--text);">${payload.missing_deps.join(', ')}</span></div>`;
    }
    msg.innerHTML = errHTML;
    
    const hintEl = document.getElementById('hpm-store-progress-hint');
    if (hintEl) hintEl.style.display = 'block';
    setTimeout(() => { modal.style.display = 'none'; bar.style.background = ''; }, 6000);
  }
}

// ── Utilities ─────────────────────────────────────────────────────────────────
function _hesc(s) {
  return String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

