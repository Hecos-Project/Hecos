/**
 * Quick Links — Sidebar Widget Client Logic
 * Manages CRUD operations for user-pinned links in the chat sidebar.
 */
(function () {
    'use strict';

    const API = '/api/ext/quick_links';
    const COLLAPSED_KEY = 'hecos-ql-collapsed';

    // ── State ────────────────────────────────────────────────────────────────

    let _links = [];
    let _collapsed = localStorage.getItem(COLLAPSED_KEY) === '1';

    // ── Bootstrap ────────────────────────────────────────────────────────────

    function qlInit() {
        _applyCollapsed(_collapsed, false);
        _fetchLinks();
    }

    // ── API Calls ────────────────────────────────────────────────────────────

    async function _fetchLinks() {
        try {
            const r = await fetch(API);
            if (!r.ok) return;
            const data = await r.json();
            _links = data.links || [];
            _render();
        } catch (e) {
            console.warn('[QuickLinks] fetch error:', e);
        }
    }

    async function _addLink(label, url, icon, target) {
        const r = await fetch(API, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ label, url, icon, target })
        });
        const data = await r.json();
        if (data.ok) {
            _links.push(data.link);
            _render();
        } else {
            alert('Error: ' + (data.error || 'unknown'));
        }
    }

    async function _deleteLink(id) {
        const r = await fetch(`${API}/${id}`, { method: 'DELETE' });
        const data = await r.json();
        if (data.ok) {
            _links = _links.filter(l => l.id !== id);
            _render();
        }
    }

    // ── Render ───────────────────────────────────────────────────────────────

    function _render() {
        const list = document.getElementById('ql-list');
        if (!list) return;

        if (_links.length === 0) {
            list.innerHTML = '<li class="ql-empty">No links yet — add one below</li>';
            return;
        }

        list.innerHTML = _links.map(l => `
      <li class="ql-item" data-id="${_esc(l.id)}">
        <a class="ql-link"
           href="${_esc(l.url)}"
           target="${l.target === '_self' ? '_self' : '_blank'}"
           rel="noopener noreferrer"
           title="${_esc(l.url)}">
          <span class="ql-link-icon">${_esc(l.icon || '🔗')}</span>
          <span class="ql-link-label">${_esc(l.label)}</span>
        </a>
        <button class="ql-delete-btn"
                onclick="qlDelete('${_esc(l.id)}')"
                title="Remove this link">✕</button>
      </li>
    `).join('');
    }

    function _esc(str) {
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    // ── Collapse / Expand ────────────────────────────────────────────────────

    function _applyCollapsed(yes, animate = true) {
        const body    = document.getElementById('ql-body');
        const chevron = document.getElementById('ql-chevron');
        if (!body || !chevron) return;

        if (yes) {
            body.style.display = 'none';
            chevron.classList.add('collapsed');
        } else {
            body.style.display = '';
            chevron.classList.remove('collapsed');
        }
    }

    // ── Form helpers ─────────────────────────────────────────────────────────

    function _clearForm() {
        const icon   = document.getElementById('ql-input-icon');
        const label  = document.getElementById('ql-input-label');
        const url    = document.getElementById('ql-input-url');
        const same   = document.getElementById('ql-input-same-tab');
        if (icon)  icon.value   = '';
        if (label) label.value  = '';
        if (url)   url.value    = '';
        if (same)  same.checked = false;
    }

    // ── Public API (called from inline HTML onclick) ─────────────────────────

    window.qlToggle = function () {
        _collapsed = !_collapsed;
        localStorage.setItem(COLLAPSED_KEY, _collapsed ? '1' : '0');
        _applyCollapsed(_collapsed);
    };

    window.qlOpenForm = function () {
        const form = document.getElementById('ql-form');
        const btn  = document.getElementById('ql-add-btn');
        if (!form) return;
        _clearForm();
        form.style.display = '';
        btn.style.display  = 'none';
        document.getElementById('ql-input-label')?.focus();
    };

    window.qlCloseForm = function () {
        const form = document.getElementById('ql-form');
        const btn  = document.getElementById('ql-add-btn');
        if (form) form.style.display = 'none';
        if (btn)  btn.style.display  = '';
    };

    window.qlSaveNew = async function () {
        const icon   = (document.getElementById('ql-input-icon')?.value  || '🔗').trim();
        const label  = (document.getElementById('ql-input-label')?.value || '').trim();
        const url    = (document.getElementById('ql-input-url')?.value   || '').trim();
        const same   = document.getElementById('ql-input-same-tab')?.checked;

        if (!label) { document.getElementById('ql-input-label')?.focus(); return; }
        if (!url)   { document.getElementById('ql-input-url')?.focus();   return; }

        await _addLink(label, url, icon, same ? '_self' : '_blank');
        qlCloseForm();
    };

    window.qlDelete = async function (id) {
        await _deleteLink(id);
    };

    // ── Allow Enter key in form ──────────────────────────────────────────────

    document.addEventListener('keydown', function (e) {
        const form = document.getElementById('ql-form');
        if (!form || form.style.display === 'none') return;
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            window.qlSaveNew();
        }
        if (e.key === 'Escape') {
            window.qlCloseForm();
        }
    });

    // ── Init on DOM ready ────────────────────────────────────────────────────

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', qlInit);
    } else {
        qlInit();
    }

})();
