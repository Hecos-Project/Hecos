/* cmd_palette.js — HDCS Palette Controller
 *
 * Two modes:
 *   MODE A: Inline suggestions (typing "/" in chat input)
 *     → Shows floating hint below input
 *     → On selection/Enter: populates chat input, fires sendMessage()
 *     → Execution goes via /api/stream → loop.py HDCS (ONE path, no double response)
 *
 *   MODE B: Standalone spotlight (Ctrl+K)
 *     → Full modal overlay
 *     → Executes via /api/commands/run and injects result directly in chat DOM
 */

import { renderPaletteHTML, renderResults, renderHintList } from './cmd_render.js';
import { fetchAllCommands, filterCommands } from './cmd_search.js';
import { executeCommand } from './cmd_execute.js';

let isSpotlightVisible = false;  // MODE B: Ctrl+K standalone
let isHintVisible = false;        // MODE A: inline / hint
let allCommands = [];
let currentResults = [];
let selectedIndex = 0;
let _mode = 'spotlight';           // 'spotlight' | 'inline'

export async function initCommandPalette() {
    // Preload the HTML structure
    renderPaletteHTML();

    // Fetch commands in background so palette is snappy on first open
    allCommands = await fetchAllCommands();

    // Global Ctrl+K: open standalone spotlight (MODE B)
    document.addEventListener('keydown', (e) => {
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            if (isSpotlightVisible) hideSpotlight();
            else openSpotlight();
        }
        if (e.key === 'Escape' && isSpotlightVisible) {
            hideSpotlight();
        }
    });

    // Spotlight modal internals
    const overlay = document.getElementById('cmd-palette-overlay');
    const palInput = document.getElementById('cmd-input');
    const resultsContainer = document.getElementById('cmd-results');

    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) hideSpotlight();
    });

    palInput.addEventListener('input', updateSpotlightResults);

    palInput.addEventListener('keydown', (e) => {
        if (e.key === 'ArrowDown') {
            selectedIndex = Math.min(selectedIndex + 1, currentResults.length - 1);
            renderResults(currentResults, selectedIndex, resultsContainer);
            e.preventDefault();
        } else if (e.key === 'ArrowUp') {
            selectedIndex = Math.max(selectedIndex - 1, 0);
            renderResults(currentResults, selectedIndex, resultsContainer);
            e.preventDefault();
        } else if (e.key === 'Enter') {
            e.preventDefault();
            handleSpotlightExecute();
        }
    });

    resultsContainer.addEventListener('click', (e) => {
        const item = e.target.closest('.cmd-item');
        if (item) {
            selectedIndex = parseInt(item.dataset.index);
            handleSpotlightExecute();
        }
    });

    // MODE A: Inline hint for chat input box
    // NOTE: We do NOT intercept or prevent default — typing / in chat is normal.
    // We just overlay a suggestion hint panel below the input.
    const chatInput = document.getElementById('user-input');
    if (chatInput) {
        chatInput.addEventListener('input', onChatInputChange);
        chatInput.addEventListener('keydown', onChatInputKeydown);
        chatInput.addEventListener('blur', () => {
            // Delay so click events on hint can fire first
            setTimeout(hideHint, 200);
        });
    }
}

// ─── MODE A: Inline Hint ─────────────────────────────────────────────────────

function onChatInputChange() {
    const chatInput = document.getElementById('user-input');
    const val = chatInput.value;
    if (val.startsWith('/')) {
        const filtered = filterCommands(allCommands, val);
        if (filtered.length > 0) {
            showHint(filtered.slice(0, 8));  // Max 8 suggestions
        } else {
            hideHint();
        }
    } else {
        hideHint();
    }
}

function onChatInputKeydown(e) {
    if (!isHintVisible) return;

    const hintEl = document.getElementById('cmd-hint-panel');
    const items = hintEl ? hintEl.querySelectorAll('.cmd-hint-item') : [];

    if (e.key === 'ArrowDown') {
        e.preventDefault();
        const active = hintEl.querySelector('.cmd-hint-item.active');
        if (active) {
            const next = active.nextElementSibling;
            if (next) { active.classList.remove('active'); next.classList.add('active'); }
        } else if (items[0]) {
            items[0].classList.add('active');
        }
    } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        const active = hintEl.querySelector('.cmd-hint-item.active');
        if (active) {
            const prev = active.previousElementSibling;
            if (prev) { active.classList.remove('active'); prev.classList.add('active'); }
        }
    } else if (e.key === 'Tab' || e.key === 'Enter') {
        // Tab: autocomplete; Enter: let chat handle it (which goes via loop.py HDCS)
        const active = hintEl ? hintEl.querySelector('.cmd-hint-item.active') : null;
        const first = hintEl ? hintEl.querySelector('.cmd-hint-item') : null;
        const target = active || first;

        if (target && e.key === 'Tab') {
            // Tab = autocomplete only, don't send
            e.preventDefault();
            const alias = target.dataset.alias;
            const chatInput = document.getElementById('user-input');
            chatInput.value = alias + (target.dataset.requiresArgs === 'true' ? ' ' : '');
            hideHint();
        }
        // Enter falls through to normal chat handleKey → sendMessage() → loop.py
        // No e.preventDefault() here! The HDCS executor in loop.py handles it.
        if (e.key === 'Enter') hideHint();
    } else if (e.key === 'Escape') {
        hideHint();
    }
}

