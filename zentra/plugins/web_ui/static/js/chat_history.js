/**
 * chat_history.js
 * Manages the chat session sidebar: load, display, switch, delete, rename.
 */

window.chatHistoryState = {
    sessions: [],
    activeSessionId: null,
    activeMode: 'normal'
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

    renderSessionList();
    updatePrivacyIndicator();
};

function renderSessionList() {
    const container = document.getElementById('chat-history-list');
    if (!container) return;

    const sessions = window.chatHistoryState.sessions;
    const activeId = window.chatHistoryState.activeSessionId;

    if (!sessions.length) {
        container.innerHTML = '<div class="history-empty">Nessuna conversazione salvata</div>';
        return;
    }

    container.innerHTML = sessions.map(s => {
        const isActive = s.id === activeId;
        const modeIcon = s.privacy_mode === 'incognito' ? '🕵️' :
                         s.privacy_mode === 'auto_wipe' ? '🔒' : '';
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
    // Determine privacy mode
    const privMode = mode || window.chatHistoryState.activeMode || 'normal';

    // If current mode is auto_wipe, wipe messages before leaving
    if (window.chatHistoryState.activeMode === 'auto_wipe' &&
        window.chatHistoryState.activeSessionId) {
        await _historyPost(`/api/chat/sessions/${window.chatHistoryState.activeSessionId}/wipe`);
    }

    // Create new session
    const res = await _historyPost('/api/chat/sessions', { privacy_mode: privMode });
    if (!res.ok) {
        alert(translator.t('error_create_session') || `Errore creazione sessione: ${res.error || 'Unknown'}`);
        return;
    }

    window.chatHistoryState.activeSessionId = res.session_id;
    window.chatHistoryState.activeMode      = privMode;
    localStorage.setItem('zentra_active_session_id', res.session_id);

    // Clear chat UI
    if (window._clearChatDOM) {
        window._clearChatDOM();
    } else if (window.clearChat) {
        // Fallback for isolated contexts where _clearChatDOM isn't defined yet
        window._clearChatDOM = window.clearChat; 
        // We do not call clearChat here because it triggers newChatSession
        window.chatArea && (window.chatArea.innerHTML = '');
    }

    // Reload session list
    await window.loadChatSessions();
    updatePrivacyIndicator();
};

window.activateChatSession = async function (sessionId) {
    if (sessionId === window.chatHistoryState.activeSessionId) return;

    // Wipe previous if auto-wipe
    if (window.chatHistoryState.activeMode === 'auto_wipe' &&
        window.chatHistoryState.activeSessionId) {
        await _historyPost(`/api/chat/sessions/${window.chatHistoryState.activeSessionId}/wipe`);
    }

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

    window.chatHistoryState.activeSessionId = sessionId;
    window.chatHistoryState.activeMode      = mode;
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
    updatePrivacyIndicator();
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

// ─── Privacy Mode Switcher ────────────────────────────────────────────────────

window.setPrivacyMode = async function (mode) {
    const res = await _historyPost('/api/chat/privacy', { mode });
    if (res.ok) {
        window.chatHistoryState.activeMode = mode;
        updatePrivacyIndicator();
    }
};

function updatePrivacyIndicator() {
    const indicator = document.getElementById('privacy-indicator');
    if (!indicator) return;
    const mode = window.chatHistoryState.activeMode;
    const map = {
        normal:     { icon: '👁', label: 'Normal',    cls: '' },
        auto_wipe:  { icon: '🔒', label: 'Auto-Wipe', cls: 'mode-autowipe' },
        incognito:  { icon: '🕵️', label: 'Incognito', cls: 'mode-incognito' }
    };
    const m = map[mode] || map.normal;
    indicator.innerHTML    = `${m.icon} <span>${m.label}</span>`;
    indicator.className    = `privacy-indicator ${m.cls}`;
    indicator.title        = `Modalità Privacy: ${m.label}. Click per cambiare.`;
}

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
