/**
 * chat_search/cs_jump.js
 * Jump-to-message navigation, safe DOM text highlighting (TreeWalker),
 * and floating In-Chat Match Navigator bar.
 */
(function (global) {
    'use strict';

    let _inChatHits = [];
    let _inChatCursor = 0;
    let _inChatQuery = '';
    let _inChatTerms = [];
    let _inChatSessionId = null;
    let _navBound = false;

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
     * Removes all inline <mark class="cs-inline-mark"> tags cleanly,
     * merging adjacent text nodes back together.
     */
    function clearHighlights() {
        const chatArea = document.getElementById('chat-area');
        if (chatArea) {
            chatArea.querySelectorAll('mark.cs-inline-mark').forEach(mark => {
                const parent = mark.parentNode;
                if (!parent) return;
                parent.replaceChild(document.createTextNode(mark.textContent || ''), mark);
                parent.normalize();
            });
            chatArea.querySelectorAll('.msg.cs-msg-flash').forEach(el => el.classList.remove('cs-msg-flash'));
        }
    }

    function hideInChatBar(alsoClear = true) {
        if (alsoClear) clearHighlights();
        const bar = document.getElementById('cs-inchat-bar');
        if (bar) bar.style.display = 'none';
        _inChatHits = [];
        _inChatCursor = 0;
        _inChatSessionId = null;
    }

    /**
     * Safely highlights matched terms inside text nodes of a message element,
     * skipping buttons, action toolbars, scripts, and styles.
     */
    function _highlightTermsInElement(msgEl, terms) {
        if (!msgEl || !Array.isArray(terms) || !terms.length) return;

        // Build accent-folded match patterns
        const foldedTerms = terms
            .map(t => _foldAccents(t).trim())
            .filter(t => t.length > 0)
            .sort((a, b) => b.length - a.length);
        if (!foldedTerms.length) return;

        const skipSelector = 'script, style, button, .msg-actions, .msg-meta, .msg-header, .msg-footer, .msg-model-badge';
        const walker = document.createTreeWalker(msgEl, NodeFilter.SHOW_TEXT, {
            acceptNode(node) {
                if (!node.nodeValue || !node.nodeValue.trim()) return NodeFilter.FILTER_REJECT;
                const parent = node.parentElement;
                if (!parent) return NodeFilter.FILTER_REJECT;
                if (parent.closest(skipSelector) || parent.tagName === 'MARK') return NodeFilter.FILTER_REJECT;
                return NodeFilter.FILTER_ACCEPT;
            }
        });

        const textNodes = [];
        let n;
        while ((n = walker.nextNode())) {
            textNodes.push(n);
        }

        const pattern = new RegExp(foldedTerms.map(_escapeRegex).join('|'), 'gi');

        textNodes.forEach(node => {
            const raw = node.nodeValue;
            // Fast check via accent-folded string; build index map back to raw UTF-16 indices
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

            pattern.lastIndex = 0;
            const ranges = [];
            let m;
            while ((m = pattern.exec(folded)) !== null) {
                if (!m[0].length) break;
                const startEntry = idxMap[m.index];
                const endEntry = idxMap[m.index + m[0].length - 1];
                if (startEntry && endEntry) {
                    ranges.push([startEntry.start, endEntry.end]);
                }
            }
            if (!ranges.length) return;

            const frag = document.createDocumentFragment();
            let cursor = 0;
            for (const [s, e] of ranges) {
                if (s < cursor) continue;
                if (s > cursor) frag.appendChild(document.createTextNode(raw.slice(cursor, s)));
                const mark = document.createElement('mark');
                mark.className = 'cs-inline-mark';
                mark.textContent = raw.slice(s, e);
                frag.appendChild(mark);
                cursor = e;
            }
            if (cursor < raw.length) frag.appendChild(document.createTextNode(raw.slice(cursor)));
            node.parentNode.replaceChild(frag, node);
        });
    }

    function _findMessageElement(msgIndex, snippet) {
        const chatArea = document.getElementById('chat-area');
        if (!chatArea) return null;

        if (msgIndex !== null && msgIndex !== undefined) {
            const exact = chatArea.querySelector(`.msg[data-hidx="${msgIndex}"]`);
            if (exact) return exact;
        }
        // Fallback: match by nth .msg element
        const allMsgs = chatArea.querySelectorAll('.msg');
        if (typeof msgIndex === 'number' && msgIndex >= 0 && msgIndex < allMsgs.length) {
            return allMsgs[msgIndex];
        }
        // Final fallback: snippet substring match
        if (snippet) {
            const probe = _foldAccents(snippet.replace(/^…|…$/g, '').slice(0, 40));
            if (probe.length >= 6) {
                for (const el of allMsgs) {
                    if (_foldAccents(el.textContent || '').includes(probe)) return el;
                }
            }
        }
        return null;
    }

    function _focusHitAt(index) {
        if (!_inChatHits.length) return;
        _inChatCursor = ((index % _inChatHits.length) + _inChatHits.length) % _inChatHits.length;
        const hit = _inChatHits[_inChatCursor];

        clearHighlights();

        const msgEl = _findMessageElement(hit.msg_index, hit.snippet);
        if (msgEl) {
            _highlightTermsInElement(msgEl, _inChatTerms);
            // Force reflow to restart flash animation cleanly
            msgEl.classList.remove('cs-msg-flash');
            void msgEl.offsetWidth;
            msgEl.classList.add('cs-msg-flash');

            const firstMark = msgEl.querySelector('mark.cs-inline-mark');
            const scrollTarget = firstMark || msgEl;
            if (typeof scrollTarget.scrollIntoView === 'function') {
                scrollTarget.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
        }

        _updateInChatBarUI();
    }

    function _updateInChatBarUI() {
        const bar = document.getElementById('cs-inchat-bar');
        const qEl = document.getElementById('cs-inchat-query');
        const cEl = document.getElementById('cs-inchat-counter');
        const prevBtn = document.getElementById('cs-inchat-prev');
        const nextBtn = document.getElementById('cs-inchat-next');
        if (!bar) return;

        if (!_inChatHits.length) {
            bar.style.display = 'none';
            return;
        }
        if (qEl) qEl.textContent = _inChatQuery;
        if (cEl) cEl.textContent = `${_inChatCursor + 1} / ${_inChatHits.length}`;
        const disableStep = _inChatHits.length <= 1;
        if (prevBtn) prevBtn.disabled = disableStep;
        if (nextBtn) nextBtn.disabled = disableStep;
        bar.style.display = 'flex';
    }

    function _bindInChatBar() {
        if (_navBound) return;
        const prevBtn = document.getElementById('cs-inchat-prev');
        const nextBtn = document.getElementById('cs-inchat-next');
        const closeBtn = document.getElementById('cs-inchat-close');
        const reopenBtn = document.getElementById('cs-inchat-reopen');
        if (!prevBtn && !closeBtn) return;
        _navBound = true;

        if (prevBtn) prevBtn.addEventListener('click', () => _focusHitAt(_inChatCursor - 1));
        if (nextBtn) nextBtn.addEventListener('click', () => _focusHitAt(_inChatCursor + 1));
        if (closeBtn) closeBtn.addEventListener('click', () => hideInChatBar(true));
        if (reopenBtn) {
            reopenBtn.addEventListener('click', () => {
                if (global.HecosChatSearch && typeof global.HecosChatSearch.open === 'function') {
                    global.HecosChatSearch.open({ initialQuery: _inChatQuery });
                }
            });
        }
    }

    async function jumpToResult(targetHit, query, matchedTerms, opts = {}) {
        _bindInChatBar();
        if (!targetHit || !targetHit.session_id) return;

        const targetSid = targetHit.session_id;
        const currentSid = global.chatHistoryState?.activeSessionId;

        if (targetSid !== currentSid && typeof global.activateChatSession === 'function') {
            await global.activateChatSession(targetSid);
            // Allow DOM message rendering to settle
            await new Promise(r => setTimeout(r, 80));
        }

        _inChatQuery = query || '';
        _inChatTerms = Array.isArray(matchedTerms) ? matchedTerms : [];
        _inChatSessionId = targetSid;

        // If the target was a title-only click (no message index), just clear old bar & stop
        if (targetHit.msg_index === null || targetHit.msg_index === undefined) {
            hideInChatBar(true);
            return;
        }

        // Fetch full list of matches inside this session so ↑/↓ jumps through ALL hits in the chat
        let sessionHits = [targetHit];
        try {
            if (global._hecosChatSearchApi && query) {
                const res = await global._hecosChatSearchApi.fetchChatSearch({
                    q: query,
                    scope: 'current',
                    sessionId: targetSid,
                    archived: Boolean(opts.archived),
                    role: opts.role || 'all',
                    date: opts.date || 'all',
                    limit: 120,
                });
                if (res && res.ok && Array.isArray(res.groups) && res.groups[0] && Array.isArray(res.groups[0].hits) && res.groups[0].hits.length) {
                    sessionHits = res.groups[0].hits;
                }
            }
        } catch (_) {}

        _inChatHits = sessionHits;
        const startIdx = Math.max(0, _inChatHits.findIndex(h => h.msg_index === targetHit.msg_index));
        _focusHitAt(startIdx);
    }

    global._hecosChatSearchJump = {
        jumpToResult,
        clearHighlights,
        hideInChatBar,
        isBarOpen: () => {
            const bar = document.getElementById('cs-inchat-bar');
            return Boolean(bar && bar.style.display !== 'none');
        },
        stepNext: () => _focusHitAt(_inChatCursor + 1),
        stepPrev: () => _focusHitAt(_inChatCursor - 1),
        getSessionId: () => _inChatSessionId,
    };

})(window);
