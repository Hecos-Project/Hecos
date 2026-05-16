/**
 * ch_modes.js
 * ─────────────────────────────────────────────────────────────────────────────
 * Hecos Chat History — Privacy Modes & UI Locking
 * ─────────────────────────────────────────────────────────────────────────────
 */

window.setPrivacyMode = async function (mode) {
    const res = await window._historyPost('/api/chat/privacy', { mode });
    if (res.ok) {
        window.chatHistoryState.activeMode = mode;
        if (window.updateModeUI) updateModeUI();
        if (window.loadChatSessions) await window.loadChatSessions();
    }
};

window.selectChatMode = function (mode) {
    // Lock picker if there are already messages
    if (window.chatHistoryState.chatModeHasMessages) return;  
    if (window.setPrivacyMode) window.setPrivacyMode(mode);
};

window.updateModeUI = function () {
    const mode        = window.chatHistoryState.activeMode;
    const hasMessages = window.chatHistoryState.chatModeHasMessages;

    // 1. Mode picker buttons
    ['normal', 'auto_wipe', 'incognito'].forEach(m => {
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
            const chipInfo = {
                auto_wipe: { icon: '🧹', label: 'Auto-Wipe', cls: 'mode-chip-autowipe' },
                incognito: { icon: '🕵️', label: 'Incognito', cls: 'mode-chip-incognito' }
            }[mode];
            chip.style.display = '';
            chip.innerHTML     = `${chipInfo.icon} ${chipInfo.label}`;
            chip.className     = `topbar-chip ${chipInfo.cls}`;
        }
    }
};

// Backward-compatibility alias used elsewhere in index.html
window.updatePrivacyIndicator = window.updateModeUI;
