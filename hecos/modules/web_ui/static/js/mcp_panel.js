/**
 * mcp_panel.js
 * ─────────────────────────────────────────────────────────────────────────────
 * Hecos MCP Bridge — Config Panel Logic
 * Handles server table rendering, add/remove/toggle servers,
 * MCP inventory polling, registry explorer search, and preset mapping.
 * ─────────────────────────────────────────────────────────────────────────────
 */

// ─────────────────────────────────────────────────────────────────────────────
// State
// ─────────────────────────────────────────────────────────────────────────────

let mcpPollInterval = null;
let mcpLiveInventory = {};  // { serverName: { status, tools } }

// ─────────────────────────────────────────────────────────────────────────────
// Preset Map
// ─────────────────────────────────────────────────────────────────────────────

const mcpPresetsMap = {
    'everything':         { name: 'everything',          cmd: 'npx', args: '-y @modelcontextprotocol/server-everything',         env: {} },
    'sequentialthinking': { name: 'sequential_thinking', cmd: 'npx', args: '-y @modelcontextprotocol/server-sequential-thinking', env: {} },
    'bravesearch':        { name: 'brave_search',        cmd: 'npx', args: '-y @modelcontextprotocol/server-brave-search',        env: { BRAVE_API_KEY: '' } },
    'google-maps':        { name: 'google_maps',         cmd: 'npx', args: '-y @modelcontextprotocol/server-google-maps',         env: { GOOGLE_MAPS_API_KEY: '' } },
    'github':             { name: 'github',              cmd: 'npx', args: '-y @modelcontextprotocol/server-github',              env: { GITHUB_PERSONAL_ACCESS_TOKEN: '' } },
    'filesystem':         { name: 'filesystem',          cmd: 'npx', args: '-y @modelcontextprotocol/server-filesystem /path/to/expose', env: {} },
    'wikipedia':          { name: 'wikipedia',           cmd: 'npx', args: '-y wikipedia-mcp',                                   env: {} },
    'postgres':           { name: 'postgres',            cmd: 'npx', args: '-y @modelcontextprotocol/server-postgres postgresql://localhost/mydb', env: {} },
    'weather':            { name: 'weather',             cmd: 'npx', args: '-y @modelcontextprotocol/server-weather',             env: { OPENWEATHER_API_KEY: '' } },
};

