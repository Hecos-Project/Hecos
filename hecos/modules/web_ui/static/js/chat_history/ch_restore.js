/**
 * ch_restore.js
 * ─────────────────────────────────────────────────────────────────────────────
 * Hecos Chat History — UI Visual Restoration Pipeline
 * ─────────────────────────────────────────────────────────────────────────────
 */

window.renderHistoryMessages = function (messages) {
    const chatArea = document.getElementById('chat-area');
    if (!chatArea) return;
    
    window.chatHistoryState.isUIRendered = true;
    
    // Sync the internal history state array for the LLM context and actions
    window.chatHistory = messages.map(m => ({
        role: m.role === 'assistant' ? 'assistant' : (m.role === 'ai' ? 'assistant' : 'user'),
        content: m.message
    }));

    // Iterate over each message and push it into the DOM interface
    messages.forEach((msg, idx) => {
        if (typeof window.appendMessage === 'function') {
            window.appendMessage(
                msg.role, 
                msg.message, 
                { timestamp: msg.timestamp, noSave: true, historyIndex: idx }
            );
        }
    });
};
