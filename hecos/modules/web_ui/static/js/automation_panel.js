/**
 * pc_automation_panel.js
 * Config panel JS for the PC Automation HPM package.
 * Loads current config values and binds save via savePluginKey().
 */

(function () {
    function loadAutomationConfig() {
        fetch('/hecos/api/plugins/pc_automation/config')
            .then(r => r.json())
            .then(cfg => {
                const enabled = document.getElementById('automation-enabled');
                if (enabled) enabled.checked = cfg.enabled !== false;

                const moveDur = document.getElementById('automation-move-duration');
                if (moveDur) moveDur.value = cfg.move_duration ?? 0.15;

                const typeInt = document.getElementById('automation-type-interval');
                if (typeInt) typeInt.value = cfg.type_interval ?? 0.02;

                const winCtrl = document.getElementById('automation-window-control');
                if (winCtrl) winCtrl.checked = cfg.allow_window_control !== false;
            })
            .catch(err => console.warn('[PC_AUTOMATION] Failed to load config:', err));
    }

    // Run when panel becomes active
    document.addEventListener('DOMContentLoaded', loadAutomationConfig);

    // Also expose for manual reload
    window.reloadAutomationPanel = loadAutomationConfig;
})();
