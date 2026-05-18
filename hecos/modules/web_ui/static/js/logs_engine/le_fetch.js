// --- Log Polling and Search Fetcher ---
window.loadLogTailIntoWindow = async function(winObj, filename) {
    try {
        const maxLinesEl = winObj.element.querySelector('.w-max-lines');
        const n = maxLinesEl ? (parseInt(maxLinesEl.value) || 500) : 500;
        const r = await fetch(`/api/logs/tail/${filename}?n=${n}`);
        const d = await r.json();
        if (d.ok) {
            d.lines.forEach(line => {
                if (window.appendRawLine) window.appendRawLine(winObj, line);
            });
        }
    } catch(e) { console.error("Tail failed", e); }
}

window.loadLogSearchIntoWindow = async function(winObj, filename) {
    try {
        const sq = encodeURIComponent(winObj.filterQ || '');
        const st = encodeURIComponent(winObj.filterT || '');
        const maxLinesEl = winObj.element.querySelector('.w-max-lines');
        const n = maxLinesEl ? (parseInt(maxLinesEl.value) || 500) : 500;
        const r = await fetch(`/api/logs/search/${filename}?n=${n}&q=${sq}&time=${st}`);
        const d = await r.json();
        if (d.ok) {
            if (d.type === 'events') {
                d.data.forEach(evt => {
                    if (window.appendDataLine) window.appendDataLine(winObj, evt);
                });
            } else if (d.type === 'lines') {
                d.data.forEach(line => {
                    if (window.appendRawLine) window.appendRawLine(winObj, line);
                });
            }
            setTimeout(() => { if (winObj && winObj.body) winObj.body.scrollTop = winObj.body.scrollHeight; }, 100);
        }
    } catch(e) { console.error("Search failed", e); }
}

window.applyWindowSearch = function(id) {
    const w = window.activeLogWindows.find(win => win.id === id);
    if (!w) return;
    const termEl = w.element.querySelector('.w-search-term');
    const timeEl = w.element.querySelector('.w-search-time');
    const btnRes = w.element.querySelector('.w-btn-reset');
    
    const newQ = termEl ? termEl.value.trim() : '';
    const newT = timeEl ? timeEl.value.trim() : '';

    // If both empty, auto-reset to full view
    if (!newQ && !newT) {
        if (w.filterQ || w.filterT) {
            window.clearWindowSearch(id);
        }
        if (btnRes) btnRes.classList.remove('active');
        return;
    }

    w.filterQ = newQ;
    w.filterT = newT;
    if (btnRes) btnRes.classList.add('active');
    
    w.body.innerHTML = '';
    w.lineCount = 0;
    window.loadLogSearchIntoWindow(w, w.source);
}

window.clearWindowSearch = function(id) {
    const w = window.activeLogWindows.find(win => win.id === id);
    if (!w) return;
    const termEl = w.element.querySelector('.w-search-term');
    const timeEl = w.element.querySelector('.w-search-time');
    const btnRes = w.element.querySelector('.w-btn-reset');
    
    if (termEl) termEl.value = '';
    if (timeEl) timeEl.value = '';
    if (btnRes) btnRes.classList.remove('active');
    
    w.filterQ = '';
    w.filterT = '';
    
    w.body.innerHTML = '';
    w.lineCount = 0;
    if (w.source !== 'LIVE') {
        window.loadLogTailIntoWindow(w, w.source);
    } else {
        // Just reload the LIVE search with no filters (essentially historical tail)
        window.loadLogSearchIntoWindow(w, 'LIVE');
    }
}