function showHint(commands) {
    isHintVisible = true;
    let panel = document.getElementById('cmd-hint-panel');
    if (!panel) {
        panel = document.createElement('div');
        panel.id = 'cmd-hint-panel';
        document.body.appendChild(panel);
    }

    // Position below the chat input
    const chatInput = document.getElementById('user-input');
    const inputBar = document.getElementById('input-bar');
    const anchor = inputBar || chatInput;
    if (anchor) {
        const rect = anchor.getBoundingClientRect();
        panel.style.cssText = `
            position: fixed;
            bottom: ${window.innerHeight - rect.top + 6}px;
            left: ${rect.left}px;
            width: ${Math.min(rect.width, 520)}px;
            z-index: 9998;
            background: rgba(20,20,28,0.95);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 10px;
            backdrop-filter: blur(10px);
            box-shadow: 0 -8px 30px rgba(0,0,0,0.4);
            overflow: hidden;
            max-height: 320px;
            overflow-y: auto;
        `;
    }

    panel.innerHTML = '';
    commands.forEach((cmd, i) => {
        const item = document.createElement('div');
        item.className = 'cmd-hint-item' + (i === 0 ? ' active' : '');
        item.dataset.alias = cmd.aliases[0];
        item.dataset.requiresArgs = cmd.requires_args ? 'true' : 'false';
        item.style.cssText = `
            display: flex; align-items: center; gap: 10px;
            padding: 10px 14px; cursor: pointer;
            border-left: 3px solid transparent;
            transition: all 0.1s;
            font-size: 13px;
        `;
        item.innerHTML = `
            <span style="font-size:16px;width:20px;text-align:center">${(function(ic){ return (ic && !ic.startsWith('fa-') && !ic.startsWith('fas ') && !ic.startsWith('<i ')) ? ic : '⚡'; })(cmd.icon)}</span>
            <span style="font-family:'JetBrains Mono',monospace;color:#00f3ff;min-width:100px">${cmd.aliases[0]}</span>
            <span style="color:#888;flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${cmd.description}</span>
            <span style="color:#444;font-size:10px;text-transform:uppercase">${cmd.category}</span>
        `;
        item.addEventListener('mouseenter', () => {
            panel.querySelectorAll('.cmd-hint-item').forEach(el => el.classList.remove('active'));
            item.classList.add('active');
        });
        item.addEventListener('mousedown', (e) => {
            // mousedown fires before blur - populate input and send
            e.preventDefault();
            const chatInput = document.getElementById('user-input');
            chatInput.value = cmd.aliases[0] + (cmd.requires_args ? ' ' : '');
            chatInput.focus();
            hideHint();
            if (!cmd.requires_args && window.sendMessage) {
                window.sendMessage(); // fires via loop.py HDCS — one single path
            }
        });
        panel.appendChild(item);
    });
}

function hideHint() {
    isHintVisible = false;
    const panel = document.getElementById('cmd-hint-panel');
    if (panel) panel.remove();
}

// ─── MODE B: Spotlight (Ctrl+K) ──────────────────────────────────────────────

function openSpotlight(initialQuery = '') {
    isSpotlightVisible = true;
    selectedIndex = 0;
    const overlay = document.getElementById('cmd-palette-overlay');
    const input = document.getElementById('cmd-input');
    overlay.classList.add('visible');
    input.value = initialQuery;
    input.focus();
    updateSpotlightResults();
}

function hideSpotlight() {
    isSpotlightVisible = false;
    const overlay = document.getElementById('cmd-palette-overlay');
    overlay.classList.remove('visible');
}

function updateSpotlightResults() {
    const query = document.getElementById('cmd-input').value;
    currentResults = filterCommands(allCommands, query);
    if (selectedIndex >= currentResults.length) selectedIndex = 0;
    renderResults(currentResults, selectedIndex, document.getElementById('cmd-results'));
}

async function handleSpotlightExecute() {
    const query = document.getElementById('cmd-input').value.trim();
    if (!query) return;

    let cmd = currentResults[selectedIndex];

    // Autocomplete if no args typed yet
    if (cmd && cmd.requires_args && !query.includes(' ')) {
        document.getElementById('cmd-input').value = cmd.aliases[0] + ' ';
        updateSpotlightResults();
        return;
    }

    // Build final command string
    let finalInput = query;
    if (!query.startsWith('/') && cmd) finalInput = cmd.aliases[0];
    if (!query.includes(' ') && query.startsWith('/') && cmd) finalInput = query;

    hideSpotlight();

    // Execute via /api/commands/run and render result directly in chat DOM
    const data = await executeCommand(finalInput);
    if (data && data.ok) {
        // Render directly without going through SSE events (avoid double render)
        if (window.hideWelcome) window.hideWelcome();
        if (window.addBubble) {
            window.addBubble('user', finalInput);
            window.addBubble('ai', data.output || '');
        }
        if (window.chatArea) window.chatArea.scrollTop = window.chatArea.scrollHeight;
    }
}
