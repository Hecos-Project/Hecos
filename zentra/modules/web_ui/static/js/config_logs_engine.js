// --- Multi-Window Log Grid Engine ---

window.logEvtSource = null;
window.activeLogWindows = [];
window.availableLogFiles = [];

async function refreshLogFiles() {
    try {
        const r = await fetch('/api/logs/files');
        const d = await r.json();
        if (d.ok) {
            availableLogFiles = d.files || [];
            // Update all existing selectors in windows
            document.querySelectorAll('.w-source-selector').forEach(sel => {
                const current = sel.value;
                sel.innerHTML = '<option value="LIVE">Live Stream (Total)</option>';
                availableLogFiles.forEach(f => {
                    const opt = document.createElement('option');
                    opt.value = f.name;
                    opt.textContent = `${f.name} (${(f.size/1024).toFixed(1)} KB)`;
                    sel.appendChild(opt);
                });
                sel.value = current;
            });
            return true;
        }
    } catch(e) { console.error("Refresh logs failed", e); }
    return false;
}

function addLogWindow(source = 'LIVE', level = 'BOTH') {
    const grid = document.getElementById('log-grid');
    const template = document.getElementById('log-window-template');
    if (!grid || !template) return;

    const id = 'win-' + Math.random().toString(36).substr(2, 9);
    const clone = template.content.cloneNode(true);
    
    // Setup elements
    const winCard = clone.querySelector('.log-window-card');
    winCard.dataset.id = id;
    
    // Populate source selector
    const sel = winCard.querySelector('.w-source-selector');
    sel.innerHTML = '<option value="LIVE">Live Stream (Total)</option>';
    availableLogFiles.forEach(f => {
        const opt = document.createElement('option');
        opt.value = f.name;
        opt.textContent = `${f.name} (${(f.size/1024).toFixed(1)} KB)`;
        sel.appendChild(opt);
    });
    sel.value = source;
    sel.setAttribute('onchange', `updateWindowSource('${id}', this.value)`);
    
    winCard.querySelector('.w-level-selector').value = level;
    winCard.querySelector('.w-level-selector').setAttribute('onchange', `updateWindowLevel('${id}', this.value)`);
    winCard.querySelector('.w-btn').setAttribute('onclick', `clearWindow('${id}')`);
    winCard.querySelector('.w-close').setAttribute('onclick', `removeLogWindow('${id}')`);
    
    // Bind search UI IDs
    const termInp = winCard.querySelector('.w-search-term');
    if (termInp) termInp.setAttribute('onkeypress', `if(event.key === 'Enter') window.applyWindowSearch('${id}')`);
    const timeInp = winCard.querySelector('.w-search-time');
    if (timeInp) timeInp.setAttribute('onkeypress', `if(event.key === 'Enter') window.applyWindowSearch('${id}')`);
    const btnFilt = winCard.querySelector('.w-btn-filter');
    if (btnFilt) btnFilt.setAttribute('onclick', `window.applyWindowSearch('${id}')`);
    const btnRes = winCard.querySelector('.w-btn-reset');
    if (btnRes) btnRes.setAttribute('onclick', `window.clearWindowSearch('${id}')`);

    grid.appendChild(winCard);
    
    const winObj = {
        id: id,
        source: source,
        level: level,
        filterQ: '',
        filterT: '',
        element: grid.lastElementChild,
        body: grid.lastElementChild.querySelector('.log-window-body'),
        lineCount: 0
    };
    
    activeLogWindows.push(winObj);
    
    if (source !== 'LIVE') {
        loadLogTailIntoWindow(winObj, source);
    }
    
    // Ensure stream is running
    startLogStream();
    updateLogGridLayout();
    
    // Force scroll to bottom shortly after history/tail is loaded
    setTimeout(() => {
        if (winObj && winObj.body) {
            winObj.body.scrollTop = winObj.body.scrollHeight;
        }
    }, 300);
}

function removeLogWindow(id) {
    activeLogWindows = activeLogWindows.filter(w => {
        if (w.id === id) {
            w.element.remove();
            return false;
        }
        return true;
    });
    updateLogGridLayout();
}

