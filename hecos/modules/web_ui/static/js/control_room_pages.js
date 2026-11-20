/**
 * Hecos Control Room — Multi-Page Manager (Home Assistant-style Views)
 * control_room_pages.js
 *
 * Shared identically by Module A (Chat Control Room, 1-col & 2-col)
 * and Module B (Standalone /home Control Room).
 */
(function (global) {
    'use strict';

    const STORAGE_ACTIVE_PAGE = 'hecos_room_active_page';

    const API = {
        PAGES:       '/api/widgets/room/pages',
        PAGE:        (id) => `/api/widgets/room/pages/${encodeURIComponent(id)}`,
        REORDER:     '/api/widgets/room/pages/reorder',
        MOVE_WIDGET: (id) => `/api/widgets/room/pages/${encodeURIComponent(id)}/move_widget`,
    };

    const PAGE_ICONS = [
        'fa-layer-group', 'fa-th-large', 'fa-briefcase', 'fa-flask',
        'fa-microchip', 'fa-chart-line', 'fa-house', 'fa-robot',
        'fa-terminal', 'fa-calendar-alt', 'fa-check-double', 'fa-music',
        'fa-cloud-sun', 'fa-shield-halved', 'fa-bolt', 'fa-compass',
        'fa-satellite-dish', 'fa-brain', 'fa-wand-magic-sparkles', 'fa-gamepad',
        'fa-bell', 'fa-star', 'fa-folder-open', 'fa-sliders',
    ];

    let _pages = [];
    let _activePageId = '';
    try { _activePageId = localStorage.getItem(STORAGE_ACTIVE_PAGE) || ''; } catch (_) {}
    let _availableWidgets = [];
    let _initialized = false;
    let _firstRender = true;
    let _editingMode = false;

    let _barEl = null;
    let _trackEl = null;
    let _leftBtn = null;
    let _rightBtn = null;
    let _addWidgetBtn = null;
    let _addPageBtn = null;
    let _resizeObserver = null;

    let _activeModal = null;
    let _activeModalType = null; // 'page' | 'widgets'
    let _widgetFilterQuery = '';
    let _activePopover = null;
    let _activePopoverBtn = null;
    let _popoverCloseHandler = null;

    // ── Helpers ───────────────────────────────────────────────────────────────

    function _tr(key, fallback) {
        if (typeof global.t === 'function') {
            const val = global.t(key);
            if (val && val !== key) return val;
        }
        return fallback;
    }

    function _esc(str) {
        return String(str == null ? '' : str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    function _safeIcon(icon) {
        if (typeof icon === 'string' && /^fa-[a-z0-9-]+$/.test(icon.trim())) {
            return icon.trim();
        }
        return 'fa-layer-group';
    }

    function _toast(msg, type = 'info') {
        if (typeof global.showToast === 'function') {
            global.showToast(msg, type);
        }
    }

    function _notifyCrossTab(action, extra = {}) {
        if (global._roomGridSync && typeof global._roomGridSync.notifyPagesChanged === 'function') {
            global._roomGridSync.notifyPagesChanged(action, extra);
        } else {
            try { localStorage.setItem('hecos_room_sync', String(Date.now())); } catch (_) {}
        }
    }

    function _getActivePage() {
        return _pages.find(p => p.id === _activePageId) || _pages[0] || null;
    }

    function _hideTooltips() {
        if (global.HecosTooltip && typeof global.HecosTooltip.hide === 'function') {
            global.HecosTooltip.hide();
        }
    }

    // ── DOM Binding & Init ────────────────────────────────────────────────────

    function init() {
        _barEl = document.getElementById('room-pages-bar');
        _trackEl = document.getElementById('cr-pages-track');
        _leftBtn = document.getElementById('cr-pages-scroll-left');
        _rightBtn = document.getElementById('cr-pages-scroll-right');
        _addWidgetBtn = document.getElementById('cr-pages-add-widget');
        _addPageBtn = document.getElementById('cr-pages-add');

        if (!_barEl || !_trackEl) return false;
        if (_barEl.dataset.crPagesBound === '1') {
            _initialized = true;
            return true;
        }
        _barEl.dataset.crPagesBound = '1';
        _initialized = true;

        if (_leftBtn) {
            _leftBtn.addEventListener('click', () => {
                _trackEl.scrollBy({ left: -160, behavior: 'smooth' });
            });
        }
        if (_rightBtn) {
            _rightBtn.addEventListener('click', () => {
                _trackEl.scrollBy({ left: 160, behavior: 'smooth' });
            });
        }

        // Mouse wheel horizontal scroll on the pill track
        _trackEl.addEventListener('wheel', (e) => {
            if (_trackEl.scrollWidth > _trackEl.clientWidth + 2) {
                const delta = Math.abs(e.deltaY) >= Math.abs(e.deltaX) ? e.deltaY : e.deltaX;
                if (delta !== 0) {
                    e.preventDefault();
                    _trackEl.scrollLeft += delta * 0.9;
                }
            }
        }, { passive: false });

        _trackEl.addEventListener('scroll', updateScrollArrows, { passive: true });

        // Delegated tab clicks & edit trigger
        _trackEl.addEventListener('click', (e) => {
            const editTrigger = e.target.closest('.cr-page-edit-trigger');
            if (editTrigger) {
                e.stopPropagation();
                _hideTooltips();
                const pid = editTrigger.dataset.pageId;
                const page = _pages.find(p => p.id === pid);
                if (page) openPageModal(page);
                return;
            }
            const tab = e.target.closest('.cr-page-tab');
            if (tab) {
                const pid = tab.dataset.pageId;
                if (pid) selectPage(pid);
            }
        });

        // Double-click or right-click any page pill to edit it
        _trackEl.addEventListener('dblclick', (e) => {
            const tab = e.target.closest('.cr-page-tab');
            if (!tab) return;
            const page = _pages.find(p => p.id === tab.dataset.pageId);
            if (page) {
                e.preventDefault();
                _hideTooltips();
                openPageModal(page);
            }
        });
        _trackEl.addEventListener('contextmenu', (e) => {
            const tab = e.target.closest('.cr-page-tab');
            if (!tab) return;
            const page = _pages.find(p => p.id === tab.dataset.pageId);
            if (page) {
                e.preventDefault();
                _hideTooltips();
                openPageModal(page);
            }
        });

        // Keyboard left/right switching (works directly from Standalone /home or
        // whenever Chat Control Room panel is open, without hijacking inputs/modals)
        if (!global._crPagesGlobalKeyBound) {
            global._crPagesGlobalKeyBound = true;
            document.addEventListener('keydown', (e) => {
                if (e.key !== 'ArrowLeft' && e.key !== 'ArrowRight') return;
                if (e.altKey || e.ctrlKey || e.metaKey || e.shiftKey) return;
                if (!_isControlRoomKeyContext()) return;

                const activeInBar = Boolean(_barEl && document.activeElement && _barEl.contains(document.activeElement));
                e.preventDefault();
                e.stopImmediatePropagation();
                stepPage(e.key === 'ArrowRight' ? 1 : -1, activeInBar);
            }, { capture: true });
        }

        if (_addPageBtn) {
            _addPageBtn.addEventListener('click', () => {
                _hideTooltips();
                openPageModal(null);
            });
        }
        if (_addWidgetBtn) {
            _addWidgetBtn.addEventListener('click', () => {
                _hideTooltips();
                openWidgetPickerModal();
            });
        }

        // Keep scroll arrows synced when panel resizes (1x <-> 2x / drag / viewport)
        if (typeof ResizeObserver !== 'undefined') {
            _resizeObserver = new ResizeObserver(() => {
                updateScrollArrows();
            });
            _resizeObserver.observe(_barEl);
            _resizeObserver.observe(_trackEl);
        }
        window.addEventListener('resize', updateScrollArrows);

        return true;
    }

    // ── Sync & Rendering ──────────────────────────────────────────────────────

    function syncFromServer(pages, activePageId, availableWidgets) {
        if (!_initialized) init();

        _pages = Array.isArray(pages) ? pages : [];
        if (activePageId) {
            _activePageId = activePageId;
            try { localStorage.setItem(STORAGE_ACTIVE_PAGE, _activePageId); } catch (_) {}
        } else if (_pages.length && !_pages.some(p => p.id === _activePageId)) {
            _activePageId = _pages[0].id;
            try { localStorage.setItem(STORAGE_ACTIVE_PAGE, _activePageId); } catch (_) {}
        }

        if (Array.isArray(availableWidgets)) {
            _availableWidgets = availableWidgets;
        }

        // Sync local window.cfg snapshot if present
        const cfg = global.cfg || (global.parent && global.parent.cfg);
        if (cfg) {
            if (!cfg.widgets) cfg.widgets = {};
            cfg.widgets.room_pages = _pages.map(p => ({
                id: p.id, name: p.name, icon: p.icon, widgets: p.widgets || []
            }));
        }

        renderBar();

        // If the widget picker modal is currently open, keep its toggles synced live
        if (_activeModal && _activeModalType === 'widgets') {
            _renderWidgetPickerList();
        }
    }

    function renderBar() {
        if (!_trackEl) return;

        const editTitle = _tr('room_page_edit', 'Edit Page');
        const html = _pages.map(p => {
            const isActive = p.id === _activePageId;
            const icon = _safeIcon(p.icon);
            const count = typeof p.count === 'number' ? p.count : (p.widgets ? p.widgets.length : 0);
            const tabTitle = `${p.name} (${count})`;
            return `
                <button type="button"
                        class="cr-page-tab${isActive ? ' active' : ''}"
                        role="tab"
                        aria-selected="${isActive ? 'true' : 'false'}"
                        data-page-id="${_esc(p.id)}"
                        title="${_esc(tabTitle)}">
                    <i class="fas ${icon} cr-page-icon" aria-hidden="true"></i>
                    <span class="cr-page-name">${_esc(p.name)}</span>
                    <span class="cr-page-count">${count}</span>
                    ${isActive ? `<span class="cr-page-edit-trigger" role="button" tabindex="-1" data-page-id="${_esc(p.id)}" title="${_esc(editTitle)}" aria-label="${_esc(editTitle)}"><i class="fas fa-pen"></i></span>` : ''}
                </button>
            `;
        }).join('');

        _trackEl.innerHTML = html;

        // Scroll active tab into view cleanly
        requestAnimationFrame(() => {
            const activeTab = _trackEl.querySelector('.cr-page-tab.active');
            if (activeTab) {
                activeTab.scrollIntoView({
                    behavior: _firstRender ? 'auto' : 'smooth',
                    inline: 'nearest',
                    block: 'nearest',
                });
            }
            _firstRender = false;
            updateScrollArrows();
        });
    }

    function updateScrollArrows() {
        if (!_barEl || !_trackEl) return;
        const maxScroll = _trackEl.scrollWidth - _trackEl.clientWidth;
        const hasOverflow = maxScroll > 4;
        _barEl.classList.toggle('has-overflow', hasOverflow);
        if (_leftBtn) {
            _leftBtn.disabled = !hasOverflow || _trackEl.scrollLeft <= 2;
        }
        if (_rightBtn) {
            _rightBtn.disabled = !hasOverflow || _trackEl.scrollLeft >= maxScroll - 2;
        }
    }

    function setEditMode(editing) {
        _editingMode = !!editing;
        if (_barEl) {
            _barEl.classList.toggle('cr-pages-editing', _editingMode);
        }
        if (!_editingMode) {
            closePopover();
        }
    }

    function getActivePageId() {
        return _activePageId || (_pages[0] ? _pages[0].id : '');
    }

    function getActivePage() {
        return _getActivePage();
    }

    function getPages() {
        return _pages.slice();
    }

    function _isControlRoomKeyContext() {
        if (!_pages || _pages.length <= 1) return false;
        if (_activeModal || _activePopover) return false;

        // Yield when any modal, overlay, or picker is open
        if (document.querySelector(
            '#preset-manager-panel.open, #soul-forge-panel.open, #session-overrides-panel.open, ' +
            '#hks-modal.open, .modal.open, .hfp-overlay.open, .hwp-overlay.open, ' +
            '.cr-modal-backdrop, .cr-move-popover, .room-card-aes-popover'
        )) {
            return false;
        }

        const active = document.activeElement;
        if (active && active !== document.body && active !== document.documentElement) {
            const tag = (active.tagName || '').toUpperCase();
            if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || active.isContentEditable) {
                return false;
            }
        }

        // Standalone Control Room (/home): always active
        if (document.getElementById('home-grid')) {
            return true;
        }

        // Chat Control Room (Module A): only when panel is open
        const panel = document.getElementById('control-room-panel');
        if (!panel || !panel.classList.contains('open')) return false;

        // Focus inside Control Room panel or its toggle button: always active
        if (active && (panel.contains(active) || active.id === 'sidebar-expand-btn')) {
            return true;
        }

        // Yield if focus is explicitly inside the Welcome carousel
        const welcomeEl = document.getElementById('welcome');
        const welcomeVisible = !!(
            welcomeEl &&
            welcomeEl.style.display !== 'none' &&
            (!global.getComputedStyle || global.getComputedStyle(welcomeEl).display !== 'none')
        );
        if (welcomeVisible && active && welcomeEl.contains(active)) {
            return false;
        }

        return true;
    }

    function stepPage(delta, focusTab = false) {
        if (!_pages || _pages.length <= 1) return false;
        const idx = _pages.findIndex(p => p.id === _activePageId);
        const baseIdx = idx >= 0 ? idx : 0;
        const nextIdx = (baseIdx + delta + _pages.length) % _pages.length;
        const nextId = _pages[nextIdx].id;
        selectPage(nextId);
        if (focusTab && _trackEl) {
            const nextTab = _trackEl.querySelector(`.cr-page-tab[data-page-id="${CSS.escape(nextId)}"]`);
            if (nextTab) nextTab.focus({ preventScroll: true });
        }
        return true;
    }

    function selectPage(pageId) {
        if (!pageId || pageId === _activePageId) return;
        if (_pages.length && !_pages.some(p => p.id === pageId)) return;

        closePopover();
        _activePageId = pageId;
        try { localStorage.setItem(STORAGE_ACTIVE_PAGE, _activePageId); } catch (_) {}
        renderBar();

        if (global.controlRoomGrid && typeof global.controlRoomGrid.refresh === 'function') {
            global.controlRoomGrid.refresh({ force: true, pageId: _activePageId });
        }
    }

    // ── Modal Infrastructure (Dark Glass, mounted on document.body) ───────────

    function closeModal() {
        if (_activeModal) {
            if (_activeModal._escHandler) {
                document.removeEventListener('keydown', _activeModal._escHandler);
            }
            _activeModal.remove();
            _activeModal = null;
            _activeModalType = null;
        }
    }

    function _createModal(type, titleHtml, bodyHtml, footerHtml, extraClass = '') {
        closeModal();
        closePopover();

        const backdrop = document.createElement('div');
        backdrop.className = 'cr-modal-backdrop';
        backdrop.innerHTML = `
            <div class="cr-modal ${extraClass}" role="dialog" aria-modal="true">
                <div class="cr-modal-header">
                    <div class="cr-modal-title">${titleHtml}</div>
                    <button type="button" class="cr-modal-close" aria-label="Close"><i class="fas fa-times"></i></button>
                </div>
                <div class="cr-modal-body">${bodyHtml}</div>
                ${footerHtml ? `<div class="cr-modal-footer">${footerHtml}</div>` : ''}
            </div>
        `;

        backdrop.addEventListener('mousedown', (e) => {
            if (e.target === backdrop) closeModal();
        });
        const closeBtn = backdrop.querySelector('.cr-modal-close');
        if (closeBtn) closeBtn.addEventListener('click', closeModal);

        const escHandler = (e) => {
            if (e.key === 'Escape') {
                e.stopPropagation();
                closeModal();
            }
        };
        document.addEventListener('keydown', escHandler);
        backdrop._escHandler = escHandler;

        document.body.appendChild(backdrop);
        _activeModal = backdrop;
        _activeModalType = type;
        return backdrop;
    }

    // ── Create / Edit Page Modal ──────────────────────────────────────────────

    function openPageModal(page) {
        const isEdit = Boolean(page && page.id);
        let selectedIcon = _safeIcon(isEdit ? page.icon : 'fa-layer-group');
        const initialName = isEdit ? page.name : '';
        const canDelete = isEdit && _pages.length > 1;
        const pageIndex = isEdit ? _pages.findIndex(p => p.id === page.id) : -1;

        const titleHtml = isEdit
            ? `<i class="fas fa-pen-to-square"></i><span>${_esc(_tr('room_page_edit', 'Edit Page'))}</span>`
            : `<i class="fas fa-plus-circle"></i><span>${_esc(_tr('room_page_new', 'New Page'))}</span>`;

        const iconsGridHtml = PAGE_ICONS.map(ic => `
            <button type="button"
                    class="cr-icon-option${ic === selectedIcon ? ' active' : ''}"
                    data-icon="${ic}"
                    title="${ic.replace('fa-', '')}">
                <i class="fas ${ic}"></i>
            </button>
        `).join('');

        const orderRowHtml = (isEdit && _pages.length > 1) ? `
            <div class="cr-field">
                <label>${_esc(_tr('room_page_order', 'Page Position'))}</label>
                <div class="cr-order-bar">
                    <button type="button" class="cr-btn cr-btn-ghost" id="cr-order-left"
                            ${pageIndex <= 0 ? 'disabled' : ''}
                            title="${_esc(_tr('room_page_move_left', 'Move left'))}">
                        <i class="fas fa-arrow-left"></i>
                    </button>
                    <span class="cr-order-status" id="cr-order-status">${pageIndex + 1} / ${_pages.length}</span>
                    <button type="button" class="cr-btn cr-btn-ghost" id="cr-order-right"
                            ${pageIndex >= _pages.length - 1 ? 'disabled' : ''}
                            title="${_esc(_tr('room_page_move_right', 'Move right'))}">
                        <i class="fas fa-arrow-right"></i>
                    </button>
                </div>
            </div>
        ` : '';

        const bodyHtml = `
            <div class="cr-field">
                <label for="cr-page-name-input">${_esc(_tr('room_page_name', 'Page Name'))}</label>
                <input type="text" id="cr-page-name-input" class="cr-input" maxlength="32"
                       value="${_esc(initialName)}"
                       placeholder="${_esc(_tr('room_page_name_placeholder', 'e.g. Productivity, System, Lab...'))}">
            </div>
            <div class="cr-field">
                <label>${_esc(_tr('room_page_icon', 'Icon'))}</label>
                <div class="cr-icon-grid" id="cr-icon-grid">${iconsGridHtml}</div>
            </div>
            ${orderRowHtml}
            <div class="cr-delete-confirm" id="cr-delete-confirm" style="display:none;">
                <p><i class="fas fa-triangle-exclamation"></i> ${_esc(_tr('room_page_delete_confirm', "Delete this page? Installed widgets won't be uninstalled."))}</p>
                <div class="cr-delete-confirm-actions">
                    <button type="button" class="cr-btn cr-btn-ghost" id="cr-delete-abort">${_esc(_tr('room_page_cancel', 'Cancel'))}</button>
                    <button type="button" class="cr-btn cr-btn-danger" id="cr-delete-confirm-btn">${_esc(_tr('room_page_delete_confirm_btn', 'Confirm Delete'))}</button>
                </div>
            </div>
        `;

        const deleteBtnHtml = isEdit
            ? `<button type="button" class="cr-btn cr-btn-danger-ghost" id="cr-page-delete-btn"
                       ${canDelete ? '' : 'disabled'}
                       title="${_esc(canDelete ? _tr('room_page_delete', 'Delete') : _tr('room_page_delete_last_hint', 'Cannot delete the last remaining page'))}">
                   <i class="fas fa-trash-alt"></i><span>${_esc(_tr('room_page_delete', 'Delete'))}</span>
               </button>`
            : '<span></span>';

        const footerHtml = `
            <div class="cr-modal-footer-left">${deleteBtnHtml}</div>
            <div class="cr-modal-footer-right">
                <button type="button" class="cr-btn cr-btn-ghost" id="cr-page-cancel-btn">${_esc(_tr('room_page_cancel', 'Cancel'))}</button>
                <button type="button" class="cr-btn cr-btn-primary" id="cr-page-submit-btn">
                    <i class="fas ${isEdit ? 'fa-check' : 'fa-plus'}"></i>
                    <span>${_esc(isEdit ? _tr('room_page_save', 'Save') : _tr('room_page_create', 'Create'))}</span>
                </button>
            </div>
        `;

        const modal = _createModal('page', titleHtml, bodyHtml, footerHtml, 'cr-modal-page');
        const nameInput = modal.querySelector('#cr-page-name-input');
        const iconGrid = modal.querySelector('#cr-icon-grid');
        const submitBtn = modal.querySelector('#cr-page-submit-btn');
        const cancelBtn = modal.querySelector('#cr-page-cancel-btn');

        setTimeout(() => {
            if (nameInput) {
                nameInput.focus();
                if (isEdit) nameInput.select();
            }
        }, 20);

        iconGrid.addEventListener('click', (e) => {
            const btn = e.target.closest('.cr-icon-option');
            if (!btn) return;
            selectedIcon = btn.dataset.icon;
            iconGrid.querySelectorAll('.cr-icon-option').forEach(b => b.classList.toggle('active', b === btn));
        });

        cancelBtn.addEventListener('click', closeModal);

        // Reorder left / right inside Edit modal
        const moveOrder = async (delta) => {
            const curIdx = _pages.findIndex(p => p.id === page.id);
            const newIdx = curIdx + delta;
            if (curIdx < 0 || newIdx < 0 || newIdx >= _pages.length) return;
            const order = _pages.map(p => p.id);
            const [moved] = order.splice(curIdx, 1);
            order.splice(newIdx, 0, moved);

            try {
                const resp = await fetch(API.REORDER, {
                    method: 'PATCH',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ order }),
                });
                const data = await resp.json();
                if (data.ok && Array.isArray(data.pages)) {
                    syncFromServer(data.pages, _activePageId, _availableWidgets);
                    _notifyCrossTab('reorder', { order });
                    const updatedIdx = _pages.findIndex(p => p.id === page.id);
                    const statusEl = modal.querySelector('#cr-order-status');
                    const leftBtn = modal.querySelector('#cr-order-left');
                    const rightBtn = modal.querySelector('#cr-order-right');
                    if (statusEl) statusEl.textContent = `${updatedIdx + 1} / ${_pages.length}`;
                    if (leftBtn) leftBtn.disabled = updatedIdx <= 0;
                    if (rightBtn) rightBtn.disabled = updatedIdx >= _pages.length - 1;
                }
            } catch (err) {
                console.warn('[RoomPages] Reorder error:', err);
            }
        };

        const orderLeftBtn = modal.querySelector('#cr-order-left');
        const orderRightBtn = modal.querySelector('#cr-order-right');
        if (orderLeftBtn) orderLeftBtn.addEventListener('click', () => moveOrder(-1));
        if (orderRightBtn) orderRightBtn.addEventListener('click', () => moveOrder(1));

        // Inline 2-step delete confirmation
        const delBtn = modal.querySelector('#cr-page-delete-btn');
        const delConfirmBox = modal.querySelector('#cr-delete-confirm');
        const delAbortBtn = modal.querySelector('#cr-delete-abort');
        const delConfirmBtn = modal.querySelector('#cr-delete-confirm-btn');

        if (delBtn && canDelete && delConfirmBox) {
            delBtn.addEventListener('click', () => {
                delConfirmBox.style.display = 'block';
                delBtn.style.visibility = 'hidden';
            });
            delAbortBtn.addEventListener('click', () => {
                delConfirmBox.style.display = 'none';
                delBtn.style.visibility = '';
            });
            delConfirmBtn.addEventListener('click', async () => {
                delConfirmBtn.disabled = true;
                try {
                    const resp = await fetch(API.PAGE(page.id), { method: 'DELETE' });
                    const data = await resp.json();
                    if (!data.ok) throw new Error(data.error || 'Delete failed');
                    const nextPageId = (page.id === _activePageId) ? data.fallback_page_id : _activePageId;
                    closeModal();
                    syncFromServer(data.pages, nextPageId, _availableWidgets);
                    _notifyCrossTab('delete', { pageId: page.id, fallbackPageId: nextPageId });
                    if (global.controlRoomGrid) {
                        global.controlRoomGrid.refresh({ force: true, pageId: nextPageId });
                    }
                    _toast(`"${page.name}" eliminata`, 'info');
                } catch (err) {
                    delConfirmBtn.disabled = false;
                    _toast(err.message || 'Errore eliminazione pagina', 'error');
                }
            });
        }

        // Submit create / save
        const doSubmit = async () => {
            const trimmed = (nameInput.value || '').trim();
            if (!trimmed) {
                nameInput.classList.add('cr-input-error');
                nameInput.focus();
                return;
            }
            submitBtn.disabled = true;
            try {
                if (isEdit) {
                    const resp = await fetch(API.PAGE(page.id), {
                        method: 'PATCH',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ name: trimmed, icon: selectedIcon }),
                    });
                    const data = await resp.json();
                    if (!data.ok) throw new Error(data.error || 'Update failed');
                    closeModal();
                    syncFromServer(data.pages, _activePageId, _availableWidgets);
                    _notifyCrossTab('update', { pageId: page.id });
                    if (global.controlRoomGrid) {
                        global.controlRoomGrid.refresh({ force: true, pageId: _activePageId });
                    }
                } else {
                    const resp = await fetch(API.PAGES, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ name: trimmed, icon: selectedIcon }),
                    });
                    const data = await resp.json();
                    if (!data.ok) throw new Error(data.error || 'Create failed');
                    const createdId = data.page ? data.page.id : _activePageId;
                    closeModal();
                    syncFromServer(data.pages, createdId, _availableWidgets);
                    _notifyCrossTab('create', { pageId: createdId });
                    if (global.controlRoomGrid) {
                        global.controlRoomGrid.refresh({ force: true, pageId: createdId });
                    }
                    _toast(`Pagina "${trimmed}" creata`, 'success');
                }
            } catch (err) {
                submitBtn.disabled = false;
                _toast(err.message || 'Errore salvataggio pagina', 'error');
            }
        };

        submitBtn.addEventListener('click', doSubmit);
        nameInput.addEventListener('input', () => nameInput.classList.remove('cr-input-error'));
        nameInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                doSubmit();
            }
        });
    }

    // ── Add / Remove Widgets Picker Modal ─────────────────────────────────────

    function openWidgetPickerModal() {
        const activePage = _getActivePage();
        if (!activePage) return;
        _widgetFilterQuery = '';

        const titleHtml = `
            <i class="fas ${_safeIcon(activePage.icon)}"></i>
            <span>${_esc(_tr('room_page_widgets_title', 'Widgets on page'))}: <strong>${_esc(activePage.name)}</strong></span>
        `;

        const showSearch = _availableWidgets.length > 5;
        const bodyHtml = `
            ${showSearch ? `
                <div class="cr-picker-search-wrap">
                    <i class="fas fa-search"></i>
                    <input type="text" id="cr-widget-search" class="cr-input"
                           placeholder="${_esc(_tr('room_page_widget_search', 'Filter widgets...'))}">
                </div>
            ` : ''}
            <div class="cr-widget-picker-list" id="cr-widget-picker-list"></div>
        `;

        const footerHtml = `
            <div class="cr-modal-footer-left">
                <button type="button" class="cr-btn cr-btn-link" id="cr-open-hub-widgets">
                    <i class="fas fa-external-link-alt"></i>
                    <span>${_esc(_tr('room_page_manage_hub', 'Manage all widgets in Central Hub'))}</span>
                </button>
            </div>
            <div class="cr-modal-footer-right">
                <button type="button" class="cr-btn cr-btn-primary" id="cr-picker-done">${_esc(_tr('room_close', 'Close'))}</button>
            </div>
        `;

        const modal = _createModal('widgets', titleHtml, bodyHtml, footerHtml, 'cr-modal-widgets');

        const searchEl = modal.querySelector('#cr-widget-search');
        if (searchEl) {
            searchEl.addEventListener('input', () => {
                _widgetFilterQuery = (searchEl.value || '').trim().toLowerCase();
                _renderWidgetPickerList();
            });
            setTimeout(() => searchEl.focus(), 20);
        }

        const doneBtn = modal.querySelector('#cr-picker-done');
        if (doneBtn) doneBtn.addEventListener('click', closeModal);

        const hubBtn = modal.querySelector('#cr-open-hub-widgets');
        if (hubBtn) {
            hubBtn.addEventListener('click', () => {
                closeModal();
                if (typeof global.hecosOpenConfig === 'function') {
                    global.hecosOpenConfig('#widgets');
                } else {
                    window.open('/hecos/config/ui#widgets', '_blank', 'noopener');
                }
            });
        }

        const listEl = modal.querySelector('#cr-widget-picker-list');
        if (listEl) {
            listEl.addEventListener('click', async (e) => {
                const row = e.target.closest('.cr-picker-row');
                if (!row || row.dataset.busy === '1') return;
                const wid = row.dataset.widgetId;
                const isOnPage = row.dataset.onPage === '1';
                const currentPage = _getActivePage();
                if (!wid || !currentPage) return;

                row.dataset.busy = '1';
                row.classList.add('busy');

                try {
                    const payload = isOnPage ? { remove_widget: wid } : { add_widget: wid };
                    const resp = await fetch(API.PAGE(currentPage.id), {
                        method: 'PATCH',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(payload),
                    });
                    const data = await resp.json();
                    if (!data.ok) throw new Error(data.error || 'Toggle failed');

                    syncFromServer(data.pages, currentPage.id, _availableWidgets);
                    _notifyCrossTab('widgets', { pageId: currentPage.id, widgetId: wid });
                    if (global.controlRoomGrid) {
                        global.controlRoomGrid.refresh({ force: true, pageId: currentPage.id });
                    }
                } catch (err) {
                    _toast(err.message || 'Errore aggiornamento widget', 'error');
                } finally {
                    row.dataset.busy = '0';
                    row.classList.remove('busy');
                }
            });
        }

        _renderWidgetPickerList();
    }

    function _renderWidgetPickerList() {
        if (!_activeModal || _activeModalType !== 'widgets') return;
        const listEl = _activeModal.querySelector('#cr-widget-picker-list');
        const activePage = _getActivePage();
        if (!listEl || !activePage) return;

        const onPageSet = new Set(activePage.widgets || []);
        const pageNameById = new Map(_pages.map(p => [p.id, p.name]));

        const filtered = _availableWidgets.filter(w => {
            if (!_widgetFilterQuery) return true;
            const dName = _tr(w.display_name, w.display_name).toLowerCase();
            const dDesc = _tr(w.description, w.description).toLowerCase();
            return dName.includes(_widgetFilterQuery)
                || w.extension_id.toLowerCase().includes(_widgetFilterQuery)
                || dDesc.includes(_widgetFilterQuery);
        });

        if (!filtered.length) {
            listEl.innerHTML = `<div class="cr-picker-empty"><i class="fas fa-cubes"></i><span>Nessun widget disponibile</span></div>`;
            return;
        }

        const addedLbl = _tr('room_page_widget_added', 'Added');
        const addLbl = _tr('room_page_widget_add', 'Add');
        const sidebarLbl = _tr('room_page_in_sidebar', 'In sidebar');

        listEl.innerHTML = filtered.map(w => {
            const onPage = onPageSet.has(w.extension_id);
            const displayName = _tr(w.display_name, w.display_name || w.extension_id);
            const desc = _tr(w.description, w.description || '');
            const otherPages = _pages
                .filter(p => p.id !== activePage.id && Array.isArray(p.widgets) && p.widgets.includes(w.extension_id))
                .map(p => pageNameById.get(p.id))
                .filter(Boolean);

            const badges = [];
            if (w.visible && !onPage) {
                badges.push(`<span class="cr-picker-badge cr-picker-badge-muted"><i class="fas fa-columns"></i> ${_esc(sidebarLbl)}</span>`);
            }
            otherPages.slice(0, 2).forEach(pn => {
                badges.push(`<span class="cr-picker-badge">${_esc(pn)}</span>`);
            });
            if (otherPages.length > 2) {
                badges.push(`<span class="cr-picker-badge">+${otherPages.length - 2}</span>`);
            }

            return `
                <div class="cr-picker-row${onPage ? ' is-added' : ''}"
                     role="button" tabindex="0"
                     data-widget-id="${_esc(w.extension_id)}"
                     data-on-page="${onPage ? '1' : '0'}">
                    <div class="cr-picker-info">
                        <div class="cr-picker-name-row">
                            <span class="cr-picker-name">${_esc(displayName)}</span>
                            ${badges.join('')}
                        </div>
                        ${desc ? `<div class="cr-picker-desc">${_esc(desc)}</div>` : ''}
                    </div>
                    <span class="cr-picker-toggle-pill${onPage ? ' active' : ''}">
                        <i class="fas ${onPage ? 'fa-check' : 'fa-plus'}"></i>
                        <span>${_esc(onPage ? addedLbl : addLbl)}</span>
                    </span>
                </div>
            `;
        }).join('');
    }

    // ── Card Chrome: Move / Copy Widget to Another Page Popover ───────────────

    function closePopover() {
        if (_activePopover) {
            _activePopover.remove();
            _activePopover = null;
        }
        if (_activePopoverBtn) {
            _activePopoverBtn.classList.remove('active');
            _activePopoverBtn = null;
        }
        if (_popoverCloseHandler) {
            document.removeEventListener('mousedown', _popoverCloseHandler);
            _popoverCloseHandler = null;
        }
    }

    function openMoveWidgetMenu(event, extId, btnEl) {
        if (event) event.stopPropagation();
        _hideTooltips();

        if (_activePopover && _activePopoverBtn === btnEl) {
            closePopover();
            return;
        }
        closePopover();

        const currentPage = _getActivePage();
        if (!currentPage) return;
        const otherPages = _pages.filter(p => p.id !== currentPage.id);

        const pop = document.createElement('div');
        pop.className = 'cr-move-popover';

        if (!otherPages.length) {
            pop.innerHTML = `
                <div class="cr-move-popover-header">${_esc(_tr('room_page_move_widget', 'Move or copy to another page'))}</div>
                <div class="cr-move-popover-empty">${_esc(_tr('room_page_no_other_pages', 'Create another page to move this widget'))}</div>
                <button type="button" class="cr-move-create-btn">
                    <i class="fas fa-plus"></i><span>${_esc(_tr('room_page_new', 'New Page'))}</span>
                </button>
            `;
            pop.querySelector('.cr-move-create-btn').addEventListener('click', () => {
                closePopover();
                openPageModal(null);
            });
        } else {
            const moveLbl = _tr('room_page_move_to', 'Move to');
            const copyLbl = _tr('room_page_copy_to', 'Also show on this page');
            const rowsHtml = otherPages.map(p => {
                const alreadyThere = Array.isArray(p.widgets) && p.widgets.includes(extId);
                return `
                    <div class="cr-move-row">
                        <button type="button" class="cr-move-target-btn" data-target-id="${_esc(p.id)}"
                                title="${_esc(`${moveLbl} ${p.name}`)}">
                            <i class="fas ${_safeIcon(p.icon)}"></i>
                            <span class="cr-move-target-name">${_esc(p.name)}</span>
                        </button>
                        <button type="button" class="cr-copy-target-btn${alreadyThere ? ' is-present' : ''}"
                                data-target-id="${_esc(p.id)}"
                                ${alreadyThere ? 'disabled' : ''}
                                title="${_esc(alreadyThere ? _tr('room_page_widget_added', 'Added') : copyLbl)}">
                            <i class="fas ${alreadyThere ? 'fa-check' : 'fa-copy'}"></i>
                        </button>
                    </div>
                `;
            }).join('');

            pop.innerHTML = `
                <div class="cr-move-popover-header">${_esc(moveLbl)}…</div>
                <div class="cr-move-list">${rowsHtml}</div>
            `;

            pop.addEventListener('click', async (e) => {
                const moveBtn = e.target.closest('.cr-move-target-btn');
                const copyBtn = e.target.closest('.cr-copy-target-btn');
                if (!moveBtn && !copyBtn) return;

                const isCopy = Boolean(copyBtn);
                const targetId = (moveBtn || copyBtn).dataset.targetId;
                const targetPage = _pages.find(p => p.id === targetId);
                if (!targetId) return;

                try {
                    const resp = await fetch(API.MOVE_WIDGET(currentPage.id), {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ ext_id: extId, target_page_id: targetId, copy: isCopy }),
                    });
                    const data = await resp.json();
                    if (!data.ok) throw new Error(data.error || 'Operation failed');

                    closePopover();
                    syncFromServer(data.pages, currentPage.id, _availableWidgets);
                    _notifyCrossTab('move_widget', { from: currentPage.id, to: targetId, extId, copy: isCopy });
                    if (global.controlRoomGrid) {
                        global.controlRoomGrid.refresh({ force: true, pageId: currentPage.id });
                    }
                    if (targetPage) {
                        _toast(
                            isCopy
                                ? `Widget aggiunto anche a "${targetPage.name}"`
                                : `Widget spostato in "${targetPage.name}"`,
                            'info'
                        );
                    }
                } catch (err) {
                    _toast(err.message || 'Errore spostamento widget', 'error');
                }
            });
        }

        document.body.appendChild(pop);
        _activePopover = pop;
        _activePopoverBtn = btnEl || null;
        if (btnEl) btnEl.classList.add('active');

        // Clamp position inside viewport
        const rect = btnEl ? btnEl.getBoundingClientRect() : { bottom: 80, left: 80, right: 100 };
        const popW = pop.offsetWidth || 210;
        const popH = pop.offsetHeight || 140;
        const top = (rect.bottom + 6 + popH > window.innerHeight - 10)
            ? Math.max(10, rect.top - popH - 6)
            : (rect.bottom + 6);
        const left = Math.max(10, Math.min(window.innerWidth - popW - 10, rect.right - popW));
        pop.style.top = `${top}px`;
        pop.style.left = `${left}px`;

        _popoverCloseHandler = (ev) => {
            if (!pop.contains(ev.target) && ev.target !== btnEl && (!btnEl || !btnEl.contains(ev.target))) {
                closePopover();
            }
        };
        setTimeout(() => document.addEventListener('mousedown', _popoverCloseHandler), 10);
    }

    // Global shortcut for widget chrome button
    global._roomGridOpenPageMenu = openMoveWidgetMenu;

    global.controlRoomPages = {
        init,
        syncFromServer,
        renderBar,
        updateScrollArrows,
        setEditMode,
        getActivePageId,
        getActivePage,
        getPages,
        selectPage,
        stepPage,
        openPageModal,
        openWidgetPickerModal,
        openMoveWidgetMenu,
        closeModal,
        closePopover,
    };

})(window);
