/* ⚡ SOUL FORGE: gp_actions.js */

window.soSaveAsNewSoul = function() {
    window.hecosPrompt("Enter the name for the new Global Preset:", async function(name) {
        if (!name) return;
        
        const id = name.toLowerCase().replace(/[^a-z0-9]/g, '_');
        const data = window.soCollectUIState();
        data.meta = { id: id, name: name, icon: "⚡" };
        
        try {
            const res = await fetch('/api/souls', {
                method: 'POST',
                headers: {'Content-Type':'application/json'},
                body: JSON.stringify(data)
            });
            if (res.ok) {
                await window.soLoadData();
                window.soActivateSoul(id);
            }
        } catch(e) {}
    });
};


window.soSaveInlineToActive = async function() {
    const newData = window.soCollectUIState();
    const sessionId = window.chatHistoryState?.activeSessionId;
    if (!sessionId) return;
    
    try {
        const res = await fetch('/api/chat/session/config', {
            method: 'POST',
            headers: {'Content-Type':'application/json'},
            body: JSON.stringify({ session_id: sessionId, config: newData })
        });
        if (res.ok) {
            document.getElementById('so-status-msg').textContent = "Overrides saved.";
            setTimeout(() => document.getElementById('so-status-msg').textContent = "", 3000);
            window.soState.isDirty = false;
        }
    } catch(e) {}
};


window.soOverwriteSoul = function() {
    window.soSaveInlineToActive();
};


window.soSaveGlobalInlineToActive = async function() {
    const soulId = window.soState.activeSoulId;
    if (!soulId) return;
    
    const soulObj = window.soState.souls.find(s => s.meta.id === soulId);
    if (!soulObj) return;
    
    const newData = window.soCollectUIState();
    newData.meta = soulObj.meta; // keep meta
    
    try {
        const res = await fetch('/api/souls', {
            method: 'POST',
            headers: {'Content-Type':'application/json'},
            body: JSON.stringify(newData)
        });
        if (res.ok) {
            document.getElementById('so-status-msg').textContent = "Global preset updated successfully.";
            setTimeout(() => document.getElementById('so-status-msg').textContent = "", 3000);
            window.soState.isDirty = false;
            
            const topBtn = document.getElementById('so-top-save-global-btn');
            if (topBtn) {
                topBtn.innerHTML = '<i class="fas fa-save"></i> Save';
                topBtn.style.backgroundColor = '';
                topBtn.style.color = '';
                topBtn.onclick = window.soOverwriteGlobalPreset;
            }
        }
    } catch(e) {}
};


window.soOverwriteGlobalPreset = function() {
    if (!window.soState.activeSoulId) {
        if (window.showToast) window.showToast("No active Global Preset selected to overwrite.", "error");
        return;
    }
    window.hecosConfirm("Do you want to overwrite the active Global Preset with these chat override settings?", function() {
        window.soSaveGlobalInlineToActive();
    });
};


window.soExportSoul = async function() {
    const soulId = window.soState.activeSoulId;
    if (!soulId) {
        if (window.showToast) window.showToast("No Global Preset selected to export.", "error");
        return;
    }
    try {
        const res = await fetch(`/api/souls/${soulId}`);
        const data = await res.json();
        if (data.ok && data.soul) {
            const blob = new Blob([JSON.stringify(data.soul, null, 2)], { type: "application/json" });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${soulId}.global_preset.json`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        }
    } catch(e) { console.error(e); }
};

window.soImportSoul = function(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    const reader = new FileReader();
    reader.onload = async function(e) {
        try {
            const soulData = JSON.parse(e.target.result);
            const res = await fetch('/api/souls', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(soulData)
            });
            if (res.ok) {
                await window.soLoadData();
                const d = await res.json();
                if (d.soul_id) window.soActivateSoul(d.soul_id);
                document.getElementById('so-status-msg').textContent = "Imported successfully.";
                setTimeout(() => document.getElementById('so-status-msg').textContent = "", 3000);
            }
        } catch(err) {
            if (window.showToast) window.showToast("Invalid JSON file.", "error");
        }
        event.target.value = '';
    };
    reader.readAsText(file);
};


window.soDeleteSoul = function() {
    const soulId = window.soState.activeSoulId;
    if (!soulId) {
        if (window.showToast) window.showToast("No Global Preset selected to delete.", "error");
        return;
    }
    window.hecosConfirm("Are you sure you want to permanently delete this Global Preset?", async function() {
        try {
            const res = await fetch(`/api/souls/${soulId}`, {
                method: 'DELETE'
            });
            if (res.ok) {
                // Clear active soul from session if it was deleted
                const sessionId = window.chatHistoryState?.activeSessionId;
                if (sessionId) {
                    await fetch('/api/souls/activate', {
                        method: 'POST',
                        headers: {'Content-Type':'application/json'},
                        body: JSON.stringify({ soul_id: "", session_id: sessionId })
                    });
                }
                await window.soLoadData();
                document.getElementById('so-status-msg').textContent = "Global Preset deleted.";
                setTimeout(() => document.getElementById('so-status-msg').textContent = "", 3000);
            } else {
                if (window.showToast) window.showToast("Error during deletion.", "error");
            }
        } catch(e) {
            if (window.showToast) window.showToast("Error during deletion.", "error");
        }
    });
};