function updateWindowSource(id, source) {
    const w = activeLogWindows.find(win => win.id === id);
    if (!w) return;
    w.source = source;
    w.body.innerHTML = '';
    w.lineCount = 0;
    if (w.filterQ || w.filterT) {
        loadLogSearchIntoWindow(w, source);
    } else if (source !== 'LIVE') {
        loadLogTailIntoWindow(w, source);
    }
}

function updateWindowLevel(id, level) {
    const w = activeLogWindows.find(win => win.id === id);
    if (w) w.level = level;
}

function clearWindow(id) {
    const w = activeLogWindows.find(win => win.id === id);
    if (w) {
        w.body.innerHTML = '';
        w.lineCount = 0;
        updateWindowStrips(w);
    }
}

function clearAllLogWindows() {
    activeLogWindows.forEach(w => clearWindow(w.id));
}

async function loadLogTailIntoWindow(winObj, filename) {
    try {
        const r = await fetch(`/api/logs/tail/${filename}?n=100`);
        const d = await r.json();
        if (d.ok) {
            d.lines.forEach(line => {
                appendRawLine(winObj, line);
            });
        }
    } catch(e) { console.error("Tail failed", e); }
}

async function loadLogSearchIntoWindow(winObj, filename) {
    try {
        const sq = encodeURIComponent(winObj.filterQ || '');
        const st = encodeURIComponent(winObj.filterT || '');
        const r = await fetch(`/api/logs/search/${filename}?n=200&q=${sq}&time=${st}`);
        const d = await r.json();
        if (d.ok) {
            if (d.type === 'events') {
                d.data.forEach(evt => appendDataLine(winObj, evt));
            } else if (d.type === 'lines') {
                d.data.forEach(line => appendRawLine(winObj, line));
            }
            setTimeout(() => { if (winObj && winObj.body) winObj.body.scrollTop = winObj.body.scrollHeight; }, 100);
        }
    } catch(e) { console.error("Search failed", e); }
}

function applyWindowSearch(id) {
    const w = activeLogWindows.find(win => win.id === id);
    if (!w) return;
    const termEl = w.element.querySelector('.w-search-term');
    const timeEl = w.element.querySelector('.w-search-time');
    w.filterQ = termEl ? termEl.value.trim() : '';
    w.filterT = timeEl ? timeEl.value.trim() : '';
    
    w.body.innerHTML = '';
    w.lineCount = 0;
    loadLogSearchIntoWindow(w, w.source);
}

function clearWindowSearch(id) {
    const w = activeLogWindows.find(win => win.id === id);
    if (!w) return;
    const termEl = w.element.querySelector('.w-search-term');
    const timeEl = w.element.querySelector('.w-search-time');
    if (termEl) termEl.value = '';
    if (timeEl) timeEl.value = '';
    w.filterQ = '';
    w.filterT = '';
    
    w.body.innerHTML = '';
    w.lineCount = 0;
    if (w.source !== 'LIVE') {
        loadLogTailIntoWindow(w, w.source);
    } else {
        // Just reload the LIVE search with no filters (essentially historical tail)
        loadLogSearchIntoWindow(w, 'LIVE');
    }
}

window.applyWindowSearch = applyWindowSearch;
window.clearWindowSearch = clearWindowSearch;

function updateLogGridLayout() {
    const layout = document.getElementById('log-grid-layout').value;
    const grid = document.getElementById('log-grid');
    if (!grid) return;
    grid.className = 'log-grid layout-' + layout;
    
    // Special 'auto' logic
    if (layout === 'auto') {
        if (activeLogWindows.length === 1) grid.classList.add('single');
        else grid.classList.remove('single');
    }
}

function startLogStream() {
    if (logEvtSource) return;
    const statusEl = document.getElementById('log-status');
    if (statusEl) { statusEl.textContent = 'Active'; statusEl.className = 'val-ok'; }

    logEvtSource = new EventSource('/api/logs/stream');
    logEvtSource.onmessage = (e) => {
        if (e.data === ': keep-alive') return;
        try {
            const data = JSON.parse(e.data);
            dispatchLogEvent(data);
        } catch(err) { }
    };
    logEvtSource.onerror = () => {
        if (statusEl) { statusEl.textContent = 'Err (Retry)'; statusEl.className = 'val-err'; }
    };
}

