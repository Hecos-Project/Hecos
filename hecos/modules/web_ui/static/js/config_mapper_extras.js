/**
 * config_mapper_extras.js
 * Populates: Executor, Automation, Browser UI panels.
 * Exposes: HecosTextFilters, saveDsb, savePluginKey.
 * Depends on: config_mapper_utils.js
 */

window.populateExecutorUI = function() {
    const p = (window.cfg?.plugins || {}).EXECUTOR || {};
    setVal('executor-timeout',        p.timeout_seconds      ?? 10);
    setCheck('executor-shell-enabled',p.enable_shell_commands ?? true);
    setVal('executor-shell-timeout',  p.shell_timeout         ?? 15);
    setVal('executor-max-read-lines', p.max_read_lines        ?? 200);
    setVal('executor-workspace-dir',  p.workspace_dir         ?? 'workspace/sandbox');
};

window.populateAutomationUI = function() {
    const p = (window.cfg?.plugins || {}).AUTOMATION || {};
    setCheck('automation-enabled',       p.enabled             ?? true);
    setVal('automation-move-duration',   p.move_duration        ?? 0.15);
    setVal('automation-type-interval',   p.type_interval        ?? 0.02);
    setCheck('automation-window-control',p.allow_window_control ?? true);
};

window.populateBrowserUI = function() {
    const c = window.cfg;
    if (!c) return;
    const browserConfig = c.plugins?.BROWSER || {};
    setCheck('browser-enabled',    browserConfig.enabled       !== false);
    setCheck('browser-headless',   browserConfig.headless      ?? false);
    setCheck('browser-block-ads',  browserConfig.block_ads     ?? true);
    setVal('browser-startup-url',  browserConfig.startup_url   || 'http://localhost:7070');
    setVal('browser-timeout',      browserConfig.default_timeout || 10000);
    setVal('browser-engine',       browserConfig.browser_type  || 'chromium');
};

/**
 * HecosTextFilters — custom text filter row manager.
 */
window.HecosTextFilters = {
    populate(filters) {
        const container = document.getElementById('custom-filters-container');
        if (!container) return;
        container.innerHTML = '';
        if (Array.isArray(filters)) {
            filters.forEach(f => this.addPlaceholderRow(f.find, f.replace, f.target));
        }
    },
    extract() {
        const container = document.getElementById('custom-filters-container');
        if (!container) return [];
        const results = [];
        container.querySelectorAll('.custom-filter-row').forEach(row => {
            const find = row.querySelector('.cf-find').value;
            if (!find) return;
            results.push({
                find,
                replace: row.querySelector('.cf-replace').value || '',
                target:  row.querySelector('.cf-target').value  || 'both'
            });
        });
        return results;
    },
    removeRow(btn) {
        if (!btn?.parentElement) return;
        btn.parentElement.remove();
        if (typeof window.saveConfig === 'function') window.saveConfig(true);
    },
    addPlaceholderRow(find = '', replace = '', target = 'both') {
        const container = document.getElementById('custom-filters-container');
        if (!container) return;
        const div = document.createElement('div');
        div.className = 'custom-filter-row';
        div.style.cssText = 'display:flex; gap:8px; align-items:center;';
        div.innerHTML = `
            <input type="text" class="config-input cf-find"    placeholder="Find..."    value="${find.replace(/"/g,'&quot;')}"    style="flex:2; padding:4px 8px; font-size:12px;">
            <input type="text" class="config-input cf-replace" placeholder="Replace..." value="${replace.replace(/"/g,'&quot;')}" style="flex:2; padding:4px 8px; font-size:12px;">
            <select class="config-input cf-target" style="flex:1.5; padding:4px 8px; font-size:12px;">
                <option value="both"  ${target==='both'  ? 'selected':''}>Voice &amp; Text</option>
                <option value="voice" ${target==='voice' ? 'selected':''}>Voice Only</option>
                <option value="text"  ${target==='text'  ? 'selected':''}>Text Only</option>
            </select>
            <button type="button" class="btn" onclick="HecosTextFilters.removeRow(this)"
                    style="padding:4px 8px; font-size:10px; background:rgba(255,50,50,0.2); color:#ff5555;">X</button>
        `;
        container.appendChild(div);
    }
};

/**
 * Quick dashboard key saver — used by toggle handlers in the Dashboard panel.
 */
window.saveDsb = function(key, val) {
    if (!window.cfg.plugins) window.cfg.plugins = {};
    if (!window.cfg.plugins.DASHBOARD) window.cfg.plugins.DASHBOARD = {};
    window.cfg.plugins.DASHBOARD[key] = val;
    if (typeof window.refreshStatus === 'function') window.refreshStatus();
    // Config persistence auto-saves on change events; no explicit saveConfig() call needed here.
};

/**
 * Generic plugin key saver — used by panels (e.g. Executor) that don't have a dedicated save fn.
 */
window.savePluginKey = function(pluginTag, key, val) {
    if (!window.cfg.plugins) window.cfg.plugins = {};
    if (!window.cfg.plugins[pluginTag]) window.cfg.plugins[pluginTag] = {};
    window.cfg.plugins[pluginTag][key] = val;
    if (typeof window.saveConfig === 'function') window.saveConfig(true);
};
