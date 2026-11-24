/**
 * coder_panel.js — Central Hub configuration controller for Hecos Coder (system_app).
 */
(function () {
    window.saveCoderKey = function (key, val) {
        if (typeof window.savePluginKey === 'function') {
            window.savePluginKey('EXECUTOR', key, val);
            window.savePluginKey('CODER', key, val);
        }
        fetch('/hecos/api/plugins/coder/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ [key]: val })
        }).catch(() => {});
    };

    window.launchCoderTerminal = async function (mode) {
        try {
            const resp = await fetch('/api/workspace/cli/open', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ mode: mode || 'shell', path: '' })
            });
            const data = await resp.json();
            if (typeof window.showToast === 'function') {
                window.showToast(data.ok ? `Opened ${data.title || mode}` : (data.error || 'Failed to launch terminal'), !data.ok);
            }
        } catch (err) {
            if (typeof window.showToast === 'function') {
                window.showToast('Failed to launch terminal: ' + (err.message || err), true);
            }
        }
    };

    window.populateCoderUI = async function () {
        const p = Object.assign(
            {},
            (window.cfg?.plugins || {}).EXECUTOR || {},
            (window.cfg?.plugins || {}).CODER || {}
        );
        if (typeof setCheck === 'function') {
            setCheck('coder-allow-ui-exec', p.allow_ui_script_execution !== false);
            setCheck('coder-auto-verify-syntax', p.auto_verify_syntax_on_write !== false);
            setCheck('coder-auto-run-tests', p.auto_run_existing_tests_on_write !== false);
        }
        if (typeof window.populateExecutorUI === 'function') {
            await window.populateExecutorUI();
        }
    };

    // Auto-populate when the coder panel is injected
    setTimeout(() => {
        if (document.getElementById('tab-coder')) {
            window.populateCoderUI();
        }
    }, 80);
})();
