/**
 * config_mapper_components.js
 * Populate + build payload for: WebUI, Privacy, Agent, Reminder.
 * Depends on: config_mapper_utils.js
 */

// ── WebUI ──────────────────────────────────────────────────────────────────────
function populateWebUIConfig() {
    const c = window.cfg;
    if (!c?.plugins?.WEB_UI) return;
    const w = c.plugins.WEB_UI;
    setVal('webui-port',         w.port         || 8080);
    setVal('webui-api-port',     w.api_port      || 5000);
    setCheck('webui-force-login',w.force_login   ?? true);
    setCheck('webui-https-enabled', w.https_enabled ?? false);
    setVal('webui-cert-file',    w.cert_file    || 'certs/cert.pem');
    setVal('webui-key-file',     w.key_file     || 'certs/key.pem');
}

function buildWebUIPayload() {
    const w = window.cfg?.plugins?.WEB_UI || {};
    return {
        plugins: {
            WEB_UI: {
                port:          parseInt(getV('webui-port',     w.port))         || 8080,
                api_port:      parseInt(getV('webui-api-port', w.api_port))     || 5000,
                force_login:   getC('webui-force-login',   w.force_login   ?? true),
                https_enabled: getC('webui-https-enabled', w.https_enabled ?? false),
                cert_file:     getV('webui-cert-file',     w.cert_file),
                key_file:      getV('webui-key-file',      w.key_file)
            }
        }
    };
}

// ── Privacy ───────────────────────────────────────────────────────────────────
function populatePrivacyUI() {
    const c = window.cfg;
    if (!c?.privacy) return;
    setVal('pr-default-mode',       c.privacy.default_mode       || 'normal');
    setCheck('pr-auto-wipe',        c.privacy.auto_wipe_enabled  ?? false);
    setCheck('pr-incognito-shortcut', c.privacy.incognito_shortcut ?? true);
}

// ── Agent ─────────────────────────────────────────────────────────────────────
function populateAgentUI() {
    const c = window.cfg;
    if (!c?.agent) return;
    const a = c.agent;
    const traceMode = a.trace_mode || (a.verbose_traces === false ? 'off' : 'detailed');
    const actionMode = a.action_console_mode || (a.action_console_enabled === false ? 'off' : 'inline');

    setCheck('agent-enabled',           a.enabled                ?? true);
    setVal('agent-max-iter',            a.max_iterations         ?? 15);
    setVal('agent-trace-mode',          traceMode);
    setVal('agent-trace-after-done',    a.trace_after_done       || 'summary');
    setCheck('agent-trace-show-args',   a.trace_show_args        ?? true);
    setCheck('agent-trace-persist',     a.trace_persist_history  ?? true);
    setVal('agent-action-console-mode', actionMode);
    setCheck('agent-cli-traces',        a.cli_traces_enabled     ?? true);
}

function buildAgentPayload() {
    const a = window.cfg?.agent || {};
    const traceMode = getV('agent-trace-mode', a.trace_mode || 'detailed');
    const actionMode = getV('agent-action-console-mode', a.action_console_mode || 'inline');
    const maxIterRaw = parseInt(getV('agent-max-iter', a.max_iterations ?? 15), 10);
    const maxIter = isNaN(maxIterRaw) ? 15 : Math.max(1, Math.min(50, maxIterRaw));

    return {
        agent: {
            enabled:                getC('agent-enabled',          a.enabled                ?? true),
            max_iterations:         maxIter,
            verbose_traces:         traceMode !== 'off',
            trace_mode:             traceMode,
            trace_after_done:       getV('agent-trace-after-done', a.trace_after_done       || 'summary'),
            trace_show_args:        getC('agent-trace-show-args',  a.trace_show_args        ?? true),
            trace_persist_history:  getC('agent-trace-persist',    a.trace_persist_history  ?? true),
            cli_traces_enabled:     getC('agent-cli-traces',       a.cli_traces_enabled     ?? true),
            action_console_enabled: actionMode !== 'off',
            action_console_mode:    actionMode
        }
    };
}

