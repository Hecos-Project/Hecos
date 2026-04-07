/**
 * Zentra Core WebUI - AutoCoder Configuration Logic
 */

function populateAutoCoderUI() {
    const c = window.cfg;
    const ac = (c.plugins || {}).AUTOCODER || {};
    
    setCheck('plugin-autocoder-enabled', ac.enabled ?? true);
    setCheck('plugin-autocoder-sandbox', ac.sandbox_only ?? false);
    setCheck('plugin-autocoder-lazy', ac.lazy_load ?? false);
}

function buildAutoCoderPayload() {
    return {
        AUTOCODER: {
            enabled: document.getElementById('plugin-autocoder-enabled').checked,
            sandbox_only: document.getElementById('plugin-autocoder-sandbox').checked,
            lazy_load: document.getElementById('plugin-autocoder-lazy').checked
        }
    };
}

// Global Exports
window.populateAutoCoderUI = populateAutoCoderUI;
window.buildAutoCoderPayload = buildAutoCoderPayload;
