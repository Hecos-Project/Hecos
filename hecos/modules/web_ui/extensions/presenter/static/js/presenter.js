/**
 * Hecos Presenter — Full Featured Extension JS
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

    // ── Icon Catalog ─────────────────────────────────────────────────
    const TYPE_META = {
        system_info:     { icon: 'fas fa-info-circle',          color: '#6cb4ee' },
        system_status:   { icon: 'fas fa-circle',               color: '#4caf50', iconSize: '9px' },
        system_warning:  { icon: 'fas fa-exclamation-triangle', color: '#ffa726' },
        action_confirm:  { icon: 'fas fa-check-circle',         color: '#66bb6a' },
        tip:             { icon: 'fas fa-lightbulb',            color: '#ffd54f' },
        package_event:   { icon: 'fas fa-box-open',             color: '#ab47bc' },
        log_important:   { icon: 'fas fa-clipboard-list',       color: '#ef5350' },
        persona_switched:{ icon: 'fas fa-user-astronaut',       color: '#e040fb' },
        new_chat:        { icon: 'fas fa-comments',             color: '#29b6f6' },
        test:            { icon: 'fas fa-flask',                color: '#26c6da' },
        briefing:        { icon: 'fas fa-satellite-dish',       color: '#ff7043' },
        default:         { icon: 'fas fa-bullhorn',             color: '#ff512f' }
    };

    // ── State ────────────────────────────────────────────────────────
    let displayMode = 'collapsed';
    let presenterEnabled = true;
    let hideTimeout;
    const feedHistory = [];
    const MAX_FEED = 50;

    // ── Helpers ──────────────────────────────────────────────────────
    // Always look up the container fresh — survives DOM replacements
    function _getEmbedded() {
        return document.getElementById('hbs-presenter-embedded');
    }
    function _getOverlay() {
        return document.getElementById('hbs-presenter-overlay');
    }

    function _resolveMeta(type) {
        return TYPE_META[type] || TYPE_META.default;
    }

    function _formatMessage(type, text) {
        const m = _resolveMeta(type);
        const sizeAttr = m.iconSize ? ` style="font-size:${m.iconSize}"` : '';
        return `<span style="color:${m.color}; margin-right:6px;"><i class="${m.icon}"${sizeAttr}></i></span>${text}`;
    }

    // ── Build HTML inside a container ────────────────────────────────
    function _ensureBuilt(container) {
        if (!container || container.dataset.presenterBuilt) return;
        container.dataset.presenterBuilt = '1';
        
        const uiState = JSON.parse(localStorage.getItem('hecos_presenter_ui_state') || '{"save":false, "lines":4, "height":""}');
        
        container.innerHTML = `
            <div class="hbs-presenter-header">
                <div class="hbs-presenter-avatar"><i class="fas fa-bullhorn"></i></div>
                <div class="hbs-presenter-title">Presenter</div>
                <div style="flex:1"></div>
                
                <div class="hbs-presenter-controls" style="display: flex; align-items: center; gap: 12px; margin-right: 12px; font-size: 11px;">
                    <label style="color:var(--muted); cursor:pointer; display:flex; align-items:center; gap:4px;" title="Remember height and max lines for next sessions">
                        <input type="checkbox" id="hbs-presenter-remember-size" ${uiState.save ? 'checked' : ''} onchange="window.Presenter.saveUIState()"> Save UI
                    </label>
                    <div style="display:flex; align-items:center; background: rgba(0,0,0,0.2); border-radius: 4px; padding: 2px 4px; border: 1px solid var(--border-color, #333);">
                        <span style="color:var(--muted); margin-right:4px;">Max lines:</span>
                        <input type="number" id="hbs-presenter-max-lines" class="presenter-dark-input" value="${uiState.lines}" min="1" max="500" onchange="window.Presenter.saveUIState(); window.Presenter.trimFeed();" style="width: 45px; background: transparent; border: none; color: var(--text); font-size: 11px; outline: none; text-align: center;">
                    </div>
                </div>

                <button id="hbs-presenter-toggle" style="background:none;border:none;color:var(--muted);cursor:pointer;" title="Collapse/Expand">
                    <i class="fas fa-chevron-up"></i>
                </button>
            </div>
            <div class="hbs-presenter-body" style="overflow-y: auto; resize: vertical; min-height: 20px; display: flex; flex-direction: column; gap: 4px; padding-bottom: 4px; ${uiState.save && uiState.height ? 'height:'+uiState.height+'px;' : ''}"></div>
            <div class="hbs-presenter-footer" style="display:none;"></div>
        `;

        // Listen for resize events using ResizeObserver
        const bodyEl = container.querySelector('.hbs-presenter-body');
        if (bodyEl) {
            const ro = new ResizeObserver(() => {
                if (document.getElementById('hbs-presenter-remember-size')?.checked) {
                    window.Presenter.saveUIState();
                }
            });
            ro.observe(bodyEl);
        }
    }

    // ── Toggle Collapse ──────────────────────────────────────────────
    document.addEventListener('click', (e) => {
        const toggleBtn = e.target.closest('#hbs-presenter-toggle');
        if (!toggleBtn) return;
        const container = document.getElementById('hbs-presenter-embedded');
        if (!container) return;
        container.classList.toggle('collapsed');
        const icon = toggleBtn.querySelector('i');
        if (icon) {
            icon.classList.toggle('fa-chevron-up', !container.classList.contains('collapsed'));
            icon.classList.toggle('fa-chevron-down', container.classList.contains('collapsed'));
        }
    });

    // ── Core Show ────────────────────────────────────────────────────
    function _show(message, title, duration, type) {
        if (!presenterEnabled) return;

        let target;
        if (displayMode === 'overlay') {
            target = _getOverlay();
        } else {
            target = _getEmbedded();
        }
        if (!target) return;

        _ensureBuilt(target);

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
            const m = _resolveMeta(type);
            avatarEl.className = m.icon;
            avatarEl.closest('.hbs-presenter-avatar').style.background = `linear-gradient(135deg, ${m.color}99, ${m.color}55)`;
        }

        // Append line instead of replacing
        if (msgEl) {
            const line = document.createElement('div');
            line.className = 'hbs-presenter-line';
            line.style.animation = 'presenterFadeIn 0.3s ease';
            
            const timeStr = new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit', second:'2-digit'});
            line.innerHTML = `<span style="font-size: 10px; color: var(--muted); margin-right: 8px; opacity: 0.7;">[${timeStr}]</span> ${message}`;
            
            msgEl.appendChild(line);
            
            // Auto scroll to bottom
            msgEl.scrollTop = msgEl.scrollHeight;
            
            // Trim feed lines based on UI max settings
            if (window.Presenter.trimFeed) {
                window.Presenter.trimFeed();
            }
        }

        target.classList.add('active');

        clearTimeout(hideTimeout);
        if (duration > 0 && displayMode === 'overlay') {
            hideTimeout = setTimeout(() => _hide(), duration);
        }
    }

    function _hide() {
        const overlay = _getOverlay();
        if (overlay) overlay.classList.remove('active');
    }

    // ── Feed ─────────────────────────────────────────────────────────
    function _addToFeed(entry) {
        feedHistory.push(entry);
        if (feedHistory.length > MAX_FEED) feedHistory.shift();
    }

    // ── UNIFIED NOTIFICATION API ─────────────────────────────────────
    function _notify(opts) {
        if (!presenterEnabled) return;
        const type     = opts.type || 'system_info';
        const text     = opts.text || '';
        const title    = opts.title || 'Presenter';
        const duration = opts.duration !== undefined ? opts.duration : 6000;
        const persist  = opts.persist !== undefined ? opts.persist : true;

        const formatted = _formatMessage(type, text);
        _show(formatted, title, duration, type);

        if (persist) {
            _addToFeed({ timestamp: new Date().toISOString(), type, text, title });
        }
    }

    // ── System Briefing ──────────────────────────────────────────────
    async function _briefing() {
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
        }
    }

    // ── Init overlay container ───────────────────────────────────────
    function _initOverlay() {
        if (document.getElementById('hbs-presenter-overlay')) return;
        const el = document.createElement('div');
        el.id = 'hbs-presenter-overlay';
        document.body.appendChild(el);
        _ensureBuilt(el);
    }

    // ── Init embedded container ──────────────────────────────────────
    function _initEmbedded() {
        const el = _getEmbedded();
        if (el) _ensureBuilt(el);
    }

    // ── Public API ───────────────────────────────────────────────────
    const Presenter = {
        notify: _notify,

        saveUIState: function() {
            const emb = _getEmbedded();
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
            const emb = _getEmbedded();
            if (!emb) return;
            const linesInput = emb.querySelector('#hbs-presenter-max-lines');
            const msgEl = emb.querySelector('.hbs-presenter-body');
            if (!linesInput || !msgEl) return;
            
            const maxLines = parseInt(linesInput.value) || 4;
            while (msgEl.children.length > maxLines) {
                msgEl.removeChild(msgEl.firstChild);
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
            presenterEnabled = enabled;
            if (!enabled) {
                _hide();
                const emb = _getEmbedded();
                if (emb) emb.classList.remove('active');
            }
        },

        setDisplayMode: function(mode) {
            displayMode = mode;
            const emb = _getEmbedded();
            const ov = _getOverlay();

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

        briefing: _briefing,
        getFeed: function() { return [...feedHistory]; }
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
                    }
                }
            })
            .catch(err => console.error("[Presenter] Load config failed", err));
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', _onReady);
    } else {
        _onReady();
    }

})();
