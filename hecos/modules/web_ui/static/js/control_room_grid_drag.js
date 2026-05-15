/**
 * Hecos Control Room - Drag & Drop Module
 * Handles mouse and touch drag events.
 */
(function (global) {
    'use strict';

    let _dragSrc = null;
    let _touchDragEl = null, _touchClone = null, _touchOX = 0, _touchOY = 0;

    const bindEvents = (card, grid) => {
        // Mouse
        card.addEventListener('dragstart', (e) => _onDragStart(e, card));
        card.addEventListener('dragend',   (e) => _onDragEnd(e, card));
        card.addEventListener('dragenter', (e) => e.preventDefault());
        card.addEventListener('dragover',  (e) => _onDragOver(e, card, grid));
        card.addEventListener('drop',      (e) => e.preventDefault());

        // Touch
        card.addEventListener('touchstart', (e) => _onTouchStart(e, card), {passive: true});
        card.addEventListener('touchmove',  (e) => _onTouchMove(e, card, grid), {passive: false});
        card.addEventListener('touchend',   () => _onTouchEnd(card));
    };

    // --- Mouse Drag ---
    function _onDragStart(e, card) {
        if (!global.controlRoomGrid?.isEditing()) { e.preventDefault(); return; }
        _dragSrc = card;
        card.style.opacity = '0.4';
        e.dataTransfer.effectAllowed = 'move';
        e.dataTransfer.setData('text/plain', card.dataset.id || 'widget');
    }

    function _onDragEnd(e, card) {
        card.style.opacity = '1';
        _dragSrc = null;
        if (global.controlRoomGrid?.persistLayout) global.controlRoomGrid.persistLayout();
    }

    function _onDragOver(e, card, grid) {
        e.preventDefault();
        if (!global.controlRoomGrid?.isEditing() || !_dragSrc) return;
        const overCard = e.target.closest('.room-widget-card');
        if (!overCard || overCard === _dragSrc) return;

        const rect = overCard.getBoundingClientRect();
        const offset = rect.y + (rect.height / 2);
        if (e.clientY > offset) overCard.after(_dragSrc);
        else overCard.before(_dragSrc);
    }

    // --- Touch Drag ---
    function _onTouchStart(e, card) {
        if (!global.controlRoomGrid?.isEditing()) return;
        const t = e.touches[0];
        _touchDragEl = card;
        _touchOX = t.clientX - card.getBoundingClientRect().left;
        _touchOY = t.clientY - card.getBoundingClientRect().top;
        _touchClone = card.cloneNode(true);
        _touchClone.style.cssText = `position:fixed; z-index:99999; pointer-events:none; opacity:0.85; width:${card.offsetWidth}px; box-shadow: 0 12px 40px rgba(0,0,0,0.5);`;
        document.body.appendChild(_touchClone);
        card.style.opacity = '0.3';
    }

    function _onTouchMove(e, card, grid) {
        if (!_touchDragEl || !_touchClone) return;
        e.preventDefault();
        const t = e.touches[0];
        _touchClone.style.left = (t.clientX - _touchOX) + 'px';
        _touchClone.style.top  = (t.clientY - _touchOY) + 'px';
        _touchClone.style.display = 'none';
        const el = document.elementFromPoint(t.clientX, t.clientY);
        _touchClone.style.display = '';
        const target = el?.closest('.room-widget-card');
        if (target && target !== _touchDragEl) grid.insertBefore(_touchDragEl, target);
    }

    function _onTouchEnd(card) {
        if (!_touchDragEl) return;
        _touchDragEl.style.opacity = '';
        if (_touchClone) { _touchClone.remove(); _touchClone = null; }
        _touchDragEl = null;
        if (global.controlRoomGrid?.persistLayout) global.controlRoomGrid.persistLayout();
    }

    global._roomGridDrag = { bindEvents };

})(window);
