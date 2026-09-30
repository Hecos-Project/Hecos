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



// ── Custom Modals for Audio Panel ───────────────────────────────────────────