// ── Reminder ──────────────────────────────────────────────────────────────────
function populateReminderUI() {
    const c = window.cfg;
    if (!c?.plugins?.REMINDER) return;
    const s = c.plugins.REMINDER;
    setVal('rem-mode',      s.reminder_mode           || 'voice');
    setVal('rem-ringtone',  s.ringtone_path            || '');
    setVal('rem-time-format', s.time_format            || '24h');
    setVal('rem-max',       s.max_reminders            ?? 50);
    setVal('rem-snooze',    s.snooze_default_minutes   ?? 15);
    setCheck('rem-snooze-ui', s.reminder_snooze_ui     ?? false);
}

function buildReminderPayload() {
    const s = window.cfg?.plugins?.REMINDER;
    if (!s) return { plugins: {} };
    return {
        plugins: {
            REMINDER: {
                reminder_mode:          getV('rem-mode',      s.reminder_mode    || 'voice'),
                ringtone_path:          getV('rem-ringtone',  s.ringtone_path    || ''),
                time_format:            getV('rem-time-format', s.time_format    || '24h'),
                max_reminders:          parseInt(getV('rem-max',   s.max_reminders))  || 50,
                snooze_default_minutes: parseInt(getV('rem-snooze',s.snooze_default_minutes)) || 15,
                reminder_snooze_ui:     getC('rem-snooze-ui', s.reminder_snooze_ui ?? false)
            }
        }
    };
}


// ── Vision / Multimodal Perception ───────────────────────────────────────────
function _populateVisionSelect(id, plainList, currentValue, backendType, richModels) {
    const el = document.getElementById(id);
    if (!el) return;
    el.innerHTML = '';

    // Add Default option at top
    const defOpt = document.createElement('option');
    defOpt.value = 'default';
    defOpt.textContent = '🎯 Use Active Chat Model (Default)';
    el.appendChild(defOpt);

    let items = plainList;
    if (plainList && typeof plainList === 'object' && !Array.isArray(plainList)) {
        items = Object.values(plainList);
    }

    const iconMap = { 'tools': '⚙️', 'vision': '👁️', 'thinking': '💭' };
    const descMap = { 'tools': 'Tools', 'vision': 'Vision', 'thinking': 'Thinking' };

    if (Array.isArray(items)) {
        items.forEach(m => {
            if (!m) return;
            const opt = document.createElement('option');
            opt.value = m;

            const richModel = (richModels || []).find(rm => {
                if (backendType === 'cloud') return rm.type === 'cloud' && rm.id === m;
                return rm.provider === backendType && rm.id === m;
            });

            if (richModel) {
                const prefix = richModel.type === 'cloud' ? '☁️ ' : '🖥️ ';
                let suffix = '';
                let sizeTag = '';

                if (richModel.parameter_size || richModel.size_bytes) {
                    const parts = [];
                    if (richModel.parameter_size) {
                        let p = richModel.parameter_size;
                        if (richModel.quantization_level) p += ' ' + richModel.quantization_level;
                        parts.push(p);
                    }
                    if (richModel.size_bytes) {
                        parts.push((richModel.size_bytes / (1024*1024*1024)).toFixed(1) + 'GB');
                    }
                    sizeTag = ' [' + parts.join(' | ') + ']';
                }

                let tooltipText = richModel.name + sizeTag;

                if (richModel.capabilities && richModel.capabilities.length > 0) {
                    const icons = richModel.capabilities.map(c => iconMap[c]).filter(Boolean).join('');
                    if (icons) suffix = ' ' + icons;
                    const descs = richModel.capabilities.map(c => descMap[c]).filter(Boolean).join(', ');
                    if (descs) tooltipText += '\nCapabilities: ' + descs;
                }

                opt.textContent = prefix + richModel.name + sizeTag + suffix;
                opt.title = tooltipText;
            } else {
                opt.textContent = m;
                opt.title = m;
            }
            el.appendChild(opt);
        });
    }

    if (currentValue) {
        el.value = currentValue;
    } else {
        el.value = 'default';
    }
}

