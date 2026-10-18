window.openVoiceClonePicker = function() {
    const current = document.getElementById('v-xtts-speaker-wav')?.value || 'C:\\';
    let initDir = current;
    if (current.includes('\\') || current.includes('/')) {
        const lastSlash = Math.max(current.lastIndexOf('\\'), current.lastIndexOf('/'));
        initDir = lastSlash > 0 ? current.substring(0, lastSlash) : current;
    }
    
    if (typeof HecosFilePicker !== 'undefined') {
        HecosFilePicker.open({
            title: 'Select Voice Clone WAV',
            initialPath: initDir,
            mode: 'file',
            onSelect: function(p) {
                const inp = document.getElementById('v-xtts-speaker-wav');
                if(inp) inp.value = p;
                if (typeof window.onVoiceClonePathInput === 'function') {
                    window.onVoiceClonePathInput();
                }
            }
        });
    } else {
        console.error("HecosFilePicker is not defined!");
    }
};

// ── Voice Clone Library ──────────────────────────────────────────────────────

window.loadVoiceCloneList = async function() {
    try {
        const r = await fetch('/api/audio/voice-clones');
        const data = await r.json();
        if (!data.ok) return;
        const sel = document.getElementById('v-xtts-clone-select');
        if (!sel) return;
        const currentPath = document.getElementById('v-xtts-speaker-wav')?.value || '';
        sel.innerHTML = '<option value="">— None (use Default Speaker) —</option>';
        for (const f of data.files) {
            const opt = document.createElement('option');
            opt.value = f.path;
            opt.textContent = f.name;
            if (f.path === currentPath) opt.selected = true;
            sel.appendChild(opt);
        }
        // If no library option matched but there's a path typed, leave dropdown at "None"
    } catch(e) {
        console.error('[AudioConfig] loadVoiceCloneList error:', e);
    }
};

window.onVoiceCloneSelect = function() {
    const sel = document.getElementById('v-xtts-clone-select');
    const input = document.getElementById('v-xtts-speaker-wav');
    if (!sel || !input) return;
    input.value = sel.value; // '' for None, path for a file
    saveAudioConfig();
};

window.onVoiceClonePathInput = function() {
    // If user types manually, deselect dropdown so it stays in sync
    const input = document.getElementById('v-xtts-speaker-wav');
    const sel = document.getElementById('v-xtts-clone-select');
    if (!sel || !input) return;
    const typed = input.value.trim();
    // Try to find a matching option
    const matched = Array.from(sel.options).find(o => o.value === typed);
    sel.value = matched ? matched.value : '';
    
    // Disable default speaker dropdown
    const speakerSel = document.getElementById('v-xtts-speaker');
    if (speakerSel) {
        if (typed !== '') {
            speakerSel.disabled = true;
            speakerSel.title = "Using Voice Clone (.wav)";
            let cloneOpt = Array.from(speakerSel.options).find(o => o.value === "CLONE");
            if (!cloneOpt) {
                cloneOpt = document.createElement('option');
                cloneOpt.value = "CLONE";
                cloneOpt.textContent = "-- Voice Clone Active --";
                speakerSel.appendChild(cloneOpt);
            }
            speakerSel.value = "CLONE";
        } else {
            speakerSel.disabled = false;
            speakerSel.title = "";
            const cloneOpt = Array.from(speakerSel.options).find(o => o.value === "CLONE");
            if (cloneOpt) {
                cloneOpt.remove();
            }
            // Restore previous value if possible, or leave it to user
        }
    }
};

window.uploadVoiceClone = async function(fileInput) {
    if (!fileInput.files.length) return;
    const file = fileInput.files[0];
    if (!file.name.toLowerCase().endsWith('.wav')) {
        if (window.showToast) window.showToast('Only WAV files are accepted.', 'error');
        return;
    }
    const fd = new FormData();
    fd.append('file', file);
    try {
        if (window.showToast) window.showToast('Uploading...', 'info');
        const r = await fetch('/api/audio/voice-clones/upload', { method: 'POST', body: fd });
        const data = await r.json();
        if (data.ok) {
            await loadVoiceCloneList();
            // Auto-select the just-uploaded file
            const sel = document.getElementById('v-xtts-clone-select');
            const input = document.getElementById('v-xtts-speaker-wav');
            if (sel && data.path) {
                sel.value = data.path;
                if (input) input.value = data.path;
                saveAudioConfig();
            }
            if (window.showToast) window.showToast(`Uploaded: ${data.filename}`, 'success');
        } else {
            if (window.showToast) window.showToast('Upload failed: ' + data.error, 'error');
        }
    } catch(e) {
        if (window.showToast) window.showToast('Upload error: ' + e.message, 'error');
    }
    fileInput.value = ''; // reset so same file can be re-uploaded
};

// ── Fish Speech Voice Clone Helpers ─────────────────────────────────────────

