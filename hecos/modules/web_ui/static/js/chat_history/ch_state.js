/**
 * ch_state.js
 * ─────────────────────────────────────────────────────────────────────────────
 * Hecos Chat History — State, API & Init
 * ─────────────────────────────────────────────────────────────────────────────
 */

window.chatHistoryState = {
    sessions: [],
    activeSessionId: null,
    activeMode: 'normal',
    chatModeHasMessages: false,  // true after first message → mode picker locks
    showArchived: false,
    isUIRendered: false
};

// ─── API helpers ──────────────────────────────────────────────────────────────

async function _historyGet(url) {
    console.log(`[HISTORY-DEBUG] GET Request to: ${url}`);
    try {
        const r = await fetch(url);
        const data = await r.json();
        return data;
    } catch (e) {
        console.error(`[HISTORY-DEBUG] GET Error:`, e);
        return { ok: false, error: e.message };
    }
}

async function _historyPost(url, body = {}, method = 'POST') {
    console.log(`[HISTORY-DEBUG] ${method} Request to: ${url}`);
    try {
        const r = await fetch(url, {
            method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        const data = await r.json();
        return data;
    } catch (e) {
        console.error(`[HISTORY-DEBUG] ${method} Error:`, e);
        return { ok: false, error: e.message };
    }
}

// Ensure these are globally accessible for siblings
window._historyGet = _historyGet;
window._historyPost = _historyPost;

// ─── Init ─────────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', async () => {
    // 1. Try to restore active session from localStorage
    const localSid = localStorage.getItem('hecos_active_session_id');

    // 2. Check current server active session
    const res = await _historyGet('/api/chat/sessions/active');

    if (res.ok && res.session_id) {
        localStorage.setItem('hecos_active_session_id', res.session_id);
    } else if (localSid) {
        console.log(`[HISTORY] Server lost active session. Attempting to reclaim: ${localSid}`);
        const reclaim = await _historyPost('/api/chat/sessions/active', { session_id: localSid });
        if (!reclaim.ok) {
            await _historyPost('/api/chat/sessions', { title: null, privacy_mode: 'normal' });
        }
    } else {
        // No session anywhere, create fresh
        await _historyPost('/api/chat/sessions', { title: null, privacy_mode: 'normal' });
    }

    if (window.loadChatSessions) await window.loadChatSessions();
});