function dispatchLogEvent(data) {
    activeLogWindows.forEach(win => {
        if (win.source !== 'LIVE') return; 

        if (win.level !== 'BOTH') {
            if (win.level === 'INFO' && data.level === 'DEBUG') return;
            if (win.level === 'DEBUG' && data.level !== 'DEBUG') return;
        }
        
        let pass = true;
        if (win.filterQ) {
            const q = win.filterQ.toLowerCase();
            const textL = (data.text || '').toLowerCase();
            const lvlL = (data.level || '').toLowerCase();
            if (!textL.includes(q) && !lvlL.includes(q)) pass = false;
        }
        if (win.filterT) {
            const t = win.filterT.toLowerCase();
            const timeL = (data.time || '').toLowerCase();
            if (!timeL.includes(t)) pass = false;
        }
        
        if (pass) {
            appendDataLine(win, data);
        }
    });
    
    // Play error beep if enabled
    if (data.level === 'ERROR' && window.cfg?.logging?.ui_error_beeps !== false) {
        playErrorBeep();
    }
}

function playErrorBeep() {
    try {
        const actx = new (window.AudioContext || window.webkitAudioContext)();
        if (!actx) return;
        const osc = actx.createOscillator();
        const gain = actx.createGain();
        osc.connect(gain);
        gain.connect(actx.destination);
        osc.type = 'square';
        osc.frequency.setValueAtTime(440, actx.currentTime);
        osc.frequency.exponentialRampToValueAtTime(880, actx.currentTime + 0.05);
        gain.gain.setValueAtTime(0.05, actx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.001, actx.currentTime + 0.1);
        osc.start(actx.currentTime);
        osc.stop(actx.currentTime + 0.1);
    } catch(e) {}
}

function appendDataLine(win, data) {
    const line = document.createElement('div');
    const colorClass = data.level ? `lvl-${data.level}` : '';
    line.className = `log-line ${colorClass}`;

    let textOut = escapeHtml(data.text);
    if (win.filterQ) {
        const qSafe = escapeHtml(win.filterQ).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        const regex = new RegExp(`(${qSafe})`, 'gi');
        textOut = textOut.replace(regex, '<span style="background-color:rgba(var(--accent-rgb),0.35); color:var(--text); border-radius:2px; padding:0 2px; border:1px solid var(--accent);">$1</span>');
    }

    line.innerHTML = `<span class="log-time">${data.time}</span><span class="log-lvl ${colorClass}">${data.level}</span><span class="log-text">${textOut}</span>`;
    
    appendToBody(win, line);
}

function appendRawLine(win, text) {
    const line = document.createElement('div');
    
    let lvlClass = '';
    if (text.includes('[ERROR]') || text.includes('Exception') || text.includes('Traceback')) lvlClass = 'lvl-ERROR';
    else if (text.includes('[WARNING]') || text.includes('[WARN]')) lvlClass = 'lvl-WARN';
    else if (text.includes('[DEBUG]')) lvlClass = 'lvl-DEBUG';
    else if (text.includes('[MONITOR]')) lvlClass = 'lvl-MONITOR';
    else if (text.includes('[INFO]')) lvlClass = 'lvl-INFO';

    line.className = `log-line ${lvlClass}`;
    
    let textOut = escapeHtml(text);
    if (win.filterQ) {
        const qSafe = escapeHtml(win.filterQ).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        const regex = new RegExp(`(${qSafe})`, 'gi');
        textOut = textOut.replace(regex, '<span style="background-color:rgba(var(--accent-rgb),0.35); color:var(--text); border-radius:2px; padding:0 2px; border:1px solid var(--accent);">$1</span>');
    }
    
    line.innerHTML = `<span class="log-text">${textOut}</span>`;
    appendToBody(win, line);
}

function appendToBody(win, line) {
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
    updateWindowStrips(win);
}

function forceTrimLines(inputEl) {
    const cardEl = inputEl.closest('.log-window-card');
    if (!cardEl) return;
    const id = cardEl.dataset.id;
    const win = activeLogWindows.find(w => w.id === id);
    if (!win) return;
    
    const maxLines = parseInt(inputEl.value) || 500;
    while (win.lineCount > maxLines) {
        if (win.body.firstChild) win.body.removeChild(win.body.firstChild);
        win.lineCount--;
    }
    updateWindowStrips(win);
}

