/**
 * config_mapper_extras.js
 * Populates: Executor, Automation, Browser UI panels.
 * Exposes: HecosTextFilters, saveDsb, savePluginKey.
 * Depends on: config_mapper_utils.js
 */

const DEFAULT_EXECUTOR_ANTI_HALLUCINATION_DIRECTIVE = [
    "CRITICAL EXECUTOR ANTI-HALLUCINATION DIRECTIVE:",
    "1. NEVER claim, imply, or announce that files or apps were created, edited, fixed, verified, or started unless you ACTUALLY called an EXECUTOR tool (`EXECUTOR__read_file`, `EXECUTOR__run_aider_task`, `EXECUTOR__patch_file`, `EXECUTOR__write_file`, `EXECUTOR__start_app`, `EXECUTOR__run_project_test`) and observed its real output in this turn.",
    "2. When asked to inspect, fix, or build a project, DO NOT paste full updated files in chat claiming the fix is applied: invoke `EXECUTOR__read_file` first or `EXECUTOR__run_aider_task` / `EXECUTOR__patch_file` directly on disk, then verify with `EXECUTOR__start_app` or `EXECUTOR__run_project_test`.",
    "3. If your model is in text-only tool mode, emit explicit `EXECUTOR__tool_name(arg=\"...\")` calls and always use forward slashes `/` in Windows paths (e.g. `C:/Hecos/hecos/media/workspace/...`)."
].join("\n");

window.populateExecutorUI = async function() {
    const p = (window.cfg?.plugins || {}).EXECUTOR || {};
    setCheck('executor-enabled',      p.enabled              !== false);
    setVal('executor-timeout',        p.timeout_seconds      ?? 10);
    setCheck('executor-shell-enabled',p.enable_shell_commands ?? true);
    setVal('executor-shell-timeout',  p.shell_timeout         ?? 15);
    setVal('executor-max-read-lines', p.max_read_lines        ?? 200);
    setVal('executor-workspace-dir',  p.workspace_dir         ?? 'workspace/sandbox');
    setVal('executor-test-timeout',   p.test_timeout_seconds  ?? 30);
    setVal('executor-python-interpreter', p.python_interpreter ?? '');

    // Model Directives & Anti-Hallucination Override
    setCheck('executor-anti-hallucination-enabled', p.enable_anti_hallucination_guard !== false);
    setVal(
        'executor-anti-hallucination-directive',
        (p.anti_hallucination_directive !== undefined && String(p.anti_hallucination_directive).trim() !== '')
            ? String(p.anti_hallucination_directive)
            : DEFAULT_EXECUTOR_ANTI_HALLUCINATION_DIRECTIVE
    );
    setVal('executor-model-directive-override', p.model_directive_override ?? '');

    // Aider Sidecar & Global Preset controls
    setCheck('executor-aider-enabled',   p.aider_enabled   !== false);
    setCheck('executor-aider-auto-lint', p.aider_auto_lint !== false);
    setVal('executor-aider-num-ctx',     p.aider_num_ctx   ?? 0);
    setVal('executor-aider-edit-format', p.aider_edit_format ?? '');

    const gpVal = (p.aider_global_preset !== undefined && p.aider_global_preset !== null)
        ? String(p.aider_global_preset)
        : 'hecos_coder';
    await _populateExecutorAiderDropdowns(gpVal, String(p.aider_model || ''));
    if (typeof window.refreshExecutorAiderStatus === 'function') {
        window.refreshExecutorAiderStatus();
    }
    
    const paths = p.important_paths || {};
    if (document.getElementById('executor-path-userprofile')) document.getElementById('executor-path-userprofile').value = paths.user_profile || 'C:\\Hecos\\hecos\\media';
    if (document.getElementById('executor-path-downloads')) document.getElementById('executor-path-downloads').value = paths.downloads || 'C:\\Hecos\\hecos\\media\\downloads';
    if (document.getElementById('executor-path-projects')) document.getElementById('executor-path-projects').value = paths.projects || 'C:\\Hecos\\hecos\\media\\workspace';
    if (document.getElementById('executor-path-generated')) document.getElementById('executor-path-generated').value = paths.generated_files || 'C:\\Hecos\\hecos\\media\\documents';
};

