/**
 * widgets_panel.js
 * ─────────────────────────────────────────────────────────────────────────────
 * Hecos WebUI - Config Widgets frontend logic.
 * Handles loading, toggling visibility, span selection, and grid synch.
 * ─────────────────────────────────────────────────────────────────────────────
 */

async function loadWidgetsPanel() {
    const container = document.getElementById('widgets-list');
    if (!container) return;
    
    // Set initial global toggle state
    const globalToggle = document.getElementById('global-sidebar-widgets-toggle');
    if (globalToggle && window.parent?.cfg?.widgets) {
        globalToggle.checked = window.parent.cfg.widgets.sidebar_widgets_enabled !== false;
    }

    // ── Stale-while-revalidate: render cached data immediately ───────────────
    if (window._widgetsData && window._widgetsData.length > 0) {
        _renderWidgetCards(container, window._widgetsData);

        // Silently re-fetch in background and update only if changed
        fetch('/api/widgets')
            .then(r => r.json())
            .then(data => {
                if (!data.ok || !data.widgets) return;
                const fresh = JSON.stringify(data.widgets);
                const stale = JSON.stringify(window._widgetsData);
                if (fresh !== stale) {
                    window._widgetsData = data.widgets;
                    const c2 = document.getElementById('widgets-list');
                    if (c2) _renderWidgetCards(c2, window._widgetsData);
                }
            })
            .catch(() => { /* keep stale */ });
        return;
    }
    // ─────────────────────────────────────────────────────────────────────────
    
    try {
        const resp = await fetch('/api/widgets');
        const data = await resp.json();
        if (!data.ok) throw new Error(data.error || 'Server error');

        window._widgetsData = data.widgets || [];
        _renderWidgetCards(container, window._widgetsData);
    } catch(e) {
        if (container) container.innerHTML = `<div style="color:var(--danger);padding:20px;">Failed to load widgets: ${e.message}</div>`;
    }
}

// Expose globally so packages_panel_manage.js can call window.loadWidgetsPanel()
window.loadWidgetsPanel = loadWidgetsPanel;

