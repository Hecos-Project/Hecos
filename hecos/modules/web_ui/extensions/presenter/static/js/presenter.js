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
        system_info:     { icon: 'fas fa-info-circle',          color: '#6cb4ee', tooltip: 'System Information' },
        system_status:   { icon: 'fas fa-circle',               color: '#4caf50', iconSize: '9px', tooltip: 'System Status' },
        system_warning:  { icon: 'fas fa-exclamation-triangle', color: '#ffa726', tooltip: 'System Warning' },
        action_confirm:  { icon: 'fas fa-check-circle',         color: '#66bb6a', tooltip: 'Action Confirmed' },
        tip:             { icon: 'fas fa-lightbulb',            color: '#ffd54f', tooltip: 'Helpful Tip' },
        package_event:   { icon: 'fas fa-box-open',             color: '#ab47bc', tooltip: 'Package Event' },
        log_important:   { icon: 'fas fa-clipboard-list',       color: '#ef5350', tooltip: 'Important Log' },
        persona_switched:{ icon: 'fas fa-user-astronaut',       color: '#e040fb', tooltip: 'Persona Switched' },
        new_chat:        { icon: 'fas fa-comments',             color: '#29b6f6', tooltip: 'New Chat Session' },
        user_comment:    { icon: 'fas fa-user',                 color: '#42a5f5', tooltip: "Comment on User's Message" },
        ai_comment:      { icon: 'fas fa-robot',                color: '#ab47bc', tooltip: "Comment on AI's Response" },
        message_exchange:{ icon: 'fas fa-exchange-alt',         color: '#78909c', tooltip: 'Comment on Chat Exchange' },
        test:            { icon: 'fas fa-flask',                color: '#26c6da', tooltip: 'Test Event' },
        briefing:        { icon: 'fas fa-satellite-dish',       color: '#ff7043', tooltip: 'System Briefing' },
        default:         { icon: 'fas fa-bullhorn',             color: '#ff512f', tooltip: 'Notification' }
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

    function _formatMessage(type, text, thinkText) {
        const m = _resolveMeta(type);
        const sizeAttr = m.iconSize ? ` style="font-size:${m.iconSize}"` : '';
        const tooltipStr = m.tooltip ? ` title="${m.tooltip}"` : ` title="${type}"`;
        
        let html = '';
        if (thinkText) {
            html += `
                <div style="margin-bottom: 6px; margin-top: 2px;">
                    <div style="cursor: pointer; color: #ffd54f; font-size: 11px; display: inline-flex; align-items: center; gap: 4px; opacity: 0.8; transition: opacity 0.2s;" onmouseover="this.style.opacity='1'" onmouseout="this.style.opacity='0.8'" onclick="this.nextElementSibling.style.display = this.nextElementSibling.style.display === 'none' ? 'block' : 'none'; this.innerHTML = this.nextElementSibling.style.display === 'none' ? '<i class=\\'fas fa-lightbulb\\'></i> Show Reasoning' : '<i class=\\'fas fa-lightbulb\\'></i> Hide Reasoning';">
                        <i class="fas fa-lightbulb"></i> Show Reasoning
                    </div>
                    <div class="hbs-presenter-think-block" style="display: none; margin-top: 6px; font-size: 11px; color: var(--text-muted, #999); padding: 8px 10px; border-left: 2px solid #ffd54f; background: rgba(0,0,0,0.15); border-radius: 0 4px 4px 0; white-space: pre-wrap; font-family: monospace; line-height: 1.4;">${thinkText}</div>
                </div>
            `;
        }
        
        html += `<span style="color:${m.color}; margin-right:6px;"${tooltipStr}><i class="${m.icon}"${sizeAttr}></i></span>${text}`;
        
        return html;
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
                        <button onclick="window.Presenter.adaptHeight()" title="Adatta altezza alle righe visibili" style="background: rgba(255,255,255,0.1); border: none; color: var(--text); font-size: 10px; margin-left: 6px; padding: 2px 6px; border-radius: 3px; cursor: pointer; transition: background 0.2s;" onmouseover="this.style.background='rgba(255,255,255,0.2)'" onmouseout="this.style.background='rgba(255,255,255,0.1)'">Adapt</button>
                    </div>
                </div>

                <button id="hbs-presenter-toggle" style="background:none;border:none;color:var(--muted);cursor:pointer;" title="Collapse/Expand">
                    <i class="fas fa-chevron-up"></i>
                </button>
            </div>
            <div class="hbs-presenter-body" style="overflow-y: auto; resize: vertical; min-height: 40px; max-height: 50vh; display: flex; flex-direction: column; gap: 4px; padding-bottom: 4px; ${uiState.save && uiState.height ? 'height:'+uiState.height+'px;' : 'height: auto;'}"></div>
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
            avatarEl.closest('.hbs-presenter-avatar').title = m.tooltip || type;
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
        const rawText  = opts.text || '';
        const title    = opts.title || 'Presenter';
        const duration = opts.duration !== undefined ? opts.duration : 6000;
        const persist  = opts.persist !== undefined ? opts.persist : true;

        let thinkText = null;
        let displayHtml = rawText;
        
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

        const formatted = _formatMessage(type, displayHtml, thinkText);
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
            
            // Hard limit physical DOM nodes to MAX_FEED to prevent DOM bloat
            while (msgEl.children.length > MAX_FEED) {
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
            const emb = _getEmbedded();
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

        clear: function() {
            feedHistory.length = 0;
            const emb = _getEmbedded();
            if (emb) {
                const msgEl = emb.querySelector('.hbs-presenter-body');
                if (msgEl) msgEl.innerHTML = '';
            }
        },

        adaptHeight: function() {
            const emb = _getEmbedded();
            if (!emb) return;
            const bodyEl = emb.querySelector('.hbs-presenter-body');
            if (bodyEl) {
                bodyEl.style.removeProperty('height');
                this.saveUIState();
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
                        parts.push(`[${combo}] ${action.label}`);
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
