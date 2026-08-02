// --- DOM Manipulation & Element Renderers ---

// Full Color mode — tag coloring is OFF by default.
window.logFullColorMode = localStorage.getItem('hecos_log_full_color') === 'true'; // Default false unless explicitly true

window.toggleLogFullColor = function(forceVal) {
    if (typeof forceVal === 'boolean') {
        window.logFullColorMode = forceVal;
    } else {
        window.logFullColorMode = !window.logFullColorMode;
    }
    localStorage.setItem('hecos_log_full_color', window.logFullColorMode);
    
    // Update all checkboxes in DOM
    document.querySelectorAll('.w-full-color-toggle').forEach(cb => { cb.checked = window.logFullColorMode; });
    
    // Clear & Re-fetch logs for all active windows so they reappear instantly
    if (window.activeLogWindows) {
        window.activeLogWindows.forEach(w => {
            w.body.innerHTML = '';
            w.lineCount = 0;
            if (w.filterQ || w.filterT) {
                if (window.loadLogSearchIntoWindow) window.loadLogSearchIntoWindow(w, w.source);
            } else {
                // For both LIVE and historical, fetch the tail
                if (window.loadLogSearchIntoWindow && w.source === 'LIVE') {
                    window.loadLogSearchIntoWindow(w, 'LIVE');
                } else if (window.loadLogTailIntoWindow) {
                    window.loadLogTailIntoWindow(w, w.source);
                }
            }
        });
    }
}

