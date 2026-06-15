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
    
    // Update the Delete All button and New Chat button based on context
    const delBtn = document.getElementById('ch-delete-all-btn');
    const newChatBtn = document.getElementById('ch-new-chat-btn');
    
    if (delBtn) {
        if (window.chatHistoryState.showArchived) {
            delBtn.innerHTML = '<i class="fas fa-trash-alt"></i>';
            delBtn.title = window.I18N?.webui_chat_delete_all_title || 'Delete all archived forever';
            
            if(newChatBtn) {
                newChatBtn.innerHTML = '<span class="icon"><i class="fas fa-folder-open"></i></span> ' + (window.I18N?.webui_chat_archive_label || 'ARCHIVE MODE');
                newChatBtn.style.pointerEvents = 'none';
                newChatBtn.style.opacity = '0.7';
                newChatBtn.style.background = 'rgba(255,255,255,0.05)';
            }
        } else {
            delBtn.innerHTML = '<i class="fas fa-archive"></i>';
            delBtn.title = window.I18N?.webui_chat_archive_all_title || 'Archive all active';
            
            if(newChatBtn) {
                newChatBtn.innerHTML = '<span class="icon"><i class="fas fa-comment-dots"></i></span> ' + (window.I18N?.webui_chat_new || 'Nuova Chat');
                newChatBtn.style.pointerEvents = 'auto';
                newChatBtn.style.opacity = '1';
                newChatBtn.style.background = '';
            }
        }
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
    
    const isArchiveView = window.chatHistoryState.showArchived;
    
    if (isArchiveView) {
        const res = await window._historyPost(`/api/chat/sessions/delete-archived`, {}, 'DELETE');
        if (res.ok) {
            if (window._clearChatDOM) window._clearChatDOM();
            else if (window.chatArea) window.chatArea.innerHTML = '';
            window.chatHistoryState.activeSessionId = null;
            await window.loadChatSessions();
            await window.newChatSession();
        } else {
            alert('Errore durante l\'eliminazione: ' + res.error);
        }
    } else {
        const res = await window._historyPost(`/api/chat/sessions/archive-all`, {}, 'POST');
        if (res.ok) {
            if (window._clearChatDOM) window._clearChatDOM();
            else if (window.chatArea) window.chatArea.innerHTML = '';
            window.chatHistoryState.activeSessionId = null;
            await window.loadChatSessions();
            await window.newChatSession();
        } else {
            alert('Errore durante l\'archiviazione: ' + res.error);
        }
    }
};

window.startRenameSession = async function (e, sessionId) {
    if (e) e.stopPropagation();
    
    // Find the title element for this session item
    let titleEl = null;
    try {
        const el = e && e.target;
        const item = el && el.closest('.history-item');
        if (item) titleEl = item.querySelector('.history-title');
    } catch (_) {}
    
    // Fallback: find by data-id
    if (!titleEl) {
        const item = document.querySelector(`.history-item[data-id="${sessionId}"]`);
        if (item) titleEl = item.querySelector('.history-title');
    }
    
    if (!titleEl) return;
    
    // Already editing?
    if (titleEl.querySelector('input')) return;
    
    const originalTitle = titleEl.textContent.trim();
    
    // Build inline input
    const input = document.createElement('input');
    input.type = 'text';
    input.value = originalTitle;
    input.className = 'history-title-input';
    input.style.cssText = 'width:100%;background:transparent;border:none;border-bottom:1px solid var(--accent,#7c6cf8);outline:none;color:inherit;font:inherit;padding:0;';
    
    titleEl.textContent = '';
    titleEl.appendChild(input);
    input.focus();
    input.select();
    
    let saved = false;
    
    async function saveRename() {
        if (saved) return;
        saved = true;
        const newTitle = input.value.trim();
        if (newTitle && newTitle !== originalTitle) {
            const res = await window._historyPost(`/api/chat/sessions/${sessionId}`, { title: newTitle }, 'PATCH');
            if (res.ok) {
                await window.loadChatSessions();
                return;
            }
        }
        // Restore original if cancelled or unchanged
        titleEl.textContent = originalTitle;
    }
    
    input.addEventListener('keydown', function(ev) {
        if (ev.key === 'Enter') { ev.preventDefault(); saveRename(); }
        if (ev.key === 'Escape') { saved = true; titleEl.textContent = originalTitle; }
        ev.stopPropagation();
    });
    
    input.addEventListener('blur', saveRename);
    input.addEventListener('click', function(ev) { ev.stopPropagation(); });
};