function applyMCPPreset(presetKey) {
    if (!presetKey || !mcpPresetsMap[presetKey]) return;
    const p = mcpPresetsMap[presetKey];
    document.getElementById('mcp-new-name').value  = p.name;
    document.getElementById('mcp-new-cmd').value   = p.cmd;
    document.getElementById('mcp-new-args').value  = p.args;
    document.getElementById('mcp-presets').value   = '';

    // Pre-populate env vars if the preset has any
    const rows = document.getElementById('mcp-env-rows');
    rows.innerHTML = '';
    if (p.env && Object.keys(p.env).length > 0) {
        // Auto-open env editor
        const editor = document.getElementById('mcp-env-editor');
        if (editor.style.display === 'none') toggleMCPEnvEditor();
        Object.entries(p.env).forEach(([k, v]) => addEnvRow(k, v));
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// Env Var Editor
// ─────────────────────────────────────────────────────────────────────────────

function toggleMCPEnvEditor() {
    const editor  = document.getElementById('mcp-env-editor');
    const chevron = document.getElementById('mcp-env-chevron');
    const isOpen  = editor.style.display !== 'none';
    editor.style.display  = isOpen ? 'none' : 'block';
    chevron.className = isOpen ? 'fas fa-chevron-down' : 'fas fa-chevron-up';
}

function addEnvRow(key = '', value = '') {
    const rows = document.getElementById('mcp-env-rows');
    const div  = document.createElement('div');
    div.style.cssText = 'display:flex; gap:6px; margin-bottom:6px; align-items:center;';
    div.innerHTML = `
        <input type="text"  placeholder="KEY"   value="${key}"   style="flex:1; font-family:'JetBrains Mono',monospace; font-size:11px;">
        <input type="text"  placeholder="value" value="${value}" style="flex:2; font-family:'JetBrains Mono',monospace; font-size:11px;">
        <button type="button" class="btn btn-danger" style="padding:3px 8px; font-size:11px;" onclick="this.parentElement.remove()">
            <i class="fas fa-times"></i>
        </button>`;
    rows.appendChild(div);
}

function getEnvVars() {
    const env  = {};
    const rows = document.querySelectorAll('#mcp-env-rows > div');
    rows.forEach(row => {
        const inputs = row.querySelectorAll('input');
        const key    = inputs[0].value.trim();
        const val    = inputs[1].value.trim();
        if (key) env[key] = val;
    });
    return env;
}

// ─────────────────────────────────────────────────────────────────────────────
// Server Table Rendering
// ─────────────────────────────────────────────────────────────────────────────

function _statusBadge(serverName) {
    const info  = mcpLiveInventory[serverName];
    if (!info) return `<span style="width:8px;height:8px;border-radius:50%;background:var(--muted);display:inline-block;" title="Unknown"></span>`;
    const s     = info.status;
    const color = s === 'connected'              ? 'var(--green)'
                : (s === 'crashed' || s === 'failed') ? 'var(--red)'
                : s === 'starting'               ? 'var(--accent)'
                : s === 'reconnecting'           ? 'var(--yellow, orange)'
                : 'var(--muted)';
    const anim  = s === 'starting' ? 'pulse-anim' : '';
    const label = s === 'connected' ? `${info.tools?.length ?? 0} tools` : s;
    return `<span class="${anim}" style="width:8px;height:8px;border-radius:50%;background:${color};display:inline-block;margin-right:4px;" title="${s}"></span>
            <span style="font-size:10px;color:${color};">${label}</span>`;
}

function renderMCPServers() {
    const tbody = document.querySelector('#mcp-servers-table tbody');
    if (!tbody) return;

    if (!window.cfg || !window.cfg.plugins) {
        if (tbody.children.length === 0)
            tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; color:var(--muted); padding:20px;">Initializing configuration...</td></tr>';
        return;
    }

    if (!window.cfg.plugins.MCP_BRIDGE)         window.cfg.plugins.MCP_BRIDGE         = { enabled: false, servers: {} };
    if (!window.cfg.plugins.MCP_BRIDGE.servers) window.cfg.plugins.MCP_BRIDGE.servers = {};

    const servers    = window.cfg.plugins.MCP_BRIDGE.servers;
    const mainToggle = document.getElementById('mcp-enabled');
    if (mainToggle) mainToggle.checked = window.cfg.plugins.MCP_BRIDGE.enabled;

    if (Object.keys(servers).length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; color:var(--muted); font-size:12px; padding:20px;">No external providers configured.</td></tr>';
        return;
    }

    let html = '';
    for (const [name, cfg] of Object.entries(servers)) {
        const cmds      = Array.isArray(cfg.args) ? cfg.args.join(' ') : (cfg.args || '');
        const isEnabled = cfg.enabled !== false;
        const envCount  = cfg.env ? Object.keys(cfg.env).length : 0;
        const envHint   = envCount > 0 ? `<span style="font-size:9px; color:var(--muted); display:block;">${envCount} env var${envCount>1?'s':''}</span>` : '';
        
        const titleText = cfg.homepage 
            ? `<a href="${cfg.homepage}" target="_blank" title="View Source / Documentation" style="color:var(--accent); text-decoration:none;"><i class="fas fa-external-link-alt" style="font-size:10px; margin-right:4px;"></i>${name}</a>`
            : name;

        html += `<tr>
            <td style="white-space:nowrap;">${_statusBadge(name)}</td>
            <td style="color:var(--accent); font-weight:bold; font-family:'JetBrains Mono',monospace;">${titleText}${envHint}</td>
            <td style="font-family:'JetBrains Mono',monospace; font-size:11px; color:var(--muted);">
                <span style="color:var(--text);">${cfg.command}</span> ${cmds}
            </td>
            <td>
                <label class="switch is-small"><input type="checkbox" ${isEnabled ? 'checked' : ''}
                       onchange="toggleMCPServer('${name}', this.checked)"><span class="slider"></span></label>
            </td>
            <td>
                <button type="button" class="btn btn-secondary" style="padding:3px 10px; font-size:11px; margin-right:4px;" onclick="restartMCPServer('${name}', this)"><i class="fas fa-redo"></i></button>
                <button type="button" class="btn btn-danger" style="padding:3px 10px; font-size:11px;" onclick="removeMCPServer('${name}')"><i class="fas fa-trash"></i></button>
            </td>
        </tr>`;
    }
    tbody.innerHTML = html;
}

// ─────────────────────────────────────────────────────────────────────────────
// MCP-specific config save (bypasses buildPayload)
// ─────────────────────────────────────────────────────────────────────────────

async function saveMcpConfig() {
    const mcpBlock = window.cfg?.plugins?.MCP_BRIDGE || { enabled: false, servers: {} };
    try {
        const r = await fetch('/api/mcp/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(mcpBlock)
        });
        const d = await r.json();
        if (!d.ok) console.error('[MCP] Config save failed:', d.error);
    } catch (e) {
        console.error('[MCP] Config save error:', e);
    }
}

async function toggleMCPServer(name, isEnabled) {
    if (window.cfg.plugins.MCP_BRIDGE.servers[name]) {
        window.cfg.plugins.MCP_BRIDGE.servers[name].enabled = isEnabled;
        await saveMcpConfig();
        fetchMCPInventory();
    }
}

async function addMCPServer() {
    const nameEl = document.getElementById('mcp-new-name');
    const cmdEl  = document.getElementById('mcp-new-cmd');
    const argsEl = document.getElementById('mcp-new-args');

    const name    = nameEl.value.trim().replace(/\s+/g, '_');
    const command = cmdEl.value.trim();
    const argsStr = argsEl.value.trim();
    const env     = getEnvVars();

    if (!name || !command) { 
        if (window.showToast) window.showToast('Name and Command are required to bridge a server.', 'error');
        else alert('Name and Command are required to bridge a server.'); 
        return; 
    }

    if (!window.cfg.plugins)                     window.cfg.plugins                     = {};
    if (!window.cfg.plugins.MCP_BRIDGE)          window.cfg.plugins.MCP_BRIDGE          = { enabled: true, servers: {} };
    if (!window.cfg.plugins.MCP_BRIDGE.servers)  window.cfg.plugins.MCP_BRIDGE.servers  = {};

    const mainToggle = document.getElementById('mcp-enabled');
    if (mainToggle && !mainToggle.checked) {
        mainToggle.checked                    = true;
        window.cfg.plugins.MCP_BRIDGE.enabled = true;
    }

    const args = argsStr ? argsStr.split(' ').filter(a => a.trim() !== '') : [];
    const homepage = nameEl.dataset.homepage || '';
    window.cfg.plugins.MCP_BRIDGE.servers[name] = { command, args, enabled: true, env, homepage };

    // Reset form
    nameEl.value = ''; cmdEl.value = ''; argsEl.value = '';
    document.getElementById('mcp-env-rows').innerHTML = '';
    const editor = document.getElementById('mcp-env-editor');
    if (editor.style.display !== 'none') toggleMCPEnvEditor();

    renderMCPServers();
    await saveMcpConfig();
    fetchMCPInventory();
}

function removeMCPServer(name) {
    const doRemove = async () => {
        delete window.cfg.plugins.MCP_BRIDGE.servers[name];
        delete mcpLiveInventory[name];
        renderMCPServers();
        await saveMcpConfig();
        fetchMCPInventory();
    };

    if (window.hpmShowConfirm) {
        window.hpmShowConfirm(
            `Unlink MCP provider <b style="color:var(--accent);">${name}</b>?<br><br><span style="font-size:13px; color:var(--muted);">This will instantly terminate the background process and remove its tools from Hecos.</span>`,
            '<i class="fas fa-trash"></i> Unlink',
            doRemove
        );
    } else {
        if (confirm(`Unlink MCP provider '${name}'? This will remove its tools from Hecos.`)) {
            doRemove();
        }
    }
}

async function restartMCPServer(name, btn) {
    if (btn) { btn.disabled = true; btn.innerHTML = '<i class="fas fa-circle-notch fa-spin"></i>'; }
    try {
        const r = await fetch('/api/mcp/restart_server', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name })
        });
        const d = await r.json();
        if (d.ok) {
            if (window.showToast) window.showToast(`Server '${name}' restarted`, 'ok');
            fetchMCPInventory();
        } else {
            if (window.showToast) window.showToast(`Error: ${d.error}`, 'error');
        }
    } catch (e) {
        console.error(e);
    } finally {
        if (btn) { btn.disabled = false; btn.innerHTML = '<i class="fas fa-redo"></i>'; }
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// MCP Bridge Reload & Inventory Polling
// ─────────────────────────────────────────────────────────────────────────────

async function reloadMCPBridge(btn = null) {
    const origText = btn ? btn.textContent : '';
    if (btn) { btn.disabled = true; btn.textContent = '⏳'; }
    try {
        const r = await fetch('/api/mcp/reload', { method: 'POST' });
        const d = await r.json();
        if (!d.ok) {
            console.warn('[MCP] Reload failed:', d.error);
        } else {
            fetchMCPInventory();
            setTimeout(fetchMCPInventory, 3000);
        }
    } catch (e) {
        console.error('[MCP] Reload error:', e);
    } finally {
        if (btn) { btn.disabled = false; btn.textContent = origText; }
    }
}

async function fetchMCPInventory() {
    try {
        const response = await fetch('/api/mcp/inventory');
        const data     = await response.json();
        if (!data.ok) return;

        const servers   = data.servers;
        let hasStarting = false;

        // Update global live state (used by renderMCPServers for status badges)
        mcpLiveInventory = servers;
        renderMCPServers();  // re-render table with fresh status dots

        const invContainer = document.getElementById('mcp-inventory-list');
        if (!invContainer) return;

        if (Object.keys(servers).length === 0) {
            invContainer.innerHTML = '<p style="color:var(--muted); font-size:12px;">No active tools discovered yet. Make sure servers are enabled and running.</p>';
            return;
        }

        let html = '';
        for (const [sName, sData] of Object.entries(servers)) {
            if (sData.status === 'starting' || sData.status === 'reconnecting') hasStarting = true;

            const color = sData.status === 'connected'                       ? 'var(--green)'
                        : (sData.status === 'crashed' || sData.status === 'failed') ? 'var(--red)'
                        : sData.status === 'starting'                        ? 'var(--accent)'
                        : 'var(--muted)';
            const pulseClass = sData.status === 'starting' ? 'pulse-anim' : '';

            html += `<div style="margin-bottom:20px;">
                <h4 style="margin:0; color:var(--text); font-size:13px; display:flex; align-items:center; gap:8px;">
                    <span class="${pulseClass}" style="width:8px; height:8px; border-radius:50%; background:${color}; display:inline-block;"></span>
                    ${sName.toUpperCase()}
                    <span style="font-size:10px; color:var(--muted); font-weight:normal;">[${sData.status}]</span>
                </h4>
                <div style="display:flex; flex-wrap:wrap; gap:6px; margin-top:8px; padding-left:16px;">`;

            if (sData.tools && sData.tools.length > 0) {
                sData.tools.forEach(t => {
                    html += `<span class="tag-mcp-tool" title="${t.description || 'No description'}">${t.name}</span>`;
                });
            } else {
                let msg = sData.status === 'starting' ? 'Starting up...'
                        : sData.status === 'failed'   ? 'Failed to fetch tools.'
                        : sData.status === 'crashed'  ? 'Server process crashed.'
                        : 'No tools discovered.';

                // Show raw error if available
                if ((sData.status === 'failed' || sData.status === 'crashed') && sData.error) {
                    msg += `<br><span style="color:var(--red); font-family:monospace; display:inline-block; margin-top:4px;">Error: ${sData.error}</span>`;
                }
                
                html += `<span style="color:var(--muted); font-size:11px; font-style:italic;">${msg}</span>`;
            }
            html += `</div></div>`;
        }
        invContainer.innerHTML = html;

        // Adaptive polling frequency: fast when any server is starting or reconnecting
        if (hasStarting) {
            if (mcpPollInterval) clearInterval(mcpPollInterval);
            mcpPollInterval = setInterval(fetchMCPInventory, 2000);
        } else {
            if (mcpPollInterval) {
                clearInterval(mcpPollInterval);
                mcpPollInterval = setInterval(fetchMCPInventory, 10000);
            }
        }
    } catch (e) {
        console.error('Failed to fetch MCP inventory', e);
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// MCP Registry Explorer
// ─────────────────────────────────────────────────────────────────────────────

async function searchRegistry() {
    const qEl       = document.getElementById('mcp-explore-query');
    const rEl       = document.getElementById('mcp-explore-registry');
    const btn       = document.getElementById('mcp-explore-btn');
    const clearBtn  = document.getElementById('mcp-explore-clear-btn');
    const container = document.getElementById('mcp-explore-results');

    const query    = qEl.value.trim();
    const registry = rEl.value;
    if (!query) return;

    btn.disabled           = true;
    btn.innerText          = '...';
    clearBtn.style.display = 'block';
    container.innerHTML    = `<p style="color:var(--muted); font-size:12px; grid-column:1/-1; text-align:center;"><i class="fas fa-search"></i> Searching ${registry}...</p>`;

    try {
        const response = await fetch(`/api/mcp/explore?q=${encodeURIComponent(query)}&reg=${registry}`);
        const data     = await response.json();

        if (!data.ok) {
            container.innerHTML = `<p style="color:var(--red); font-size:12px; grid-column:1/-1; text-align:center;">Error: ${data.error || 'Failed to fetch results'}</p>`;
            return;
        }
        if (!data.results || data.results.length === 0) {
            container.innerHTML = `<p style="color:var(--muted); font-size:12px; grid-column:1/-1; text-align:center;">No results found for "${query}".</p>`;
            return;
        }

        let html = '';
        data.results.forEach(res => {
            const packageIdent = res.qualifiedName || res.name;
            let cmdArgs = `-y ${packageIdent}`;
            if (packageIdent.startsWith('hf:')) {
                const spaceId = packageIdent.replace('hf:', '');
                cmdArgs = `-y @llmindset/hf-mcp-server --space ${spaceId}`;
            } else if (registry === 'smithery') {
                cmdArgs = `-y @smithery/cli run ${packageIdent}`;
            }
            const cardData = {
                name: res.name.split('/').pop().replace(/[^a-z0-9]/gi, '_').toLowerCase(),
                cmd:  'npx',
                args: cmdArgs,
                homepage: res.homepage || res.repository || res.url || ''
            };
            const dataStr   = btoa(JSON.stringify(cardData));
            const url       = res.homepage || res.repository || res.url || '';
            const author    = res.author || res.owner || (res.name.includes('/') ? res.name.split('/')[0] : '');
            const titleHtml = url
                ? `<a href="${url}" target="_blank" style="color:var(--accent); font-weight:bold; font-size:12px; font-family:'JetBrains Mono',monospace; text-decoration:none;" title="Open Repository in New Tab"><i class="fas fa-link"></i> ${res.name}</a>`
                : `<span style="color:var(--accent); font-weight:bold; font-size:12px; font-family:'JetBrains Mono',monospace;">${res.name}</span>`;
            const authorHtml = author ? `<div style="font-size:10px; color:var(--muted); margin-top:2px;">by <b>${author}</b></div>` : '';

            let descHtml = '';
            if (res.description && res.description.length > 100) {
                descHtml = `<p style="font-size:11px; color:var(--muted); line-height:1.4; margin-bottom:0px; display:-webkit-box; -webkit-line-clamp:3; -webkit-box-orient:vertical; overflow:hidden;">${res.description}</p>
                <span style="font-size:9px; color:rgba(var(--accent-rgb),0.8); cursor:pointer; display:block; text-align:right; margin-bottom:10px;" onclick="this.previousElementSibling.style.display='block'; this.previousElementSibling.style.webkitLineClamp='unset'; this.style.display='none'; event.stopPropagation();">Read more ▼</span>`;
            } else {
                descHtml = `<p style="font-size:11px; color:var(--muted); line-height:1.4; margin-bottom:10px;">${res.description || 'No description available.'}</p>`;
            }

            html += `<div style="background:var(--glass); padding:14px; border-radius:10px; border:1px solid var(--glass-border); display:flex; flex-direction:column; justify-content:space-between;">
                <div>
                    <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:6px;">
                        <div style="display:flex; flex-direction:column;">${titleHtml}${authorHtml}</div>
                        <span style="font-size:10px; color:var(--muted); white-space:nowrap; margin-left:8px;">${res.useCount || res.downloads || 0} ${registry === 'smithery' ? 'uses' : 'dls'}</span>
                    </div>
                    ${descHtml}
                </div>
                <button type="button" class="btn btn-secondary" style="width:100%; font-size:11px;" onclick="addFromExplore('${dataStr}')"><i class="fas fa-plus"></i> Add to Hecos</button>
            </div>`;
        });

        container.innerHTML          = html;
        window.HecosMCPSearchResults = html;

    } catch (e) {
        container.innerHTML = '<p style="color:var(--red); font-size:12px; grid-column:1/-1; text-align:center;">Network error. Make sure Hecos is online.</p>';
    } finally {
        btn.disabled  = false;
        btn.innerText = 'Search';
    }
}

function clearMCPExplore() {
    document.getElementById('mcp-explore-query').value              = '';
    document.getElementById('mcp-explore-clear-btn').style.display  = 'none';
    document.getElementById('mcp-explore-results').innerHTML        = '<p style="color:var(--muted); font-size:12px; grid-column:1/-1; text-align:center;">Enter a search term to discover new capabilities.</p>';
    window.HecosMCPSearchResults = null;
}

function addFromExplore(encodedData) {
    try {
        const data = JSON.parse(atob(encodedData));
        document.getElementById('mcp-new-name').value = data.name;
        document.getElementById('mcp-new-name').dataset.homepage = data.homepage || '';
        document.getElementById('mcp-new-cmd').value  = data.cmd;
        document.getElementById('mcp-new-args').value = data.args;

        // Flash the add form to draw attention
        const addSection = document.querySelector('#tab-mcp .card:nth-child(2) > div:last-child');
        if (addSection) {
            addSection.style.boxShadow = '0 0 15px rgba(var(--accent-rgb), 0.4)';
            setTimeout(() => { addSection.style.boxShadow = 'none'; }, 2000);
            addSection.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    } catch (e) { console.error('Failed to parse explore data', e); }
}

// ─────────────────────────────────────────────────────────────────────────────
// Bootstrap — runs immediately even when panel is injected dynamically via AJAX
// ─────────────────────────────────────────────────────────────────────────────

function initMCPPanel() {
    // Guard: don't init twice if somehow called again
    if (window._mcpPanelInitialized) return;
    window._mcpPanelInitialized = true;

    renderMCPServers();
    fetchMCPInventory();

    // Restore cached search results across tab navigation
    if (window.HecosMCPSearchResults) {
        const container = document.getElementById('mcp-explore-results');
        if (container) container.innerHTML = window.HecosMCPSearchResults;
        const clearBtn = document.getElementById('mcp-explore-clear-btn');
        if (clearBtn) clearBtn.style.display = 'block';
    }

    const qEl = document.getElementById('mcp-explore-query');
    if (qEl) qEl.addEventListener('keypress', e => { if (e.key === 'Enter') { e.preventDefault(); searchRegistry(); } });

    // Polling: re-render table every 5s, inventory every 10s
    setInterval(renderMCPServers, 5000);
    mcpPollInterval = setInterval(fetchMCPInventory, 10000);
}

// Run immediately if DOM is ready, otherwise wait for it
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initMCPPanel);
} else {
    // DOM already ready (panel loaded dynamically after page init)
    initMCPPanel();
}
