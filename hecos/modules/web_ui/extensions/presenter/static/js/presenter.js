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
    function _show(message, title, duration, type) {
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
            
            const timeStr = new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit', second:'2-digit'});
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

        const formatted = UI.formatMessage(type, displayHtml, thinkText);
        _show(formatted, title, duration, type);

        if (persist) {
            // Keep the original text with tags for the feed history
            _addToFeed({ timestamp: new Date().toISOString(), type, text: rawText, title });
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
            }
        } catch (e) {
            console.warn('[Presenter] Briefing fetch failed:', e);
        } finally {
            setTimeout(() => { window._briefingInProgress = false; }, 3000);
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
            const linesInput = emb.querySelector('#hbs-presenter-max-lines');
            const msgEl = emb.querySelector('.hbs-presenter-body');
            if (!linesInput || !msgEl) return;
            
            // Hard limit physical DOM nodes to MAX_FEED to prevent DOM bloat
            while (msgEl.children.length > STATE.MAX_FEED) {
                msgEl.removeChild(msgEl.firstChild);
            }
            
            const maxLines = parseInt(linesInput.value) || 4;
            const children = Array.from(msgEl.children);
            const total = children.length;
            
            children.forEach((child, index) => {
                if (index < total - maxLines) {
                    child.style.display = 'none';
                } else {
                    child.style.display = '';
                }
            });
        },

        setLines: function(num) {
            const emb = UI.getEmbedded();
            if (!emb) return;
            const linesInput = emb.querySelector('#hbs-presenter-max-lines');
            if (linesInput) {
                linesInput.value = num;
                this.saveUIState();
                this.trimFeed();
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
            const bodyEl = emb.querySelector('.hbs-presenter-body');
            if (bodyEl) {
                bodyEl.style.removeProperty('height');
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
        _renderDisabledState: UI.renderDisabledState
    };

    window.Presenter = Presenter;
    window.HBSPresenter = Presenter; // Legacy alias

    // ── SSE Handler ──────────────────────────────────────────────────
    // SSE format from state_manager: {"type":"presenter_feed", "timestamp":..., "event_name":..., "text":...}
    window._hecosSSEHandlers = window._hecosSSEHandlers || {};
    window._hecosSSEHandlers["presenter_feed"] = function(ev) {
        // ev is the full SSE object: {type, timestamp, event_name, text}
        const text = ev.text || (ev.data && ev.data.text);
        const eventType = ev.event_name || ev.type || 'system_info';
        
        if (eventType === 'new_chat') {
            Presenter.clear();
            setTimeout(() => Presenter.briefing(), 500); // Reload briefing
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

        fetch('/api/ext/presenter/config')
            .then(res => res.json())
            .then(d => {
                if (d.ok && d.config) {
                    Presenter.setEnabled(d.config.enabled);
                    Presenter.setDisplayMode(d.config.panel_default);
                    if (d.config.enabled) {
                        _notify({
                            type: 'system_info',
                            text: 'Presenter core online.',
                            duration: 4000,
                            persist: false
                        });
                        if (d.config.briefing_on_new_chat) {
                            setTimeout(() => Presenter.briefing(), 1500);
                        }
                    } else {
                        // Render the disabled notice immediately
                        UI.renderDisabledState();
                    }
                }
            })
            .catch(err => console.error("[Presenter] Load config failed", err));

        // Log keyboard shortcuts to Presenter feed (after init is complete)
        setTimeout(() => {
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
                        persist: true
                    });
                }
            }
        }, 2500);

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