window.resetExecutorAntiHallucinationDirective = function() {
    setVal('executor-anti-hallucination-directive', DEFAULT_EXECUTOR_ANTI_HALLUCINATION_DIRECTIVE);
    if (typeof savePluginKey === 'function') {
        savePluginKey('EXECUTOR', 'anti_hallucination_directive', DEFAULT_EXECUTOR_ANTI_HALLUCINATION_DIRECTIVE);
    }
    if (typeof showToast === 'function') {
        showToast('Default Anti-Hallucination directive restored.', false);
    }
};

async function _populateExecutorAiderDropdowns(currentGp, currentModel) {
    const gpSelect = document.getElementById('executor-aider-gp');
    if (gpSelect) {
        gpSelect.innerHTML = '';
        const noneOpt = document.createElement('option');
        noneOpt.value = '';
        noneOpt.textContent = '-- None (Use direct model override or active model) --';
        gpSelect.appendChild(noneOpt);
        try {
            const resp = await fetch('/api/souls');
            const data = await resp.json();
            const souls = (data.ok && Array.isArray(data.souls)) ? data.souls : [];
            souls.sort((a, b) => String(a.meta?.name || '').localeCompare(String(b.meta?.name || '')));
            souls.forEach(s => {
                const id = s.meta?.id || '';
                if (!id) return;
                const icon = s.meta?.icon || '🤖';
                const name = s.meta?.name || id;
                const mName = s.model?.model_name ? ` — ${s.model.model_name}` : '';
                const ctxTag = s.inference?.num_ctx ? ` (ctx ${s.inference.num_ctx})` : '';
                const opt = document.createElement('option');
                opt.value = id;
                opt.textContent = `${icon} ${name}${mName}${ctxTag}`;
                gpSelect.appendChild(opt);
            });
        } catch (e) {
            console.warn('[Executor] Could not load Global Presets for Aider:', e);
        }
        gpSelect.value = currentGp;
    }

    const modelSelect = document.getElementById('executor-aider-model');
    if (modelSelect) {
        modelSelect.innerHTML = '';
        const autoOpt = document.createElement('option');
        autoOpt.value = '';
        autoOpt.textContent = '-- Follow Selected Global Preset (or active model) --';
        modelSelect.appendChild(autoOpt);

        const sysOptions = window.sysOptions || {};
        const richModels = (typeof _ensureRichModels === 'function') ? await _ensureRichModels() : [];
        const normCloudValue = (raw) => {
            const s = String(raw || '').trim();
            if (!s || s.includes('/')) return s;
            const low = s.toLowerCase();
            if (low.startsWith('claude-')) return `anthropic/${s}`;
            if (low.startsWith('gemini-')) return `gemini/${s}`;
            if (low.startsWith('deepseek-')) return `deepseek/${s}`;
            if (/^(gpt-|o1|o3|o4|chatgpt-)/.test(low)) return `openai/${s}`;
            return s;
        };
        const formatRichLabel = (mId, backendType) => {
            const rm = (richModels || []).find(r =>
                backendType === 'cloud' ? (r.type === 'cloud' && r.id === mId) : (r.provider === backendType && r.id === mId)
            );
            if (!rm) return (backendType === 'cloud' ? '☁️ ' : '🖥️ ') + mId;
            const prefix = rm.type === 'cloud' ? '☁️ ' : '🖥️ ';
            const parts = [];
            if (rm.parameter_size) parts.push(rm.parameter_size + (rm.quantization_level ? ' ' + rm.quantization_level : ''));
            if (rm.size_bytes) parts.push((rm.size_bytes / (1024 * 1024 * 1024)).toFixed(1) + 'GB');
            const sizeTag = parts.length ? ` [${parts.join(' | ')}]` : '';
            return prefix + (rm.name || mId) + sizeTag;
        };

        const ollamaList = Array.isArray(sysOptions.ollama_models)
            ? sysOptions.ollama_models
            : Object.values(sysOptions.ollama_models || {});
        if (ollamaList.length) {
            const og = document.createElement('optgroup');
            og.label = '🖥️ Local Models (Ollama)';
            ollamaList.forEach(m => {
                const opt = document.createElement('option');
                opt.value = String(m).includes('ollama_chat/') ? String(m) : `ollama_chat/${m}`;
                opt.textContent = formatRichLabel(m, 'ollama');
                og.appendChild(opt);
            });
            modelSelect.appendChild(og);
        }

        const cloudList = Array.isArray(sysOptions.all_cloud)
            ? sysOptions.all_cloud
            : Object.values(sysOptions.all_cloud || {});
        if (cloudList.length) {
            const cg = document.createElement('optgroup');
            cg.label = '☁️ Cloud API Models';
            cloudList.forEach(m => {
                const opt = document.createElement('option');
                opt.value = normCloudValue(m);
                opt.textContent = formatRichLabel(m, 'cloud');
                cg.appendChild(opt);
            });
            modelSelect.appendChild(cg);
        }

        if (currentModel) {
            const candidateOllama = currentModel.includes('/') ? currentModel : `ollama_chat/${currentModel}`;
            const existsDirect = Array.from(modelSelect.options).some(o => o.value === currentModel);
            const existsPrefixed = Array.from(modelSelect.options).some(o => o.value === candidateOllama);
            if (existsDirect) {
                modelSelect.value = currentModel;
            } else if (existsPrefixed) {
                modelSelect.value = candidateOllama;
            } else {
                const customOpt = document.createElement('option');
                customOpt.value = currentModel;
                customOpt.textContent = `${currentModel} (custom)`;
                modelSelect.appendChild(customOpt);
                modelSelect.value = currentModel;
            }
        } else {
            modelSelect.value = '';
        }
    }
}

