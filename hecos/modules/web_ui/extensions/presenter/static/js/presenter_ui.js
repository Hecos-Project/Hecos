/**
 * Hecos Presenter — UI & Rendering Logic
 */
(function() {
    'use strict';

    function getEmbedded() {
        return document.getElementById('hbs-presenter-embedded');
    }

    function getOverlay() {
        return document.getElementById('hbs-presenter-overlay');
    }

    function resolveMeta(type) {
        const state = window.HBSPresenterState;
        return state.TYPE_META[type] || state.TYPE_META.default;
    }

    function formatMessage(type, text, thinkText) {
        const m = resolveMeta(type);
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

    function ensureBuilt(container) {
        if (!container || container.dataset.presenterBuilt) return;
        container.dataset.presenterBuilt = '1';
        
        const uiState = JSON.parse(localStorage.getItem('hecos_presenter_ui_state') || '{"save":false, "lines":4, "height":""}');
        const state = window.HBSPresenterState;
        
        container.innerHTML = `
            <div class="hbs-presenter-header" style="cursor: pointer;">
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
                    <button id="hbs-presenter-advanced-toggle" onclick="window.Presenter.toggleAdvanced()" title="Advanced filters &amp; search" style="background: rgba(255,255,255,0.07); border: 1px solid rgba(255,255,255,0.1); color: var(--muted); font-size: 10px; padding: 2px 8px; border-radius: 3px; cursor: pointer; display:flex; align-items:center; gap:4px; transition: background 0.2s;" onmouseover="this.style.background='rgba(255,255,255,0.14)'" onmouseout="this.style.background='rgba(255,255,255,0.07)'">
                        <i class="fas fa-sliders-h"></i> Advanced
                    </button>
                    <a href="/hecos/config/ui#presenter" target="_blank" title="Open Presenter Settings" style="display:flex; align-items:center; justify-content:center; width:24px; height:24px; border-radius:50%; background: rgba(255,255,255,0.07); border: 1px solid rgba(255,255,255,0.1); color: var(--muted); font-size: 11px; cursor: pointer; transition: all 0.2s; text-decoration:none;" onmouseover="this.style.background='rgba(255,255,255,0.18)'; this.style.color='var(--text)';" onmouseout="this.style.background='rgba(255,255,255,0.07)'; this.style.color='var(--muted)';">
                        <i class="fas fa-cog"></i>
                    </a>
                </div>

                <button id="hbs-presenter-toggle" style="background:none;border:none;color:var(--muted);cursor:pointer;" title="Collapse/Expand">
                    <i class="fas fa-chevron-up"></i>
                </button>
            </div>

            <!-- Advanced panel: hidden by default -->
            <div id="hbs-presenter-advanced" style="display:none; padding: 6px 12px 8px 12px; background: rgba(0,0,0,0.2); border-bottom: 1px solid rgba(255,255,255,0.06);">
                <div style="display:flex; align-items:center; gap:8px; margin-bottom:8px;">
                    <i class="fas fa-search" style="color:var(--muted); font-size:11px;"></i>
                    <input id="hbs-presenter-search" type="text" placeholder="Search messages..." oninput="window.Presenter.setSearch(this.value)" style="flex:1; background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); border-radius: 4px; padding: 4px 8px; color: var(--text); font-size: 11px; outline: none;">
                    <button onclick="document.getElementById('hbs-presenter-search').value=''; window.Presenter.setSearch('');" title="Clear search" style="background:none; border:none; color:var(--muted); cursor:pointer; font-size:12px;"><i class="fas fa-times"></i></button>
                </div>
                <div style="font-size:10px; color:var(--muted); margin-bottom:5px; letter-spacing:0.5px; text-transform:uppercase;">Filter by type:</div>
                <div id="hbs-presenter-filter-chips" style="display:flex; flex-wrap:wrap; gap:5px;">
                    <button id="hbs-presenter-filter-all" onclick="window.Presenter.toggleAllFilters(this)" 
                        title="Toggle all categories"
                        style="display:inline-flex;align-items:center;gap:4px; font-size:10px; padding:2px 8px; border-radius:12px; border:1px solid rgba(255,255,255,0.25); background: rgba(255,255,255,0.12); color:var(--text); cursor:pointer; transition: all 0.15s; font-weight:700;">
                        <i class="fas fa-eye" style="font-size:9px;"></i> All
                    </button>
                    ${Object.entries(state.TYPE_META).filter(([k]) => k !== 'default').map(([k, v]) => `
                        <button data-filter-type="${k}" onclick="window.Presenter.toggleFilter('${k}', this)" 
                            title="Toggle ${v.tooltip || k}"
                            style="display:inline-flex;align-items:center;gap:4px; font-size:10px; padding:2px 8px; border-radius:12px; border:1px solid ${v.color}44; background: ${v.color}22; color:${v.color}; cursor:pointer; transition: all 0.15s; opacity:1;">
                            <i class="${v.icon}" style="font-size:9px;"></i> ${v.tooltip || k}
                        </button>
                    `).join('')}
                    <button onclick="window.Presenter.resetFilters()" title="Reset all filters &amp; search" style="display:inline-flex;align-items:center;gap:4px; font-size:10px; padding:2px 8px; border-radius:12px; border:1px solid rgba(255,255,255,0.15); background: rgba(255,255,255,0.05); color:var(--muted); cursor:pointer; transition: all 0.15s;">
                        <i class="fas fa-undo" style="font-size:9px;"></i> Reset
                    </button>
                </div>
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

    function renderDisabledState() {
        const emb = getEmbedded();
        if (!emb) return;
        ensureBuilt(emb);
        const msgEl = emb.querySelector('.hbs-presenter-body');
        if (!msgEl) return;
        // Don't add twice
        if (emb.querySelector('#hbs-presenter-disabled-notice')) return;
        const notice = document.createElement('div');
        notice.id = 'hbs-presenter-disabled-notice';
        notice.style.cssText = 'display:flex; flex-direction:column; align-items:center; justify-content:center; padding:20px 16px; gap:10px; text-align:center;';
        notice.innerHTML = `
            <div style="font-size:28px; opacity:0.25;"><i class="fas fa-bullhorn"></i></div>
            <div style="font-size:13px; font-weight:600; color:var(--text); opacity:0.7;">Presenter is disabled</div>
            <div style="font-size:11px; color:var(--muted); line-height:1.6; max-width:260px;">
                The Presenter module is currently off. Enable it from the
                <a href="/hecos/config/ui#presenter" target="_blank"
                   style="color:var(--accent,#66fcf1); text-decoration:none; font-weight:600;"
                   onmouseover="this.style.textDecoration='underline'" onmouseout="this.style.textDecoration='none'">
                   Central Hub &rarr; Presenter
                </a>
                settings panel.
            </div>
            <a href="/hecos/config/ui#presenter" target="_blank"
               style="display:inline-flex; align-items:center; gap:6px; margin-top:4px; padding:5px 14px; border-radius:20px; background:rgba(102,252,241,0.1); border:1px solid rgba(102,252,241,0.25); color:var(--accent,#66fcf1); font-size:11px; font-weight:600; text-decoration:none; transition:background 0.2s;"
               onmouseover="this.style.background='rgba(102,252,241,0.2)'" onmouseout="this.style.background='rgba(102,252,241,0.1)'">
                <i class="fas fa-cog"></i> Open Settings
            </a>
        `;
        msgEl.appendChild(notice);
    }

    function clearDisabledState() {
        const notice = document.getElementById('hbs-presenter-disabled-notice');
        if (notice) notice.remove();
    }

    function applyFilters() {
        const state = window.HBSPresenterState;
        const emb = getEmbedded();
        if (!emb) return;
        const lines = emb.querySelectorAll('.hbs-presenter-line');
        lines.forEach(line => {
            const logType = line.dataset.logType || 'system_info';
            const typeHidden = state.presenterHiddenTypes.has(logType);
            const searchHidden = state.presenterSearchQuery && !line.textContent.toLowerCase().includes(state.presenterSearchQuery.toLowerCase());
            line.style.display = (typeHidden || searchHidden) ? 'none' : '';
        });
    }

    // Toggle Collapse Events
    document.addEventListener('click', (e) => {
        const header = e.target.closest('.hbs-presenter-header');
        if (!header) return;
        
        // Prevent collapse if clicking on controls, inputs, or links (unless it's the toggle button itself)
        if (e.target.closest('.hbs-presenter-controls') || e.target.closest('input') || e.target.closest('a')) {
            if (!e.target.closest('#hbs-presenter-toggle')) {
                return;
            }
        }

        const container = document.getElementById('hbs-presenter-embedded');
        if (!container) return;
        container.classList.toggle('collapsed');
        
        const toggleBtn = header.querySelector('#hbs-presenter-toggle');
        if (toggleBtn) {
            const icon = toggleBtn.querySelector('i');
            if (icon) {
                icon.classList.toggle('fa-chevron-up', !container.classList.contains('collapsed'));
                icon.classList.toggle('fa-chevron-down', container.classList.contains('collapsed'));
            }
        }
    });

    window.HBSPresenterUI = {
        getEmbedded,
        getOverlay,
        resolveMeta,
        formatMessage,
        ensureBuilt,
        renderDisabledState,
        clearDisabledState,
        applyFilters
    };

})();
