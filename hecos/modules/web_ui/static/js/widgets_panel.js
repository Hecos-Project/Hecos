/**
 * widgets_panel.js
 * ─────────────────────────────────────────────────────────────────────────────
 * Hecos WebUI - Config Widgets frontend logic.
 * Handles loading, toggling visibility, span selection, and grid synch.
 * ─────────────────────────────────────────────────────────────────────────────
 */

async function loadWidgetsPanel() {
    const container = document.getElementById('widgets-list');
    
    // Set initial global toggle state
    const globalToggle = document.getElementById('global-sidebar-widgets-toggle');
    if (globalToggle && window.parent?.cfg?.widgets) {
        globalToggle.checked = window.parent.cfg.widgets.sidebar_widgets_enabled !== false;
    }
    
    try {
        const resp = await fetch('/api/widgets');
        const data = await resp.json();
        if (!data.ok) throw new Error(data.error);

        container.innerHTML = '';
        data.widgets.forEach(w => {
            const card = document.createElement('div');
            const pluginOk = w.plugin_active !== false;
            card.className = `widget-card ${pluginOk ? '' : 'plugin-disabled'}`;
            card.dataset.id = w.extension_id;

            const icon = window.getIconForModule ? window.getIconForModule(w.extension_id, w.display_name) : `<i class="fas fa-cube"></i>`;

            // Per-widget prefs
            const prefs = w.prefs || {};
            const sidebarVisible = w.visible !== false;
            const roomVisible   = prefs.room_visible === true || w.room_visible === true;
            const roomSpan      = prefs.room_span || w.room_span || 1;
            const roomTheme     = prefs.theme || w.theme || 'default';

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
                    <div class="widget-toggle-row">
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
                    <div class="widget-toggle-row">
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
            `;
            container.appendChild(card);

            // Prepare for sync
            card.dataset.bg_color = w.bg_color || '';
            card.dataset.bg_image = w.bg_image || '';
        });
    } catch (err) {
        container.innerHTML = `<div style="color:var(--red); padding:20px;">Error: ${err.message}</div>`;
    }
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

    // OPTIMISTIC XOR: If sidebar enabled, disable room immediately
    if (visible) {
        const roomToggle = document.getElementById(`check-room-${id}`);
        if (roomToggle && roomToggle.checked) {
            console.log(`[XOR] Auto-disabling room for ${id}`);
            roomToggle.checked = false;
            syncLocalConfig(id, 'room_visible', false);
            broadcastWidgetSync(id, 'room_visible', false);
            const spanRow = document.getElementById(`span-row-${id}`);
            if (spanRow) { spanRow.style.opacity = '0.3'; spanRow.style.pointerEvents = 'none'; }
            const themeRow = document.getElementById(`theme-row-${id}`);
            if (themeRow) { themeRow.style.opacity = '0.3'; themeRow.style.pointerEvents = 'none'; }
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

    // OPTIMISTIC XOR: If room enabled, disable sidebar immediately
    if (visible) {
        const sideToggle = document.getElementById(`check-side-${id}`);
        if (sideToggle && sideToggle.checked) {
            console.log(`[XOR] Auto-disabling sidebar for ${id}`);
            sideToggle.checked = false;
            syncLocalConfig(id, 'visible', false);
            broadcastWidgetSync(id, 'visible', false);
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

// ── Init ─────────────────────────────────────────────────────────────────────
// Add load event listener to execute when the scripts are ready.
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', loadWidgetsPanel);
} else {
    // If we're already loaded, run it now (e.g., async injection)
    loadWidgetsPanel();
}
