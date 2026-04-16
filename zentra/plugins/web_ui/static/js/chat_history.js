/**
 * chat_history.js
 * Manages the chat session sidebar: load, display, switch, delete, rename.
 * v2 — Unified 3-state privacy mode picker with session-level lock.
 */

window.chatHistoryState = {
    sessions: [],
    activeSessionId: null,
    activeMode: 'normal',
    chatModeHasMessages: false  // true after first message → mode picker locks
};

// ─── API helpers ──────────────────────────────────────────────────────────────

async function _historyGet(url) {
    console.log(`[HISTORY-DEBUG] GET Request to: ${url}`);
    try {
        const r = await fetch(url);
        console.log(`[HISTORY-DEBUG] Response status: ${r.status}`);
        const data = await r.json();
        console.log(`[HISTORY-DEBUG] Response data:`, data);
        return data;
    } catch (e) {
        console.error(`[HISTORY-DEBUG] GET Error:`, e);
        return { ok: false, error: e.message };
    }
}

async function _historyPost(url, body = {}, method = 'POST') {
    console.log(`[HISTORY-DEBUG] ${method} Request to: ${url} with body:`, body);
    try {
        const r = await fetch(url, {
            method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        console.log(`[HISTORY-DEBUG] Response status: ${r.status}`);
        const data = await r.json();
        console.log(`[HISTORY-DEBUG] Response data:`, data);
        return data;
    } catch (e) {
        console.error(`[HISTORY-DEBUG] ${method} Error:`, e);
        return { ok: false, error: e.message };
    }
}

// ─── Load & Render ────────────────────────────────────────────────────────────

window.loadChatSessions = async function () {
    const [resSessions, resActive] = await Promise.all([
        _historyGet('/api/chat/sessions'),
        _historyGet('/api/chat/sessions/active')
    ]);

    if (resSessions.ok) {
        window.chatHistoryState.sessions = resSessions.sessions || [];
    }
    if (resActive.ok) {
        window.chatHistoryState.activeSessionId = resActive.session_id;
        window.chatHistoryState.activeMode      = resActive.mode || 'normal';
        if (resActive.session_id) {
            localStorage.setItem('zentra_active_session_id', resActive.session_id);
        }
    }

    // Restore lock state: check if the active session already has messages
    const activeSess = window.chatHistoryState.sessions.find(
        s => s.id === window.chatHistoryState.activeSessionId
    );
    window.chatHistoryState.chatModeHasMessages = activeSess
        ? (activeSess.message_count || 0) > 0
        : false;

    renderSessionList();
    updateModeUI();
};

function renderSessionList() {
    const container = document.getElementById('chat-history-list');
    if (!container) return;

    const sessions = window.chatHistoryState.sessions;
    const activeId = window.chatHistoryState.activeSessionId;

    if (!sessions.length) {
        container.innerHTML = `<div class="history-empty">${window.I18N?.webui_chat_history_empty || 'No conversations saved'}</div>`;
        return;
    }

    container.innerHTML = sessions.map(s => {
        const isActive = s.id === activeId;
        const modeIcon = s.privacy_mode === 'incognito' ? '🕵️' :
                         s.privacy_mode === 'auto_wipe' ? '🧹' : '';
        const msgCount = s.message_count || 0;
        const dateStr  = s.updated_at ? s.updated_at.slice(0, 16).replace('T', ' ') : '';
        const title    = escapeHistoryHtml(s.title || 'Chat senza titolo');

        return `
        <div class="history-item${isActive ? ' active' : ''}" data-id="${s.id}" onclick="activateChatSession('${s.id}')">
          <div class="history-item-main">
            <span class="history-icon">${modeIcon || '💬'}</span>
            <div class="history-item-info">
              <div class="history-title" title="Doppio click per rinominare" ondblclick="startRenameSession(event, '${s.id}')">${title}</div>
              <div class="history-meta">${dateStr} · ${msgCount} msg</div>
            </div>
          </div>
          <div class="history-item-actions">
            <button class="history-action-btn" title="Elimina" onclick="deleteChatSession(event, '${s.id}')">🗑️</button>
          </div>
        </div>`;
    }).join('');
}

// ─── Session Actions ──────────────────────────────────────────────────────────

window.newChatSession = async function (mode = null) {
    // New chats are always 'normal' unless explicitly passed a different mode
    const privMode = mode || 'normal';

    // Create new session
    const res = await _historyPost('/api/chat/sessions', { privacy_mode: privMode });
    if (!res.ok) {
        alert(`Errore creazione sessione: ${res.error || 'Unknown'}`);
        return;
    }

    window.chatHistoryState.activeSessionId     = res.session_id;
    window.chatHistoryState.activeMode          = privMode;
    window.chatHistoryState.chatModeHasMessages = false;  // new session → picker unlocked
    localStorage.setItem('zentra_active_session_id', res.session_id);

    // Clear chat UI
    if (window._clearChatDOM) {
        window._clearChatDOM();
    } else if (window.clearChat) {
        window._clearChatDOM = window.clearChat;
        window.chatArea && (window.chatArea.innerHTML = '');
    }

    // Reload session list (also calls updateModeUI internally)
    await window.loadChatSessions();
};

window.activateChatSession = async function (sessionId) {
    if (sessionId === window.chatHistoryState.activeSessionId) return;

    // Refresh data to ensure counts are accurate
    if (window.loadChatSessions) await window.loadChatSessions();

    // Fetch messages of the clicked session
    const res = await _historyGet(`/api/chat/sessions/${sessionId}/messages`);
    if (!res.ok) {
        alert(`Errore caricamento messaggi: ${res.error || 'Unknown'}`);
        return;
    }

    const session = window.chatHistoryState.sessions.find(s => s.id === sessionId);
    const mode    = session?.privacy_mode || 'normal';

    // Activate server-side
    await _historyPost('/api/chat/sessions/active', { session_id: sessionId, privacy_mode: mode });

    window.chatHistoryState.activeSessionId     = sessionId;
    window.chatHistoryState.activeMode          = mode;
    window.chatHistoryState.chatModeHasMessages = (res.messages || []).length > 0;
    localStorage.setItem('zentra_active_session_id', sessionId);

    // Restore messages in chat UI
    if (window._clearChatDOM) {
        window._clearChatDOM();
    } else if (window.chatArea) {
        window.chatArea.innerHTML = '';
    }

    if (window.renderHistoryMessages) {
        window.renderHistoryMessages(res.messages || []);
    }

    renderSessionList();
    updateModeUI();
};

window.deleteChatSession = async function (e, sessionId) {
    e.stopPropagation();
    if (!confirm('Eliminare questa conversazione? L\'operazione non è reversibile.')) return;
    await _historyPost(`/api/chat/sessions/${sessionId}`, {}, 'DELETE');
    if (window.chatHistoryState.activeSessionId === sessionId) {
        if (window._clearChatDOM) window._clearChatDOM();
        else if (window.chatArea) window.chatArea.innerHTML = '';
        window.chatHistoryState.activeSessionId = null;
    }
    await window.loadChatSessions();
    
    // Fallback: If no sessions left, create a fresh one. If sessions exist but none active, activate the first one.
    if (window.chatHistoryState.sessions.length === 0) {
        await window.newChatSession();
    } else if (!window.chatHistoryState.activeSessionId) {
        await window.activateChatSession(window.chatHistoryState.sessions[0].id);
    }
};

window.deleteAllChatSessions = async function (e) {
    if (e) e.stopPropagation();
    const msg = window.I18N?.webui_chat_delete_confirm_all || 'Delete ALL conversations? This cannot be undone.';
    if (!confirm(msg)) return;
    const res = await _historyPost(`/api/chat/sessions/all`, {}, 'DELETE');
    if (res.ok) {
        if (window._clearChatDOM) window._clearChatDOM();
        else if (window.chatArea) window.chatArea.innerHTML = '';
        window.chatHistoryState.activeSessionId = null;
        await window.loadChatSessions();
        await window.newChatSession();
    } else {
        alert('Errore durante l\'eliminazione: ' + res.error);
    }
};

window.startRenameSession = async function (e, sessionId) {
    e.stopPropagation();
    const item = e.currentTarget;
    const current = item.textContent.trim();
    const newName = prompt('Rinomina conversazione:', current);
    if (!newName || newName === current) return;
    const res = await _historyPost(`/api/chat/sessions/${sessionId}`, { title: newName }, 'PATCH');
    if (res.ok) await window.loadChatSessions();
};

// ─── Privacy / Mode Switcher ──────────────────────────────────────────────────

window.setPrivacyMode = async function (mode) {
    const res = await _historyPost('/api/chat/privacy', { mode });
    if (res.ok) {
        window.chatHistoryState.activeMode = mode;
        updateModeUI();
        if (window.loadChatSessions) await window.loadChatSessions();
    }
};

/**
 * Called by the 3-button mode picker in the sidebar.
 * Silently ignored if the mode is already locked (session has messages),
 * which is also enforced visually via pointer-events:none on the buttons.
 */
window.selectChatMode = function (mode) {
    if (window.chatHistoryState.chatModeHasMessages) return;  // double-guard
    if (window.setPrivacyMode) window.setPrivacyMode(mode);
};

// ─── Mode UI ──────────────────────────────────────────────────────────────────

function updateModeUI() {
    const mode        = window.chatHistoryState.activeMode;
    const hasMessages = window.chatHistoryState.chatModeHasMessages;

    // ── 1. Mode picker buttons ──
    ['normal', 'auto_wipe', 'incognito'].forEach(m => {
        const btn = document.getElementById(`mode-btn-${m}`);
        if (btn) btn.classList.toggle('active', m === mode);
    });

    // ── 2. Lock / unlock picker ──
    const picker = document.getElementById('chat-mode-picker');
    const notice = document.getElementById('mode-lock-notice');
    if (picker) picker.classList.toggle('locked', hasMessages);
    if (notice) notice.style.display = hasMessages ? 'block' : 'none';

    // ── 3. Topbar mode chip ──
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
}

// Backward-compatibility alias
window.updatePrivacyIndicator = updateModeUI;

// ─── Chat Restoration ─────────────────────────────────────────────────────────

window.renderHistoryMessages = function (messages) {
    const chatArea = document.getElementById('chat-area');
    if (!chatArea) return;
    messages.forEach(msg => {
        if (typeof window.appendMessage === 'function') {
            window.appendMessage(msg.role, msg.message, { timestamp: msg.timestamp, noSave: true });
        }
    });
};

// ─── Utility ──────────────────────────────────────────────────────────────────

function escapeHistoryHtml(str) {
    return (str || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

// ─── Init ─────────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', async () => {
    // 1. Try to restore active session from localStorage (helps if server restarted)
    const localSid = localStorage.getItem('zentra_active_session_id');

    // 2. Check current server active session
    const res = await _historyGet('/api/chat/sessions/active');

    if (res.ok && res.session_id) {
        // Server already has an active session, use it
        localStorage.setItem('zentra_active_session_id', res.session_id);
    } else if (localSid) {
        // Server lost it (reboot), but we have it! Try to reclaim it.
        console.log(`[HISTORY] Server lost active session. Attempting to reclaim: ${localSid}`);
        const reclaim = await _historyPost('/api/chat/sessions/active', { session_id: localSid });
        if (!reclaim.ok) {
            // Reclaim failed (maybe session deleted from DB), create new
            await _historyPost('/api/chat/sessions', { title: null, privacy_mode: 'normal' });
        }
    } else {
        // No session anywhere, create fresh
        await _historyPost('/api/chat/sessions', { title: null, privacy_mode: 'normal' });
    }

    await window.loadChatSessions();
});
