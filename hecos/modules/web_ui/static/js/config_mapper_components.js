/**
 * Hecos WebUI - Mapper Logic for Specialized Components
 * Handles Reminder, Executor, and Automation.
 */

function populateReminderUI() {
    const c = window.cfg;
    if (!c || !c.plugins || !c.plugins.REMINDER) return;
    const s = c.plugins.REMINDER;
    setVal('rem-mode', s.reminder_mode || 'voice');
    setVal('rem-ringtone', s.ringtone_path || '');
    setVal('rem-time-format', s.time_format || '24h');
    setVal('rem-max', s.max_reminders ?? 50);
    setVal('rem-snooze', s.snooze_default_minutes ?? 15);
    setCheck('rem-snooze-ui', s.reminder_snooze_ui ?? false);
}

function buildReminderPayload() {
    const el = document.getElementById('rem-mode');
    const s = window.cfg.plugins?.REMINDER || {};
    return {
        plugins: {
            REMINDER: {
                reminder_mode: getV('rem-mode', s.reminder_mode || 'voice'),
                ringtone_path: getV('rem-ringtone', s.ringtone_path || ''),
                time_format: getV('rem-time-format', s.time_format || '24h'),
                max_reminders: parseInt(getV('rem-max', s.max_reminders)) || 50,
                snooze_default_minutes: parseInt(getV('rem-snooze', s.snooze_default_minutes)) || 15,
                reminder_snooze_ui: getC('rem-snooze-ui', s.reminder_snooze_ui ?? false)
            }
        }
    };
}

function populateExecutorUI() {
    const p = (window.cfg.plugins || {}).EXECUTOR || {};
    setVal('executor-timeout',        p.timeout_seconds ?? 10);
    setCheck('executor-shell-enabled',  p.enable_shell_commands ?? true);
    setVal('executor-shell-timeout',  p.shell_timeout ?? 15);
    setVal('executor-max-read-lines', p.max_read_lines ?? 200);
    setVal('executor-workspace-dir',  p.workspace_dir ?? 'workspace/sandbox');
}

function populateAutomationUI() {
    const p = (window.cfg.plugins || {}).AUTOMATION || {};
    setCheck('automation-enabled',       p.enabled ?? true);
    setVal('automation-move-duration', p.move_duration ?? 0.15);
    setVal('automation-type-interval', p.type_interval ?? 0.02);
    setCheck('automation-window-control',p.allow_window_control ?? true);
}

// Bridges for global scope
window.populateReminderUI = populateReminderUI;
window.buildReminderPayload = buildReminderPayload;
window.populateExecutorUI = populateExecutorUI;
window.populateAutomationUI = populateAutomationUI;
