/**
 * ch_modes.js
 * ─────────────────────────────────────────────────────────────────────────────
 * Hecos Chat History — Privacy Modes (Normal / Incognito) & UI Locking
 * ─────────────────────────────────────────────────────────────────────────────
 */

window.normalizePrivacyMode = function (mode) {
    const val = String(mode || 'normal').trim().toLowerCase();
    return (val === 'incognito' || val === 'auto_wipe') ? 'incognito' : 'normal';
};

window.getDefaultPrivacyMode = function () {
    const raw = window.cfg?.privacy?.default_mode || 'normal';
    return window.normalizePrivacyMode(raw);
};

window.setPrivacyMode = async function (mode) {
    const norm = window.normalizePrivacyMode(mode);
    const res = await window._historyPost('/api/chat/privacy', { mode: norm });
    if (res.ok) {
        window.chatHistoryState.activeMode = window.normalizePrivacyMode(res.mode || norm);
        if (window.updateModeUI) updateModeUI();
        if (window.loadChatSessions) await window.loadChatSessions();
    }
};

window.selectChatMode = function (mode) {
    // Lock picker if there are already messages in this session
    if (window.chatHistoryState.chatModeHasMessages) return;
    if (window.setPrivacyMode) window.setPrivacyMode(mode);
};

window.updateModeUI = function () {
    const mode        = window.normalizePrivacyMode(window.chatHistoryState.activeMode);
    const hasMessages = window.chatHistoryState.chatModeHasMessages;

    // 1. Mode picker buttons
    ['normal', 'incognito'].forEach(m => {
        const btn = document.getElementById(`mode-btn-${m}`);
        if (btn) btn.classList.toggle('active', m === mode);
    });

    // 2. Lock / unlock picker
    const picker = document.getElementById('chat-mode-picker');
    const notice = document.getElementById('mode-lock-notice');
    if (picker) picker.classList.toggle('locked', hasMessages);
    if (notice) notice.style.display = hasMessages ? 'block' : 'none';

    // 3. Topbar mode chip
    const chip = document.getElementById('topbar-mode-chip');
    if (chip) {
        if (mode === 'normal') {
            chip.style.display = 'none';
        } else {
            chip.style.display = '';
            chip.innerHTML     = '🕵️ Incognito';
            chip.className     = 'topbar-chip mode-chip-incognito';
            chip.title         = window.I18N?.webui_chat_mode_incognito_tip
                || 'Incognito: RAM-only session, zero disk writes, anonymous identity';
        }
    }
};

// Backward-compatibility alias used elsewhere in index.html
window.updatePrivacyIndicator = window.updateModeUI;
