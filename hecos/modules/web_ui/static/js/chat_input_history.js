/**
 * chat_input_history.js
 * Handles up/down arrow navigation for input history in the WebUI.
 */

window._inputHistory = [];
window._inputHistoryCursor = -1;
window._inputHistoryDraft = "";

document.addEventListener('DOMContentLoaded', async () => {
    // Load history from API
    try {
        const r = await fetch('/api/input-history?limit=50');
        const d = await r.json();
        if (d.ok && Array.isArray(d.entries)) {
            window._inputHistory = d.entries;
            window._inputHistoryCursor = d.entries.length;
        }
    } catch (e) {
        console.warn("Could not load input history:", e);
    }
    
    const userInput = document.getElementById('user-input');
    if (!userInput) return;
    
    userInput.addEventListener('keydown', (e) => {
        // Only trigger if no modifiers are pressed
        if (e.shiftKey || e.ctrlKey || e.altKey || e.metaKey) return;
        
        // Handle Up Arrow
        if (e.key === 'ArrowUp') {
            // Check if cursor is on the first line
            const isSingleLine = userInput.value.indexOf('\n') === -1;
            const isOnFirstLine = userInput.selectionStart <= userInput.value.indexOf('\n') || isSingleLine;
            
            if (isOnFirstLine) {
                if (window._inputHistoryCursor > 0) {
                    e.preventDefault();
                    if (window._inputHistoryCursor === window._inputHistory.length) {
                        window._inputHistoryDraft = userInput.value;
                    }
                    window._inputHistoryCursor--;
                    userInput.value = window._inputHistory[window._inputHistoryCursor];
                    if (typeof autoResize === 'function') autoResize(userInput);
                }
            }
        }
        
        // Handle Down Arrow
        if (e.key === 'ArrowDown') {
            // Check if cursor is on the last line
            const isSingleLine = userInput.value.indexOf('\n') === -1;
            const lastNewLine = userInput.value.lastIndexOf('\n');
            const isOnLastLine = userInput.selectionEnd > lastNewLine || isSingleLine;
            
            if (isOnLastLine) {
                if (window._inputHistoryCursor < window._inputHistory.length) {
                    e.preventDefault();
                    window._inputHistoryCursor++;
                    if (window._inputHistoryCursor === window._inputHistory.length) {
                        userInput.value = window._inputHistoryDraft;
                    } else {
                        userInput.value = window._inputHistory[window._inputHistoryCursor];
                    }
                    if (typeof autoResize === 'function') autoResize(userInput);
                }
            }
        }
    });
});

// Hook into clearInput / sendMessage to save history
const _originalClearInput = window.clearInput;
window.clearInput = function() {
    if (window.userInput) {
        const val = window.userInput.value.trim();
        if (val) {
            // Optimistically update local buffer
            if (window._inputHistory.length === 0 || window._inputHistory[window._inputHistory.length - 1] !== val) {
                window._inputHistory.push(val);
                // max entries logic handled server-side, local can grow or be sliced
                if (window._inputHistory.length > 200) {
                    window._inputHistory = window._inputHistory.slice(-200);
                }
            }
            window._inputHistoryCursor = window._inputHistory.length;
            window._inputHistoryDraft = "";
            
            // Post to API
            fetch('/api/input-history/push', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: val })
            }).catch(e => console.warn("Could not save input history:", e));
        }
    }
    
    // Call original
    if (_originalClearInput) {
        _originalClearInput();
    }
};
