/**
 * Hecos Sidebar Widgets Manager
 * Handles interactive reordering (drag & drop + up/down arrows),
 * real-time updates via localStorage events, and persistence.
 */

let sidebarOrderMode = false;
const widgetChannel = new BroadcastChannel('hecos_widgets');

// 1. Listen via BroadcastChannel (for same-tab, e.g. iframe in Central Hub)
widgetChannel.onmessage = (event) => {
    console.log("[WIDGETS] Sync signal received via BroadcastChannel.");
    refreshSidebarWidgets();
};

// 2. Listen via localStorage (for cross-tab sync)
window.addEventListener('storage', (event) => {
    if (event.key === 'hecos_sidebar_sync') {
        console.log("[WIDGETS] Sync signal received via localStorage.");
        refreshSidebarWidgets();
    }
});

function toggleSidebarOrderMode() {
    sidebarOrderMode = !sidebarOrderMode;
    const zone = document.getElementById('sidebar-widgets-zone');
    const chrome = document.querySelectorAll('.widget-reorder-chrome');
    const btn = event.target;

    if (sidebarOrderMode) {
        zone.classList.add('ordering-mode');
        chrome.forEach(c => c.style.display = 'flex');
        btn.innerHTML = '✅ Done Ordering';
        btn.style.opacity = '1';
        btn.style.color = 'var(--accent)';
    } else {
        zone.classList.remove('ordering-mode');
        chrome.forEach(c => c.style.display = 'none');
        btn.innerHTML = '⚙️ Manage Widgets';
        btn.style.opacity = '0.5';
        btn.style.color = '';
        saveCurrentSidebarOrder();
    }
}

async function toggleStatusCollapse() {
    const card = document.getElementById('status-card');
    if (!card) return;
    
    const isCollapsed = card.classList.toggle('collapsed');
    console.log(`[WIDGETS] Status collapsed: ${isCollapsed}`);

    try {
        await fetch('/api/widgets/status-collapsed', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({collapsed: isCollapsed})
        });
    } catch (err) {
        console.error("[WIDGETS] Failed to save status collapse state:", err);
    }
}

async function toggleAudioCollapse() {
    const card = document.getElementById('audio-card');
    if (!card) return;
    
    const isCollapsed = card.classList.toggle('collapsed');
    console.log(`[WIDGETS] Audio collapsed: ${isCollapsed}`);

    try {
        await fetch('/api/widgets/audio-collapsed', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({collapsed: isCollapsed})
        });
    } catch (err) {
        console.error("[WIDGETS] Failed to save audio collapse state:", err);
    }
}

async function refreshSidebarWidgets() {
    try {
        // Cache-buster to prevent stale responses on some browsers
        const resp = await fetch(`/api/widgets/render?t=${Date.now()}`);
        const data = await resp.json();
        if (data.ok) {
            const container = document.getElementById('widgets-container');
            const emptyState = document.getElementById('widgets-empty-state');
            const footer = document.getElementById('widgets-manage-footer');
            
            if (!container) {
                console.warn("[WIDGETS] Container #widgets-container not found in DOM.");
                return;
            }

            // Update HTML
            container.innerHTML = data.html;
            
            // Re-check widget presence
            const hasWidgets = container.querySelectorAll('.sidebar-widget-wrapper').length > 0;
            container.style.display = hasWidgets ? 'block' : 'none';
            if (emptyState) emptyState.style.display = hasWidgets ? 'none' : 'block';
            if (footer) footer.style.display = hasWidgets ? 'block' : 'none';
            
            console.log(`[WIDGETS] Sidebar refreshed. Active widgets: ${hasWidgets}`);
        }
    } catch (err) {
        console.error("[WIDGETS] Failed to refresh widgets:", err);
    }
}

function moveWidgetUp(btn) {
    const wrapper = btn.closest('.sidebar-widget-wrapper');
    const prev = wrapper.previousElementSibling;
    if (prev) {
        wrapper.parentNode.insertBefore(wrapper, prev);
    }
}

function moveWidgetDown(btn) {
    const wrapper = btn.closest('.sidebar-widget-wrapper');
    const next = wrapper.nextElementSibling;
    if (next) {
        wrapper.parentNode.insertBefore(next, wrapper);
    }
}

async function saveCurrentSidebarOrder() {
    const wrappers = document.querySelectorAll('.sidebar-widget-wrapper');
    const order = Array.from(wrappers).map(w => w.dataset.id);
    
    console.log("[WIDGETS] Saving order:", order);
    try {
        const resp = await fetch('/api/widgets/order', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({order})
        });
        const data = await resp.json();
        if (data.ok) {
            console.log("[WIDGETS] Order saved successfully.");
            broadcastWidgetSync();
        }
    } catch (err) {
        console.error("[WIDGETS] Failed to save order:", err);
    }
}

// ── Drag & Drop Implementation ──
document.addEventListener('DOMContentLoaded', () => {
    const zone = document.getElementById('sidebar-widgets-zone');
    if (!zone) return;

    let draggedItem = null;

    zone.addEventListener('dragstart', (e) => {
        if (!sidebarOrderMode) { e.preventDefault(); return; }
        draggedItem = e.target.closest('.sidebar-widget-wrapper');
        draggedItem.style.opacity = '0.4';
        e.dataTransfer.effectAllowed = 'move';
    });

    zone.addEventListener('dragend', (e) => {
        if (draggedItem) {
            draggedItem.style.opacity = '1';
            draggedItem = null;
        }
    });

    zone.addEventListener('dragover', (e) => {
        e.preventDefault();
        if (!sidebarOrderMode || !draggedItem) return;
        
        const overItem = e.target.closest('.sidebar-widget-wrapper');
        if (!overItem || overItem === draggedItem) return;

        const bounding = overItem.getBoundingClientRect();
        const offset = bounding.y + (bounding.height / 2);
        
        if (e.clientY - offset > 0) {
            overItem.after(draggedItem);
        } else {
            overItem.before(draggedItem);
        }
    });

    // Support for the handle specifically
    zone.addEventListener('mousedown', (e) => {
        const handle = e.target.closest('.widget-drag-handle');
        if (handle) {
            const wrapper = handle.closest('.sidebar-widget-wrapper');
            wrapper.setAttribute('draggable', 'true');
        }
    });
    
    zone.addEventListener('mouseup', (e) => {
        const wrapper = e.target.closest('.sidebar-widget-wrapper');
        if (wrapper) wrapper.setAttribute('draggable', 'false');
    });
});
