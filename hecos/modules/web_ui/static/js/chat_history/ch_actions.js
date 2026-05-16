/**
 * ch_actions.js
 * ─────────────────────────────────────────────────────────────────────────────
 * Hecos Chat History — User Actions and Interactions
 * ─────────────────────────────────────────────────────────────────────────────
 */

window.newChatSession = async function (mode = null) {
    const privMode = mode || 'normal';
    const res = await window._historyPost('/api/chat/sessions', { privacy_mode: privMode });
    
    if (!res.ok) {
        alert(`Errore creazione sessione: ${res.error || 'Unknown'}`);
        return;
    }

    window.chatHistoryState.activeSessionId     = res.session_id;
    window.chatHistoryState.activeMode          = privMode;
    window.chatHistoryState.chatModeHasMessages = false;
    localStorage.setItem('hecos_active_session_id', res.session_id);

    if (window._clearChatDOM) window._clearChatDOM();
    else if (window.clearChat) {
        window._clearChatDOM = window.clearChat;
        window.chatArea && (window.chatArea.innerHTML = '');
    }
    window.chatHistoryState.isUIRendered = true;

    await window.loadChatSessions();
};

window.activateChatSession = async function (sessionId) {
    if (sessionId === window.chatHistoryState.activeSessionId && window.chatHistoryState.isUIRendered) return;

    const res = await window._historyGet(`/api/chat/sessions/${sessionId}/messages`);
    if (!res.ok) {
        alert(`Errore caricamento messaggi: ${res.error || 'Unknown'}`);
        return;
    }

    const session = window.chatHistoryState.sessions.find(s => s.id === sessionId);
    const mode    = session?.privacy_mode || 'normal';

    await window._historyPost('/api/chat/sessions/active', { session_id: sessionId, privacy_mode: mode });

    window.chatHistoryState.activeSessionId     = sessionId;
    window.chatHistoryState.activeMode          = mode;
    window.chatHistoryState.chatModeHasMessages = (res.messages || []).length > 0;
    localStorage.setItem('hecos_active_session_id', sessionId);

    if (window._clearChatDOM) window._clearChatDOM();
    else if (window.chatArea) window.chatArea.innerHTML = '';

    if (window.renderHistoryMessages) window.renderHistoryMessages(res.messages || []);
    if (window.loadChatSessions) await window.loadChatSessions();

    const overlay = document.getElementById('mobile-overlay');
    if (overlay && overlay.classList.contains('active')) {
        const sidebar = document.getElementById('sidebar');
        if (sidebar) sidebar.classList.remove('open');
        overlay.classList.remove('active');
    }
};

window.archiveChatSession = async function (e, sessionId, archiveState = true) {
    e.stopPropagation();
    const msg = archiveState 
        ? (window.I18N?.webui_chat_archive_confirm || "Archive this conversation?")
        : (window.I18N?.webui_chat_unarchive_confirm || "Restore this conversation?");
        
    if (!confirm(msg)) return;
    
    await window._historyPost(`/api/chat/sessions/${sessionId}/archive`, { archived: archiveState });
    
    if (archiveState && window.chatHistoryState.activeSessionId === sessionId) {
        if (window._clearChatDOM) window._clearChatDOM();
        else if (window.chatArea) window.chatArea.innerHTML = '';
        window.chatHistoryState.activeSessionId = null;
    }
    
    await window.loadChatSessions();
    
    if (archiveState && !window.chatHistoryState.sessions.find(s => s.id === window.chatHistoryState.activeSessionId)) {
        if (window.chatHistoryState.sessions.length > 0) {
            await window.activateChatSession(window.chatHistoryState.sessions[0].id);
        } else {
            await window.newChatSession();
        }
    }
};

window.toggleShowArchived = async function() {
    window.chatHistoryState.showArchived = !window.chatHistoryState.showArchived;
    const btn = document.getElementById('toggle-archive-btn');
    if (btn) {
        btn.textContent = window.chatHistoryState.showArchived ? '💬' : '📂';
        btn.title = window.chatHistoryState.showArchived 
            ? (window.I18N?.webui_chat_archive_view_active || 'View Active Chats') 
            : (window.I18N?.webui_chat_archive_open || 'Open Archive');
        btn.style.opacity = window.chatHistoryState.showArchived ? '1' : '0.5';
    }
    await window.loadChatSessions();
};

window.deleteChatSession = async function (e, sessionId) {
    e.stopPropagation();
    if (!confirm(window.I18N?.webui_chat_delete_confirm || 'Delete this conversation?')) return;
    
    await window._historyPost(`/api/chat/sessions/${sessionId}`, {}, 'DELETE');
    
    if (window.chatHistoryState.activeSessionId === sessionId) {
        if (window._clearChatDOM) window._clearChatDOM();
        else if (window.chatArea) window.chatArea.innerHTML = '';
        window.chatHistoryState.activeSessionId = null;
    }
    await window.loadChatSessions();
    
    if (window.chatHistoryState.sessions.length === 0) {
        await window.newChatSession();
    } else if (!window.chatHistoryState.activeSessionId) {
        await window.activateChatSession(window.chatHistoryState.sessions[0].id);
    }
};

window.deleteAllChatSessions = async function (e) {
    if (e) e.stopPropagation();
    const msg = window.I18N?.webui_chat_delete_confirm_all || 'Delete ALL conversations?';
    if (!confirm(msg)) return;
    
    const res = await window._historyPost(`/api/chat/sessions/all`, {}, 'DELETE');
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
    const newName = prompt(window.I18N?.webui_chat_rename_prompt || 'Rename conversation:', current);
    
    if (!newName || newName === current) return;
    const res = await window._historyPost(`/api/chat/sessions/${sessionId}`, { title: newName }, 'PATCH');
    if (res.ok) await window.loadChatSessions();
};
