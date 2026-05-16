/**
 * config_mapper_components.js
 * Populate + build payload for: RemoteTriggers, WebUI, Privacy, Agent, Reminder.
 * Depends on: config_mapper_utils.js
 */

// ── Remote Triggers ────────────────────────────────────────────────────────────
function populateRemoteTriggersUI() {
    const c = window.cfg;
    if (!c?.plugins?.REMOTE_TRIGGERS) return;
    const settings = c.plugins.REMOTE_TRIGGERS.settings || {};
    setCheck('rt-enable-mediasession', settings.enable_mediasession ?? true);
    setCheck('rt-enable-volume-keys',  settings.enable_volume_keys  ?? true);
    setCheck('rt-enable-volume-loop',  settings.enable_volume_loop  ?? false);
    setCheck('rt-feedback-sounds',     settings.feedback_sounds     ?? true);
    setCheck('rt-visual-indicator',    settings.visual_indicator    ?? true);
}

function buildRemoteTriggersPayload() {
    const settings = window.cfg?.plugins?.REMOTE_TRIGGERS?.settings || {};
    return {
        plugins: {
            REMOTE_TRIGGERS: {
                settings: {
                    enable_mediasession: getC('rt-enable-mediasession', settings.enable_mediasession),
                    enable_volume_keys:  getC('rt-enable-volume-keys',  settings.enable_volume_keys),
                    enable_volume_loop:  getC('rt-enable-volume-loop',  settings.enable_volume_loop),
                    feedback_sounds:     getC('rt-feedback-sounds',     settings.feedback_sounds),
                    visual_indicator:    getC('rt-visual-indicator',    settings.visual_indicator)
                }
            }
        }
    };
}

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
    setCheck('agent-enabled',       a.enabled              ?? true);
    setVal('agent-max-iter',        a.max_iterations       ?? 10);
    setCheck('agent-verbose',       a.verbose_traces       ?? true);
    setCheck('agent-action-console',a.action_console_enabled ?? true);
}

function buildAgentPayload() {
    const a = window.cfg?.agent || {};
    return {
        agent: {
            enabled:                getC('agent-enabled',        a.enabled                 ?? true),
            max_iterations:         parseInt(getV('agent-max-iter', a.max_iterations))     || 10,
            verbose_traces:         getC('agent-verbose',        a.verbose_traces          ?? true),
            action_console_enabled: getC('agent-action-console', a.action_console_enabled  ?? true)
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
    const s = window.cfg?.plugins?.REMINDER || {};
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

window.populateRemoteTriggersUI  = populateRemoteTriggersUI;
window.buildRemoteTriggersPayload = buildRemoteTriggersPayload;
window.populateWebUIConfig       = populateWebUIConfig;
window.buildWebUIPayload         = buildWebUIPayload;
window.populatePrivacyUI         = populatePrivacyUI;
window.populateAgentUI           = populateAgentUI;
window.buildAgentPayload         = buildAgentPayload;
window.populateReminderUI        = populateReminderUI;
window.buildReminderPayload      = buildReminderPayload;