window.appendDataLine = function(win, data) {
    if (win.isPaused) return;
    const line = document.createElement('div');
    const colorClass = data.level ? `lvl-${data.level}` : '';
    line.className = `log-line ${colorClass}`;

    // Use global escapeHtml provided by config_core utils or define fallback if not present
    const escHtml = window.escapeHtml || function(text) {
        const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
        return text.replace(/[&<>"']/g, function(m) { return map[m]; });
    };

    let textOut = escHtml(data.text || '');
    if (win.filterQ) {
        const qSafe = escHtml(win.filterQ).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        const regex = new RegExp(`(${qSafe})`, 'gi');
        textOut = textOut.replace(regex, '<span style="background-color:rgba(var(--accent-rgb),0.35); color:var(--text); border-radius:2px; padding:0 2px; border:1px solid var(--accent);">$1</span>');
    }

    // Linkify URLs
    textOut = textOut.replace(/(https?:\/\/[^\s<"']+)/gi, '<a href="$1" target="_blank" style="color:var(--accent); text-decoration:underline;">$1</a>');

    // Colorize source tags in text (in case any exist)
    if (window.logFullColorMode) {
        textOut = textOut.replace(/\[CORE[^\]]*\]/gi, '<span style="color:#4dabf7; font-weight:bold;">$&</span>'); // Blue
        textOut = textOut.replace(/\[DAEMON[^\]]*\]/gi, '<span style="color:#b197fc; font-weight:bold;">$&</span>'); // Purple
        textOut = textOut.replace(/\[WEBUI[^\]]*\]/gi, '<span style="color:#69db7c; font-weight:bold;">$&</span>'); // Green
        textOut = textOut.replace(/\[PLUGIN[^\]]*\]/gi, '<span style="color:#ffa94d; font-weight:bold;">$&</span>'); // Orange
    }

    // Format module tag for LIVE logs
    let modHtml = '';
    if (data.module) {
        let rawMod = `[${data.module}]`;
        if (window.logFullColorMode) {
            const upperMod = rawMod.toUpperCase();
            if (upperMod.includes('[CORE')) rawMod = `<span style="color:#4dabf7; font-weight:bold;">${rawMod}</span>`;
            else if (upperMod.includes('[DAEMON')) rawMod = `<span style="color:#b197fc; font-weight:bold;">${rawMod}</span>`;
            else if (upperMod.includes('[WEBUI')) rawMod = `<span style="color:#69db7c; font-weight:bold;">${rawMod}</span>`;
            else if (upperMod.includes('[PLUGIN')) rawMod = `<span style="color:#ffa94d; font-weight:bold;">${rawMod}</span>`;
        }
        modHtml = `<span class="log-module" style="margin-right:6px;">${rawMod}</span>`;
    }

    line.innerHTML = `<span class="log-time">${data.time}</span><span class="log-lvl ${colorClass}">${data.level}</span>${modHtml}<span class="log-text">${textOut}</span>`;
    
    window.appendToBody(win, line);
}

window.appendRawLine = function(win, text) {
    if (win.isPaused) return;
    const line = document.createElement('div');
    
    let lvlClass = '';
    const upperText = (text || '').toUpperCase();
    if (upperText.includes('[ERROR]') || upperText.includes('EXCEPTION') || upperText.includes('TRACEBACK') || upperText.includes(' CRITICAL ')) lvlClass = 'lvl-ERROR';
    else if (upperText.includes('[WARNING]') || upperText.includes('[WARN]') || upperText.includes(' WARNING ')) lvlClass = 'lvl-WARN';
    else if (upperText.includes('[DEBUG]')) lvlClass = 'lvl-DEBUG';
    else if (upperText.includes('[MONITOR]')) lvlClass = 'lvl-MONITOR';
    else if (upperText.includes('[INFO]')) lvlClass = 'lvl-INFO';

    line.className = `log-line ${lvlClass}`;
    
    const escHtml = window.escapeHtml || function(tx) {
        const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
        return tx.replace(/[&<>"']/g, function(m) { return map[m]; });
    };

    let textOut = escHtml(text || '');
    if (win.filterQ) {
        const qSafe = escHtml(win.filterQ).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        const regex = new RegExp(`(${qSafe})`, 'gi');
        textOut = textOut.replace(regex, '<span style="background-color:rgba(var(--accent-rgb),0.35); color:var(--text); border-radius:2px; padding:0 2px; border:1px solid var(--accent);">$1</span>');
    }
    
    // Linkify URLs
    textOut = textOut.replace(/(https?:\/\/[^\s<"']+)/gi, '<a href="$1" target="_blank" style="color:var(--accent); text-decoration:underline;">$1</a>');

    // Colorize source tags (only when Full Color mode is active)
    if (window.logFullColorMode) {
        textOut = textOut.replace(/\[CORE[^\]]*\]/gi, '<span style="color:#4dabf7; font-weight:bold;">$&</span>'); // Blue
        textOut = textOut.replace(/\[DAEMON[^\]]*\]/gi, '<span style="color:#b197fc; font-weight:bold;">$&</span>'); // Purple
        textOut = textOut.replace(/\[WEBUI[^\]]*\]/gi, '<span style="color:#69db7c; font-weight:bold;">$&</span>'); // Green
        textOut = textOut.replace(/\[PLUGIN[^\]]*\]/gi, '<span style="color:#ffa94d; font-weight:bold;">$&</span>'); // Orange
    }

    line.innerHTML = `<span class="log-text">${textOut}</span>`;
    window.appendToBody(win, line);
}

window.appendToBody = function(win, line) {
    const autoSc = win.element.querySelector('.w-autoscroll');
    const isAutoScrollEnabled = autoSc && autoSc.checked;

    const threshold = 60; 
    let isAtBottom = true;
    if (win.body.scrollHeight > win.body.clientHeight) {
         isAtBottom = (win.body.scrollHeight - win.body.scrollTop) <= (win.body.clientHeight + threshold);
    }
    
    win.body.appendChild(line);
    win.lineCount++;
    
    const maxLinesEl = win.element.querySelector('.w-max-lines');
    const maxLines = maxLinesEl ? (parseInt(maxLinesEl.value) || 500) : 500;
    
    while (win.lineCount > maxLines) {
        if (win.body.firstChild) win.body.removeChild(win.body.firstChild);
        win.lineCount--;
    }

    if (isAutoScrollEnabled && isAtBottom) {
        win.body.scrollTop = win.body.scrollHeight;
    }
    window.updateWindowStrips(win);
}

window.forceTrimLines = function(inputEl) {
    const cardEl = inputEl.closest('.log-window-card');
    if (!cardEl) return;
    const id = cardEl.dataset.id;
    const win = window.activeLogWindows.find(w => w.id === id);
    if (!win) return;
    
    const maxLines = parseInt(inputEl.value) || 500;

    // If source is a file (not LIVE) and we increase the limit, reload to fill history
    if (win.source !== 'LIVE' && maxLines > win.lineCount) {
        win.body.innerHTML = '';
        win.lineCount = 0;
        if (win.filterQ || win.filterT) {
            if (window.loadLogSearchIntoWindow) window.loadLogSearchIntoWindow(win, win.source);
        } else {
            if (window.loadLogTailIntoWindow) window.loadLogTailIntoWindow(win, win.source);
        }
        return;
    }

    while (win.lineCount > maxLines) {
        if (win.body.firstChild) win.body.removeChild(win.body.firstChild);
        win.lineCount--;
    }
    window.updateWindowStrips(win);
}

window.updateWindowStrips = function(win) {
    const cnt = win.element.querySelector('.w-line-count');
    if (cnt) cnt.textContent = win.lineCount + ' lines';
}

window.toggleStripedRows = function(inputEl) {
    const cardEl = inputEl.closest('.log-window-card');
    if (!cardEl) return;
    const bodyEl = cardEl.querySelector('.log-window-body');
    if (bodyEl) {
        if (inputEl.checked) {
            bodyEl.classList.add('striped-rows');
        } else {
            bodyEl.classList.remove('striped-rows');
        }
    }
}
