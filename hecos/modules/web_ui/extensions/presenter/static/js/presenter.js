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

        // Respect collapsed state: do not force auto-expand when collapsed
        if (target.classList.contains('collapsed')) {
            // Keep collapsed
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
            const emptyNotice = msgEl.querySelector('.hbs-presenter-empty-search');
            if (emptyNotice) emptyNotice.remove();

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

    // ── Session Feed Cache (Delegated to UI) ──────────────────────────
    function _saveCurrentSessionFeed(targetSid) {
        if (UI && UI.saveCurrentSessionFeed) UI.saveCurrentSessionFeed(targetSid);
    }

    function _restoreSessionFeed(sid) {
        return (UI && UI.restoreSessionFeed) ? UI.restoreSessionFeed(sid) : false;
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
        } else if (displayHtml.includes('<think>')) {
            // Unclosed <think> tag
            const parts = displayHtml.split('<think>');
            thinkText = parts.slice(1).join('').trim();
            displayHtml = parts[0].trim();
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
            const emb = UI.getEmbedded();
            if (emb && (emb.classList.contains('netsearch-presenter-embedded') || emb.closest('.search-copilot') || (window.location && window.location.pathname.includes('/netsearch')))) {
                const pill = emb.querySelector('#hbs-presenter-playbook-pill');
                if (pill) pill.style.display = 'none';
                return;
            }
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
            // Always active so it is visible immediately
            el.classList.add('active');
            localStorage.setItem('hecos_presenter_active', 'true');
            // Flush any counts that were already in memory before DOM was built
            if (window.HBSPresenterStatsUI && typeof window.HBSPresenterStatsUI.render === 'function') {
                window.HBSPresenterStatsUI.render();
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
            const isNetSearch = (window.location && window.location.pathname.includes('/netsearch')) || (emb && emb.classList.contains('netsearch-presenter-embedded'));
            const storageKey = isNetSearch ? 'hecos_netsearch_presenter_collapsed' : 'hecos_chat_presenter_collapsed';
            const stored = localStorage.getItem(storageKey);
            const shouldCollapse = stored !== null ? (stored === 'true') : (window.innerWidth <= 768);

            if (mode === 'embedded') {
                if (emb) {
                    emb.classList.toggle('collapsed', shouldCollapse);
                    if (UI && typeof UI.updatePowerUI === 'function') UI.updatePowerUI(!shouldCollapse);
                }
                if (ov) ov.classList.remove('active');
            } else if (mode === 'collapsed') {
                if (emb) {
                    emb.classList.add('collapsed');
                    if (UI && typeof UI.updatePowerUI === 'function') UI.updatePowerUI(false);
                }
                if (ov) ov.classList.remove('active');
            } else if (mode === 'overlay') {
                if (emb) emb.classList.remove('active');
            } else if (mode === 'hidden') {
                _hide();
                if (emb) emb.classList.remove('active');
            }
        },

        togglePower: function(e) {
            if (e) {
                e.preventDefault();
                e.stopPropagation();
            }
            const emb = UI.getEmbedded();
            if (!emb) return;
            const isColl = emb.classList.contains('collapsed');
            const nextActive = isColl; // if collapsed, turn ON; else turn OFF
            Presenter.setContextEnabled(nextActive);
        },

        setContextEnabled: function(active) {
            const emb = UI.getEmbedded();
            const isNetSearch = (window.location && window.location.pathname.includes('/netsearch')) || (emb && emb.classList.contains('netsearch-presenter-embedded'));
            const ctx = isNetSearch ? 'netsearch' : 'chat';
            const storageKey = isNetSearch ? 'hecos_netsearch_presenter_collapsed' : 'hecos_chat_presenter_collapsed';

            if (emb) {
                if (active) {
                    emb.classList.remove('collapsed');
                    localStorage.setItem(storageKey, 'false');
                } else {
                    emb.classList.add('collapsed');
                    localStorage.setItem(storageKey, 'true');
                }
            }
            if (UI && typeof UI.updatePowerUI === 'function') {
                UI.updatePowerUI(active);
            }

            // Sync with backend independent context toggle
            fetch('/api/ext/presenter/toggle_context', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ context: ctx, enabled: !!active })
            }).catch(err => console.error('[Presenter] Failed to toggle context:', err));
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

        toggleAdvanced: function(panel, btn) {
            if (UI && UI.toggleAdvanced) {
                const p = panel || document.getElementById('hbs-presenter-advanced');
                const b = btn || document.getElementById('hbs-presenter-advanced-toggle');
                UI.toggleAdvanced(p, b);
            }
        },

        toggleFilter: function(type, btn) {
            if (UI && UI.toggleFilter) UI.toggleFilter(type, btn);
        },

        resetFilters: function() {
            if (UI && UI.resetFilters) UI.resetFilters();
        },

        toggleAllFilters: function(btn) {
            if (UI && UI.toggleAllFilters) UI.toggleAllFilters(btn);
        },

        setSearch: function(query) {
            if (UI && UI.setSearch) UI.setSearch(query);
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
            if (UI && UI.loadSessionFeed) {
                UI.loadSessionFeed(sessionId, isNewSession);
            }
        },

        resetFeed: function(e) {
            if (UI && UI.resetFeed) {
                UI.resetFeed(e);
            }
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

        const isNetSearch = (window.location && window.location.pathname.includes('/netsearch')) || (UI.getEmbedded() && UI.getEmbedded().classList.contains('netsearch-presenter-embedded'));
        if (isNetSearch) {
            const isSearch = eventType.startsWith('search_') || (text && text.includes('[NetSearch]'));
            if (!isSearch) {
                return; // Ignore non-search events in NetSearch sidebar
            }
        }

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

        const isNetSearch = (window.location && window.location.pathname.includes('/netsearch')) || (UI.getEmbedded() && UI.getEmbedded().classList.contains('netsearch-presenter-embedded'));
        const targetSid = isNetSearch ? 'global' : (localStorage.getItem('hecos_active_session_id') || 'global');
        Presenter.loadSessionFeed(targetSid, false);
        STATE.appBooted = true;

        const storageKey = isNetSearch ? 'hecos_netsearch_presenter_collapsed' : 'hecos_chat_presenter_collapsed';
        const storedCollapsed = localStorage.getItem(storageKey);
        const isSavedCollapsed = storedCollapsed !== null ? (storedCollapsed === 'true') : (window.innerWidth <= 768);
        const embInit = UI.getEmbedded();
        if (embInit) {
            if (isSavedCollapsed) {
                embInit.classList.add('collapsed');
                if (UI && typeof UI.updatePowerUI === 'function') UI.updatePowerUI(false);
            } else {
                embInit.classList.remove('collapsed');
                if (UI && typeof UI.updatePowerUI === 'function') UI.updatePowerUI(true);
            }
        }

        fetch('/api/ext/presenter/config')
            .then(res => res.json())
            .then(d => {
                if (d.ok && d.config) {
                    Presenter.setEnabled(d.config.enabled);
                    if (!isNetSearch) {
                        Presenter.setDisplayMode(d.config.panel_default);
                    }
                    // If a saved collapsed state exists in localStorage, sync with backend context
                    if (localStorage.getItem(storageKey) !== null) {
                        Presenter.setContextEnabled(!isSavedCollapsed);
                    }

                    if (d.config.enabled && !isNetSearch) {
                        // Only run initial boot banner in chat
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
                    } else if (!d.config.enabled) {
                        // Render the disabled notice immediately
                        UI.renderDisabledState();
                    }
                }
            })
            .catch(err => console.error("[Presenter] Load config failed", err));

        // Active Playbook Pill & Status Integration
        setTimeout(() => _updatePlaybookStatus(false), 800);

        // Ensure Notification Stats are synced and rendered
        setTimeout(() => {
            if (window.HBSPresenterStats && typeof window.HBSPresenterStats.syncFromDOM === 'function') {
                window.HBSPresenterStats.syncFromDOM();
            } else if (window.HBSPresenterStatsUI && typeof window.HBSPresenterStatsUI.render === 'function') {
                window.HBSPresenterStatsUI.render();
            }
        }, 500);

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
