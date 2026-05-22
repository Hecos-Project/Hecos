/**
 * ch_render.js
 * ─────────────────────────────────────────────────────────────────────────────
 * Hecos Chat History — UI Rendering & Data Fetching
 * ─────────────────────────────────────────────────────────────────────────────
 */

window.loadChatSessions = async function () {
    const [resSessions, resActive] = await Promise.all([
        window._historyGet(`/api/chat/sessions${window.chatHistoryState.showArchived ? '?archived=1' : ''}`),
        window._historyGet('/api/chat/sessions/active')
    ]);

    if (resSessions.ok) {
        window.chatHistoryState.sessions = resSessions.sessions || [];
    }
    if (resActive.ok) {
        window.chatHistoryState.activeSessionId = resActive.session_id;
        window.chatHistoryState.activeMode      = resActive.mode || 'normal';
        // Ensure chatHistory is empty for a new session until messages are loaded
        window.chatHistory = []; 
        if (resActive.session_id) {
            localStorage.setItem('hecos_active_session_id', resActive.session_id);
        }
    }

    // Restore lock state
    const activeSess = window.chatHistoryState.sessions.find(
        s => s.id === window.chatHistoryState.activeSessionId
    );
    window.chatHistoryState.chatModeHasMessages = activeSess
        ? (activeSess.message_count || 0) > 0
        : false;

    renderSessionList();
    if (window.updateModeUI) window.updateModeUI();
};

function _dayKey(dateStr) {
    return dateStr ? dateStr.slice(0, 10) : '';
}

function _dateSeparatorLabel(dayKey) {
    if (!dayKey) return '';
    const today     = new Date();
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);
    const fmt = d => d.toISOString().slice(0, 10);

    if (dayKey === fmt(today))     return window.I18N?.webui_date_today     || 'Oggi';
    if (dayKey === fmt(yesterday)) return window.I18N?.webui_date_yesterday  || 'Ieri';

    const [y, m, d] = dayKey.split('-').map(Number);
    const dateObj = new Date(y, m - 1, d);
    return dateObj.toLocaleDateString(navigator.language || 'it-IT', {
        weekday: 'short', day: 'numeric', month: 'short'
    });
}

function escapeHistoryHtml(str) {
    return (str || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function renderSessionList() {
    const container = document.getElementById('chat-history-list');
    if (!container) return;

    const sessions = window.chatHistoryState.sessions;
    const activeId = window.chatHistoryState.activeSessionId;

    if (!sessions.length) {
        container.innerHTML = `<div class="history-empty">${window.I18N?.webui_chat_history_empty || 'No conversations saved'}</div>`;
        return;
    }

    const groups = []; 
    const keyMap = {};
    sessions.forEach(s => {
        const key = _dayKey(s.updated_at || s.created_at || '');
        if (!keyMap[key]) {
            keyMap[key] = { dayKey: key, label: _dateSeparatorLabel(key), sessions: [] };
            groups.push(keyMap[key]);
        }
        keyMap[key].sessions.push(s);
    });

    let html = '';
    groups.forEach(group => {
        html += `<div class="history-date-group"><span class="history-date-label">${escapeHistoryHtml(group.label)}</span></div>`;

        group.sessions.forEach(s => {
            const isActive   = s.id === activeId;
            const modeIcon   = s.privacy_mode === 'incognito' ? '🕵️' :
                               s.privacy_mode === 'auto_wipe' ? '🧹' : '';
            const msgCount   = s.message_count || 0;
            const timeStr    = s.updated_at ? s.updated_at.slice(11, 16) : '';
            const title      = escapeHistoryHtml(s.title || 'Chat senza titolo');
            const isNormal   = s.privacy_mode === 'normal';
            
            let actionsHtml = '';
            
            if (isNormal) {
                if (window.chatHistoryState.showArchived) {
                    const restoreTitle = window.I18N?.webui_chat_archive_restore || 'Restore';
                    const restoreFn    = `window.archiveChatSession(event, '${s.id}', false)`;
                    actionsHtml += `<button class="history-action-btn" title="${restoreTitle}" onclick="${restoreFn}">♻️</button>`;
                    
                    const delTitle = window.I18N?.webui_chat_delete || 'Delete forever';
                    const delFn    = `window.deleteChatSession(event, '${s.id}')`;
                    actionsHtml += `<button class="history-action-btn" style="margin-left:2px;" title="${delTitle}" onclick="${delFn}">🗑️</button>`;
                } else {
                    const arcTitle = window.I18N?.webui_chat_archive_close || 'Archive';
                    const arcFn    = `window.archiveChatSession(event, '${s.id}', true)`;
                    actionsHtml += `<button class="history-action-btn" title="${arcTitle}" onclick="${arcFn}">✖️</button>`;
                }
            } else {
                const descTitle = window.I18N?.webui_chat_delete || 'Delete';
                const descFn    = `window.deleteChatSession(event, '${s.id}')`;
                actionsHtml += `<button class="history-action-btn" title="${descTitle}" onclick="${descFn}">🗑️</button>`;
            }

            html += `
        <div class="history-item${isActive ? ' active' : ''}" data-id="${s.id}" onclick="window.activateChatSession('${s.id}')">
          <div class="history-item-main">
            <span class="history-icon">${modeIcon || '💬'}</span>
            <div class="history-item-info">
              <div class="history-title" title="${window.I18N?.webui_chat_rename_hint || 'Double click to rename'}" ondblclick="window.startRenameSession(event, '${s.id}')">${title}</div>
              <div class="history-meta">${timeStr} · ${msgCount} msg</div>
            </div>
          </div>
          <div class="history-item-actions">
            ${actionsHtml}
          </div>
        </div>`;
        });
    });

    container.innerHTML = html;
}
