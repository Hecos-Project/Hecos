/**
 * hecos_cmd_palette.js — HDCS Command Palette
 * Self-contained, no ES module imports needed.
 *
 * Mode A: Typing "/" in the chat textarea → inline hint dropdown (no focus steal)
 * Mode B: Clicking the palette icon button or pressing Ctrl+Shift+Space → full spotlight modal
 *
 * For Mode A: on Enter/click, the chat input is sent via window.sendMessage()
 *             which goes through /api/stream → loop.py HDCS → one single path, no double render.
 * For Mode B: executes via /api/commands/run and injects response directly in DOM.
 */

(function () {
    'use strict';

    let _allCommands = [];
    let _hintVisible = false;
    let _spotlightVisible = false;
    let _spotlightResults = [];
    let _spotlightSelected = 0;
    let _lastActiveElement = null;

    // ── Fetch commands from backend ───────────────────────────────────────────
    async function _fetchCommands() {
        try {
            const res = await fetch('/api/commands/list');
            if (!res.ok) return [];
            const data = await res.json();
            return data.ok ? (data.commands || []) : [];
        } catch (e) {
            console.warn('[HDCS] Could not fetch commands:', e);
            return [];
        }
    }

    // ── Filter logic ──────────────────────────────────────────────────────────
    function _filter(commands, query) {
        if (!query) return commands;
        const q = query.toLowerCase().replace(/^\//, '');
        return commands.filter(cmd => {
            const haystack = [cmd.id, ...cmd.aliases, cmd.description, cmd.category].join(' ').toLowerCase();
            return haystack.includes(q);
        });
    }

    // ══════════════════════════════════════════════════════════════════════════
    // MODE A: Inline Hint Dropdown (chat input "/" trigger)
    // ══════════════════════════════════════════════════════════════════════════

    function _onChatInput(e) {
        const val = e.target.value;
        if (val.startsWith('/')) {
            const filtered = _filter(_allCommands, val);
            if (filtered.length > 0) _showHint(filtered);
            else _hideHint();
        } else {
            _hideHint();
        }
    }

    function _onChatKeydown(e) {
        if (!_hintVisible) return;
        const panel = document.getElementById('hdcs-hint-panel');
        if (!panel) return;
        const items = panel.querySelectorAll('.hdcs-hint-item');
        const activeEl = panel.querySelector('.hdcs-hint-item.active');

        if (e.key === 'ArrowDown') {
            e.preventDefault();
            if (activeEl && activeEl.nextElementSibling) {
                activeEl.classList.remove('active');
                activeEl.nextElementSibling.classList.add('active');
            } else if (!activeEl && items[0]) {
                items[0].classList.add('active');
            }
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            if (activeEl && activeEl.previousElementSibling) {
                activeEl.classList.remove('active');
                activeEl.previousElementSibling.classList.add('active');
            }
        } else if (e.key === 'Tab') {
            // Tab = autocomplete alias in input
            const target = activeEl || items[0];
            if (target) {
                e.preventDefault();
                const targetInput = _lastActiveElement && (_lastActiveElement.tagName === 'INPUT' || _lastActiveElement.tagName === 'TEXTAREA') ? _lastActiveElement : document.getElementById('user-input');
                if (targetInput) {
                    targetInput.value = target.dataset.alias + (target.dataset.needsArgs === 'true' ? ' ' : '');
                    targetInput.dispatchEvent(new Event('input', { bubbles: true }));
                }
                _hideHint();
            }
        } else if (e.key === 'Enter') {
            // Don't prevent default — let the normal chat handleKey() fire
            // which calls sendMessage() → /api/stream → loop.py HDCS (one path only)
            _hideHint();
        } else if (e.key === 'Escape') {
            _hideHint();
        }
    }

    function _showHint(commands) {
        _hintVisible = true;
        let panel = document.getElementById('hdcs-hint-panel');
        if (!panel) {
            panel = document.createElement('div');
            panel.id = 'hdcs-hint-panel';
            document.body.appendChild(panel);
        }

        const anchor = _lastActiveElement || document.getElementById('input-bar') || document.getElementById('user-input');
        if (anchor) {
            const rect = anchor.getBoundingClientRect();
            panel.style.cssText = `
                position:fixed;
                z-index:9990;
                background:rgba(16,16,22,0.97);
                border:1px solid rgba(0,243,255,0.2);
                border-radius:10px;
                backdrop-filter:blur(12px);
                -webkit-backdrop-filter:blur(12px);
                box-shadow:0 -12px 40px rgba(0,0,0,0.5);
                overflow:hidden;
                max-height:300px;
                overflow-y:auto;
                font-family:'Inter','JetBrains Mono',monospace;
            `;
            if (_lastActiveElement && _lastActiveElement.id !== 'user-input') {
                panel.style.top = (rect.bottom + 4) + 'px';
                panel.style.left = rect.left + 'px';
                panel.style.width = Math.min(rect.width, 560) + 'px';
            } else {
                panel.style.bottom = (window.innerHeight - rect.top + 8) + 'px';
                panel.style.left = (rect.left + 8) + 'px';
                panel.style.width = Math.min(rect.width - 16, 560) + 'px';
            }
        }

        panel.innerHTML = '';
        const header = document.createElement('div');
        header.style.cssText = 'padding:6px 14px;font-size:10px;color:#444;text-transform:uppercase;letter-spacing:1px;border-bottom:1px solid rgba(255,255,255,0.05)';
        header.textContent = '⚡ Hecos Direct Commands  —  Tab to complete  ·  Enter to run';
        panel.appendChild(header);

        commands.forEach((cmd, i) => {
            const item = document.createElement('div');
            item.className = 'hdcs-hint-item' + (i === 0 ? ' active' : '');
            item.dataset.alias = cmd.aliases[0];
            item.dataset.needsArgs = cmd.requires_args ? 'true' : 'false';
            item.style.cssText = `
                display:flex;align-items:center;gap:12px;
                padding:9px 14px;cursor:pointer;
                border-left:3px solid transparent;
                transition:all 0.1s;
            `;
            item.innerHTML = `
                <span style="font-size:16px;width:22px;text-align:center">${cmd.icon || '⚡'}</span>
                <span style="font-family:'JetBrains Mono',monospace;color:#00f3ff;min-width:110px;font-size:13px">${cmd.aliases[0]}</span>
                <span style="color:#777;flex:1;font-size:12px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${cmd.description}</span>
                <span style="color:#333;font-size:10px;text-transform:uppercase;letter-spacing:0.5px">${cmd.category}</span>
            `;
            item.addEventListener('mouseenter', () => {
                panel.querySelectorAll('.hdcs-hint-item').forEach(el => el.classList.remove('active'));
                item.classList.add('active');
            });
            item.addEventListener('mousedown', (ev) => {
                ev.preventDefault(); // Prevent blur
                const targetInput = _lastActiveElement && (_lastActiveElement.tagName === 'INPUT' || _lastActiveElement.tagName === 'TEXTAREA') ? _lastActiveElement : document.getElementById('user-input');
                if (targetInput) {
                    targetInput.value = cmd.aliases[0] + (cmd.requires_args ? ' ' : '');
                    targetInput.dispatchEvent(new Event('input', { bubbles: true }));
                    targetInput.focus();
                }
                _hideHint();
                if (!cmd.requires_args && window.sendMessage && (!targetInput || targetInput.id === 'user-input')) {
                    window.sendMessage(); // Fires via loop.py HDCS — one path, no double render
                }
            });
            panel.appendChild(item);
        });
    }

    function _hideHint() {
        _hintVisible = false;
        const panel = document.getElementById('hdcs-hint-panel');
        if (panel) panel.remove();
    }

    // ══════════════════════════════════════════════════════════════════════════
    // MODE B: Spotlight Modal (Ctrl+Shift+Space or palette button)
    // ══════════════════════════════════════════════════════════════════════════

    function _buildSpotlightHTML() {
        if (document.getElementById('hdcs-overlay')) return;
        const el = document.createElement('div');
        el.innerHTML = `
            <div id="hdcs-overlay" style="
                position:fixed;top:0;left:0;right:0;bottom:0;
                background:rgba(0,0,0,0.45);backdrop-filter:blur(5px);-webkit-backdrop-filter:blur(5px);
                z-index:9999;display:none;align-items:flex-start;justify-content:center;
                padding-top:14vh;opacity:0;transition:opacity 0.15s;
            ">
                <div id="hdcs-modal" style="
                    width:90%;max-width:580px;
                    background:rgba(20,20,28,0.92);
                    border:1px solid rgba(255,255,255,0.1);
                    border-radius:14px;
                    box-shadow:0 24px 60px rgba(0,0,0,0.6),inset 0 1px 0 rgba(255,255,255,0.05);
                    overflow:hidden;
                    transform:translateY(-20px) scale(0.96);
                    transition:transform 0.2s cubic-bezier(0.175,0.885,0.32,1.275);
                    font-family:'Inter',sans-serif;
                ">
                    <div style="display:flex;align-items:center;padding:16px 20px;border-bottom:1px solid rgba(255,255,255,0.07)">
                        <i class="fas fa-terminal" style="color:#00f3ff;font-size:17px;margin-right:14px;text-shadow:0 0 10px rgba(0,243,255,0.4)"></i>
                        <input id="hdcs-input" type="text" placeholder="Type a command or search…" autocomplete="off"
                            style="flex:1;background:transparent;border:none;outline:none;color:#fff;font-size:17px;font-family:'JetBrains Mono',monospace;">
                        <span style="color:#444;font-size:11px;margin-left:10px">Ctrl+Alt+Space</span>
                    </div>
                    <div id="hdcs-results" style="max-height:380px;overflow-y:auto;padding:8px 0"></div>
                    <div style="
                        padding:8px 18px;background:rgba(0,0,0,0.25);
                        border-top:1px solid rgba(255,255,255,0.05);
                        display:flex;align-items:center;justify-content:space-between;
                        font-size:11px;color:#555;
                    ">
                        <div style="display:flex;gap:14px">
                            <span><kbd style="background:rgba(255,255,255,0.1);border-radius:3px;padding:1px 5px">↑↓</kbd> Naviga</span>
                            <span><kbd style="background:rgba(255,255,255,0.1);border-radius:3px;padding:1px 5px">Enter</kbd> Esegui</span>
                            <span><kbd style="background:rgba(255,255,255,0.1);border-radius:3px;padding:1px 5px">Esc</kbd> Chiudi</span>
                        </div>
                        <span>HDCS — Hecos Direct Command System</span>
                    </div>
                </div>
            </div>
        `;
        document.body.appendChild(el.firstElementChild);

        // Bindings
        document.getElementById('hdcs-overlay').addEventListener('click', (e) => {
            if (e.target.id === 'hdcs-overlay') _hideSpotlight();
        });
        document.getElementById('hdcs-input').addEventListener('input', _updateSpotlight);
        document.getElementById('hdcs-input').addEventListener('keydown', (e) => {
            if (e.key === 'Escape') { _hideSpotlight(); return; }
            if (e.key === 'ArrowDown') { e.preventDefault(); _spotlightSelected = Math.min(_spotlightSelected + 1, _spotlightResults.length - 1); _renderSpotlight(); }
            if (e.key === 'ArrowUp') { e.preventDefault(); _spotlightSelected = Math.max(_spotlightSelected - 1, 0); _renderSpotlight(); }
            if (e.key === 'Enter') { e.preventDefault(); _execSpotlight(); }
        });
    }

    function _openSpotlight() {
        _lastActiveElement = document.activeElement;
        _spotlightSelected = 0;
        const overlay = document.getElementById('hdcs-overlay');
        overlay.style.display = 'flex';
        requestAnimationFrame(() => { overlay.style.opacity = '1'; document.getElementById('hdcs-modal').style.transform = 'translateY(0) scale(1)'; });
        document.getElementById('hdcs-input').value = '';
        document.getElementById('hdcs-input').focus();
        _updateSpotlight();
        _spotlightVisible = true;
    }

    function _hideSpotlight() {
        _spotlightVisible = false;
        const overlay = document.getElementById('hdcs-overlay');
        if (overlay) {
            overlay.style.opacity = '0';
            document.getElementById('hdcs-modal').style.transform = 'translateY(-20px) scale(0.96)';
            setTimeout(() => { overlay.style.display = 'none'; }, 150);
        }
    }

    function _updateSpotlight() {
        const q = document.getElementById('hdcs-input').value;
        _spotlightResults = _filter(_allCommands, q);
        if (_spotlightSelected >= _spotlightResults.length) _spotlightSelected = 0;
        _renderSpotlight();
    }

    function _renderSpotlight() {
        const container = document.getElementById('hdcs-results');
        if (!container) return;
        container.innerHTML = '';
        if (_spotlightResults.length === 0) {
            container.innerHTML = '<div style="padding:20px;text-align:center;color:#444;font-size:13px">No commands found.</div>';
            return;
        }
        _spotlightResults.forEach((cmd, i) => {
            const isSelected = i === _spotlightSelected;
            const div = document.createElement('div');
            div.style.cssText = `
                display:flex;align-items:center;gap:12px;padding:11px 18px;cursor:pointer;
                border-left:3px solid ${isSelected ? '#00f3ff' : 'transparent'};
                background:${isSelected ? 'linear-gradient(90deg,rgba(0,243,255,0.08) 0%,transparent 100%)' : 'transparent'};
                transition:all 0.1s;
            `;
            const catColor = cmd.category === 'CORE' ? '#00f3ff' : cmd.category === 'FLOWS' ? '#bb86fc' : '#aaa';
            div.innerHTML = `
                <span style="font-size:18px;width:24px;text-align:center">${cmd.icon || '⚡'}</span>
                <div style="flex:1">
                    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:3px">
                        <span style="font-family:'JetBrains Mono',monospace;color:#00f3ff;font-size:14px;font-weight:500">${cmd.aliases[0]}</span>
                        <span style="font-size:10px;padding:2px 6px;border-radius:4px;background:rgba(255,255,255,0.07);color:${catColor}">${cmd.category}</span>
                    </div>
                    <div style="font-size:12px;color:#777">${cmd.description}</div>
                    ${isSelected && cmd.example ? `<div style="font-size:11px;color:#444;font-family:'JetBrains Mono',monospace;margin-top:2px">e.g. ${cmd.example}</div>` : ''}
                </div>
            `;
            div.addEventListener('mouseenter', () => { _spotlightSelected = i; _renderSpotlight(); });
            div.addEventListener('mousedown', (e) => { e.preventDefault(); _spotlightSelected = i; _execSpotlight(); });
            container.appendChild(div);
        });
        // Scroll selected into view
        const selectedEl = container.children[_spotlightSelected + 1]; // +1 for header
        if (selectedEl) selectedEl.scrollIntoView({ block: 'nearest' });
    }

    async function _execSpotlight() {
        const query = document.getElementById('hdcs-input').value.trim();
        if (!query) return;
        const cmd = _spotlightResults[_spotlightSelected];

        // Autocomplete if needs args
        if (cmd && cmd.requires_args && !query.includes(' ')) {
            if (!(_lastActiveElement && (_lastActiveElement.tagName === 'INPUT' || _lastActiveElement.tagName === 'TEXTAREA') && _lastActiveElement.id !== 'hdcs-input' && _lastActiveElement.id !== 'user-input')) {
                document.getElementById('hdcs-input').value = cmd.aliases[0] + ' ';
                _updateSpotlight();
                return;
            }
        }

        const finalInput = query.startsWith('/') ? query : (cmd ? cmd.aliases[0] : query);
        _hideSpotlight();

        // Autocomplete into an active input field (like a Flows node parameter)
        if (_lastActiveElement && (_lastActiveElement.tagName === 'INPUT' || _lastActiveElement.tagName === 'TEXTAREA') && 
            _lastActiveElement.id !== 'hdcs-input' && _lastActiveElement.id !== 'user-input') {
            const start = _lastActiveElement.selectionStart || 0;
            const end = _lastActiveElement.selectionEnd || 0;
            const val = _lastActiveElement.value || "";
            _lastActiveElement.value = val.substring(0, start) + finalInput + val.substring(end);
            _lastActiveElement.dispatchEvent(new Event('input', { bubbles: true }));
            _lastActiveElement.focus();
            return;
        }

        try {
            const res = await fetch('/api/commands/run', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ cmd: finalInput, context: 'spotlight' })
            });
            const data = await res.json();
            if (data.ok) {
                if (window.hideWelcome) window.hideWelcome();
                if (window.addBubble) {
                    window.addBubble('user', finalInput);
                    window.addBubble('ai', data.output || '');
                    if (window.chatArea) window.chatArea.scrollTop = window.chatArea.scrollHeight;
                } else {
                    alert(`⚡ Command Executed: ${finalInput}\n\n${data.output || 'Success'}`);
                }
            } else {
                console.warn('[HDCS] Command error:', data.error);
                if (window.addBubble) {
                    window.addBubble('user', finalInput);
                    window.addBubble('ai', data.output || `❌ ${data.error}`);
                } else {
                    alert(`❌ Error executing ${finalInput}:\n${data.error}\n${data.output || ''}`);
                }
            }
        } catch (err) {
            console.error('[HDCS] Execution failed:', err);
            if (!window.addBubble) alert(`❌ Execution failed: ${err}`);
        }
    }

    // ══════════════════════════════════════════════════════════════════════════
    // INIT
    // ══════════════════════════════════════════════════════════════════════════

    function init() {
        _buildSpotlightHTML();

        // Fetch commands once
        _fetchCommands().then(cmds => {
            _allCommands = cmds;
            console.log(`[HDCS] Loaded ${cmds.length} commands.`);
        });

        // Global keyboard: Ctrl+Alt+Space → spotlight
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey && e.altKey && e.code === 'Space') {
                e.preventDefault();
                if (_spotlightVisible) _hideSpotlight();
                else _openSpotlight();
            }
        });

        // Global input listener: "/" trigger → inline hint (Mode A)
        document.body.addEventListener('input', (e) => {
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
                if (e.target.id === 'hdcs-input') return;
                const val = e.target.value;
                if (val.startsWith('/')) {
                    _lastActiveElement = e.target;
                    const filtered = _filter(_allCommands, val);
                    if (filtered.length > 0) _showHint(filtered);
                    else _hideHint();
                } else {
                    _hideHint();
                }
            }
        });
        document.body.addEventListener('keydown', (e) => {
            if (_hintVisible && (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') && e.target.id !== 'hdcs-input') {
                _onChatKeydown(e);
            }
        });
        document.body.addEventListener('focusout', (e) => {
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
                setTimeout(_hideHint, 200);
            }
        });
    }

    // Run init
    init();

    // Expose globally for palette button and programmatic use
    window.HecosCmd = {
        open: _openSpotlight,
        close: _hideSpotlight,
        reload: () => _fetchCommands().then(c => { _allCommands = c; }),
    };

})();
