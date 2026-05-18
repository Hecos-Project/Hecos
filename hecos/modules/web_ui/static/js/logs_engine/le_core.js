// --- Core State & Streaming ---
window.logEvtSource = null;
window.activeLogWindows = [];
window.availableLogFiles = [];

window.refreshLogFiles = async function() {
    try {
        const r = await fetch('/api/logs/files');
        const d = await r.json();
        if (d.ok) {
            window.availableLogFiles = d.files || [];
            // Update all existing selectors in windows
            document.querySelectorAll('.w-source-selector').forEach(sel => {
                const current = sel.value;
                sel.innerHTML = '<option value="LIVE">Live Stream (Total)</option>';
                window.availableLogFiles.forEach(f => {
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

window.startLogStream = function() {
    if (window.logEvtSource) return;
    const statusEl = document.getElementById('log-status');
    if (statusEl) { statusEl.textContent = 'Active'; statusEl.className = 'val-ok'; }

    window.logEvtSource = new EventSource('/api/logs/stream');
    window.logEvtSource.onmessage = (e) => {
        if (e.data === ': keep-alive') return;
        try {
            const data = JSON.parse(e.data);
            window.dispatchLogEvent(data);
        } catch(err) { }
    };
    window.logEvtSource.onerror = () => {
        if (statusEl) { statusEl.textContent = 'Err (Retry)'; statusEl.className = 'val-err'; }
    };
}

window.dispatchLogEvent = function(data) {
    window.activeLogWindows.forEach(win => {
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
            if (window.appendDataLine) window.appendDataLine(win, data);
        }
    });
    
    // Play error beep if enabled
    if (data.level === 'ERROR' && window.cfg?.logging?.ui_error_beeps !== false) {
        window.playErrorBeep();
    }
}

window.playErrorBeep = function() {
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