function _renderWidgetCards(container, widgets) {
    container.innerHTML = '';
    widgets.forEach(w => {
            const card = document.createElement('div');
            const pluginOk = w.plugin_active !== false;
            card.className = `widget-card ${pluginOk ? '' : 'plugin-disabled'}`;
            card.dataset.id = w.extension_id;

            const icon = window.getIconForModule ? window.getIconForModule(w.extension_id, w.display_name) : `<i class="fas fa-cube"></i>`;

            // Per-widget prefs — enforce XOR: only one of sidebar/room can be active
            const prefs = w.prefs || {};
            const widgetEnabled  = w.enabled !== false;
            let sidebarVisible = w.visible === true;
            let roomVisible    = w.room_visible === true;

            // XOR enforcement at render time:
            // If both somehow ended up true, room takes priority.
            if (sidebarVisible && roomVisible) {
                sidebarVisible = false;
            }
            // If neither is true, default to Control Room (room_visible = true)
            if (!sidebarVisible && !roomVisible) {
                roomVisible = true;
            }

            const roomSpan  = prefs.room_span || w.room_span || 1;
            const roomTheme = prefs.theme || w.theme || 'default';

            // We safely call t() from window if defined
            const safeTranslate = (key) => typeof window.t === 'function' ? window.t(key) : key;
            const displayName = safeTranslate(w.display_name);
            const displayDesc = safeTranslate(w.description || '');

            card.innerHTML = `
                <div class="drag-handle" title="Drag to reorder"><i class="fas fa-grip-vertical"></i></div>
                <div class="widget-icon">${icon}</div>
                <div class="widget-info">
                    <div class="widget-name">
                        ${displayName}
                        <span class="badge-v">v${w.version || '1.0'}</span>
                    </div>
                    <div class="widget-desc">${displayDesc}</div>
                </div>
                <div class="widget-controls-col">
                    <!-- Sidebar toggle -->
                    <div class="widget-toggle-row" id="sidebar-row-${w.extension_id}">
                        <span class="widget-toggle-lbl"><i class="fas fa-comments" style="font-size:9px;"></i> Sidebar</span>
                        <label class="switch no-autosave" title="Toggle sidebar visibility">
                            <input type="checkbox"
                                   id="check-side-${w.extension_id}"
                                   ${sidebarVisible ? 'checked' : ''}
                                   ${pluginOk ? '' : 'disabled'}
                                   onchange="toggleWidgetVisibility('${w.extension_id}', this.checked, this)">
                            <span class="slider"></span>
                        </label>
                    </div>
                    <!-- Room toggle -->
                    <div class="widget-toggle-row" id="room-row-${w.extension_id}">
                        <span class="widget-toggle-lbl"><i class="fas fa-th-large" style="font-size:9px;"></i> Room</span>
                        <label class="switch no-autosave" title="Toggle Control Room visibility">
                            <input type="checkbox"
                                   id="check-room-${w.extension_id}"
                                   ${roomVisible ? 'checked' : ''}
                                   ${pluginOk ? '' : 'disabled'}
                                   onchange="toggleRoomVisibility('${w.extension_id}', this.checked, this)">
                            <span class="slider"></span>
                        </label>
                    </div>
                    <!-- Span selector (only meaningful if room visible) -->
                    <div class="span-selector" id="span-row-${w.extension_id}" style="${roomVisible ? '' : 'opacity:0.3; pointer-events:none;'}">
                        <span class="span-lbl"><i class="fas fa-arrows-alt-h" style="font-size:9px;"></i></span>
                        <button class="span-btn ${roomSpan === 1 ? 'active' : ''}"
                                onclick="setRoomSpan('${w.extension_id}', 1, this)" title="Normal width (1 column)">1</button>
                        <button class="span-btn ${roomSpan === 2 ? 'active' : ''}"
                                onclick="setRoomSpan('${w.extension_id}', 2, this)" title="Wide (2 columns)">2×</button>
                    </div>
                </div>
                ${w.extension_id === 'telemetry_widget' ? `
                <!-- Telemetry Hardware Metrics — loaded from package's own TOML, not core plugins.yaml -->
                <div class="telemetry-extras" style="flex-basis: 100%; display: flex; flex-wrap: wrap; gap: 14px; margin-top:0px; padding-top:14px; border-top:1px solid rgba(255,255,255,0.05);">
                    <div style="flex-basis:100%; font-size:10px; color:var(--text); text-transform:uppercase; font-weight:700; letter-spacing:0.5px; opacity:0.9; margin-bottom:-5px;"><i class="fas fa-microchip"></i> Hardware Monitoring</div>
                    <div class="widget-toggle-row">
                        <span class="widget-toggle-lbl">CPU</span>
                        <label class="switch no-autosave"><input type="checkbox" id="track-cpu-enabled" onchange="toggleTelemetryMetric('track_cpu', this.checked)"><span class="slider"></span></label>
                    </div>
                    <div class="widget-toggle-row">
                        <span class="widget-toggle-lbl">RAM</span>
                        <label class="switch no-autosave"><input type="checkbox" id="track-ram-enabled" onchange="toggleTelemetryMetric('track_ram', this.checked)"><span class="slider"></span></label>
                    </div>
                    <div class="widget-toggle-row">
                        <span class="widget-toggle-lbl">VRAM</span>
                        <label class="switch no-autosave"><input type="checkbox" id="track-vram-enabled" onchange="toggleTelemetryMetric('track_vram', this.checked)"><span class="slider"></span></label>
                    </div>
                    <div style="flex-basis: 100%; font-size:10.5px; color:var(--yellow); line-height:1.4; opacity:0.9; margin-top: 2px;">
                        <i class="fas fa-exclamation-triangle"></i> ${safeTranslate('webui_telemetry_warning')}
                    </div>
                </div>
                ` : ''}
            `;
            if (w.extension_id === 'telemetry_widget') {
                card.style.flexWrap = 'wrap';
            }
            container.appendChild(card);

            // Prepare for sync
            card.dataset.bg_color = w.bg_color || '';
            card.dataset.bg_image = w.bg_image || '';
    });
}

// ── Channels ────────────────────────────────────────────────────────────────
const widgetChannel = new BroadcastChannel('hecos_widgets');
function broadcastWidgetSync(id, field, value) {
    widgetChannel.postMessage({ 
        type: 'widget_update', 
        id: id, 
        field: field, 
        value: value 
    });
    localStorage.setItem('hecos_sidebar_sync', Date.now());
    localStorage.setItem('hecos_room_sync', Date.now());
}