window.forceTrimLines = forceTrimLines;

function updateWindowStrips(win) {
    const cnt = win.element.querySelector('.w-line-count');
    if (cnt) cnt.textContent = win.lineCount + ' lines';
}

// --- Log Management & Polish ---

function toggleStripedRows(inputEl) {
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

window.toggleStripedRows = toggleStripedRows;

async function openLogDeleteModal() {
    const listEl = document.getElementById('log-delete-list');
    listEl.innerHTML = '<div style="color:var(--muted); text-align:center;">Loading...</div>';
    document.getElementById('log-delete-modal').style.display = 'flex';
    
    try {
        const r = await fetch('/api/logs/files');
        const data = await r.json();
        listEl.innerHTML = '';
        if (data.ok && data.files.length > 0) {
            data.files.forEach(f => {
                const sizeKb = (f.size / 1024).toFixed(1);
                listEl.innerHTML += `
                    <label style="display:flex; justify-content:space-between; align-items:center; background:var(--glass-b); padding:10px; border-radius:6px; cursor:pointer; gap:10px; border:1px solid var(--border);">
                        <div style="display:flex; align-items:center; gap:10px; flex:1; overflow:hidden;">
                            <input type="checkbox" class="log-del-cb" value="${f.name}">
                            <div style="display:flex; flex-direction:column; overflow:hidden;">
                                <span style="color:var(--text); font-size:13px; text-overflow:ellipsis; white-space:nowrap; overflow:hidden;">📄 ${f.name}</span>
                                <span style="color:var(--muted); font-size:11px;">${window.t ? window.t('webui_conf_logs_last_mod') : 'Last Modified'}: ${f.modified}</span>
                            </div>
                        </div>
                        <span style="color:var(--muted); font-size:12px; white-space:nowrap;">${sizeKb} KB</span>
                    </label>
                `;
            });
        } else {
            listEl.innerHTML = '<div style="color:var(--muted); text-align:center;">No log files found.</div>';
        }
    } catch (e) {
        listEl.innerHTML = `<div style="color:#f87171; text-align:center;">Error: ${e.message}</div>`;
    }
}

function closeLogDeleteModal() {
    document.getElementById('log-delete-modal').style.display = 'none';
}

async function deleteSelectedLogs(all = false) {
    const confirmMsg = all 
        ? (window.t ? window.t('webui_conf_logs_confirm_all') : "Are you sure you want to delete ALL logs?")
        : (window.t ? window.t('webui_conf_logs_confirm_sel') : "Delete selected logs?");
        
    if (!confirm(confirmMsg)) {
        return;
    }
    
    const payload = { all: all, files: [] };
    if (!all) {
        document.querySelectorAll('.log-del-cb:checked').forEach(cb => payload.files.push(cb.value));
        if (payload.files.length === 0) {
            alert(window.t ? window.t('webui_conf_logs_none_sel') : "No files selected.");
            return;
        }
    }
    
    try {
        const r = await fetch('/api/logs/files', {
            method: 'DELETE',
            body: JSON.stringify(payload)
        });
        const data = await r.json();
        if (data.ok) {
            const successMsg = window.t ? window.t('webui_conf_logs_delete_success') : "files deleted successfully.";
            alert(`✅ ${data.deleted} ${successMsg}`);
            closeLogDeleteModal();
            refreshLogFiles();
        } else {
            const errMsg = window.t ? window.t('webui_conf_logs_delete_err') : "Error during deletion:";
            alert(`❌ ${errMsg} ${data.error}`);
        }
    } catch(e) {
        alert("Errore di rete: " + e.message);
    }
}

window.openLogDeleteModal = openLogDeleteModal;
window.closeLogDeleteModal = closeLogDeleteModal;
window.deleteSelectedLogs = deleteSelectedLogs;
window.addLogWindow = addLogWindow;
window.refreshLogFiles = refreshLogFiles;
window.updateLogGridLayout = updateLogGridLayout;
window.startLogStream = startLogStream;
window.loadLogTailIntoWindow = loadLogTailIntoWindow;
window.loadLogSearchIntoWindow = loadLogSearchIntoWindow;
