/**
 * Hecos WebUI - Mapper Logic for Privacy Settings
 */

function populatePrivacyUI() {
    const c = window.cfg;
    if (!c || !c.privacy) return;
    setVal('pr-default-mode', c.privacy.default_mode || 'normal');
    setCheck('pr-auto-wipe', c.privacy.auto_wipe_enabled ?? false);
    setCheck('pr-incognito-shortcut', c.privacy.incognito_shortcut ?? true);
}

window.populatePrivacyUI = populatePrivacyUI;