// ── Global Toggle ────────────────────────────────────────────────────────────
async function toggleSidebarWidgetsEnabled(enabled) {
    try {
        const resp = await fetch('/api/widgets/sidebar-enabled', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({enabled})
        });
        const data = await resp.json();
        if (data.ok) {
            if (window.parent && window.parent.cfg) {
                if (!window.parent.cfg.widgets) window.parent.cfg.widgets = {};
                window.parent.cfg.widgets.sidebar_widgets_enabled = enabled;
            }
            if (window.showToast) window.showToast(`Sezione Widgets: ${enabled ? 'attivata' : 'disattivata'}`, 'info');
            widgetChannel.postMessage({ type: 'sidebar_enabled', value: enabled });
        } else throw new Error(data.error);
    } catch (err) {
        if (window.showToast) window.showToast(`Errore: ${err.message}`, 'error');
        document.getElementById('global-sidebar-widgets-toggle').checked = !enabled;
    }
}

// ── Sidebar visibility ───────────────────────────────────────────────────────
async function toggleWidgetVisibility(id, visible, inputEl) {
    if (!id || id === 'undefined') return;

    // MANDATORY XOR: sidebar and room are mutually exclusive.
    // Enabling sidebar → disables room.
    // Disabling sidebar → enables room.
    const roomToggle = document.getElementById(`check-room-${id}`);
    if (visible) {
        // Sidebar ON → force Room OFF
        if (roomToggle && roomToggle.checked) {
            roomToggle.checked = false;
            syncLocalConfig(id, 'room_visible', false);
            broadcastWidgetSync(id, 'room_visible', false);
            const spanRow = document.getElementById(`span-row-${id}`);
            if (spanRow) { spanRow.style.opacity = '0.3'; spanRow.style.pointerEvents = 'none'; }
            // Also persist to backend asynchronously
            fetch(`/api/widgets/${id}/room_visible`, {
                method: 'POST', headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({visible: false})
            });
        }
    } else {
        // Sidebar OFF → force Room ON
        if (roomToggle && !roomToggle.checked) {
            roomToggle.checked = true;
            syncLocalConfig(id, 'room_visible', true);
            broadcastWidgetSync(id, 'room_visible', true);
            const spanRow = document.getElementById(`span-row-${id}`);
            if (spanRow) { spanRow.style.opacity = ''; spanRow.style.pointerEvents = ''; }
            fetch(`/api/widgets/${id}/room_visible`, {
                method: 'POST', headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({visible: true})
            });
        }
    }
    const card = inputEl.closest('.widget-card');
    card.style.opacity = '0.5'; card.style.pointerEvents = 'none';
    try {
        const resp = await fetch(`/api/widgets/${id}/visible`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({visible})
        });
        const data = await resp.json();
        if (data.ok) {
            if (window.cfg) {
                if (!window.cfg.widgets) window.cfg.widgets = {};
                if (!window.cfg.widgets.per_widget) window.cfg.widgets.per_widget = {};
                if (!window.cfg.widgets.per_widget[id]) window.cfg.widgets.per_widget[id] = {};
                window.cfg.widgets.per_widget[id].visible = visible;
            }
            if (window.showToast) window.showToast(`Sidebar: widget ${visible ? 'attivato' : 'disattivato'}`, 'info');
            broadcastWidgetSync(id, 'visible', visible);
        } else throw new Error(data.error);
    } catch (err) {
        if (window.showToast) window.showToast(`Errore: ${err.message}`, 'error');
        inputEl.checked = !visible;
    } finally {
        card.style.opacity = '1'; card.style.pointerEvents = 'all';
    }
}

// ── Local Config Sync (CRITICAL: prevent revert-on-save race condition) ──────
function syncLocalConfig(widgetId, field, value) {
    if (!window.parent || !window.parent.cfg) return;
    const cfg = window.parent.cfg;
    if (!cfg.widgets) cfg.widgets = { per_widget: {} };
    if (!cfg.widgets.per_widget) cfg.widgets.per_widget = {};
    if (!cfg.widgets.per_widget[widgetId]) cfg.widgets.per_widget[widgetId] = {};
    cfg.widgets.per_widget[widgetId][field] = value;
    console.log(`[WIDGET-SYNC] Synced ${widgetId}.${field}=${value} to global window.parent.cfg`);
}

