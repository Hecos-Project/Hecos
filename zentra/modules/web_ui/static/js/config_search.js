/**
 * Zentra Config Search Engine v0.2.0
 * Shows matching .card sections inline below the search bar.
 * Does NOT mangle existing panel structures.
 */
(function () {
    'use strict';

    // ── Settings ──────────────────────────────────────────────────────────────
    const SETTINGS_KEY = 'zentra-search-settings';
    const DEFAULTS = {
        case_sensitive:    false,
        highlight_results: true,
        highlight_color:   '#66fcf1',
        auto_navigate:     false,    // navigate on single match
        search_in_values:  false,
        debounce_ms:       280
    };

    let S = loadSettings();
    let _debounce = null;

    function loadSettings() {
        try {
            const raw = localStorage.getItem(SETTINGS_KEY);
            return Object.assign({}, DEFAULTS, raw ? JSON.parse(raw) : {});
        } catch { return Object.assign({}, DEFAULTS); }
    }
    function saveSettings() {
        try { localStorage.setItem(SETTINGS_KEY, JSON.stringify(S)); } catch {}
    }

    // ── Injection ─────────────────────────────────────────────────────────────
    function inject() {
        if (document.getElementById('zentra-search-bar')) return;
        const anchor = document.getElementById('config-filter-tabs');
        if (!anchor) return;

        // --- SEARCH BAR ---
        const bar = document.createElement('div');
        bar.id = 'zentra-search-bar';
        bar.innerHTML = `
            <div style="display:flex;align-items:center;gap:8px;padding:8px 0 6px;">
                <div id="zs-wrapper" style="display:flex;align-items:center;flex:1;background:rgba(255,255,255,0.05);border:1px solid var(--border);border-radius:10px;overflow:hidden;transition:border-color .2s,box-shadow .2s;">
                    <span style="padding:0 10px;font-size:14px;color:var(--muted);user-select:none;">🔍</span>
                    <input id="zs-input" type="text" placeholder="Search configuration... (Ctrl+F)" autocomplete="off"
                        style="flex:1;background:transparent;border:none;outline:none;color:var(--text);font-size:13px;padding:8px 4px;font-family:inherit;">
                    <button id="zs-clear" title="Clear (Esc)" style="display:none;background:none;border:none;cursor:pointer;padding:4px 10px;color:var(--muted);font-size:14px;">✕</button>
                </div>
                <span id="zs-count" style="font-size:11px;color:var(--muted);min-width:70px;text-align:center;"></span>
                <div style="position:relative;">
                    <button id="zs-settings-btn" title="Search Settings" style="background:rgba(255,255,255,0.05);border:1px solid var(--border);border-radius:8px;padding:6px 10px;cursor:pointer;color:var(--muted);font-size:13px;">⚙️</button>
                    <div id="zs-settings-panel" style="display:none;position:absolute;top:calc(100% + 6px);right:0;background:var(--bg2,#111);border:1px solid var(--border);border-radius:12px;padding:16px;z-index:9999;min-width:290px;box-shadow:0 8px 30px rgba(0,0,0,.5);">
                        ${buildSettingsHTML()}
                    </div>
                </div>
            </div>
            <!-- RESULTS PANE -->
            <div id="zs-results" style="display:none;flex-direction:column;gap:10px;margin-bottom:10px;max-height:60vh;overflow-y:auto;padding-right:4px;"></div>
        `;
        anchor.parentNode.insertBefore(bar, anchor);

        // Events
        const inp = document.getElementById('zs-input');
        inp.addEventListener('input', () => {
            clearTimeout(_debounce);
            _debounce = setTimeout(() => runSearch(inp.value.trim()), S.debounce_ms);
            document.getElementById('zs-clear').style.display = inp.value ? 'block' : 'none';
            focusStyle(inp.value.length > 0);
        });
        inp.addEventListener('keydown', e => { if (e.key === 'Escape') clearSearch(); });
        document.getElementById('zs-clear').addEventListener('click', clearSearch);
        document.getElementById('zs-settings-btn').addEventListener('click', e => {
            e.stopPropagation();
            const p = document.getElementById('zs-settings-panel');
            if (!p) return;
            const open = p.style.display !== 'none';
            p.style.display = open ? 'none' : 'block';
            if (!open) p.innerHTML = buildSettingsHTML();
        });
        document.addEventListener('click', e => {
            if (!e.target.closest('#zs-settings-btn') && !e.target.closest('#zs-settings-panel')) {
                const p = document.getElementById('zs-settings-panel');
                if (p) p.style.display = 'none';
            }
        });
        document.addEventListener('keydown', e => {
            if ((e.ctrlKey || e.metaKey) && (e.key === 'f' || e.key === 'k')) {
                e.preventDefault();
                const i = document.getElementById('zs-input');
                if (i) { i.focus(); i.select(); }
            }
        });
    }

    function focusStyle(active) {
        const w = document.getElementById('zs-wrapper');
        if (!w) return;
        w.style.borderColor = active ? 'var(--accent,#66fcf1)' : 'var(--border)';
        w.style.boxShadow   = active ? '0 0 8px rgba(102,252,241,.2)' : 'none';
    }

    // ── Core Search ───────────────────────────────────────────────────────────
    function matchQ(text, q) {
        if (!q) return true;
        return S.case_sensitive ? text.includes(q) : text.toLowerCase().includes(q.toLowerCase());
    }

    function cardText(card) {
        const parts = [];
        if (card.dataset.search) parts.push(card.dataset.search);
        card.querySelectorAll('.card-title,.card-subtitle,label,.toggle-info,.muted,h3,h4').forEach(n => {
            const t = n.textContent.trim();
            if (t) parts.push(t);
        });
        if (S.search_in_values) {
            card.querySelectorAll('input,select,textarea').forEach(n => {
                if (n.placeholder) parts.push(n.placeholder);
                if (n.value && n.type !== 'password') parts.push(n.value);
            });
        }
        return parts.join(' ');
    }

    function panelLabel(panel) {
        // Look for the tab button that corresponds to this panel
        const id = panel.id.replace('tab-', '');
        const btn = document.querySelector(`.tab[onclick*="'${id}'"]`);
        if (btn) return btn.textContent.trim();
        return id;
    }

    function runSearch(q) {
        const resultsEl = document.getElementById('zs-results');
        const countEl   = document.getElementById('zs-count');
        if (!q) { clearSearch(); return; }

        const matchingCards = [];

        document.querySelectorAll('#config-form .panel').forEach(panel => {
            const label = panelLabel(panel);
            panel.querySelectorAll('.card').forEach(card => {
                const text = cardText(card) + ' ' + label;
                if (matchQ(text, q)) {
                    matchingCards.push({ card, panelLabel: label });
                }
            });
        });

        // Build results
        if (matchingCards.length === 0) {
            resultsEl.style.display = 'flex';
            resultsEl.innerHTML = `<div style="padding:12px;text-align:center;color:var(--muted);font-size:13px;">No results for "<strong style='color:var(--text)'>${escQ(q)}</strong>"</div>`;
            countEl.innerHTML = `<span style="color:var(--red)">No results</span>`;
        } else {
            resultsEl.style.display = 'flex';
            resultsEl.innerHTML = matchingCards.map(({ card, panelLabel: pl }) => {
                const title = card.querySelector('.card-title')?.textContent.trim() || pl;
                let cardHTML = card.outerHTML;
                // Highlight query in the clone
                if (S.highlight_results) {
                    const esc = q.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
                    const flags = S.case_sensitive ? 'g' : 'gi';
                    cardHTML = cardHTML.replace(
                        new RegExp(`(${esc})(?=[^<>]*<)`, flags),
                        `<mark style="background:${S.highlight_color};color:#0b0c10;border-radius:3px;padding:0 2px;">$1</mark>`
                    );
                }
                return `
                <div style="border-left:3px solid var(--accent,#66fcf1);padding-left:10px;">
                    <div style="font-size:10px;color:var(--muted);margin-bottom:4px;text-transform:uppercase;letter-spacing:.05em;">📂 ${escQ(pl)}</div>
                    ${cardHTML}
                </div>`;
            }).join('');

            const n = matchingCards.length;
            countEl.innerHTML = `<span style="color:#66fcf1">${n} card${n > 1 ? 's' : ''}</span>`;

            // Auto-navigate: find the panel with the most matching cards
            if (S.auto_navigate && typeof window.showTab === 'function') {
                const tabCounts = {};
                matchingCards.forEach(({ card }) => {
                    const panel = card.closest('.panel');
                    if (panel) tabCounts[panel.id] = (tabCounts[panel.id] || 0) + 1;
                });
                const bestPanelId = Object.entries(tabCounts).sort((a, b) => b[1] - a[1])[0]?.[0];
                if (bestPanelId) window.showTab(bestPanelId.replace('tab-', ''));
            }
        }
    }

    function escQ(str) {
        return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
    }

    function clearSearch() {
        const inp = document.getElementById('zs-input');
        const clr = document.getElementById('zs-clear');
        const res = document.getElementById('zs-results');
        const cnt = document.getElementById('zs-count');
        if (inp) inp.value = '';
        if (clr) clr.style.display = 'none';
        if (res) { res.style.display = 'none'; res.innerHTML = ''; }
        if (cnt) cnt.innerHTML = '';
        focusStyle(false);
    }

    // ── Settings Panel ────────────────────────────────────────────────────────
    function buildSettingsHTML() {
        return `
        <div style="font-size:13px;font-weight:600;color:var(--accent,#66fcf1);margin-bottom:12px;">🔍 Search Settings</div>
        <div style="display:flex;flex-direction:column;gap:12px;">
            ${sRow('Case Sensitive',             'zs-s-case',    S.case_sensitive)}
            ${sRow('Highlight Matches',          'zs-s-hl',      S.highlight_results)}
            ${sRow('Auto-Navigate (most hits)',  'zs-s-nav',     S.auto_navigate)}
            ${sRow('Search in Input Values',     'zs-s-vals',    S.search_in_values)}
            <div style="display:flex;align-items:center;gap:8px;">
                <span style="flex:1;font-size:12px;color:var(--muted);">Highlight Color</span>
                <input type="color" id="zs-s-color" value="${S.highlight_color}" style="width:36px;height:24px;border:none;background:none;cursor:pointer;padding:0;">
            </div>
            <div style="display:flex;align-items:center;gap:8px;">
                <span style="flex:1;font-size:12px;color:var(--muted);">Debounce (ms)</span>
                <input type="number" id="zs-s-debounce" value="${S.debounce_ms}" min="50" max="2000"
                    style="width:70px;background:var(--bg3,#222);border:1px solid var(--border);color:var(--text);border-radius:6px;padding:3px 6px;font-size:11px;">
            </div>
        </div>
        <div style="display:flex;gap:8px;margin-top:14px;">
            <button onclick="window.ZentraSearch.save()" style="flex:1;padding:6px;background:var(--accent,#66fcf1);color:#0b0c10;border:none;border-radius:8px;font-size:12px;font-weight:600;cursor:pointer;">Save</button>
            <button onclick="window.ZentraSearch.reset()" style="flex:1;padding:6px;background:rgba(255,50,50,.15);color:#ff5555;border:1px solid rgba(255,50,50,.3);border-radius:8px;font-size:12px;cursor:pointer;">Reset</button>
        </div>
        <div style="margin-top:8px;font-size:10px;color:var(--muted);text-align:center;">Shortcut: Ctrl+F / Ctrl+K</div>
        `;
    }

    // Renders a toggle row using simple inline HTML (no reliance on .switch/.slider classes)
    function sRow(label, id, val) {
        return `
        <div style="display:flex;align-items:center;gap:8px;">
            <span style="flex:1;font-size:12px;color:var(--muted);">${label}</span>
            <label style="position:relative;display:inline-block;width:38px;height:20px;cursor:pointer;">
                <input type="checkbox" id="${id}" ${val ? 'checked' : ''} style="opacity:0;width:0;height:0;position:absolute;">
                <span id="${id}-track" style="
                    position:absolute;inset:0;border-radius:20px;transition:.2s;cursor:pointer;
                    background:${val ? 'var(--accent,#66fcf1)' : 'rgba(255,255,255,0.15)'};
                "></span>
                <span id="${id}-thumb" style="
                    position:absolute;top:3px;left:${val ? '20px' : '3px'};width:14px;height:14px;
                    border-radius:50%;background:#fff;transition:.2s;
                "></span>
            </label>
        </div>`;
    }

    // ── Public API ─────────────────────────────────────────────────────────────
    window.ZentraSearch = {
        save: function() {
            const g = id => document.getElementById(id);
            S.case_sensitive    = !!g('zs-s-case')?.checked;
            S.highlight_results = !!g('zs-s-hl')?.checked;
            S.auto_navigate     = !!g('zs-s-nav')?.checked;
            S.search_in_values  = !!g('zs-s-vals')?.checked;
            S.highlight_color   = g('zs-s-color')?.value || '#66fcf1';
            S.debounce_ms       = parseInt(g('zs-s-debounce')?.value || 280);
            saveSettings();
            const p = document.getElementById('zs-settings-panel');
            if (p) p.style.display = 'none';
            const q = document.getElementById('zs-input')?.value.trim();
            if (q) runSearch(q);
        },
        reset: function() {
            S = Object.assign({}, DEFAULTS);
            saveSettings();
            const p = document.getElementById('zs-settings-panel');
            if (p) p.innerHTML = buildSettingsHTML();
        },
        clear: clearSearch,
        run: query => { const i = document.getElementById('zs-input'); if (i) { i.value = query; focusStyle(true); } runSearch(query); }
    };

    // Reactive toggle knobs for settings panel
    document.addEventListener('change', e => {
        const id = e.target?.id;
        if (!id || !id.startsWith('zs-s-')) return;
        const val = e.target.checked;
        const track = document.getElementById(id + '-track');
        const thumb = document.getElementById(id + '-thumb');
        if (track) track.style.background = val ? 'var(--accent,#66fcf1)' : 'rgba(255,255,255,0.15)';
        if (thumb) thumb.style.left = val ? '20px' : '3px';
    });

    // ── Boot ──────────────────────────────────────────────────────────────────
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => setTimeout(inject, 700));
    } else {
        setTimeout(inject, 700);
    }
})();
