// --- Dynamic Window Layout & Lifecycle ---
window.addLogWindow = function(source = 'LIVE', level = 'BOTH') {
    const grid = document.getElementById('log-grid');
    const template = document.getElementById('log-window-template');
    if (!grid || !template) return;

    const id = 'win-' + Math.random().toString(36).substr(2, 9);
    const clone = template.content.cloneNode(true);
    
    // Setup elements
    const winCard = clone.querySelector('.log-window-card');
    winCard.dataset.id = id;
    winCard.dataset.source = source;
    
    // Populate source selector
    const sel = winCard.querySelector('.w-source-selector');
    sel.innerHTML = '<option value="LIVE">Live Stream (Total)</option>';
    window.availableLogFiles.forEach(f => {
        const opt = document.createElement('option');
        opt.value = f.name;
        opt.textContent = `${f.name} (${(f.size/1024).toFixed(1)} KB)`;
        sel.appendChild(opt);
    });
    sel.value = source;
    sel.setAttribute('onchange', `window.updateWindowSource('${id}', this.value)`);
    
    winCard.querySelector('.w-level-selector').value = level;
    winCard.querySelector('.w-level-selector').setAttribute('onchange', `window.updateWindowLevel('${id}', this.value)`);
    winCard.querySelector('.w-btn').setAttribute('onclick', `window.clearWindow('${id}')`);
    winCard.querySelector('.w-close').setAttribute('onclick', `window.removeLogWindow('${id}')`);
    
    const btnRaw = winCard.querySelector('.w-raw-btn');
    if (btnRaw) btnRaw.setAttribute('onclick', `window.openRawLog('${id}')`);
    
    // Bind search UI IDs
    const termInp = winCard.querySelector('.w-search-term');
    if (termInp) termInp.setAttribute('oninput', `window.applyWindowSearch('${id}')`);
    const timeInp = winCard.querySelector('.w-search-time');
    if (timeInp) timeInp.setAttribute('oninput', `window.applyWindowSearch('${id}')`);
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
    
    window.activeLogWindows.push(winObj);
    
    if (source !== 'LIVE') {
        if (window.loadLogTailIntoWindow) window.loadLogTailIntoWindow(winObj, source);
    }
    
    // Ensure stream is running
    if (window.startLogStream) window.startLogStream();
    window.updateLogGridLayout();
    
    // Force scroll to bottom shortly after history/tail is loaded
    setTimeout(() => {
        if (winObj && winObj.body) {
            winObj.body.scrollTop = winObj.body.scrollHeight;
        }
    }, 300);
}

window.removeLogWindow = function(id) {
    window.activeLogWindows = window.activeLogWindows.filter(w => {
        if (w.id === id) {
            w.element.remove();
            return false;
        }
        return true;
    });
    window.updateLogGridLayout();
}

window.updateWindowSource = function(id, source) {
    const w = window.activeLogWindows.find(win => win.id === id);
    if (!w) return;
    w.source = source;
    w.element.dataset.source = source;
    w.body.innerHTML = '';
    w.lineCount = 0;
    if (w.filterQ || w.filterT) {
        if (window.loadLogSearchIntoWindow) window.loadLogSearchIntoWindow(w, source);
    } else if (source !== 'LIVE') {
        if (window.loadLogTailIntoWindow) window.loadLogTailIntoWindow(w, source);
    }
}

window.updateWindowLevel = function(id, level) {
    const w = window.activeLogWindows.find(win => win.id === id);
    if (w) w.level = level;
}

window.clearWindow = function(id) {
    const w = window.activeLogWindows.find(win => win.id === id);
    if (w) {
        w.body.innerHTML = '';
        w.lineCount = 0;
        if (window.updateWindowStrips) window.updateWindowStrips(w);
    }
}

window.clearAllLogWindows = function() {
    window.activeLogWindows.forEach(w => window.clearWindow(w.id));
}

window.updateLogGridLayout = function() {
    const layoutInput = document.getElementById('log-grid-layout');
    if (!layoutInput) return;
    const layout = layoutInput.value;
    const grid = document.getElementById('log-grid');
    if (!grid) return;
    grid.className = 'log-grid layout-' + layout;
    
    // Special 'auto' logic
    if (layout === 'auto') {
        if (window.activeLogWindows.length === 1) grid.classList.add('single');
        else grid.classList.remove('single');
    }
}