window.onExecutorAiderConfigChange = function(key, val) {
    savePluginKey('EXECUTOR', key, val);
    setTimeout(() => {
        if (typeof window.refreshExecutorAiderStatus === 'function') window.refreshExecutorAiderStatus();
    }, 350);
};

window.refreshExecutorAiderStatus = async function() {
    const el = document.getElementById('executor-aider-live-status');
    const btn = document.getElementById('executor-aider-install-btn');
    if (!el) return;
    try {
        const resp = await fetch('/api/workspace/aider/status');
        const data = await resp.json();
        if (!resp.ok || !data.ok) {
            el.textContent = 'Status unavailable';
            return;
        }
        const gpTxt = data.global_preset ? `GP: <code>${data.global_preset}</code> · ` : '';
        if (data.installed) {
            el.innerHTML = `<span style="color:#34d399; font-weight:600;">● ${data.version || 'Ready'}</span> · ${gpTxt}Active: <code>${data.model || '?'}</code> (ctx ${data.num_ctx || 16384})`;
            if (btn) btn.innerHTML = '<i class="fas fa-sync-alt"></i> Update Aider';
        } else {
            el.innerHTML = `<span style="color:#fbbf24; font-weight:600;">● Not Installed</span> · ${gpTxt}Target: <code>${data.model || '?'}</code>`;
            if (btn) btn.innerHTML = '<i class="fas fa-download"></i> Install Aider';
        }
    } catch (e) {
        el.textContent = 'Offline / Error checking Aider';
    }
};

window.installOrUpdateAiderFromPanel = async function() {
    const btn = document.getElementById('executor-aider-install-btn');
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Working...';
    }
    try {
        const resp = await fetch('/api/workspace/aider/install', { method: 'POST' });
        const data = await resp.json();
        if (typeof showToast === 'function') showToast(data.message || data.error || 'Done', !data.ok);
    } catch (e) {
        if (typeof showToast === 'function') showToast('Aider error: ' + e, true);
    } finally {
        if (btn) btn.disabled = false;
        window.refreshExecutorAiderStatus();
    }
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
            <button type="button" class="btn btn-danger btn-sm" onclick="HecosTextFilters.removeRow(this)" title="Remove"><i class="fas fa-trash"></i></button>
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
    // Explicitly persist: saveDsb is called from onclick handlers, not DOM change events,
    // so the global auto-save listener never fires for these mutations.
    if (typeof window.saveConfig === 'function') window.saveConfig(true);
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
