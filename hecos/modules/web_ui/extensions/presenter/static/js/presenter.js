/**
 * Hecos Presenter — Full Featured Extension JS (Core Module)
 * ─────────────────────────────────────────────────────────────────────
 * Unified notification system: toast, briefing, live commentary, feed.
 * Container (#hbs-presenter-embedded) lives in chat.html outside chat-area
 * so it survives SPA navigation.
 *
 * PUBLIC API — window.Presenter:
 *   .notify({ type, text, icon, title, duration })  — unified entry point
 *   .toast(type, text)                              — shorthand for action_confirm
 *   .show(message, title, duration)                 — legacy show
 *   .hide()                                         — hide overlay
 *   .setEnabled(bool)                               — enable/disable
 *   .setDisplayMode(mode)                           — 'embedded'|'collapsed'|'overlay'|'hidden'
 *   .briefing()                                     — fetch and display system briefing
 *   .getFeed()                                      — returns recent feed entries
 * ─────────────────────────────────────────────────────────────────────
 */

(function() {
    'use strict';

    const STATE = window.HBSPresenterState;
    const UI = window.HBSPresenterUI;

    // ── Core Show ────────────────────────────────────────────────────
    function _show(message, title, duration, type, timestamp) {
        if (!STATE.presenterEnabled) return;

        let target;
        if (STATE.displayMode === 'overlay') {
            target = UI.getOverlay();
        } else {
            target = UI.getEmbedded();
        }
        if (!target) return;

        UI.ensureBuilt(target);

        // Auto-expand when message arrives
        if (target.classList.contains('collapsed')) {
            target.classList.remove('collapsed');
            const icon = target.querySelector('#hbs-presenter-toggle i');
            if (icon) { icon.classList.remove('fa-chevron-down'); icon.classList.add('fa-chevron-up'); }
        }

        const msgEl = target.querySelector('.hbs-presenter-body');
        const titleEl = target.querySelector('.hbs-presenter-title');
        const avatarEl = target.querySelector('.hbs-presenter-avatar i');

        if (titleEl) titleEl.innerText = title || 'Presenter';
        if (avatarEl && type) {
            const m = UI.resolveMeta(type);
            avatarEl.className = m.icon;
            avatarEl.closest('.hbs-presenter-avatar').style.background = `linear-gradient(135deg, ${m.color}99, ${m.color}55)`;
            avatarEl.closest('.hbs-presenter-avatar').title = m.tooltip || type;
        }

        // Append line instead of replacing
        if (msgEl) {
            const line = document.createElement('div');
            line.className = 'hbs-presenter-line';
            line.dataset.logType = type || 'system_info';
            line.style.animation = 'presenterFadeIn 0.3s ease';
            
            const dateObj = timestamp ? new Date(timestamp) : new Date();
            const timeStr = dateObj.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit', second:'2-digit'});
            line.innerHTML = `<span style="font-size: 10px; color: var(--muted); margin-right: 8px; opacity: 0.7;">[${timeStr}]</span> ${message}`;
            
            // Apply active filters and search
            const hidden = STATE.presenterHiddenTypes.has(line.dataset.logType);
            const searchHidden = STATE.presenterSearchQuery && !line.textContent.toLowerCase().includes(STATE.presenterSearchQuery.toLowerCase());
            if (hidden || searchHidden) line.style.display = 'none';
            
            msgEl.appendChild(line);
            
            // Auto scroll to bottom
            msgEl.scrollTop = msgEl.scrollHeight;
            
            // Trim feed lines based on UI max settings
            if (window.Presenter.trimFeed) {
                window.Presenter.trimFeed();
            }
            _saveCurrentSessionFeed();
        }

        if (localStorage.getItem('hecos_presenter_active') !== 'false' || STATE.displayMode === 'overlay') {
            target.classList.add('active');
            if (STATE.displayMode !== 'overlay') {
                localStorage.setItem('hecos_presenter_active', 'true');
            }
        }

        clearTimeout(STATE.hideTimeout);
        if (duration > 0 && STATE.displayMode === 'overlay') {
            STATE.hideTimeout = setTimeout(() => _hide(), duration);
        }
    }

    function _hide() {
        const overlay = UI.getOverlay();
        if (overlay) overlay.classList.remove('active');
    }

    // ── Session Feed Cache ───────────────────────────────────────────
    function _saveCurrentSessionFeed(targetSid) {
        const sid = targetSid || STATE.currentSessionId || localStorage.getItem('hecos_active_session_id') || 'global';
        if (!sid) return;
        const emb = UI.getEmbedded();
        if (!emb) return;
        const msgEl = emb.querySelector('.hbs-presenter-body');
        if (!msgEl) return;
        
        STATE.sessionFeeds = STATE.sessionFeeds || {};
        const feedData = {
            html: msgEl.innerHTML,
            history: [...STATE.feedHistory],
            timestamp: Date.now()
        };
        STATE.sessionFeeds[sid] = feedData;
        try {
            sessionStorage.setItem('hecos_pfeed_' + sid, JSON.stringify(feedData));
        } catch (e) {}
    }

    function _restoreSessionFeed(sid) {
        if (!sid) return false;
        const emb = UI.getEmbedded();
        if (!emb) return false;
        const msgEl = emb.querySelector('.hbs-presenter-body');
        if (!msgEl) return false;

        let feedData = STATE.sessionFeeds && STATE.sessionFeeds[sid];
        if (!feedData || !feedData.html) {
            try {
                const raw = sessionStorage.getItem('hecos_pfeed_' + sid);
                if (raw) {
                    feedData = JSON.parse(raw);
                    STATE.sessionFeeds = STATE.sessionFeeds || {};
                    STATE.sessionFeeds[sid] = feedData;
                }
            } catch (e) {}
        }

        if (feedData && typeof feedData.html === 'string' && feedData.html.trim().length > 0) {
            msgEl.innerHTML = feedData.html;
            STATE.feedHistory = Array.isArray(feedData.history) ? [...feedData.history] : [];
            msgEl.scrollTop = msgEl.scrollHeight;
            return true;
        }
        return false;
    }

    // ── Feed ─────────────────────────────────────────────────────────
    function _addToFeed(entry) {
        STATE.feedHistory.push(entry);
        if (STATE.feedHistory.length > STATE.MAX_FEED) STATE.feedHistory.shift();
    }

    // ── UNIFIED NOTIFICATION API ─────────────────────────────────────
    function _notify(opts) {
        if (!STATE.presenterEnabled) return;
        const type     = opts.type || 'system_info';
        const rawText  = opts.text || '';
        const title    = opts.title || 'Presenter';
        const duration = opts.duration !== undefined ? opts.duration : 6000;
        const persist  = opts.persist !== undefined ? opts.persist : true;

        let thinkText = null;
        let displayHtml = rawText;
        
        // Update stats counters
        if (window.HBSPresenterStats) {
            window.HBSPresenterStats.increment(type);
        }
        
        // Extract <think> tag if present
        const thinkMatch = displayHtml.match(/<think>([\s\S]*?)<\/think>/i);
        if (thinkMatch) {
            thinkText = thinkMatch[1].trim();
            displayHtml = displayHtml.replace(/<think>[\s\S]*?<\/think>/gi, '').trim();
        } else if (displayHtml.includes('</think>')) {
            // Bare </think> tag
            const parts = displayHtml.split('</think>');
            thinkText = parts[0].trim();
            displayHtml = parts.slice(1).join('').trim();
        }

        const timestamp = opts.timestamp || new Date().toISOString();
        const formatted = UI.formatMessage(type, displayHtml, thinkText);
        _show(formatted, title, duration, type, timestamp);

        if (persist) {
            // Keep the original text with tags for the feed history
            _addToFeed({ timestamp, type, text: rawText, title });
        }
    }

    // ── System Briefing ──────────────────────────────────────────────
    async function _briefing() {
        if (window._briefingInProgress) return;
        window._briefingInProgress = true;
        try {
            const res = await fetch('/api/ext/presenter/briefing');
            const data = await res.json();
            if (data.ok && data.items && data.items.length > 0) {
                let delay = 0;
                for (const item of data.items) {
                    setTimeout(() => {
                        _notify({
                            type: item.type || 'system_info',
                            text: item.text,
                            title: 'System Briefing',
                            duration: 0,
                            persist: false
                        });
                    }, delay);
                    delay += 600;
                }
                _updatePlaybookStatus(false);
            }
        } catch (e) {
            console.warn('[Presenter] Briefing fetch failed:', e);
        } finally {
            setTimeout(() => { window._briefingInProgress = false; }, 3000);
        }
    }

    // ── Playbook Status & Header Pill ─────────────────────────────────
    async function _updatePlaybookStatus(notify = false) {
        try {
            const chatId = (window.chatHistoryState && window.chatHistoryState.activeSessionId) ||
                           localStorage.getItem('hecos_active_session_id') ||
                           (window.privacy_manager && typeof window.privacy_manager.get_session_id === 'function' ? window.privacy_manager.get_session_id() : 'default') ||
                           'default';
            const res = await fetch(`/api/ext/presenter/playbook_status?chat_id=${encodeURIComponent(chatId)}`);
            const data = await res.json();
            if (data.ok) {
                if (UI.renderPlaybookPill) {
                    UI.renderPlaybookPill(data);
                }
                
                if (notify) {
                    if (data.has_active && data.active_playbook) {
                        const pb = data.active_playbook;
                        const tabList = (pb.tabs || [])
                            .filter(t => t.enabled !== false)
                            .map(t => `${t.name} [${(t.target || 'presenter').toUpperCase()}]`)
                            .join('  •  ');
                        
                        _notify({
                            type: 'system_status',
                            text: `📖 Playbook active: <strong>${pb.name}</strong> (${pb.mode.toUpperCase()}) — ${pb.enabled_tabs}/${pb.total_tabs} tabs enabled`,
                            title: 'Presenter',
                            duration: 7000,
                            persist: true
                        });
                        const sim = data.simulation || {};
                        function _getRoleStr(val, fallback) {
                            if (typeof val === 'string' && val.trim()) return val.trim();
                            if (val && typeof val === 'object') {
                                if (typeof val.role === 'string' && val.role.trim()) return val.role.trim();
                                if (typeof val.name === 'string' && val.name.trim()) return val.name.trim();
                            }
                            return fallback;
                        }
                        const effUser = _getRoleStr(sim.user_role, _getRoleStr(pb.effective_user_role, _getRoleStr((pb.mission || {}).user_role, 'User')));
                        const effChat = _getRoleStr(sim.chat_role, _getRoleStr(pb.effective_chat_role, _getRoleStr((pb.mission || {}).chat_role, 'Chat AI')));
                        const isSwapped = !!sim.swapped;
                        _notify({
                            type: 'system_info',
                            text: `🎭 Simulation Roles: <strong>You:</strong> ${effUser} • <strong>Chat AI:</strong> ${effChat}${isSwapped ? ' <em>(⇄ Swapped)</em>' : ''}`,
                            title: 'Presenter',
                            duration: 7000,
                            persist: true
                        });
                        if (tabList) {
                            _notify({
                                type: 'system_info',
                                text: `🎯 Playbook Targets: ${tabList}`,
                                title: 'Presenter',
                                duration: 7000,
                                persist: true
                            });
                        }
                    } else if (data.installed) {
                        _notify({
                            type: 'system_info',
                            text: `📖 Playbooks inactive: all playbooks disabled.`,
                            title: 'Presenter',
                            duration: 5000,
                            persist: true
                        });
                    }
                }
            }
        } catch (e) {
            console.debug('[Presenter] Playbook status check error:', e);
        }
    }

    // ── Init overlay container ───────────────────────────────────────
    function _initOverlay() {
        if (document.getElementById('hbs-presenter-overlay')) return;
        const el = document.createElement('div');
        el.id = 'hbs-presenter-overlay';
        document.body.appendChild(el);
        UI.ensureBuilt(el);
    }

    // ── Init embedded container ──────────────────────────────────────
    function _initEmbedded() {
        const el = UI.getEmbedded();
        if (el) {
            UI.ensureBuilt(el);
            // Restore active state
            if (localStorage.getItem('hecos_presenter_active') === 'true') {
                el.classList.add('active');
            }
        }
    }

    // ── Public API ───────────────────────────────────────────────────
    const Presenter = {
        notify: _notify,

        saveUIState: function() {
            const emb = UI.getEmbedded();
            if (!emb) return;
            const cb = emb.querySelector('#hbs-presenter-remember-size');
            const linesInput = emb.querySelector('#hbs-presenter-max-lines');
            const bodyEl = emb.querySelector('.hbs-presenter-body');
            
            if (cb && linesInput && bodyEl) {
                const state = {
                    save: cb.checked,
                    lines: parseInt(linesInput.value) || 4,
                    height: cb.checked ? bodyEl.offsetHeight : ""
                };
                localStorage.setItem('hecos_presenter_ui_state', JSON.stringify(state));
            }
        },
        
        trimFeed: function() {
            const emb = UI.getEmbedded();
            if (!emb) return;
            const msgEl = emb.querySelector('.hbs-presenter-body');
            if (!msgEl) return;
            
            // Hard limit physical DOM nodes to MAX_FEED to prevent DOM bloat
            while (msgEl.children.length > STATE.MAX_FEED) {
                msgEl.removeChild(msgEl.firstChild);
            }
        },

        setLines: function(num) {
            const emb = UI.getEmbedded();
            if (!emb) return;
            const linesInput = emb.querySelector('#hbs-presenter-max-lines');
            if (linesInput) {
                linesInput.value = num;
                this.saveUIState();
                this.adaptHeight();
            }
        },

        toast: function(type, text, duration) {
            _notify({
                type: type || 'action_confirm',
                text: text,
                title: 'Presenter',
                duration: duration || 3000,
                persist: type !== 'action_confirm'
            });
        },

        // Legacy
        show: function(message, title, duration) {
            _show(message, title || 'Presenter', duration || 6000, null);
        },

        hide: _hide,

        setEnabled: function(enabled) {
            STATE.presenterEnabled = enabled;
            window._presenterEnabled = enabled; // expose for toolbar check
            if (!enabled) {
                _hide();
                const emb = UI.getEmbedded();
                if (emb) emb.classList.remove('active');
                UI.renderDisabledState();
            } else {
                UI.clearDisabledState();
            }
        },

        setDisplayMode: function(mode) {
            STATE.displayMode = mode;
            const emb = UI.getEmbedded();
            const ov = UI.getOverlay();

            if (mode === 'embedded') {
                if (emb) { emb.classList.remove('collapsed'); }
                if (ov) ov.classList.remove('active');
            } else if (mode === 'collapsed') {
                if (emb) {
                    emb.classList.add('collapsed');
                    const icon = emb.querySelector('#hbs-presenter-toggle i');
                    if (icon) { icon.classList.remove('fa-chevron-up'); icon.classList.add('fa-chevron-down'); }
                }
                if (ov) ov.classList.remove('active');
            } else if (mode === 'overlay') {
                if (emb) emb.classList.remove('active');
            } else if (mode === 'hidden') {
                _hide();
                if (emb) emb.classList.remove('active');
            }
        },

        clear: function() {
            STATE.feedHistory.length = 0;
            const emb = UI.getEmbedded();
            if (emb) {
                const msgEl = emb.querySelector('.hbs-presenter-body');
                if (msgEl) msgEl.innerHTML = '';
            }
            if (window.HBSPresenterStats) {
                window.HBSPresenterStats.clear();
            }
        },

        adaptHeight: function() {
            const emb = UI.getEmbedded();
            if (!emb) return;
            const linesInput = emb.querySelector('#hbs-presenter-max-lines');
            const bodyEl = emb.querySelector('.hbs-presenter-body');
            if (bodyEl) {
                const maxLines = linesInput ? (parseInt(linesInput.value) || 4) : 4;
                bodyEl.style.height = (maxLines * 26 + 12) + 'px';
                this.saveUIState();
            }
        },

        toggleAdvanced: function() {
            const panel = document.getElementById('hbs-presenter-advanced');
            const btn = document.getElementById('hbs-presenter-advanced-toggle');
            if (!panel) return;
            const isOpen = panel.style.display !== 'none';
            panel.style.display = isOpen ? 'none' : 'block';
            if (btn) {
                btn.style.background = isOpen ? 'rgba(255,255,255,0.07)' : 'rgba(102,252,241,0.12)';
                btn.style.borderColor = isOpen ? 'rgba(255,255,255,0.1)' : 'rgba(102,252,241,0.3)';
                btn.style.color = isOpen ? 'var(--muted)' : 'var(--accent, #66fcf1)';
            }
        },

        toggleFilter: function(type, btn) {
            const isHidden = STATE.presenterHiddenTypes.has(type);
            if (isHidden) {
                STATE.presenterHiddenTypes.delete(type);
                if (btn) { btn.style.opacity = '1'; btn.style.textDecoration = 'none'; }
            } else {
                STATE.presenterHiddenTypes.add(type);
                if (btn) { btn.style.opacity = '0.35'; btn.style.textDecoration = 'line-through'; }
            }
            UI.applyFilters();
        },

        resetFilters: function() {
            STATE.presenterHiddenTypes.clear();
            STATE.presenterSearchQuery = '';
            const searchInput = document.getElementById('hbs-presenter-search');
            if (searchInput) searchInput.value = '';
            document.querySelectorAll('[data-filter-type]').forEach(btn => {
                btn.style.opacity = '1';
                btn.style.textDecoration = 'none';
            });
            // Reset All button state
            const allBtn = document.getElementById('hbs-presenter-filter-all');
            if (allBtn) {
                allBtn.style.background = 'rgba(255,255,255,0.12)';
                allBtn.style.color = 'var(--text)';
                allBtn.innerHTML = '<i class="fas fa-eye" style="font-size:9px;"></i> All';
                allBtn._allHidden = false;
            }
            UI.applyFilters();
        },

        toggleAllFilters: function(btn) {
            const allHidden = btn._allHidden;
            const allTypes = Object.keys(STATE.TYPE_META).filter(k => k !== 'default');
            
            if (allHidden) {
                // Show all: clear hidden types
                STATE.presenterHiddenTypes.clear();
                document.querySelectorAll('[data-filter-type]').forEach(chip => {
                    chip.style.opacity = '1';
                    chip.style.textDecoration = 'none';
                });
                btn.style.background = 'rgba(255,255,255,0.12)';
                btn.style.color = 'var(--text)';
                btn.innerHTML = '<i class="fas fa-eye" style="font-size:9px;"></i> All';
                btn._allHidden = false;
            } else {
                // Hide all: add all types to hidden
                allTypes.forEach(t => STATE.presenterHiddenTypes.add(t));
                document.querySelectorAll('[data-filter-type]').forEach(chip => {
                    chip.style.opacity = '0.35';
                    chip.style.textDecoration = 'line-through';
                });
                btn.style.background = 'rgba(239,68,68,0.15)';
                btn.style.color = '#ef4444';
                btn.innerHTML = '<i class="fas fa-eye-slash" style="font-size:9px;"></i> All';
                btn._allHidden = true;
            }
            UI.applyFilters();
        },

        setSearch: function(query) {
            STATE.presenterSearchQuery = (query || '').trim();
            UI.applyFilters();
        },

        briefing: _briefing,
        getFeed: function() { return [...STATE.feedHistory]; },
        updatePlaybookStatus: _updatePlaybookStatus,
        logShortcuts: function() {
            if (window.HKS_ACTIONS && window.HKS_BINDINGS) {
                const parts = [];
                for (const action of window.HKS_ACTIONS.getAll()) {
                    const combo = window.HKS_BINDINGS.get(action.id);
                    if (combo) {
                        parts.push(`<span style="color:#ffffff;">[${combo}]</span> ${action.label}`);
                    }
                }
                if (parts.length > 0) {
                    _notify({
                        type: 'tip',
                        text: `⌨️ Shortcuts: ${parts.join('  •  ')}`,
                        title: 'Presenter',
                        duration: 0,
                        persist: false
                    });
                }
            }
        },

        loadSessionFeed: function(sessionId, isNewSession = false) {
            if (!sessionId) return;

            // 1. Save outgoing session's feed before switching
            const prevSid = STATE.currentSessionId;
            if (prevSid && prevSid !== sessionId) {
                _saveCurrentSessionFeed(prevSid);
            }
            STATE.currentSessionId = sessionId;
            localStorage.setItem('hecos_active_session_id', sessionId);

            // 2. New chat session creation: boot ONCE only
            if (isNewSession) {
                if (STATE.sessionBooted && STATE.sessionBooted[sessionId]) {
                    console.debug('[Presenter] Session already booted, ignoring duplicate boot:', sessionId);
                    return;
                }
                STATE.sessionBooted = STATE.sessionBooted || {};
                STATE.sessionBooted[sessionId] = true;
                STATE.appBooted = true;

                Presenter.clear();
                _notify({
                    type: 'system_info',
                    text: 'Presenter core online.',
                    duration: 4000,
                    persist: false
                });
                setTimeout(() => Presenter.briefing(), 400);
                setTimeout(() => Presenter.logShortcuts(), 3500);
                setTimeout(() => _updatePlaybookStatus(true), 1200);
                return;
            }

            // 3. Switching to an EXISTING session (isNewSession === false):
            // Boot sequence is NEVER triggered on tab switch
            STATE.sessionBooted = STATE.sessionBooted || {};
            STATE.sessionBooted[sessionId] = true;

            // Fast restore from memory / sessionStorage cache
            const restored = _restoreSessionFeed(sessionId);
            if (restored) {
                UI.applyFilters();
                _updatePlaybookStatus(false);
                return;
            }

            // Not yet in cache: fetch from disk
            const chatParam = `&chat_id=${encodeURIComponent(sessionId)}`;
            fetch(`/api/ext/presenter/feed?limit=30${chatParam}`)
                .then(res => res.json())
                .then(data => {
                    if (STATE.currentSessionId !== sessionId) return;

                    Presenter.clear();
                    const hasEntries = data.ok && Array.isArray(data.entries) && data.entries.length > 0;
                    if (hasEntries) {
                        data.entries.forEach(entry => {
                            const entryType = entry.event_name || 'system_info';
                            const entryText = entry.text || '';
                            if (entryText) {
                                _notify({
                                    type: entryType === 'presenter_feed' ? 'system_info' : entryType,
                                    text: entryText,
                                    title: 'Presenter',
                                    duration: 0,
                                    persist: true,
                                    timestamp: entry.timestamp
                                });
                            }
                        });
                    } else {
                        // If session has no persisted feed entries yet, show playbook status quietly
                        _updatePlaybookStatus(true);
                    }
                    _saveCurrentSessionFeed(sessionId);
                    UI.applyFilters();
                })
                .catch(err => {
                    console.debug('[Presenter] loadSessionFeed error:', err);
                    _updatePlaybookStatus(false);
                });
        },

        resetFeed: function(e) {
            if (e) {
                e.preventDefault();
                e.stopPropagation();
            }
            
            // Visual feedback on the reset button icon
            const btn = document.getElementById('hbs-presenter-reset-btn');
            const icon = btn ? btn.querySelector('i') : null;
            if (icon) {
                icon.classList.add('fa-spin');
                setTimeout(() => icon.classList.remove('fa-spin'), 1000);
            }

            const sid = STATE.currentSessionId || localStorage.getItem('hecos_active_session_id') || 'global';
            
            // Clear current session memory and sessionStorage cache
            if (STATE.sessionFeeds && sid) {
                delete STATE.sessionFeeds[sid];
            }
            try {
                sessionStorage.removeItem('hecos_pfeed_' + sid);
            } catch (err) {}

            STATE.sessionBooted = STATE.sessionBooted || {};
            STATE.sessionBooted[sid] = true;
            STATE.appBooted = true;
            window._briefingInProgress = false;

            // Clear panel DOM
            Presenter.clear();

            // Run fresh boot sequence and announcements
            _notify({
                type: 'system_info',
                text: 'Presenter core reloaded.',
                duration: 4000,
                persist: false
            });
            setTimeout(() => Presenter.briefing(), 400);
            setTimeout(() => Presenter.logShortcuts(), 3500);
            setTimeout(() => _updatePlaybookStatus(true), 1200);
        },
        _renderDisabledState: UI.renderDisabledState
    };

    window.Presenter = Presenter;
    window.HBSPresenter = Presenter; // Legacy alias

    // ── SSE Handler ──────────────────────────────────────────────────
    // SSE format from state_manager: {"type":"presenter_feed", "timestamp":..., "event_name":..., "session_id":..., "text":...}
    window._hecosSSEHandlers = window._hecosSSEHandlers || {};
    window._hecosSSEHandlers["presenter_feed"] = function(ev) {
        const text = ev.text || (ev.data && ev.data.text);
        const eventType = ev.event_name || ev.type || 'system_info';
        const evSessionId = ev.session_id || null;

        if (eventType === 'new_chat') {
            const sid = evSessionId || localStorage.getItem('hecos_active_session_id');
            if (sid) {
                // If already booted by ch_actions.js loadSessionFeed, ignore duplicate!
                if (STATE.sessionBooted && STATE.sessionBooted[sid]) {
                    return;
                }
                Presenter.loadSessionFeed(sid, true);
            }
            return;
        }

        // Only render events that belong to the currently active session
        // (or global / system-level events with no session_id)
        const activeSid = STATE.currentSessionId || localStorage.getItem('hecos_active_session_id');
        if (evSessionId && activeSid && evSessionId !== 'global' && evSessionId !== activeSid) {
            // Buffer to background session cache if present
            if (STATE.sessionFeeds && STATE.sessionFeeds[evSessionId] && text) {
                try {
                    const formatted = UI.formatMessage(eventType === 'presenter_feed' ? 'system_info' : eventType, text, null);
                    const dateObj = new Date();
                    const timeStr = dateObj.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit', second:'2-digit'});
                    const lineHtml = `<div class="hbs-presenter-line" data-log-type="${eventType || 'system_info'}" style="animation: presenterFadeIn 0.3s ease;"><span style="font-size: 10px; color: var(--muted); margin-right: 8px; opacity: 0.7;">[${timeStr}]</span> ${formatted}</div>`;
                    STATE.sessionFeeds[evSessionId].html = (STATE.sessionFeeds[evSessionId].html || '') + lineHtml;
                    if (Array.isArray(STATE.sessionFeeds[evSessionId].history)) {
                        STATE.sessionFeeds[evSessionId].history.push({ timestamp: new Date().toISOString(), type: eventType, text: text, title: 'Presenter' });
                    }
                } catch(e) {}
            }
            return; // belongs to a different session — skip rendering to active DOM
        }

        if (text) {
            _notify({
                type: eventType === 'presenter_feed' ? 'system_info' : eventType,
                text: text,
                title: 'Presenter',
                duration: 8000,
                persist: false // already persisted on backend
            });
        }
    };

    // ── On Load ──────────────────────────────────────────────────────
    function _onReady() {
        _initOverlay();
        _initEmbedded();

        // Clear legacy flag
        try { sessionStorage.removeItem('hecos_presenter_booted'); } catch(e) {}

        const initialSid = localStorage.getItem('hecos_active_session_id');
        if (initialSid) {
            Presenter.loadSessionFeed(initialSid, false);
            STATE.appBooted = true;
        }

        fetch('/api/ext/presenter/config')
            .then(res => res.json())
            .then(d => {
                if (d.ok && d.config) {
                    Presenter.setEnabled(d.config.enabled);
                    Presenter.setDisplayMode(d.config.panel_default);
                    if (d.config.enabled) {
                        // Only run initial boot banner if no chat was active and app hasn't booted yet
                        if (!initialSid && !STATE.appBooted) {
                            STATE.appBooted = true;
                            _notify({
                                type: 'system_info',
                                text: 'Presenter core online.',
                                duration: 4000,
                                persist: false
                            });
                            if (d.config.briefing_on_new_chat) {
                                setTimeout(() => Presenter.briefing(), 800);
                                setTimeout(() => Presenter.logShortcuts(), 4800);
                            }
                        }
                    } else {
                        // Render the disabled notice immediately
                        UI.renderDisabledState();
                    }
                }
            })
            .catch(err => console.error("[Presenter] Load config failed", err));

        // Active Playbook Pill & Status Integration
        setTimeout(() => _updatePlaybookStatus(false), 800);

        // Listen for storage events (sync when Playbooks are toggled/edited in another tab)
        window.addEventListener('storage', (e) => {
            if (e.key === 'hecos_playbook_last_update') {
                _updatePlaybookStatus(true);
            }
        });

        // Listen for internal custom event in the same window
        window.addEventListener('hecos:playbook:change', () => {
            _updatePlaybookStatus(true);
        });

        // Refresh pill when window regains focus
        window.addEventListener('focus', () => {
            _updatePlaybookStatus(false);
        });

        // Listen for Unified Toast events
        if (window.hecos && window.hecos.core && window.hecos.core.events && window.hecos.core.events.bus) {
            window.hecos.core.events.bus.addEventListener('hecos:system:toast', (e) => {
                if (e.detail && e.detail.message) {
                    _notify({
                        type: 'system_info',
                        text: e.detail.message,
                        title: 'Presenter',
                        duration: 0,
                        persist: true
                    });
                }
            });
        } else {
            // Fallback: poll until bus is ready, then attach
            const _busInterval = setInterval(() => {
                if (window.hecos && window.hecos.core && window.hecos.core.events && window.hecos.core.events.bus) {
                    clearInterval(_busInterval);
                    window.hecos.core.events.bus.addEventListener('hecos:system:toast', (e) => {
                        if (e.detail && e.detail.message) {
                            _notify({
                                type: 'system_info',
                                text: e.detail.message,
                                title: 'Presenter',
                                duration: 0,
                                persist: true
                            });
                        }
                    });
                }
            }, 500);
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', _onReady);
    } else {
        _onReady();
    }

})();
