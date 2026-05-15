/**
 * Hecos WebUI - Status & UI State
 * Handles status bar updates, view modes, and categories.
 */

window.viewMode = localStorage.getItem('hecos-config-view') || 'tabs';
window.activeCategoryFilter = sessionStorage.getItem('hecos-config-filter') || '';
window.uiState = { collapsedCategories: [] };

async function refreshStatus() {
  try {
    const r = await fetch('/hecos/status');
    const d = await r.json();
    setSpanText('s-backend', d.backend || '—');
    
    const updateMetric = (id, val) => {
        const el = document.getElementById(id);
        if (!el) return;
        el.textContent = (val !== undefined && val !== null) ? val + '%' : '—';
        el.className = 'stat-val ' + (val >= 90 ? 'val-err' : '');
    };
    updateMetric('s-cpu', d.cpu);
    updateMetric('s-ram', d.ram);
    updateMetric('s-vram', d.vram);
    
    const updateStatus = (id, val) => {
        const el = document.getElementById(id);
        if (!el) return;
        el.textContent = val || '—';
        el.className = 'stat-val ' + (val === 'ON' ? 'val-ok' : 'val-err');
    };
    updateStatus('s-mic', d.mic);
    updateStatus('s-tts', d.tts);
    updateStatus('s-ptt', d.ptt);
    
    setSpanText('s-bridge', d.bridge || '—');
    setSpanText('s-config', d.config || '—');
    setSpanText('s-model', d.model || '—');
    setSpanText('s-tokens', (d.tokens_p > 0 || d.tokens_c > 0) ? `${d.tokens_p} / ${d.tokens_c}` : '—');
    
    // Status indicators visiblity
    const dsb = window.cfg?.plugins?.DASHBOARD || {};
    const globalDashEnabled = dsb.enabled !== false;
    const webuiDashEnabled = dsb.webui_dashboard_enabled !== false;
    const webuiTelemetryEnabled = dsb.webui_telemetry_enabled !== false;
    
    const liveStatusEl = document.getElementById('live-status');
    if (liveStatusEl) liveStatusEl.style.display = (globalDashEnabled && webuiDashEnabled) ? 'flex' : 'none';

    const dashEnabled = globalDashEnabled && webuiDashEnabled && webuiTelemetryEnabled;
    document.querySelectorAll('.dashboard-only').forEach(el => el.style.display = dashEnabled ? '' : 'none');
    
  } catch(e) { console.error("refreshStatus err:", e); }
}

function setViewMode(mode) {
    window.viewMode = mode;
    localStorage.setItem('hecos-config-view', mode);
    const tabsContainer = document.getElementById('tabs-bar-container');
    const wallContainer = document.getElementById('config-wall');
    const switcherTabs = document.getElementById('view-tabs');
    const switcherWall = document.getElementById('view-wall');

    if (mode === 'wall') {
        if (tabsContainer) tabsContainer.style.display = 'none';
        if (wallContainer) wallContainer.style.display = 'flex';
        if (switcherWall) switcherWall.classList.add('active');
        if (switcherTabs) switcherTabs.classList.remove('active');
        renderConfigHub('wall');
    } else {
        if (tabsContainer) tabsContainer.style.display = 'block';
        if (wallContainer) wallContainer.style.display = 'none';
        if (switcherTabs) switcherTabs.classList.add('active');
        if (switcherWall) switcherWall.classList.remove('active');
        renderConfigHub('tabs');
    }
}

function setSaveMsg(msg, type) {
  const el = document.getElementById('save-msg');
  if (!el) return;
  el.textContent = msg;
  el.style.color = type === 'ok' ? 'var(--green)' : type === 'err' ? 'var(--red)' : 'var(--muted)';
}

function setSpanText(id, text) { const el = document.getElementById(id); if (el) el.textContent = text; }

function toggleCategory(catId) {
    const idx = window.uiState.collapsedCategories.indexOf(catId);
    if (idx === -1) window.uiState.collapsedCategories.push(catId);
    else window.uiState.collapsedCategories.splice(idx, 1);
    if (typeof saveUIState === 'function') saveUIState();
    renderConfigHub();
}

function toggleAllCategories(expanded) {
    const hub = window.CONFIG_HUB;
    if (!hub || !hub.categories) return;
    if (expanded) {
        window.uiState.collapsedCategories = [];
    } else {
        window.uiState.collapsedCategories = Object.keys(hub.categories);
    }
    if (typeof saveUIState === 'function') saveUIState();
    renderConfigHub();
}

// Bridges
window.refreshStatus = refreshStatus;
window.setViewMode = setViewMode;
window.setSaveMsg = setSaveMsg;
window.toggleCategory = toggleCategory;
window.toggleAllCategories = toggleAllCategories;
