/**
 * config_core_status.js
 * System status polling and header indicator updates.
 * Depends on: config_core_utils.js (setSaveMsg, setSpanText)
 */

async function refreshStatus() {
  try {
    const r = await fetch('/hecos/status');
    const d = await r.json();
    setSpanText('s-backend', d.backend || '—');

    // System Metrics with threshold coloring
    const updateMetric = (id, val) => {
        const el = document.getElementById(id);
        if (!el) return;
        el.textContent = (val !== undefined && val !== null) ? val + '%' : '—';
        el.className = 'stat-val ' + (val >= 90 ? 'val-err' : '');
    };
    updateMetric('s-cpu',  d.cpu);
    updateMetric('s-ram',  d.ram);
    updateMetric('s-vram', d.vram);

    // Status indicators with ON/OFF coloring
    const updateStatus = (id, val) => {
        const el = document.getElementById(id);
        if (!el) return;
        el.textContent = val || '—';
        el.className = 'stat-val ' + (val === 'ON' ? 'val-ok' : 'val-err');
    };
    updateStatus('s-mic', d.mic);
    updateStatus('s-tts', d.tts);
    updateStatus('s-ptt', d.ptt);

    setSpanText('s-bridge', d.bridge   || '—');
    setSpanText('s-config', d.config   || '—');
    setSpanText('s-model',  d.model    || '—');
    setSpanText('s-tool',   d.last_tool || '—');

    // Format tokens: P/C
    let tokensText = '—';
    if (d.tokens_p > 0 || d.tokens_c > 0) {
        tokensText = `${d.tokens_p} / ${d.tokens_c}`;
    }
    setSpanText('s-tokens', tokensText);

    // Header pill: Online / Offline
    const isOnline = !!d.model;
    const hdrModel = document.getElementById('hdr-model');
    if (hdrModel) {
        hdrModel.textContent = isOnline ? 'Online' : (window.I18N?.webui_chat_offline || 'Offline');
        hdrModel.style.color = isOnline ? 'var(--green)' : 'var(--red)';
    }
    const hdrDot = document.getElementById('hdr-dot');
    if (hdrDot) {
        hdrDot.style.background  = isOnline ? 'var(--green)' : 'var(--red)';
        hdrDot.style.boxShadow   = isOnline ? '0 0 8px var(--green)' : '0 0 8px var(--red)';
        hdrDot.style.animation   = isOnline ? 'pulse 2s infinite' : 'none';
    }

    // Conditional visibility for system metrics panel
    const dsb = window.cfg?.plugins?.DASHBOARD || {};
    const globalDashEnabled  = dsb.enabled !== false;
    const webuiDashEnabled   = dsb.webui_dashboard_enabled !== false;
    const webuiTelEnabled    = dsb.webui_telemetry_enabled !== false;

    const liveStatusEl = document.getElementById('live-status');
    if (liveStatusEl) {
        liveStatusEl.style.display = (globalDashEnabled && webuiDashEnabled) ? 'flex' : 'none';
    }

    const dashEnabled = globalDashEnabled && webuiDashEnabled && webuiTelEnabled;
    const trackCpu    = dsb.track_cpu  !== false;
    const trackRam    = dsb.track_ram  !== false;
    const trackVram   = dsb.track_vram !== false;

    document.querySelectorAll('.dashboard-only').forEach(el => {
        el.style.display = dashEnabled ? '' : 'none';
    });

    if (dashEnabled) {
        const eCpu  = document.getElementById('s-cpu');
        if (eCpu?.parentElement)  eCpu.parentElement.style.display  = trackCpu  ? '' : 'none';
        const eRam  = document.getElementById('s-ram');
        if (eRam?.parentElement)  eRam.parentElement.style.display  = trackRam  ? '' : 'none';
        const eVram = document.getElementById('s-vram');
        if (eVram?.parentElement) eVram.parentElement.style.display = trackVram ? '' : 'none';
    }
  } catch(e) {
    // On error: force pill to Offline
    const hdrModel = document.getElementById('hdr-model');
    if (hdrModel) {
        hdrModel.textContent = window.I18N?.webui_chat_offline || 'Offline';
        hdrModel.style.color = 'var(--red)';
    }
    const hdrDot = document.getElementById('hdr-dot');
    if (hdrDot) {
        hdrDot.style.background = 'var(--red)';
        hdrDot.style.boxShadow  = '0 0 8px var(--red)';
        hdrDot.style.animation  = 'none';
    }
  }
}

window.refreshStatus = refreshStatus;
