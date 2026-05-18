/**
 * mcp_panel.js
 * ─────────────────────────────────────────────────────────────────────────────
 * Hecos MCP Bridge — Config Panel Logic
 * Handles server table rendering, add/remove/toggle servers,
 * MCP inventory polling, registry explorer search, and preset mapping.
 * ─────────────────────────────────────────────────────────────────────────────
 */

// ─────────────────────────────────────────────────────────────────────────────
// Preset Map
// ─────────────────────────────────────────────────────────────────────────────

const mcpPresetsMap = {
    'everything':         { name: 'everything',         cmd: 'npx', args: '-y @modelcontextprotocol/server-everything' },
    'sequentialthinking': { name: 'sequential_thinking', cmd: 'npx', args: '-y @modelcontextprotocol/server-sequential-thinking' },
    'bravesearch':        { name: 'brave_search',        cmd: 'npx', args: '-y @modelcontextprotocol/server-brave-search' },
    'google-maps':        { name: 'google_maps',         cmd: 'npx', args: '-y @modelcontextprotocol/server-google-maps' },
    'github':             { name: 'github',              cmd: 'npx', args: '-y @modelcontextprotocol/server-github' },
    'filesystem':         { name: 'filesystem',          cmd: 'npx', args: '-y @modelcontextprotocol/server-filesystem /path/to/expose' },
    'wikipedia':          { name: 'wikipedia',           cmd: 'npx', args: '-y wikipedia-mcp' },
    'postgres':           { name: 'postgres',            cmd: 'npx', args: '-y @modelcontextprotocol/server-postgres postgresql://localhost/mydb' },
    'weather':            { name: 'weather',             cmd: 'npx', args: '-y @modelcontextprotocol/server-weather' }
};

function applyMCPPreset(presetKey) {
    if (!presetKey || !mcpPresetsMap[presetKey]) return;
    const p = mcpPresetsMap[presetKey];
    document.getElementById('mcp-new-name').value  = p.name;
    document.getElementById('mcp-new-cmd').value   = p.cmd;
    document.getElementById('mcp-new-args').value  = p.args;
    document.getElementById('mcp-presets').value   = '';
}

// ─────────────────────────────────────────────────────────────────────────────
// Server Table Rendering
// ─────────────────────────────────────────────────────────────────────────────

function renderMCPServers() {
    const tbody = document.querySelector('#mcp-servers-table tbody');
    if (!tbody) return;

    if (!window.cfg || !window.cfg.plugins) {
        if (tbody.children.length === 0)
            tbody.innerHTML = '<tr><td colspan="4" style="text-align:center; color:var(--muted); padding:20px;">Initializing configuration...</td></tr>';
        return;
    }

    if (!window.cfg.plugins.MCP_BRIDGE)         window.cfg.plugins.MCP_BRIDGE         = { enabled: false, servers: {} };
    if (!window.cfg.plugins.MCP_BRIDGE.servers) window.cfg.plugins.MCP_BRIDGE.servers = {};

    const servers     = window.cfg.plugins.MCP_BRIDGE.servers;
    const mainToggle  = document.getElementById('mcp-enabled');
    if (mainToggle) mainToggle.checked = window.cfg.plugins.MCP_BRIDGE.enabled;

    if (Object.keys(servers).length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" style="text-align:center; color:var(--muted); font-size:12px; padding:20px;">No external providers configured.</td></tr>';
        return;
    }

    let html = '';
    for (const [name, cfg] of Object.entries(servers)) {
        const cmds      = Array.isArray(cfg.args) ? cfg.args.join(' ') : (cfg.args || '');
        const isEnabled = cfg.enabled !== false;
        html += `<tr>
            <td style="color:var(--accent); font-weight:bold; font-family:'JetBrains Mono',monospace;">${name}</td>
            <td style="font-family:'JetBrains Mono',monospace; font-size:11px; color:var(--muted);">
                <span style="color:var(--text);">${cfg.command}</span> ${cmds}
            </td>
            <td>
                <label class="switch is-small"><input type="checkbox" ${isEnabled ? 'checked' : ''}
                       onchange="toggleMCPServer('${name}', this.checked)"><span class="slider"></span></label>
            </td>
            <td>
                <button type="button" class="btn btn-danger" style="padding:3px 10px; font-size:11px;" onclick="removeMCPServer('${name}')"><i class="fas fa-trash"></i> Remove</button>
            </td>
        </tr>`;
    }
    tbody.innerHTML = html;
}

function toggleMCPServer(name, isEnabled) {
    if (window.cfg.plugins.MCP_BRIDGE.servers[name]) {
        window.cfg.plugins.MCP_BRIDGE.servers[name].enabled = isEnabled;
        saveConfig(true);
    }
}

function addMCPServer() {
    const nameEl = document.getElementById('mcp-new-name');
    const cmdEl  = document.getElementById('mcp-new-cmd');
    const argsEl = document.getElementById('mcp-new-args');

    const name    = nameEl.value.trim().replace(/\s+/g, '_');
    const command = cmdEl.value.trim();
    const argsStr = argsEl.value.trim();

    if (!name || !command) { alert('Name and Command are required to bridge a server.'); return; }

    if (!window.cfg.plugins)                     window.cfg.plugins                     = {};
    if (!window.cfg.plugins.MCP_BRIDGE)          window.cfg.plugins.MCP_BRIDGE          = { enabled: true, servers: {} };
    if (!window.cfg.plugins.MCP_BRIDGE.servers)  window.cfg.plugins.MCP_BRIDGE.servers  = {};

    const mainToggle = document.getElementById('mcp-enabled');
    if (mainToggle && !mainToggle.checked) {
        mainToggle.checked                    = true;
        window.cfg.plugins.MCP_BRIDGE.enabled = true;
    }

    const args = argsStr ? argsStr.split(' ').filter(a => a.trim() !== '') : [];
    window.cfg.plugins.MCP_BRIDGE.servers[name] = { command, args, enabled: true, env: {} };

    nameEl.value = ''; cmdEl.value = ''; argsEl.value = '';
    renderMCPServers();
    saveConfig(true);
    setTimeout(() => reloadMCPBridge(), 500);
}

