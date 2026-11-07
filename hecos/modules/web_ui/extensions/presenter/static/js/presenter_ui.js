/**
 * Hecos Presenter — UI & Rendering Logic
 */
(function () {
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
        const isNetSearch = container.classList.contains('netsearch-presenter-embedded') || container.closest('.search-copilot') || (window.location && window.location.pathname.includes('/netsearch'));
        const filterTypes = isNetSearch
            ? Object.entries(state.TYPE_META).filter(([k]) => ['search_milestone', 'search_commentary'].includes(k))
            : Object.entries(state.TYPE_META).filter(([k]) => k !== 'default' && !['search_milestone', 'search_commentary'].includes(k));

        // Subbar is hidden in NetSearch context (no playbook or event stats needed there)
        const subbarHidden = isNetSearch ? 'display:none;' : '';
        // Restore subbar open/closed state from localStorage (default closed on mobile <=768px)
        const isMobileView = window.innerWidth <= 768;
        const subbarStored = localStorage.getItem('hecos_presenter_subbar_open');
        const subbarOpen = subbarStored !== null ? subbarStored !== 'false' : !isMobileView;

        container.innerHTML = `
            <div class="hbs-presenter-header" style="cursor: pointer;">
                <div class="hbs-presenter-brand">
                    <div class="hbs-presenter-avatar"><i class="fas fa-bullhorn"></i></div>
                    <div class="hbs-presenter-title">Presenter</div>
                    <button id="hbs-presenter-power-btn" onclick="window.Presenter.togglePower(event)"
                        title="Toggle Presenter (Turn ON/OFF)"
                        style="display:inline-flex; align-items:center; gap:4px; margin-left: 6px; background: rgba(168, 85, 247, 0.15); border: 1px solid rgba(168, 85, 247, 0.35); color: #c084fc; padding: 1.5px 7px; border-radius: 10px; font-size: 10px; font-weight: 700; cursor: pointer; transition: all 0.2s ease; line-height: 1.2;">
                        <i class="fas fa-power-off" style="font-size: 8.5px;"></i>
                        <span class="power-label">ON</span>
                    </button>
                </div>

                <div class="hbs-presenter-spacer"></div>

                <div class="hbs-presenter-controls">
                    <label class="hbs-presenter-ctrl-label" title="Remember height and max lines for next sessions">
                        <input type="checkbox" id="hbs-presenter-remember-size" ${uiState.save ? 'checked' : ''} onchange="window.Presenter.saveUIState()"> Save UI
                    </label>
                    <div class="hbs-presenter-max-lines-box">
                        <span>Max lines:</span>
                        <input type="number" id="hbs-presenter-max-lines" class="presenter-dark-input" value="${uiState.lines}" min="1" max="500" onchange="window.Presenter.saveUIState(); window.Presenter.adaptHeight();">
                        <button onclick="window.Presenter.adaptHeight()" title="Adatta altezza alle righe visibili">Adapt</button>
                    </div>
                    <button id="hbs-presenter-reset-btn" onclick="window.Presenter.resetFeed(event)" title="Reset &amp; reload Presenter feed" style="background: rgba(255,255,255,0.07); border: 1px solid rgba(255,255,255,0.1); color: var(--muted); font-size: 10px; padding: 2px 8px; border-radius: 3px; cursor: pointer; display:flex; align-items:center; gap:4px; transition: all 0.2s; white-space:nowrap; flex-shrink:0;" onmouseover="this.style.background='rgba(255,255,255,0.15)'; this.style.color='var(--text)';" onmouseout="this.style.background='rgba(255,255,255,0.07)'; this.style.color='var(--muted)';">
                        <i class="fas fa-sync-alt"></i> <span class="presenter-btn-text">Reset</span>
                    </button>
                    <button id="hbs-presenter-advanced-toggle" onclick="window.Presenter.toggleAdvanced()" title="Advanced filters &amp; search" style="background: rgba(255,255,255,0.07); border: 1px solid rgba(255,255,255,0.1); color: var(--muted); font-size: 10px; padding: 2px 8px; border-radius: 3px; cursor: pointer; display:flex; align-items:center; gap:4px; transition: background 0.2s; white-space:nowrap; flex-shrink:0;" onmouseover="this.style.background='rgba(255,255,255,0.14)'" onmouseout="this.style.background='rgba(255,255,255,0.07)'">
                        <i class="fas fa-sliders-h"></i> <span class="presenter-btn-text">Advanced</span>
                    </button>
                    <a href="/hecos/config/ui#presenter" target="_blank" title="Open Presenter Settings" style="display:flex; align-items:center; justify-content:center; width:24px; height:24px; border-radius:50%; background: rgba(255,255,255,0.07); border: 1px solid rgba(255,255,255,0.1); color: var(--muted); font-size: 11px; cursor: pointer; transition: all 0.2s; text-decoration:none; flex-shrink:0;" onmouseover="this.style.background='rgba(255,255,255,0.18)'; this.style.color='var(--text)';" onmouseout="this.style.background='rgba(255,255,255,0.07)'; this.style.color='var(--muted)';">
                        <i class="fas fa-cog"></i>
                    </a>
                    ${!isNetSearch ? `
                    <button id="hbs-presenter-subbar-btn"
                        title="${subbarOpen ? 'Hide info bar (Playbook & Stats)' : 'Show info bar (Playbook & Stats)'}"
                        onclick="window.HBSPresenterUI.toggleSubbar(event)"
                        style="display:inline-flex; align-items:center; justify-content:center; width:22px; height:22px; border-radius:4px; background: ${subbarOpen ? 'rgba(99,102,241,0.18)' : 'rgba(255,255,255,0.07)'}; border: 1px solid ${subbarOpen ? 'rgba(99,102,241,0.4)' : 'rgba(255,255,255,0.1)'}; color: ${subbarOpen ? '#a5b4fc' : 'var(--muted)'}; font-size: 11px; cursor: pointer; transition: all 0.2s; flex-shrink:0;"
                        onmouseover="this.style.background='rgba(99,102,241,0.28)'; this.style.borderColor='rgba(99,102,241,0.55)'; this.style.color='#c7d2fe';"
                        onmouseout="this.style.background=window.HBSPresenterUI.isSubbarOpen()?'rgba(99,102,241,0.18)':'rgba(255,255,255,0.07)'; this.style.borderColor=window.HBSPresenterUI.isSubbarOpen()?'rgba(99,102,241,0.4)':'rgba(255,255,255,0.1)'; this.style.color=window.HBSPresenterUI.isSubbarOpen()?'#a5b4fc':'var(--muted)';">
                        <i class="fas fa-layer-group" style="font-size:9.5px;"></i>
                    </button>` : ''}
                </div>

                <button id="hbs-presenter-toggle" class="hbs-presenter-toggle-btn" onclick="window.Presenter.togglePower(event)" title="Collapse/Expand">
                    <i class="fas fa-chevron-up"></i>
                </button>
            </div>

            <!-- Sub-bar: Playbook pill + Event stats — hidden in NetSearch context -->
            <div id="hbs-presenter-subbar" class="hbs-presenter-subbar ${subbarOpen ? 'open' : ''}" style="${subbarHidden}">
                <div id="hbs-presenter-playbook-pill" class="hbs-presenter-playbook-pill" style="display:none;"></div>
                <div id="hbs-presenter-stats-container" class="hbs-presenter-stats-container"></div>
                <div class="hbs-presenter-subbar-spacer"></div>
            </div>

            <!-- Advanced panel: hidden by default -->
            <div id="hbs-presenter-advanced" style="display:none; padding: 6px 12px 8px 12px; background: rgba(0,0,0,0.2); border-bottom: 1px solid rgba(255,255,255,0.06);">
                <div style="display:flex; align-items:center; gap:8px; margin-bottom:8px;">
                    <i class="fas fa-search" style="color:var(--muted); font-size:11px;"></i>
                    <input id="hbs-presenter-search" type="text" placeholder="${isNetSearch ? 'Search events &amp; commentary...' : 'Search messages...'}" oninput="window.Presenter.setSearch(this.value)" style="flex:1; background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); border-radius: 4px; padding: 4px 8px; color: var(--text); font-size: 11px; outline: none;">
                    <button onclick="document.getElementById('hbs-presenter-search').value=''; window.Presenter.setSearch('');" title="Clear search" style="background:none; border:none; color:var(--muted); cursor:pointer; font-size:12px;"><i class="fas fa-times"></i></button>
                </div>
                <div style="font-size:10px; color:var(--muted); margin-bottom:5px; letter-spacing:0.5px; text-transform:uppercase;">${isNetSearch ? 'Filter search events:' : 'Filter by type:'}</div>
                <div id="hbs-presenter-filter-chips" style="display:flex; flex-wrap:wrap; gap:5px;">
                    <button id="hbs-presenter-filter-all" onclick="window.Presenter.toggleAllFilters(this)"
                        title="Toggle all categories"
                        style="display:inline-flex;align-items:center;gap:4px; font-size:10px; padding:2px 8px; border-radius:12px; border:1px solid rgba(255,255,255,0.25); background: rgba(255,255,255,0.12); color:var(--text); cursor:pointer; transition: all 0.15s; font-weight:700;">
                        <i class="fas fa-eye" style="font-size:9px;"></i> All
                    </button>
                    ${filterTypes.map(([k, v]) => `
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

            <div class="hbs-presenter-body" style="${(!isMobileView && uiState.save && uiState.height) ? 'height:' + uiState.height + 'px;' : 'height: auto;'}"></div>
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

    function escapeHtml(str) {
        if (!str) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    async function simAction(action, e) {
        if (e) {
            e.preventDefault();
            e.stopPropagation();
        }
        try {
            let chatId = (window.chatHistoryState && window.chatHistoryState.activeSessionId) ||
                localStorage.getItem('hecos_active_session_id') ||
                window.currentSessionId ||
                window.selectedSessionId ||
                (window.privacy_manager && typeof window.privacy_manager.get_session_id === 'function' ? window.privacy_manager.get_session_id() : 'default') ||
                'default';

            const res = await fetch(`/api/ext/presenter/simulation/${action}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ chat_id: chatId })
            });
            const data = await res.json();
            if (data.ok) {
                if (window.Presenter && typeof window.Presenter.updatePlaybookStatus === 'function') {
                    window.Presenter.updatePlaybookStatus(true);
                }
            } else {
                alert(`Simulation action failed: ${data.error || 'Unknown error'}`);
            }
        } catch (err) {
            console.error(`[Simulation] ${action} failed:`, err);
        }
    }

    function renderPlaybookPill(status) {
        const emb = getEmbedded();
        if (!emb) return;
        if (emb.classList.contains('netsearch-presenter-embedded') || emb.closest('.search-copilot') || (window.location && window.location.pathname.includes('/netsearch'))) {
            const existing = emb.querySelector('#hbs-presenter-playbook-pill');
            if (existing) existing.style.display = 'none';
            return;
        }
        // Pill is pre-rendered inside #hbs-presenter-subbar by ensureBuilt() — just look it up.
        // No dynamic insertBefore needed; this eliminates the DOMException from the old approach.
        let pill = emb.querySelector('#hbs-presenter-playbook-pill');
        if (!pill) return; // subbar not yet built

        if (!status || !status.installed) {
            pill.style.display = 'none';
            return;
        }

        pill.style.display = 'inline-flex';

        if (status.has_active && status.active_playbook) {
            const pb = status.active_playbook;
            const sim = status.simulation || { status: 'idle', turn_count: 0, swapped: false, violations: [] };
            const m = pb.mission || {};
            const iconClass = pb.icon || 'fa-book-open';
            const modeLabel = pb.mode ? pb.mode.charAt(0).toUpperCase() + pb.mode.slice(1) : 'Training';
            const simStatus = sim.status || 'idle';
            const isRunning = simStatus === 'running';
            const isPaused = simStatus === 'paused';
            const isSwapped = !!sim.swapped;

            function extractRoleName(val, fallback) {
                if (typeof val === 'string' && val.trim()) return val.trim();
                if (val && typeof val === 'object') {
                    if (typeof val.role === 'string' && val.role.trim()) return val.role.trim();
                    if (typeof val.name === 'string' && val.name.trim()) return val.name.trim();
                }
                return fallback;
            }

            const rawUser = extractRoleName(m.user_role, 'User');
            const rawChat = extractRoleName(m.chat_role, 'Interlocutor');
            const effUser = extractRoleName(sim.user_role, isSwapped ? rawChat : rawUser);
            const effChat = extractRoleName(sim.chat_role, isSwapped ? rawUser : rawChat);

            const swapTitle = isSwapped
                ? `⇄ Swap Roles (ACTIVE) — Roles are inverted: You play [${effUser}], AI plays [${effChat}] (Click to restore original roles)`
                : `⇄ Swap Roles — Current: You play [${effUser}], AI plays [${effChat}] (Click to invert roles)`;

            let dotClass = 'dot-active';
            let dotStyle = '';
            let simBadge = '';
            let simButtons = '';

            if (isRunning) {
                dotStyle = 'background:#10b981; box-shadow:0 0 7px #10b981;';
                simBadge = `<span style="font-size:9px; font-weight:700; color:#10b981; background:rgba(16,185,129,0.15); padding:2px 8px; border-radius:20px; border:1px solid rgba(16,185,129,0.3);">RUNNING (T${sim.turn_count || 0})</span>`;
                simButtons = `
                    <button class="pb-sim-btn pb-sim-btn-pause" onclick="window.HBSPresenterUI.simAction('pause', event)" title="Pause Simulation">
                        <i class="fas fa-pause"></i>
                    </button>
                    <button class="pb-sim-btn pb-sim-btn-stop" onclick="window.HBSPresenterUI.simAction('stop', event)" title="Stop Simulation (Return to Normal Chat)">
                        <i class="fas fa-stop"></i>
                    </button>
                    <button class="pb-sim-btn pb-sim-btn-swap ${isSwapped ? 'swapped' : ''}" onclick="window.HBSPresenterUI.simAction('swap', event)" title="${escapeHtml(swapTitle)}">
                        <i class="fas fa-exchange-alt"></i> ${isSwapped ? 'Swapped' : 'Swap'}
                    </button>
                `;
            } else if (isPaused) {
                dotStyle = 'background:#f59e0b; box-shadow:0 0 7px #f59e0b;';
                simBadge = `<span style="font-size:9px; font-weight:700; color:#fbbf24; background:rgba(245,158,11,0.15); padding:2px 8px; border-radius:20px; border:1px solid rgba(245,158,11,0.3);">PAUSED</span>`;
                simButtons = `
                    <button class="pb-sim-btn pb-sim-btn-play" onclick="window.HBSPresenterUI.simAction('start', event)" title="Resume Simulation">
                        <i class="fas fa-play"></i>
                    </button>
                    <button class="pb-sim-btn pb-sim-btn-stop" onclick="window.HBSPresenterUI.simAction('stop', event)" title="Stop Simulation">
                        <i class="fas fa-stop"></i>
                    </button>
                    <button class="pb-sim-btn pb-sim-btn-swap ${isSwapped ? 'swapped' : ''}" onclick="window.HBSPresenterUI.simAction('swap', event)" title="${escapeHtml(swapTitle)}">
                        <i class="fas fa-exchange-alt"></i> ${isSwapped ? 'Swapped' : 'Swap'}
                    </button>
                `;
            } else {
                dotStyle = 'background:#64748b;';
                simBadge = `<span style="font-size:9px; color:#94a3b8; background:rgba(148,163,184,0.15); padding:2px 8px; border-radius:20px; border:1px solid rgba(148,163,184,0.25);">IDLE</span>`;
                simButtons = `
                    <button class="pb-sim-btn pb-sim-btn-play" onclick="window.HBSPresenterUI.simAction('start', event)" title="Start Live Simulation (Activate Mission, Roles &amp; Rules)">
                        <i class="fas fa-play" style="font-size:8px;"></i> Start
                    </button>
                    <button class="pb-sim-btn pb-sim-btn-swap ${isSwapped ? 'swapped' : ''}" onclick="window.HBSPresenterUI.simAction('swap', event)" title="${escapeHtml(swapTitle)}">
                        <i class="fas fa-exchange-alt"></i> ${isSwapped ? 'Swapped' : 'Swap'}
                    </button>
                `;
            }

            // Detailed tabs & targets breakdown for tooltip
            const tabLines = (pb.tabs || []).map((t, idx) => {
                const tgt = (t.target || 'presenter').toUpperCase();
                const mark = t.enabled !== false ? '✓' : '✗';
                return `  ${idx + 1}. [${mark}] ${t.name || 'Tab'} (${tgt})`;
            }).join('\n');

            pill.classList.remove('inactive');
            pill.title = `Active Playbook: ${pb.name} (${modeLabel} Mode)\n` +
                `Simulation: ${simStatus.toUpperCase()}` + (isSwapped ? ' [Roles Swapped]' : '') + `\n` +
                `Assigned Roles:\n  • You (User): ${effUser}\n  • Chat (AI): ${effChat}\n` +
                `Active Tabs: ${pb.enabled_tabs}/${pb.total_tabs} injected into prompts\n\n` +
                `Tabs & Target Breakdown:\n${tabLines}\n\n` +
                `Click name to open Playbooks Hub`;

            pill.innerHTML = `
                <div class="${dotClass}" style="${dotStyle}" title="Simulation ${simStatus}"></div>
                <i class="fas ${escapeHtml(iconClass)}" style="color:#60a5fa; font-size:10px;"></i>
                <span class="pb-name-click" style="font-weight:600; color:#fff; overflow:hidden; text-overflow:ellipsis; max-width:110px; cursor:pointer;" title="Open Playbooks Studio">${escapeHtml(pb.name)}</span>
                ${simBadge}
                <div class="pb-sim-actions" style="display:inline-flex; align-items:center; gap:4px; margin-left:4px;">
                    ${simButtons}
                </div>
            `;
            pill.onclick = (e) => {
                if (e.target.closest('.pb-sim-btn')) return;
                e.stopPropagation();
                window.open('/hecos/config/ui#playbooks', '_blank');
            };
        } else {
            pill.classList.add('inactive');
            pill.title = `Playbooks Engine installed (${status.total_installed || 0} available), but none currently active.\nClick to configure.`;
            pill.innerHTML = `
                <div class="dot-inactive" title="Inactive"></div>
                <i class="fas fa-book-open" style="color:var(--muted); font-size:10px;"></i>
                <span style="color:var(--muted); font-size:10.5px; font-weight:500;">Playbook: Off</span>
            `;
            pill.onclick = (e) => {
                e.stopPropagation();
                window.open('/hecos/config/ui#playbooks', '_blank');
            };
        }
    }

    function updatePowerUI(active) {
        const emb = getEmbedded();
        if (!emb) return;
        const pwr = emb.querySelector('#hbs-presenter-power-btn');
        if (pwr) {
            const lbl = pwr.querySelector('.power-label');
            if (active) {
                pwr.style.background = 'rgba(168, 85, 247, 0.15)';
                pwr.style.borderColor = 'rgba(168, 85, 247, 0.35)';
                pwr.style.color = '#c084fc';
                if (lbl) lbl.textContent = 'ON';
                pwr.title = 'Presenter is ACTIVE (Click to turn OFF and save resources)';
            } else {
                pwr.style.background = 'rgba(255, 255, 255, 0.06)';
                pwr.style.borderColor = 'rgba(255, 255, 255, 0.14)';
                pwr.style.color = 'var(--muted)';
                if (lbl) lbl.textContent = 'OFF';
                pwr.title = 'Presenter is OFF (Click to turn ON)';
            }
        }
        const toggleBtn = emb.querySelector('#hbs-presenter-toggle');
        if (toggleBtn) {
            const icon = toggleBtn.querySelector('i');
            if (icon) {
                icon.classList.toggle('fa-chevron-up', active);
                icon.classList.toggle('fa-chevron-down', !active);
            }
        }
    }

    // ── Sub-bar toggle ────────────────────────────────────────────────
    function isSubbarOpen() {
        const stored = localStorage.getItem('hecos_presenter_subbar_open');
        return stored !== null ? stored !== 'false' : (window.innerWidth > 768);
    }

    function toggleSubbar(e) {
        if (e) e.stopPropagation();
        const subbar = document.getElementById('hbs-presenter-subbar');
        const btn = document.getElementById('hbs-presenter-subbar-btn');
        if (!subbar) return;

        const willOpen = !subbar.classList.contains('open');
        subbar.classList.toggle('open', willOpen);
        localStorage.setItem('hecos_presenter_subbar_open', willOpen ? 'true' : 'false');

        if (btn) {
            btn.title = willOpen ? 'Hide info bar (Playbook & Stats)' : 'Show info bar (Playbook & Stats)';
            btn.style.background = willOpen ? 'rgba(99,102,241,0.18)' : 'rgba(255,255,255,0.07)';
            btn.style.borderColor = willOpen ? 'rgba(99,102,241,0.4)' : 'rgba(255,255,255,0.1)';
            btn.style.color = willOpen ? '#a5b4fc' : 'var(--muted)';
        }
    }

    // Toggle Collapse & Power Events
    document.addEventListener('click', (e) => {
        if (!e.target || typeof e.target.closest !== 'function') return;
        const header = e.target.closest('.hbs-presenter-header');
        if (!header) return;

        // Sub-bar toggle, power, or chevron button — handled by their own onclick
        if (e.target.closest('#hbs-presenter-subbar-btn') ||
            e.target.closest('#hbs-presenter-power-btn') ||
            e.target.closest('#hbs-presenter-toggle')) {
            return;
        }

        // Prevent collapse if clicking on controls, inputs, links, or playbook pill
        if (e.target.closest('.hbs-presenter-controls') || e.target.closest('input') || e.target.closest('a') || e.target.closest('.hbs-presenter-playbook-pill')) {
            return;
        }

        const container = document.getElementById('hbs-presenter-embedded');
        if (!container) return;

        if (window.Presenter && typeof window.Presenter.togglePower === 'function') {
            window.Presenter.togglePower(e);
        } else {
            container.classList.toggle('collapsed');
        }
    });

    // ── Session Feed Cache ───────────────────────────────────────────
    function saveCurrentSessionFeed(targetSid) {
        const state = window.HBSPresenterState;
        const sid = targetSid || state.currentSessionId || localStorage.getItem('hecos_active_session_id') || 'global';
        if (!sid) return;
        const emb = getEmbedded();
        if (!emb) return;
        const msgEl = emb.querySelector('.hbs-presenter-body');
        if (!msgEl) return;

        state.sessionFeeds = state.sessionFeeds || {};
        const feedData = {
            html: msgEl.innerHTML,
            history: [...state.feedHistory],
            timestamp: Date.now()
        };
        state.sessionFeeds[sid] = feedData;
        try {
            sessionStorage.setItem('hecos_pfeed_' + sid, JSON.stringify(feedData));
        } catch (e) { }
    }

    function restoreSessionFeed(sid) {
        if (!sid) return false;
        const emb = getEmbedded();
        if (!emb) return false;
        const msgEl = emb.querySelector('.hbs-presenter-body');
        if (!msgEl) return false;
        const state = window.HBSPresenterState;

        let feedData = state.sessionFeeds && state.sessionFeeds[sid];
        if (!feedData || !feedData.html) {
            try {
                const raw = sessionStorage.getItem('hecos_pfeed_' + sid);
                if (raw) {
                    feedData = JSON.parse(raw);
                    state.sessionFeeds = state.sessionFeeds || {};
                    state.sessionFeeds[sid] = feedData;
                }
            } catch (e) { }
        }

        if (feedData && typeof feedData.html === 'string' && feedData.html.trim().length > 0) {
            msgEl.innerHTML = feedData.html;
            state.feedHistory = Array.isArray(feedData.history) ? [...feedData.history] : [];
            msgEl.scrollTop = msgEl.scrollHeight;
            if (window.HBSPresenterStats && typeof window.HBSPresenterStats.syncFromDOM === 'function') {
                window.HBSPresenterStats.syncFromDOM();
            } else if (window.HBSPresenterStatsUI && typeof window.HBSPresenterStatsUI.render === 'function') {
                window.HBSPresenterStatsUI.render();
            }
            return true;
        }
        return false;
    }

    function loadSessionFeed(sessionId, isNewSession = false) {
        if (!sessionId) return;
        const state = window.HBSPresenterState;

        // 1. Save outgoing session's feed before switching
        const prevSid = state.currentSessionId;
        if (prevSid && prevSid !== sessionId) {
            saveCurrentSessionFeed(prevSid);
        }
        state.currentSessionId = sessionId;
        localStorage.setItem('hecos_active_session_id', sessionId);

        const notifyFn = (opts) => {
            if (window.Presenter && typeof window.Presenter.notify === 'function') {
                window.Presenter.notify(opts);
            }
        };

        // 2. New chat session creation: boot ONCE only
        if (isNewSession) {
            if (state.sessionBooted && state.sessionBooted[sessionId]) {
                console.debug('[Presenter] Session already booted, ignoring duplicate boot:', sessionId);
                return;
            }
            state.sessionBooted = state.sessionBooted || {};
            state.sessionBooted[sessionId] = true;
            state.appBooted = true;

            if (window.Presenter && window.Presenter.clear) window.Presenter.clear();
            notifyFn({
                type: 'system_info',
                text: 'Presenter core online.',
                duration: 4000,
                persist: false
            });
            setTimeout(() => { if (window.Presenter && window.Presenter.briefing) window.Presenter.briefing(); }, 400);
            setTimeout(() => { if (window.Presenter && window.Presenter.logShortcuts) window.Presenter.logShortcuts(); }, 3500);
            setTimeout(() => { if (window.Presenter && window.Presenter.updatePlaybookStatus) window.Presenter.updatePlaybookStatus(true); }, 1200);
            return;
        }

        // 3. Switching to an EXISTING session (isNewSession === false)
        state.sessionBooted = state.sessionBooted || {};
        state.sessionBooted[sessionId] = true;

        // Fast restore from memory / sessionStorage cache
        const restored = restoreSessionFeed(sessionId);
        if (restored) {
            applyFilters();
            if (window.Presenter && window.Presenter.updatePlaybookStatus) window.Presenter.updatePlaybookStatus(false);
            return;
        }

        // Not yet in cache: fetch from disk
        const chatParam = `&chat_id=${encodeURIComponent(sessionId)}`;
        fetch(`/api/ext/presenter/feed?limit=30${chatParam}`)
            .then(res => res.json())
            .then(data => {
                if (state.currentSessionId !== sessionId) return;

                if (window.Presenter && window.Presenter.clear) window.Presenter.clear();
                const isNetSearch = (window.location && window.location.pathname.includes('/netsearch')) || (getEmbedded() && getEmbedded().classList.contains('netsearch-presenter-embedded'));
                const hasEntries = data.ok && Array.isArray(data.entries) && data.entries.length > 0;
                let renderedCount = 0;
                if (hasEntries) {
                    data.entries.forEach(entry => {
                        const entryType = entry.event_name || 'system_info';
                        const entryText = entry.text || '';
                        if (isNetSearch) {
                            const isSearch = entryType.startsWith('search_') || entryText.includes('[NetSearch]');
                            if (!isSearch) return;
                        }
                        if (entryText) {
                            renderedCount++;
                            notifyFn({
                                type: entryType === 'presenter_feed' ? 'system_info' : entryType,
                                text: entryText,
                                title: 'Presenter',
                                duration: 0,
                                persist: true,
                                timestamp: entry.timestamp
                            });
                        }
                    });
                }
                if (window.HBSPresenterStats && typeof window.HBSPresenterStats.syncFromDOM === 'function') {
                    window.HBSPresenterStats.syncFromDOM();
                } else if (window.HBSPresenterStatsUI && typeof window.HBSPresenterStatsUI.render === 'function') {
                    window.HBSPresenterStatsUI.render();
                }
                if (isNetSearch && renderedCount === 0) {
                    const emb = getEmbedded();
                    const msgEl = emb ? emb.querySelector('.hbs-presenter-body') : null;
                    if (msgEl) {
                        msgEl.innerHTML = '<div class="hbs-presenter-empty-search" style="color:var(--muted);font-size:11px;font-style:italic;padding:14px 6px;text-align:center;opacity:0.7;"><i class="fas fa-satellite-dish" style="margin-right:6px;"></i>Waiting for search events &amp; live commentary...</div>';
                    }
                } else if (!isNetSearch && !hasEntries) {
                    if (window.Presenter && window.Presenter.updatePlaybookStatus) window.Presenter.updatePlaybookStatus(true);
                }
                saveCurrentSessionFeed(sessionId);
                applyFilters();
            })
            .catch(err => {
                console.debug('[Presenter] loadSessionFeed error:', err);
                if (window.Presenter && window.Presenter.updatePlaybookStatus) window.Presenter.updatePlaybookStatus(false);
            });
    }

    function resetFeed(e) {
        if (e) {
            e.preventDefault();
            e.stopPropagation();
        }

        const btn = document.getElementById('hbs-presenter-reset-btn');
        const icon = btn ? btn.querySelector('i') : null;
        if (icon) {
            icon.classList.add('fa-spin');
            setTimeout(() => icon.classList.remove('fa-spin'), 1000);
        }

        const state = window.HBSPresenterState;
        const sid = state.currentSessionId || localStorage.getItem('hecos_active_session_id') || 'global';

        if (state.sessionFeeds && sid) {
            delete state.sessionFeeds[sid];
        }
        try {
            sessionStorage.removeItem('hecos_pfeed_' + sid);
        } catch (err) { }

        state.sessionBooted = state.sessionBooted || {};
        state.sessionBooted[sid] = true;
        state.appBooted = true;
        window._briefingInProgress = false;

        if (window.Presenter && window.Presenter.clear) window.Presenter.clear();

        const isNetSearch = (window.location && window.location.pathname.includes('/netsearch')) || (getEmbedded() && getEmbedded().classList.contains('netsearch-presenter-embedded'));
        if (isNetSearch) {
            loadSessionFeed('global', false);
            return;
        }

        const notifyFn = (opts) => {
            if (window.Presenter && typeof window.Presenter.notify === 'function') {
                window.Presenter.notify(opts);
            }
        };

        notifyFn({
            type: 'system_info',
            text: 'Presenter core reloaded.',
            duration: 4000,
            persist: false
        });
        setTimeout(() => { if (window.Presenter && window.Presenter.briefing) window.Presenter.briefing(); }, 400);
        setTimeout(() => { if (window.Presenter && window.Presenter.logShortcuts) window.Presenter.logShortcuts(); }, 3500);
        setTimeout(() => { if (window.Presenter && window.Presenter.updatePlaybookStatus) window.Presenter.updatePlaybookStatus(true); }, 1200);
    }

    // ── Filter & Search Controls ──────────────────────────────────────
    function toggleFilter(type, btn) {
        const state = window.HBSPresenterState;
        const isHidden = state.presenterHiddenTypes.has(type);
        if (isHidden) {
            state.presenterHiddenTypes.delete(type);
            if (btn) { btn.style.opacity = '1'; btn.style.textDecoration = 'none'; }
        } else {
            state.presenterHiddenTypes.add(type);
            if (btn) { btn.style.opacity = '0.35'; btn.style.textDecoration = 'line-through'; }
        }
        applyFilters();
    }

    function resetFilters() {
        const state = window.HBSPresenterState;
        state.presenterHiddenTypes.clear();
        state.presenterSearchQuery = '';
        const searchInput = document.getElementById('hbs-presenter-search');
        if (searchInput) searchInput.value = '';
        document.querySelectorAll('[data-filter-type]').forEach(btn => {
            btn.style.opacity = '1';
            btn.style.textDecoration = 'none';
        });
        const allBtn = document.getElementById('hbs-presenter-filter-all');
        if (allBtn) {
            allBtn.style.background = 'rgba(255,255,255,0.12)';
            allBtn.style.color = 'var(--text)';
            allBtn.innerHTML = '<i class="fas fa-eye" style="font-size:9px;"></i> All';
            allBtn._allHidden = false;
        }
        applyFilters();
    }

    function toggleAllFilters(btn) {
        const state = window.HBSPresenterState;
        const allHidden = btn._allHidden;
        const isNetSearch = (window.location && window.location.pathname.includes('/netsearch')) || (getEmbedded() && getEmbedded().classList.contains('netsearch-presenter-embedded'));
        const allTypes = isNetSearch
            ? ['search_milestone', 'search_commentary']
            : Object.keys(state.TYPE_META).filter(k => k !== 'default' && !['search_milestone', 'search_commentary'].includes(k));

        if (allHidden) {
            state.presenterHiddenTypes.clear();
            document.querySelectorAll('[data-filter-type]').forEach(chip => {
                chip.style.opacity = '1';
                chip.style.textDecoration = 'none';
            });
            btn.style.background = 'rgba(255,255,255,0.12)';
            btn.style.color = 'var(--text)';
            btn.innerHTML = '<i class="fas fa-eye" style="font-size:9px;"></i> All';
            btn._allHidden = false;
        } else {
            allTypes.forEach(t => state.presenterHiddenTypes.add(t));
            document.querySelectorAll('[data-filter-type]').forEach(chip => {
                chip.style.opacity = '0.35';
                chip.style.textDecoration = 'line-through';
            });
            btn.style.background = 'rgba(239,68,68,0.15)';
            btn.style.color = '#ef4444';
            btn.innerHTML = '<i class="fas fa-eye-slash" style="font-size:9px;"></i> All';
            btn._allHidden = true;
        }
        applyFilters();
    }

    function setSearch(query) {
        const state = window.HBSPresenterState;
        state.presenterSearchQuery = (query || '').trim();
        applyFilters();
    }

    function toggleAdvanced(panel, btn) {
        if (!panel) return;
        const isOpen = panel.style.display !== 'none';
        panel.style.display = isOpen ? 'none' : 'block';
        if (btn) {
            btn.style.background = isOpen ? 'rgba(255,255,255,0.07)' : 'rgba(102,252,241,0.12)';
            btn.style.borderColor = isOpen ? 'rgba(255,255,255,0.1)' : 'rgba(102,252,241,0.3)';
            btn.style.color = isOpen ? 'var(--muted)' : 'var(--accent, #66fcf1)';
        }
    }

    window.HBSPresenterUI = {
        getEmbedded,
        getOverlay,
        resolveMeta,
        formatMessage,
        ensureBuilt,
        renderDisabledState,
        clearDisabledState,
        applyFilters,
        renderPlaybookPill,
        updatePowerUI,
        simAction,
        toggleSubbar,
        isSubbarOpen,
        // Session Feed Cache
        saveCurrentSessionFeed,
        restoreSessionFeed,
        loadSessionFeed,
        resetFeed,
        // Filter & Search Controls
        toggleFilter,
        resetFilters,
        toggleAllFilters,
        setSearch,
        toggleAdvanced
    };

})();