async function populateVisionUI() {
    const c = window.cfg;
    if (!c?.vision) return;
    const v = c.vision;
    setCheck('vision-enabled',          v.enabled                   ?? true);
    setVal('vision-max-res',            v.max_resolution_px        ?? 512);
    setVal('vision-quality',            v.jpeg_quality             ?? 80);
    setVal('vision-timeout',            v.timeout_seconds          ?? 5);

    const b = v.bridge || {};
    setCheck('vision-bridge-enabled',   b.enabled                   ?? true);
    setVal('vision-bridge-mode',        b.mode                     || 'auto');
    setVal('vision-inspection-prompt',  b.inspection_prompt        || 'Describe in detail and objectively the visual elements of the image: subjects, actions, visible text, colors, setting, and notable details.');

    // Populate rich dropdowns mirroring AI Backend
    const sysOptions = window.sysOptions || {};
    const richModels = (typeof _ensureRichModels === 'function') ? await _ensureRichModels() : [];
    
    // Cloud Inspector Select
    _populateVisionSelect('vision-cloud-model', sysOptions.all_cloud || [], b.cloud_model || 'gemini/gemini-2.5-flash', 'cloud', richModels);
    
    // Local Ollama Select
    _populateVisionSelect('vision-local-model', sysOptions.ollama_models || [], b.local_model || 'default', 'ollama', richModels);

    // Apply visibility based on mode
    if (typeof window._applyVisionModeVisibility === 'function') {
        window._applyVisionModeVisibility(b.mode || 'auto');
    }

    const ns = v.net_search || {};
    setCheck('vision-netsearch-verify', ns.verify_results          ?? true);
    setVal('vision-netsearch-max',      ns.max_thumbnails          ?? 4);
}

function buildVisionPayload() {
    const v = window.cfg?.vision || {};
    const b = v.bridge || {};
    const ns = v.net_search || {};

    const localModelEl = document.getElementById('vision-local-model');
    const cloudModelEl = document.getElementById('vision-cloud-model');

    return {
        vision: {
            enabled:           getC('vision-enabled',          v.enabled ?? true),
            max_resolution_px: parseInt(getV('vision-max-res', v.max_resolution_px)) || 512,
            jpeg_quality:      parseInt(getV('vision-quality', v.jpeg_quality)) || 80,
            timeout_seconds:   parseInt(getV('vision-timeout', v.timeout_seconds)) || 5,
            bridge: {
                enabled:           getC('vision-bridge-enabled',  b.enabled ?? true),
                mode:              getV('vision-bridge-mode',     b.mode || 'auto'),
                cloud_model:       localModelEl && cloudModelEl ? cloudModelEl.value : (b.cloud_model || 'gemini/gemini-2.5-flash'),
                local_model:       localModelEl ? localModelEl.value : (b.local_model || 'default'),
                inspection_prompt: getV('vision-inspection-prompt', b.inspection_prompt || '')
            },
            net_search: {
                verify_results: getC('vision-netsearch-verify', ns.verify_results ?? true),
                max_thumbnails: parseInt(getV('vision-netsearch-max', ns.max_thumbnails)) || 4
            }
        }
    };
}

window.populateWebUIConfig       = populateWebUIConfig;
window.buildWebUIPayload         = buildWebUIPayload;
window.populatePrivacyUI         = populatePrivacyUI;
window.populateAgentUI           = populateAgentUI;
window.buildAgentPayload         = buildAgentPayload;
window.populateReminderUI        = populateReminderUI;
window.buildReminderPayload      = buildReminderPayload;

window.populateVisionUI = populateVisionUI;
window.buildVisionPayload = buildVisionPayload;
