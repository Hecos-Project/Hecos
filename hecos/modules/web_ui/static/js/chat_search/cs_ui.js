/**
 * chat_search/cs_ui.js
 * Hecos Chat Search Modal UI, keyboard navigation (Ctrl+K, ↑/↓, Enter, Tab, Esc),
 * strict Active vs Archive Mode scoping, and live snippet highlighting.
 */
(function (global) {
    'use strict';

    let _isOpen = false;
    let _scope = 'all';        // 'all' | 'current'
    let _role = 'all';         // 'all' | 'user' | 'assistant'
    let _date = 'all';         // 'all' | 'today' | '7d' | '30d'
    let _archivedMode = false; // strictly mirrors chatHistoryState.showArchived on open
    let _query = '';
    let _debounceTimer = null;
    let _lastResults = null;
    let _selectedIdx = -1;
    let _prevFocusEl = null;
    let _initialized = false;

    function _tr(key, fallback) {
        if (typeof global.t === 'function') {
            const v = global.t(key);
            if (v && v !== key) return v;
        }
        if (global.I18N && global.I18N[key]) return global.I18N[key];
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

    function _foldAccents(str) {
        return String(str || '')
            .normalize('NFKD')
            .replace(/[\u0300-\u036f]/g, '')
            .toLowerCase();
    }

    function _escapeRegex(str) {
        return String(str || '').replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    }

    /**
     * Safely HTML-escapes text and wraps accent-insensitive matches in <mark class="cs-mark">.
     */
    function _highlightSafeHtml(text, terms) {
        const raw = String(text || '');
        if (!raw || !Array.isArray(terms) || !terms.length) return _esc(raw);

        const foldedTerms = terms
            .map(t => _foldAccents(t).trim())
            .filter(t => t.length > 0)
            .sort((a, b) => b.length - a.length);
        if (!foldedTerms.length) return _esc(raw);

        const chars = Array.from(raw);
        let folded = '';
        const idxMap = [];
        let rawPos = 0;
        for (const ch of chars) {
            const f = _foldAccents(ch);
            for (let k = 0; k < f.length; k++) {
                folded += f[k];
                idxMap.push({ start: rawPos, end: rawPos + ch.length });
            }
            rawPos += ch.length;
        }

        const rx = new RegExp(foldedTerms.map(_escapeRegex).join('|'), 'gi');
        const ranges = [];
        let m;
        while ((m = rx.exec(folded)) !== null) {
            if (!m[0].length) break;
            const sObj = idxMap[m.index];
            const eObj = idxMap[m.index + m[0].length - 1];
            if (sObj && eObj) ranges.push([sObj.start, eObj.end]);
        }
        if (!ranges.length) return _esc(raw);

        let out = '';
        let cursor = 0;
        for (const [s, e] of ranges) {
            if (s < cursor) continue;
            if (s > cursor) out += _esc(raw.slice(cursor, s));
            out += `<mark class="cs-mark">${_esc(raw.slice(s, e))}</mark>`;
            cursor = e;
        }
        if (cursor < raw.length) out += _esc(raw.slice(cursor));
        return out;
    }

    function _formatDateShort(ts) {
        if (!ts) return '';
        const s = String(ts);
        const day = s.slice(0, 10);
        const hm = s.slice(11, 16);
        const today = new Date().toISOString().slice(0, 10);
        if (day === today) return hm || day;
        return `${day.slice(8, 10)}/${day.slice(5, 7)} ${hm}`.trim();
    }

    // ── Modal State & Rendering ───────────────────────────────────────────────

    function _syncModeBadges() {
        const badge = document.getElementById('cs-mode-badge');
        const banner = document.getElementById('cs-archive-banner');
        const scopeAllLbl = document.getElementById('cs-scope-all-label');
        const isCurrentIncognito = (_scope === 'current' && global.chatHistoryState?.activeMode === 'incognito');

        if (scopeAllLbl) {
            scopeAllLbl.textContent = _archivedMode
                ? _tr('webui_chat_search_scope_archived', 'Archived chats')
                : _tr('webui_chat_search_scope_all', 'All active chats');
        }

        if (banner) {
            banner.style.display = _archivedMode ? 'flex' : 'none';
        }

        if (badge) {
            if (_archivedMode) {
                badge.className = 'cs-mode-badge is-archive';
                badge.innerHTML = `<i class="fas fa-folder-open"></i> ${_esc(_tr('webui_chat_search_badge_archive', 'ARCHIVE'))}`;
                badge.style.display = 'inline-flex';
            } else if (isCurrentIncognito) {
                badge.className = 'cs-mode-badge is-incognito';
                badge.innerHTML = `<i class="fas fa-user-secret"></i> INCOGNITO (RAM)`;
                badge.style.display = 'inline-flex';
            } else {
                badge.style.display = 'none';
            }
        }
    }

    function _syncToolbarUI() {
        const btnAll = document.getElementById('cs-scope-all');
        const btnCur = document.getElementById('cs-scope-current');
        if (btnAll) {
            btnAll.classList.toggle('active', _scope === 'all');
            btnAll.setAttribute('aria-selected', _scope === 'all' ? 'true' : 'false');
        }
        if (btnCur) {
            btnCur.classList.toggle('active', _scope === 'current');
            btnCur.setAttribute('aria-selected', _scope === 'current' ? 'true' : 'false');
        }
        document.querySelectorAll('#cs-role-filters .cs-filter-pill').forEach(b => {
            b.classList.toggle('active', b.dataset.role === _role);
        });
        document.querySelectorAll('#cs-date-filters .cs-filter-pill').forEach(b => {
            b.classList.toggle('active', b.dataset.date === _date);
        });
        _syncModeBadges();
    }

    function _renderEmptyPrompt() {
        const container = document.getElementById('cs-results');
        const statusEl = document.getElementById('cs-status-text');
        if (!container) return;

        const scopeDesc = _archivedMode
            ? _tr('webui_chat_search_hint_archive', 'Search inside archived chats only. Active chats are kept separate.')
            : (_scope === 'current'
                ? _tr('webui_chat_search_hint_current', 'Searching only inside the currently open conversation.')
                : _tr('webui_chat_search_hint_active', 'Searches titles and messages across active conversations (archived and incognito chats excluded).'));

        container.innerHTML = `
            <div class="cs-empty-state">
                <i class="fas ${_archivedMode ? 'fa-folder-open' : 'fa-search'}"></i>
                <div class="cs-empty-title">${_esc(_tr('webui_chat_search_prompt_title', 'Type to search conversations'))}</div>
                <div class="cs-empty-hint">
                    ${_esc(scopeDesc)}<br>
                    ${_esc(_tr('webui_chat_search_hint_quotes', 'Tip: use'))} <code>"exact phrase"</code> ${_esc(_tr('webui_chat_search_hint_quotes_end', 'for exact matches'))}.
                </div>
            </div>
        `;
        if (statusEl) statusEl.textContent = '';
        _selectedIdx = -1;
    }

    function _renderLoading() {
        const statusEl = document.getElementById('cs-status-text');
        if (statusEl) statusEl.innerHTML = `<i class="fas fa-spinner fa-spin"></i> ${_esc(_tr('webui_chat_search_searching', 'Searching...'))}`;
    }

    function _renderResults(data) {
        const container = document.getElementById('cs-results');
        const statusEl = document.getElementById('cs-status-text');
        if (!container) return;

        _lastResults = data;
        const groups = Array.isArray(data.groups) ? data.groups : [];
        const terms = Array.isArray(data.matched_terms) ? data.matched_terms : [];

        if (!groups.length) {
            container.innerHTML = `
                <div class="cs-empty-state">
                    <i class="fas fa-search-minus"></i>
                    <div class="cs-empty-title">${_esc(_tr('webui_chat_search_no_results', 'No matching messages found'))}</div>
                    <div class="cs-empty-hint">${_esc(_tr('webui_chat_search_try_broader', 'Try different keywords, check the scope (All vs Current chat), or relax filters.'))}</div>
                </div>
            `;
            if (statusEl) {
                statusEl.textContent = `0 ${_tr('webui_chat_search_results_word', 'results')} · ${data.elapsed_ms ?? 0} ms`;
            }
            _selectedIdx = -1;
            return;
        }

        const userLabel = _tr('webui_chat_search_role_user', 'You');
        let html = '';
        let flatIdx = 0;

        groups.forEach((g, gIdx) => {
            const icon = g.is_incognito ? '🕵️' : (g.is_archived ? '📂' : '💬');
            const titleHtml = _highlightSafeHtml(g.title || 'Chat', terms);
            const dateStr = _formatDateShort(g.updated_at);
            const countText = g.match_count > 0
                ? `${g.match_count} ${g.match_count === 1 ? 'match' : 'matches'}`
                : _tr('webui_chat_search_title_match', 'title');

            const isHeaderSelectable = (!g.hits || !g.hits.length);
            const headerNavAttr = isHeaderSelectable
                ? `data-cs-nav="${flatIdx++}" data-group-idx="${gIdx}" data-hit-idx="-1"`
                : `data-group-idx="${gIdx}" data-hit-idx="-1"`;

            html += `
                <div class="cs-group">
                    <div class="cs-group-header" ${headerNavAttr}>
                        <div class="cs-group-title-wrap">
                            <span class="cs-group-icon">${icon}</span>
                            <span class="cs-group-title">${titleHtml}</span>
                        </div>
                        <div class="cs-group-meta">
                            <span>${_esc(dateStr)}</span>
                            <span class="cs-group-count">${_esc(countText)}</span>
                        </div>
                    </div>
            `;

            (g.hits || []).forEach((h, hIdx) => {
                const isUser = h.role === 'user';
                const roleBadge = isUser
                    ? `<span class="cs-role-tag role-user">${_esc(userLabel)}</span>`
                    : `<span class="cs-role-tag role-assistant">AI</span>`;
                const thinkTag = h.in_thinking ? `<span class="cs-think-tag">&lt;think&gt;</span>` : '';
                const snippetHtml = _highlightSafeHtml(h.snippet || '', terms);

                html += `
                    <div class="cs-hit-row" role="option"
                         data-cs-nav="${flatIdx++}"
                         data-group-idx="${gIdx}"
                         data-hit-idx="${hIdx}">
                        <div class="cs-hit-meta">
                            ${roleBadge}
                            ${thinkTag}
                            <span>${_esc(_formatDateShort(h.timestamp))}</span>
                        </div>
                        <div class="cs-hit-snippet">${snippetHtml}</div>
                    </div>
                `;
            });

            html += `</div>`;
        });

        container.innerHTML = html;

        const resWord = data.total_matches === 1
            ? _tr('webui_chat_search_result_word', 'result')
            : _tr('webui_chat_search_results_word', 'results');
        const chatWord = data.total_sessions === 1 ? 'chat' : 'chats';
        if (statusEl) {
            statusEl.textContent = `${data.total_matches} ${resWord} (${data.total_sessions} ${chatWord}) · ${data.elapsed_ms ?? 0} ms`;
        }

        _setSelectedIndex(0);
    }

    function _getNavItems() {
        const container = document.getElementById('cs-results');
        return container ? Array.from(container.querySelectorAll('[data-cs-nav]')) : [];
    }

    function _setSelectedIndex(idx) {
        const items = _getNavItems();
        if (!items.length) {
            _selectedIdx = -1;
            return;
        }
        _selectedIdx = ((idx % items.length) + items.length) % items.length;
        items.forEach((el, i) => {
            const active = i === _selectedIdx;
            el.classList.toggle('cs-item-active', active);
            el.setAttribute('aria-selected', active ? 'true' : 'false');
            if (active && typeof el.scrollIntoView === 'function') {
                el.scrollIntoView({ block: 'nearest' });
            }
        });
    }

    function _activateItem(el) {
        if (!el || !_lastResults || !Array.isArray(_lastResults.groups)) return;
        const gIdx = parseInt(el.dataset.groupIdx, 10);
        const hIdx = parseInt(el.dataset.hitIdx, 10);
        const group = _lastResults.groups[gIdx];
        if (!group) return;

        const hit = (hIdx >= 0 && group.hits && group.hits[hIdx])
            ? group.hits[hIdx]
            : { session_id: group.session_id, msg_index: null, snippet: '' };

        const q = _query;
        const terms = _lastResults.matched_terms || [];
        const opts = { archived: _archivedMode, role: _role, date: _date };

        close();
        if (global._hecosChatSearchJump) {
            global._hecosChatSearchJump.jumpToResult(hit, q, terms, opts);
        }
    }

    // ── Query Execution ───────────────────────────────────────────────────────

    function _scheduleSearch(immediate = false) {
        clearTimeout(_debounceTimer);
        const q = _query.trim();
        const clearBtn = document.getElementById('cs-clear-btn');
        if (clearBtn) clearBtn.style.display = q ? 'inline-flex' : 'none';

        if (!q) {
            if (global._hecosChatSearchApi) global._hecosChatSearchApi.abortPendingSearch();
            _lastResults = null;
            _renderEmptyPrompt();
            return;
        }

        const run = async () => {
            _renderLoading();
            try {
                const sid = global.chatHistoryState?.activeSessionId || null;
                const data = await global._hecosChatSearchApi.fetchChatSearch({
                    q,
                    scope: _scope,
                    sessionId: sid,
                    archived: _archivedMode,
                    role: _role,
                    date: _date,
                    limit: _scope === 'current' ? 100 : 50,
                });
                if (!data || !data.ok) throw new Error(data?.error || 'Search error');
                if (_isOpen) _renderResults(data);
            } catch (err) {
                if (err && err.name === 'AbortError') return;
                const statusEl = document.getElementById('cs-status-text');
                if (statusEl) statusEl.textContent = `Error: ${err?.message || 'Search failed'}`;
            }
        };

        if (immediate) {
            run();
        } else {
            _debounceTimer = setTimeout(run, 170);
        }
    }

    // ── Open / Close / Toggle ─────────────────────────────────────────────────

    function open(opts = {}) {
        if (!_initialized) _init();
        const backdrop = document.getElementById('cs-modal-backdrop');
        const input = document.getElementById('cs-search-input');
        if (!backdrop || !input) return;

        _prevFocusEl = document.activeElement;
        _archivedMode = Boolean(global.chatHistoryState?.showArchived);
        if (opts.scope === 'all' || opts.scope === 'current') {
            _scope = opts.scope;
        } else {
            _scope = 'all';
        }
        if (typeof opts.initialQuery === 'string') {
            _query = opts.initialQuery;
            input.value = _query;
        }

        _isOpen = true;
        backdrop.style.display = 'flex';
        backdrop.setAttribute('aria-hidden', 'false');
        _syncToolbarUI();

        if (_query.trim()) {
            _scheduleSearch(true);
        } else {
            _renderEmptyPrompt();
        }

        setTimeout(() => {
            input.focus();
            if (input.value) input.select();
        }, 20);
    }

    function close() {
        const backdrop = document.getElementById('cs-modal-backdrop');
        if (!backdrop) return;
        _isOpen = false;
        clearTimeout(_debounceTimer);
        if (global._hecosChatSearchApi) global._hecosChatSearchApi.abortPendingSearch();
        backdrop.style.display = 'none';
        backdrop.setAttribute('aria-hidden', 'true');
        if (_prevFocusEl && typeof _prevFocusEl.focus === 'function' && document.contains(_prevFocusEl)) {
            try { _prevFocusEl.focus({ preventScroll: true }); } catch (_) {}
        }
    }

    function toggle(opts = {}) {
        if (_isOpen) close();
        else open(opts);
    }

    // ── Event Binding ─────────────────────────────────────────────────────────

    function _init() {
        if (_initialized) return;
        const backdrop = document.getElementById('cs-modal-backdrop');
        const input = document.getElementById('cs-search-input');
        const clearBtn = document.getElementById('cs-clear-btn');
        const closeBtn = document.getElementById('cs-close-btn');
        const resultsEl = document.getElementById('cs-results');
        if (!backdrop || !input) return;
        _initialized = true;

        backdrop.addEventListener('mousedown', (e) => {
            if (e.target === backdrop) close();
        });
        if (closeBtn) closeBtn.addEventListener('click', close);
        if (clearBtn) {
            clearBtn.addEventListener('click', () => {
                _query = '';
                input.value = '';
                _scheduleSearch(true);
                input.focus();
            });
        }

        input.addEventListener('input', () => {
            _query = input.value || '';
            _scheduleSearch(false);
        });

        // Scope buttons
        document.querySelectorAll('.cs-scope-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                _scope = btn.dataset.scope === 'current' ? 'current' : 'all';
                _syncToolbarUI();
                _scheduleSearch(true);
                input.focus();
            });
        });

        // Role filters
        document.querySelectorAll('#cs-role-filters .cs-filter-pill').forEach(btn => {
            btn.addEventListener('click', () => {
                _role = btn.dataset.role || 'all';
                _syncToolbarUI();
                _scheduleSearch(true);
                input.focus();
            });
        });

        // Date filters
        document.querySelectorAll('#cs-date-filters .cs-filter-pill').forEach(btn => {
            btn.addEventListener('click', () => {
                _date = btn.dataset.date || 'all';
                _syncToolbarUI();
                _scheduleSearch(true);
                input.focus();
            });
        });

        // Delegated result clicks & hover sync
        if (resultsEl) {
            resultsEl.addEventListener('click', (e) => {
                const target = e.target.closest('[data-group-idx]');
                if (target) _activateItem(target);
            });
            resultsEl.addEventListener('mousemove', (e) => {
                const navItem = e.target.closest('[data-cs-nav]');
                if (!navItem) return;
                const idx = parseInt(navItem.dataset.csNav, 10);
                if (!Number.isNaN(idx) && idx !== _selectedIdx) {
                    _setSelectedIndex(idx);
                }
            });
        }

        // Global Capture Keydown: Ctrl+K fallback + modal keyboard navigation
        document.addEventListener('keydown', (e) => {
            // Let HKS handle customizable 'ui.chat_search' when registered; keep Ctrl+K fallback otherwise
            const hksManagesSearch = Boolean(
                global.HKS &&
                global.HKS_BINDINGS &&
                global.HKS_ACTIONS &&
                typeof global.HKS_ACTIONS.find === 'function' &&
                global.HKS_ACTIONS.find('ui.chat_search')
            );
            if (!hksManagesSearch && (e.ctrlKey || e.metaKey) && !e.altKey && !e.shiftKey && e.key.toLowerCase() === 'k') {
                if (!_isOpen && document.querySelector('#preset-manager-panel.open, #hks-modal.open, .cr-modal-backdrop')) {
                    return;
                }
                e.preventDefault();
                e.stopImmediatePropagation();
                toggle();
                return;
            }

            if (_isOpen) {
                if (e.key === 'Escape') {
                    e.preventDefault();
                    e.stopImmediatePropagation();
                    close();
                    return;
                }
                if (e.key === 'ArrowDown') {
                    e.preventDefault();
                    e.stopPropagation();
                    _setSelectedIndex(_selectedIdx + 1);
                    return;
                }
                if (e.key === 'ArrowUp') {
                    e.preventDefault();
                    e.stopPropagation();
                    _setSelectedIndex(_selectedIdx - 1);
                    return;
                }
                if (e.key === 'Tab') {
                    e.preventDefault();
                    e.stopPropagation();
                    _scope = (_scope === 'all') ? 'current' : 'all';
                    _syncToolbarUI();
                    _scheduleSearch(true);
                    return;
                }
                if (e.key === 'Enter') {
                    const items = _getNavItems();
                    const chosen = items[_selectedIdx] || items[0];
                    if (chosen) {
                        e.preventDefault();
                        e.stopImmediatePropagation();
                        _activateItem(chosen);
                    }
                    return;
                }
                return;
            }

            // Escape while in-chat highlight bar is open (and focus not in another modal) -> clear highlights
            if (e.key === 'Escape' && global._hecosChatSearchJump?.isBarOpen()) {
                if (!document.querySelector('#preset-manager-panel.open, #hks-modal.open, .cr-modal-backdrop')) {
                    global._hecosChatSearchJump.hideInChatBar(true);
                }
            }
        }, { capture: true });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', _init);
    } else {
        _init();
    }

    global.HecosChatSearch = {
        open,
        close,
        toggle,
        isOpen: () => _isOpen,
        clearHighlights: () => global._hecosChatSearchJump?.hideInChatBar(true),
    };

})(window);