function removeMCPServer(name) {
    if (confirm(`Unlink MCP provider '${name}'? This will remove its tools from Hecos.`)) {
        delete window.cfg.plugins.MCP_BRIDGE.servers[name];
        renderMCPServers();
        saveConfig(true);
        setTimeout(() => reloadMCPBridge(), 500);
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// MCP Bridge Reload & Inventory Polling
// ─────────────────────────────────────────────────────────────────────────────

let mcpPollInterval = null;

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

        const invContainer = document.getElementById('mcp-inventory-list');
        if (!invContainer) return;

        const servers     = data.servers;
        let hasStarting   = false;

        if (Object.keys(servers).length === 0) {
            invContainer.innerHTML = '<p style="color:var(--muted); font-size:12px;">No active tools discovered yet. Make sure servers are enabled and running.</p>';
            return;
        }

        let html = '';
        for (const [sName, sData] of Object.entries(servers)) {
            if (sData.status === 'starting') hasStarting = true;

            const color = sData.status === 'connected' ? 'var(--green)'
                        : (sData.status === 'crashed' || sData.status === 'failed') ? 'var(--red)'
                        : sData.status === 'starting' ? 'var(--accent)'
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
                const msg = sData.status === 'starting' ? 'Starting up...'
                          : sData.status === 'failed'   ? 'Failed to fetch tools'
                          : 'No tools discovered.';
                html += `<span style="color:var(--muted); font-size:11px; font-style:italic;">${msg}</span>`;
            }
            html += `</div></div>`;
        }
        invContainer.innerHTML = html;

        // Adaptive polling frequency
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
    const qEl      = document.getElementById('mcp-explore-query');
    const rEl      = document.getElementById('mcp-explore-registry');
    const btn      = document.getElementById('mcp-explore-btn');
    const clearBtn = document.getElementById('mcp-explore-clear-btn');
    const container = document.getElementById('mcp-explore-results');

    const query    = qEl.value.trim();
    const registry = rEl.value;
    if (!query) return;

    btn.disabled       = true;
    btn.innerText      = '...';
    clearBtn.style.display = 'block';
    container.innerHTML = `<p style="color:var(--muted); font-size:12px; grid-column:1/-1; text-align:center;"><i class="fas fa-search"></i> Searching ${registry}...</p>`;

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
            }
            const cardData = {
                name: res.name.split('/').pop().replace(/[^a-z0-9]/gi, '_').toLowerCase(),
                cmd:  'npx',
                args: cmdArgs
            };
            const dataStr  = btoa(JSON.stringify(cardData));
            const url      = res.homepage || res.repository || res.url || '';
            const author   = res.author || res.owner || (res.name.includes('/') ? res.name.split('/')[0] : '');
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

        container.innerHTML         = html;
        window.HecosMCPSearchResults = html;

    } catch (e) {
        container.innerHTML = '<p style="color:var(--red); font-size:12px; grid-column:1/-1; text-align:center;">Network error. Make sure Hecos is online.</p>';
    } finally {
        btn.disabled  = false;
        btn.innerText = 'Search';
    }
}

function clearMCPExplore() {
    document.getElementById('mcp-explore-query').value     = '';
    document.getElementById('mcp-explore-clear-btn').style.display = 'none';
    document.getElementById('mcp-explore-results').innerHTML = '<p style="color:var(--muted); font-size:12px; grid-column:1/-1; text-align:center;">Enter a search term to discover new capabilities.</p>';
    window.HecosMCPSearchResults = null;
}

function addFromExplore(encodedData) {
    try {
        const data = JSON.parse(atob(encodedData));
        document.getElementById('mcp-new-name').value = data.name;
        document.getElementById('mcp-new-cmd').value  = data.cmd;
        document.getElementById('mcp-new-args').value = data.args;

        const addSection = document.querySelector('#tab-mcp .card:nth-child(2) > div:last-child');
        if (addSection) {
            addSection.style.boxShadow = '0 0 15px rgba(var(--accent-rgb), 0.4)';
            setTimeout(() => { addSection.style.boxShadow = 'none'; }, 2000);
            addSection.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    } catch (e) { console.error('Failed to parse explore data', e); }
}

// ─────────────────────────────────────────────────────────────────────────────
// Bootstrap
// ─────────────────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
    renderMCPServers();
    fetchMCPInventory();

    // Restore cached search results across tab navigation
    if (window.HecosMCPSearchResults) {
        document.getElementById('mcp-explore-results').innerHTML = window.HecosMCPSearchResults;
        document.getElementById('mcp-explore-clear-btn').style.display = 'block';
    }

    const qEl = document.getElementById('mcp-explore-query');
    if (qEl) qEl.addEventListener('keypress', e => { if (e.key === 'Enter') { e.preventDefault(); searchRegistry(); } });

    setInterval(renderMCPServers, 5000);
    mcpPollInterval = setInterval(fetchMCPInventory, 10000);
});