window.openFishVoiceClonePicker = function() {
    const current = document.getElementById('v-fish-speaker-wav')?.value || 'C:\\';
    let initDir = current;
    if (current.includes('\\') || current.includes('/')) {
        const lastSlash = Math.max(current.lastIndexOf('\\'), current.lastIndexOf('/'));
        initDir = lastSlash > 0 ? current.substring(0, lastSlash) : current;
    }
    
    if (typeof HecosFilePicker !== 'undefined') {
        HecosFilePicker.open({
            title: 'Select Fish Speech Voice Clone WAV',
            initialPath: initDir,
            mode: 'file',
            onSelect: function(p) {
                const inp = document.getElementById('v-fish-speaker-wav');
                if(inp) inp.value = p;
                if (typeof window.onFishVoiceClonePathInput === 'function') {
                    window.onFishVoiceClonePathInput();
                }
            }
        });
    } else {
        console.error("HecosFilePicker is not defined!");
    }
};

window._voiceClonesTranscriptMap = {};

window.loadFishVoiceCloneList = async function() {
    try {
        const [voicesRes, clonesRes] = await Promise.all([
            fetch('/api/audio/voices?engine=fish_speech').then(r => r.json()).catch(() => ({})),
            fetch('/api/audio/voice-clones').then(r => r.json()).catch(() => ({ ok: false }))
        ]);
        
        if (clonesRes && clonesRes.ok && clonesRes.files) {
            window._voiceClonesTranscriptMap = {};
            for (const f of clonesRes.files) {
                window._voiceClonesTranscriptMap[f.filename] = f.transcript || '';
                window._voiceClonesTranscriptMap[f.path] = f.transcript || '';
                window._voiceClonesTranscriptMap[f.name] = f.transcript || '';
            }
        }

        const sel = document.getElementById('v-fish-clone-select');
        if (!sel) return;
        const currentPath = (document.getElementById('v-fish-speaker-wav')?.value || '').trim();
        const list = voicesRes.fish_speech || voicesRes;
        sel.innerHTML = '';
        for (const [key, label] of Object.entries(list)) {
            const opt = document.createElement('option');
            opt.value = key === 'default' ? '' : key;
            opt.textContent = label;
            
            if (opt.value && (currentPath === opt.value || currentPath.endsWith(opt.value) || currentPath.split('\\').pop() === opt.value || currentPath.split('/').pop() === opt.value)) {
                opt.selected = true;
            } else if (!opt.value && !currentPath) {
                opt.selected = true;
            }
            sel.appendChild(opt);
        }
    } catch(e) {
        console.error('[AudioConfig] loadFishVoiceCloneList error:', e);
    }
};

window.onFishVoiceCloneSelect = function() {
    const sel = document.getElementById('v-fish-clone-select');
    const input = document.getElementById('v-fish-speaker-wav');
    const refTextInput = document.getElementById('v-fish-reference-text');
    if (!sel || !input) return;
    input.value = sel.value;

    if (sel.value && window._voiceClonesTranscriptMap) {
        const base = sel.value.split('\\').pop().split('/').pop();
        const transcript = window._voiceClonesTranscriptMap[sel.value] || window._voiceClonesTranscriptMap[base];
        if (transcript !== undefined && refTextInput) {
            refTextInput.value = transcript;
        }
    }

    if (typeof saveAudioConfig === 'function') saveAudioConfig();
};

window.onFishVoiceClonePathInput = function() {
    const input = document.getElementById('v-fish-speaker-wav');
    const sel = document.getElementById('v-fish-clone-select');
    const refTextInput = document.getElementById('v-fish-reference-text');
    if (!sel || !input) return;
    const typed = input.value.trim();
    const matched = Array.from(sel.options).find(o => o.value && (o.value === typed || typed.endsWith(o.value)));
    sel.value = matched ? matched.value : '';

    if (typed && window._voiceClonesTranscriptMap && refTextInput && !refTextInput.value.trim()) {
        const base = typed.split('\\').pop().split('/').pop();
        const transcript = window._voiceClonesTranscriptMap[typed] || window._voiceClonesTranscriptMap[base];
        if (transcript) {
            refTextInput.value = transcript;
        }
    }
};

window.uploadFishVoiceClone = async function(fileInput) {
    if (!fileInput.files.length) return;
    const file = fileInput.files[0];
    if (!file.name.toLowerCase().endsWith('.wav')) {
        if (window.showToast) window.showToast('Only WAV files are accepted.', 'error');
        return;
    }
    const fd = new FormData();
    fd.append('file', file);
    try {
        if (window.showToast) window.showToast('Uploading...', 'info');
        const r = await fetch('/api/audio/voice-clones/upload', { method: 'POST', body: fd });
        const data = await r.json();
        if (data.ok) {
            await loadFishVoiceCloneList();
            if (typeof loadVoiceCloneList === 'function') await loadVoiceCloneList();
            const sel = document.getElementById('v-fish-clone-select');
            const input = document.getElementById('v-fish-speaker-wav');
            if (sel && data.path) {
                sel.value = data.path;
                if (input) input.value = data.path;
                if (typeof saveAudioConfig === 'function') saveAudioConfig();
            }
            if (window.showToast) window.showToast(`Uploaded: ${data.filename}`, 'success');
        } else {
            if (window.showToast) window.showToast('Upload failed: ' + data.error, 'error');
        }
    } catch(e) {
        if (window.showToast) window.showToast('Upload error: ' + e.message, 'error');
    }
    fileInput.value = '';
};



// ── Custom Modals for Audio Panel ───────────────────────────────────────────
