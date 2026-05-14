/**
 * Hecos Control Room Grid Engine
 * Vanilla JS drag-and-drop grid with touch support.
 * Binds to #room-grid (Module A) and #home-grid (Module B).
 *
 * Usage: controlRoomGrid.init(gridEl)
 */
(function (global) {
    'use strict';

    // ─── Constants ────────────────────────────────────────────────────────────
    const API = {
        ROOM:    '/api/widgets/room',
        LAYOUT:  '/api/widgets/room/layout',
        FRAME:   (id) => `/api/widgets/room/${id}/frame`,
    };

    // ─── State ────────────────────────────────────────────────────────────────
    let _grid = null;           // the grid DOM element
    let _editing = false;       // edit mode flag
    let _dragSrc = null;        // dragged card element
    let _placeholder = null;    // drop indicator element
    let _saveTimer = null;      // debounce for layout save
    let _editBtn = null;        // edit mode toggle button
    let _widgetChannel = null;  // Keep reference so it doesn't get garbage collected
    let _refreshDelayTimer = null; // follow-up refresh timer

    // ─── Initialization of Global Sync (Active on script load) ────────────────
    const _initGlobalSync = () => {
        if (!_widgetChannel) {
            _widgetChannel = new BroadcastChannel('hecos_widgets');
            _widgetChannel.onmessage = (event) => {
                const data = event.data;
                console.log('[RoomGrid] BroadcastChannel signal:', data);
                if (data && data.type === 'widget_update') {
                    _syncLocalConfig(data.id, data.field, data.value);
                }
                // Call global instance method
                if (global.controlRoomGrid) global.controlRoomGrid.debouncedRefresh();
            };
            window.addEventListener('storage', (e) => {
                if (e.key === 'hecos_room_sync') {
                    console.log('[RoomGrid] localStorage sync signal');
                    if (global.controlRoomGrid) global.controlRoomGrid.debouncedRefresh();
                }
            });
        }
    };
    _initGlobalSync();

    // ─── Public API ───────────────────────────────────────────────────────────
    const controlRoomGrid = {

        async init(gridEl, editBtn) {
            _grid = gridEl;
            _editBtn = editBtn || null;
            await this.refresh();

            if (_editBtn) {
                _editBtn.addEventListener('click', () => this.toggleEditMode());
            }
        },

        /**
         * Refreshes immediately and then follows up after a delay
         * to ensure backend persistence is captured.
         */
        debouncedRefresh() {
            console.log('[RoomGrid] debouncedRefresh triggered.');
            // 1. Immediate refresh for snappy responsiveness
            this.refresh();

            // 2. Clear existing follower to prevent spam
            if (_refreshDelayTimer) clearTimeout(_refreshDelayTimer);

            // 3. Delayed follow-up (2s) for deep reliability (disk/system latency)
            _refreshDelayTimer = setTimeout(() => {
                console.log('[RoomGrid] Running 2s follow-up refresh...');
                this.refresh();
            }, 2000);
        },

        // ─── Fetch & Render ──────────────────────────────────────────────────
        async refresh() {
            if (!_grid) return;
            try {
                const resp = await fetch(`${API.ROOM}?t=${Date.now()}`);
                const data = await resp.json();
                console.log('[RoomGrid] /api/widgets/room response:', data);

                if (!data.ok) throw new Error(data.error || 'API error');

                const widgets = Array.isArray(data.widgets) ? data.widgets : [];
                console.log('[RoomGrid] Widgets to render:', widgets.length, widgets.map(w => w.extension_id));

                _render(widgets);

                // Toggle empty-state visibility
                const empty = _grid.querySelector('.room-empty-state');
                if (empty) empty.style.display = widgets.length ? 'none' : '';
            } catch (err) {
                console.error('[RoomGrid] Refresh error:', err);
            }
        },

        // ─── Edit Mode ───────────────────────────────────────────────────────
        toggleEditMode() {
            _editing = !_editing;
            if (_grid) {
                _grid.classList.toggle('room-grid-editing', _editing);
            }
            
            // Update edit button label/icon dynamically using stored ref
            if (_editBtn) {
                const isHomeBtn = _editBtn.id === 'home-edit-btn';
                
                if (isHomeBtn) {
                    _editBtn.innerHTML = _editing
                        ? '<i class="fas fa-check"></i><span>Done</span>'
                        : '<i class="fas fa-pen-to-square"></i><span>Edit</span>';
                } else {
                    _editBtn.innerHTML = _editing
                        ? '<i class="fas fa-check"></i>'
                        : '<i class="fas fa-pen-to-square"></i>';
                }
                
                _editBtn.title = _editing ? 'Save layout' : 'Edit layout';
                _editBtn.classList.toggle('active', _editing);
            }
            
            if (!_editing) _persistLayout();  // auto-save on exit
        },

        isEditing() { return _editing; },
    };
    
    // ─── Private: Local Config Sync ───────────────────────────────────────────
    function _syncLocalConfig(widgetId, field, value) {
        // window.cfg exists on home.html, window.parent.cfg exists in the sliding panel.
        const cfg = window.cfg || (window.parent && window.parent.cfg);
        if (!cfg) return;
        
        if (!cfg.widgets) cfg.widgets = { per_widget: {} };
        if (!cfg.widgets.per_widget) cfg.widgets.per_widget = {};
        if (!cfg.widgets.per_widget[widgetId]) cfg.widgets.per_widget[widgetId] = {};
        
        cfg.widgets.per_widget[widgetId][field] = value;
        console.log(`[RoomGrid] Synced ${widgetId}.${field}=${value} to global cfg object.`);
    }

    // ─── Private: Render ─────────────────────────────────────────────────────
    function _render(widgets) {
        // Keep non-card children (empty-state, loading, add-btn) at end
        const stable = [..._grid.children].filter(c =>
            c.classList.contains('room-empty-state') ||
            c.classList.contains('room-loading') ||
            c.id === 'room-add-btn'
        );

        // Clear cards
        [..._grid.children].forEach(c => {
            if (!stable.includes(c)) c.remove();
        });

        if (widgets.length === 0) {
            _showEmpty();
            return;
        } else {
            _hideEmpty();
        }

        // Render each widget as a card
        widgets.forEach(w => {
            const card = _makeCard(w);
            _grid.insertBefore(card, stable[0] || null);
        });

        _ensureAddBtn();
    }

    function _makeCard(w) {
        const card = document.createElement('div');
        const themeVal = (w.theme || 'default').replace('theme-', '');
        card.className = `room-widget-card border-glow${w.room_span === 2 ? ' span-2' : ''} theme-${themeVal}`;
        if (w.room_height) {
            card.style.minHeight = w.room_height + 'px';
        }
        card.dataset.id  = w.extension_id;
        card.dataset.span = w.room_span || 1;

        // Chrome (visible only in edit mode)
        card.innerHTML = `
            <div class="room-card-chrome">
                <span class="room-card-drag-handle" title="Drag to reorder">
                    <i class="fas fa-grip-vertical"></i>
                </span>
                <button class="room-card-span-btn ${w.room_span === 2 ? 'active' : ''}"
                        onclick="event.stopPropagation(); _roomGridToggleSpan('${w.extension_id}', this)"
                        title="${w.room_span === 2 ? 'Switch to normal width' : 'Switch to wide (2 columns)'}">
                    ${w.room_span === 2 ? '<i class="fas fa-compress-alt"></i> 2×' : '<i class="fas fa-expand-alt"></i> 1×'}
                </button>
                <button class="room-card-remove-btn"
                        onclick="event.stopPropagation(); _roomGridRemoveWidget('${w.extension_id}')"
                        title="Remove from room">
                    <i class="fas fa-times"></i>
                </button>
            </div>
            <iframe src="${API.FRAME(w.extension_id)}?t=${Date.now()}"
                    class="room-widget-iframe"
                    loading="lazy"
                    scrolling="no"
                    frameborder="0"
                    allowtransparency="true"
                    title="${w.display_name}">
            </iframe>
            <div class="room-card-resize-handle" title="Trascina per ridimensionare (Doppio clic per resettare)"
                 onmousedown="event.stopPropagation(); _roomGridStartResize(event, '${w.extension_id}')"
                 ontouchstart="event.stopPropagation(); _roomGridStartResize(event, '${w.extension_id}')"
                 ondblclick="event.stopPropagation(); _roomGridResetHeight('${w.extension_id}')">
                 <div class="drag-line"></div>
            </div>
        `;

        // ── Drag (mouse) ──
        card.draggable = _editing;  // draggable if already in edit mode
        card.addEventListener('dragstart', _onDragStart);
        card.addEventListener('dragend',   _onDragEnd);
        card.addEventListener('dragenter', _onDragEnter);
        card.addEventListener('dragover',  _onDragOver);
        card.addEventListener('drop',      _onDrop);

        // ── Touch ──
        card.addEventListener('touchstart', _onTouchStart, {passive: true});
        card.addEventListener('touchmove',  _onTouchMove,  {passive: false});
        card.addEventListener('touchend',   _onTouchEnd);

        return card;
    }

    function _showEmpty() {
        let el = _grid.querySelector('.room-empty-state');
        if (!el) {
            el = document.createElement('div');
            el.className = 'room-empty-state';
            el.innerHTML = `
                <i class="fas fa-th-large"></i>
                <p>La Control Room è vuota.<br>Abilita i widget in <strong>Central Hub → Widget Manager</strong>.</p>
            `;
            _grid.appendChild(el);
        }
        el.style.display = '';
    }

    function _hideEmpty() {
        let el = _grid.querySelector('.room-empty-state');
        if (el) el.style.display = 'none';
    }

    function _ensureAddBtn() {
        if (_grid.querySelector('#room-add-btn')) return;
        const btn = document.createElement('div');
        btn.id = 'room-add-btn';
        btn.className = 'room-add-btn';
        btn.title = 'Apri Widget Manager';
        btn.innerHTML = `<i class="fas fa-plus"></i>`;
        btn.addEventListener('click', () => {
            if (window.hecosOpenConfig) hecosOpenConfig('#widgets');
            else window.open('/hecos/config/ui#widgets', '_blank');
        });
        _grid.appendChild(btn);
    }

    // ─── Private: Persist layout ─────────────────────────────────────────────
    function _persistLayout() {
        clearTimeout(_saveTimer);
        _saveTimer = setTimeout(async () => {
            const cards = [..._grid.querySelectorAll('.room-widget-card')];
            const layout = cards.map(c => c.dataset.id);
            try {
                await fetch(API.LAYOUT, {
                    method: 'PATCH',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({layout})
                });
                console.log('[RoomGrid] Layout saved:', layout);
            } catch (err) {
                console.warn('[RoomGrid] Layout save failed:', err);
            }
        }, 400);
    }

    // ─── Drag & Drop (Mouse) ─────────────────────────────────────────────────
    function _onDragStart(e) {
        if (!_editing) { e.preventDefault(); return; }
        _dragSrc = this;
        this.style.opacity = '0.4';
        e.dataTransfer.effectAllowed = 'move';
        // Safari/Firefox require some data to start drag
        e.dataTransfer.setData('text/plain', this.dataset.id || 'widget');
    }

    function _onDragEnd(e) {
        if (_dragSrc) {
            _dragSrc.style.opacity = '1';
            _dragSrc = null;
        }
        _persistLayout();
    }

    function _onDragEnter(e) {
        e.preventDefault();
    }

    function _onDragOver(e) {
        e.preventDefault(); // Unconditionally required
        if (!_editing || !_dragSrc) return;

        const overCard = e.target.closest('.room-widget-card');
        if (!overCard || overCard === _dragSrc) return;

        const bounding = overCard.getBoundingClientRect();
        // Since it's a grid, we should probably check Y
        const offset = bounding.y + (bounding.height / 2);
        
        if (e.clientY > offset) {
            overCard.after(_dragSrc);
        } else {
            overCard.before(_dragSrc);
        }
    }

    function _onDrop(e) {
        e.preventDefault();
        // DOM is already reordered during dragover.
    }

    // ─── Touch Drag & Drop ────────────────────────────────────────────────────
    let _touchDragEl = null;
    let _touchClone  = null;
    let _touchOX = 0, _touchOY = 0;

    function _onTouchStart(e) {
        if (!_editing) return;
        const t = e.touches[0];
        _touchDragEl = this;
        _touchOX = t.clientX - this.getBoundingClientRect().left;
        _touchOY = t.clientY - this.getBoundingClientRect().top;

        // Create a visual clone
        _touchClone = this.cloneNode(true);
        _touchClone.style.cssText = `
            position:fixed; z-index:99999; pointer-events:none; opacity:0.85;
            width:${this.offsetWidth}px; box-shadow: 0 12px 40px rgba(0,0,0,0.5);
        `;
        document.body.appendChild(_touchClone);
        this.style.opacity = '0.3';
    }

    function _onTouchMove(e) {
        if (!_touchDragEl || !_touchClone) return;
        e.preventDefault();
        const t = e.touches[0];
        _touchClone.style.left = (t.clientX - _touchOX) + 'px';
        _touchClone.style.top  = (t.clientY - _touchOY) + 'px';

        // Find card under finger
        _touchClone.style.display = 'none';
        const el = document.elementFromPoint(t.clientX, t.clientY);
        _touchClone.style.display = '';
        const target = el?.closest('.room-widget-card');
        if (target && target !== _touchDragEl) {
            _grid.insertBefore(_touchDragEl, target);
        }
    }

    function _onTouchEnd() {
        if (!_touchDragEl) return;
        _touchDragEl.style.opacity = '';
        if (_touchClone) { _touchClone.remove(); _touchClone = null; }
        _touchDragEl = null;
        _persistLayout();
    }

    // ─── Global helpers called by inline onclick ──────────────────────────────
    global._roomGridToggleSpan = async function (id, btn) {
        const card = btn.closest('.room-widget-card');
        const newSpan = card.dataset.span === '2' ? 1 : 2;
        try {
            const resp = await fetch(`/api/widgets/${id}/room_span`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ span: newSpan })
            });
            const data = await resp.json();
            if (data.ok) {
                card.dataset.span = newSpan;
                card.classList.toggle('span-2', newSpan === 2);
                _syncLocalConfig(id, 'room_span', newSpan);
                btn.innerHTML = newSpan === 2
                    ? '<i class="fas fa-compress-alt"></i> 2×'
                    : '<i class="fas fa-expand-alt"></i> 1×';
                btn.title = newSpan === 2 ? 'Switch to normal width' : 'Switch to wide';
                btn.classList.toggle('active', newSpan === 2);
                _persistLayout();
            }
        } catch (err) { console.warn('[RoomGrid] span toggle error:', err); }
    };

    global._roomGridRemoveWidget = async function (id) {
        try {
            await fetch(`/api/widgets/${id}/room_visible`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ visible: false })
            });
            _syncLocalConfig(id, 'room_visible', false);
            const card = _grid.querySelector(`.room-widget-card[data-id="${id}"]`);
            if (card) {
                card.style.transition = 'opacity 0.25s, transform 0.25s';
                card.style.opacity = '0';
                card.style.transform = 'scale(0.92)';
                setTimeout(() => {
                    card.remove();
                    if (!_grid.querySelectorAll('.room-widget-card').length) _showEmpty();
                }, 280);
            }
            // Notify channel
            const ch = new BroadcastChannel('hecos_widgets');
            ch.postMessage({ type: 'refresh' });
            localStorage.setItem('hecos_room_sync', Date.now());
        } catch (err) { console.warn('[RoomGrid] remove error:', err); }
    };

    // ─── Set draggable flag dynamically based on edit mode ────────────────────
    const _origToggle = controlRoomGrid.toggleEditMode.bind(controlRoomGrid);
    controlRoomGrid.toggleEditMode = function () {
        _origToggle();
        _grid.querySelectorAll('.room-widget-card').forEach(c => {
            c.draggable = _editing;
        });
    };

    // ─── Global helpers: Resize ──────────────────────────────────────────────────
    global._roomGridStartResize = function(e, id) {
        if (!_editing) return;
        e.preventDefault();
        const card = _grid.querySelector(`.room-widget-card[data-id="${id}"]`);
        if (!card) return;

        const startY = e.type.includes('touch') ? e.touches[0].clientY : e.clientY;
        const startHeight = card.offsetHeight;
        
        const line = document.createElement('div');
        line.className = 'room-resize-indicator-line';
        document.body.appendChild(line);

        // Position initial line correctly
        const rect = card.getBoundingClientRect();
        line.style.top = rect.bottom + 'px';
        line.style.left = rect.left + 'px';
        line.style.width = rect.width + 'px';

        const onMove = (moveEvent) => {
            const currentY = moveEvent.type.includes('touch') ? moveEvent.touches[0].clientY : moveEvent.clientY;
            let newHeight = Math.max(200, startHeight + (currentY - startY)); // min height 200px
            card.style.minHeight = newHeight + 'px';
            
            // visual line
            const currentRect = card.getBoundingClientRect();
            line.style.top = currentRect.bottom + 'px';
            line.style.left = currentRect.left + 'px';
            line.style.width = currentRect.width + 'px';
        };

        const onEnd = async (upEvent) => {
            document.removeEventListener('mousemove', onMove);
            document.removeEventListener('mouseup', onEnd);
            document.removeEventListener('touchmove', onMove);
            document.removeEventListener('touchend', onEnd);
            line.remove();
            
            const finalHeight = parseInt(card.style.minHeight);
            
            try {
                await fetch(`/api/widgets/${id}/room_height`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ height: finalHeight })
                });
                _syncLocalConfig(id, 'room_height', finalHeight);
            } catch (err) { console.warn('[RoomGrid] height save err:', err); }
        };

        document.addEventListener('mousemove', onMove);
        document.addEventListener('mouseup', onEnd);
        document.addEventListener('touchmove', onMove, {passive: false});
        document.addEventListener('touchend', onEnd);
    };

    global._roomGridResetHeight = async function(id) {
        if (!_editing) return;
        const card = _grid.querySelector(`.room-widget-card[data-id="${id}"]`);
        if (!card) return;
        
        card.style.minHeight = ''; // Remove inline style
        
        try {
            await fetch(`/api/widgets/${id}/room_height`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ height: null })
            });
            _syncLocalConfig(id, 'room_height', null);
        } catch (err) { console.warn('[RoomGrid] reset height err:', err); }
    };

    // ─── Export ───────────────────────────────────────────────────────────────
    global.controlRoomGrid = controlRoomGrid;

})(window);