// ── Room toggle ──────────────────────────────────────────────────────────────
async function toggleRoomVisibility(id, visible, inputEl) {
    if (!id || id === 'undefined') return;

    // MANDATORY XOR: sidebar and room are mutually exclusive.
    // Enabling room → disables sidebar.
    // Disabling room → enables sidebar.
    const sideToggle = document.getElementById(`check-side-${id}`);
    if (visible) {
        // Room ON → force Sidebar OFF
        if (sideToggle && sideToggle.checked) {
            sideToggle.checked = false;
            syncLocalConfig(id, 'visible', false);
            broadcastWidgetSync(id, 'visible', false);
            fetch(`/api/widgets/${id}/visible`, {
                method: 'POST', headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({visible: false})
            });
        }
    } else {
        // Room OFF → force Sidebar ON
        if (sideToggle && !sideToggle.checked) {
            sideToggle.checked = true;
            syncLocalConfig(id, 'visible', true);
            broadcastWidgetSync(id, 'visible', true);
            fetch(`/api/widgets/${id}/visible`, {
                method: 'POST', headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({visible: true})
            });
        }
    }

    const card = inputEl.closest('.widget-card');
    card.style.opacity = '0.5'; card.style.pointerEvents = 'none';
    try {
        const resp = await fetch(`/api/widgets/${id}/room_visible`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({visible})
        });
        const data = await resp.json();
        if (data.ok) {
            syncLocalConfig(id, 'room_visible', visible);
            // Dim/undim the span selector
            const spanRow = document.getElementById(`span-row-${id}`);
            if (spanRow) {
                spanRow.style.opacity = visible ? '' : '0.3';
                spanRow.style.pointerEvents = visible ? '' : 'none';
            }
            const themeRow = document.getElementById(`theme-row-${id}`);
            if (themeRow) {
                themeRow.style.opacity = visible ? '' : '0.3';
                themeRow.style.pointerEvents = visible ? '' : 'none';
            }
            if (window.showToast) window.showToast(`Room: widget ${visible ? 'aggiunto' : 'rimosso'}`, 'info');
            broadcastWidgetSync(id, 'room_visible', visible);
        } else throw new Error(data.error);
    } catch (err) {
        if (window.showToast) window.showToast(`Errore: ${err.message}`, 'error');
        inputEl.checked = !visible;
    } finally {
        card.style.opacity = '1'; card.style.pointerEvents = 'all';
    }
}

// ── Room span ────────────────────────────────────────────────────────────────
async function setRoomSpan(id, span, btnEl) {
    try {
        const resp = await fetch(`/api/widgets/${id}/room_span`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({span})
        });
        const data = await resp.json();
        if (data.ok) {
            syncLocalConfig(id, 'room_span', span);
            // Update sibling buttons
            const parent = btnEl.closest('.span-selector');
            parent.querySelectorAll('.span-btn').forEach(b => b.classList.remove('active'));
            btnEl.classList.add('active');
            if (window.showToast) window.showToast(`Larghezza: ${span === 2 ? 'doppio' : 'normale'}`, 'info');
            broadcastWidgetSync(id, 'room_span', span);
        } else throw new Error(data.error);
    } catch (err) {
        if (window.showToast) window.showToast(`Errore: ${err.message}`, 'error');
    }
}

// ── Telemetry Extras — Autonomous Package Config (no core plugins.yaml involved) ──
async function _loadTelemetryWidgetSwitches() {
    try {
        const r = await fetch('/api/telemetry_widget/config');
        if (!r.ok) return;
        const d = await r.json();
        const cpu  = document.getElementById('track-cpu-enabled');
        const ram  = document.getElementById('track-ram-enabled');
        const vram = document.getElementById('track-vram-enabled');
        if (cpu)  cpu.checked  = !!d.track_cpu;
        if (ram)  ram.checked  = !!d.track_ram;
        if (vram) vram.checked = !!d.track_vram;
    } catch(e) {
        console.warn('[TELEMETRY-WIDGET] Could not load config:', e);
    }
}

async function toggleTelemetryMetric(field, enabled) {
    // Save directly to the package's own TOML via its autonomous API
    try {
        const r  = await fetch('/api/telemetry_widget/config');
        const current = r.ok ? await r.json() : {};
        const payload = {
            track_cpu:  current.track_cpu  || false,
            track_ram:  current.track_ram  || false,
            track_vram: current.track_vram || false,
        };
        payload[field] = enabled;
        await fetch('/api/telemetry_widget/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        console.log(`[TELEMETRY-WIDGET] ${field}=${enabled} saved to package TOML.`);
    } catch(e) {
        console.warn('[TELEMETRY-WIDGET] Save failed:', e);
    }
}

// Load initial switch states from package config after panel renders
setTimeout(_loadTelemetryWidgetSwitches, 200);

// ── Init ─────────────────────────────────────────────────────────────────────
// Add load event listener to execute when the scripts are ready.
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', loadWidgetsPanel);
} else {
    // If we're already loaded, run it now (e.g., async injection)
    loadWidgetsPanel();
}
