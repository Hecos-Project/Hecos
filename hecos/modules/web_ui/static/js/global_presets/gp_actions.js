/* ⚡ SOUL FORGE: gp_actions.js */

window.sfSaveAsNewSoul = function() {
    window.hecosPrompt("Enter the name for the new Global Preset:", async function(name) {
        if (!name) return;
        
        const id = name.toLowerCase().replace(/[^a-z0-9]/g, '_');
        const data = window.sfCollectUIState();
        data.meta = { id: id, name: name, icon: "⚡" };
        
        try {
            const res = await fetch('/api/souls', {
                method: 'POST',
                headers: {'Content-Type':'application/json'},
                body: JSON.stringify(data)
            });
            if (res.ok) {
                await window.sfLoadData();
                window.sfActivateSoul(id);
            }
        } catch(e) {}
    });
};


window.sfSaveInlineToActive = async function() {
    const soulId = window.sfState.activeSoulId;
    if (!soulId) return;
    
    const soulObj = window.sfState.souls.find(s => s.meta.id === soulId);
    if (!soulObj) return;
    
    const newData = window.sfCollectUIState();
    newData.meta = soulObj.meta; // keep meta
    
    try {
        const res = await fetch('/api/souls', {
            method: 'POST',
            headers: {'Content-Type':'application/json'},
            body: JSON.stringify(newData)
        });
        if (res.ok) {
            document.getElementById('sf-status-msg').textContent = "Updated successfully.";
            setTimeout(() => document.getElementById('sf-status-msg').textContent = "", 3000);
            window.sfState.isDirty = false;
            
            const topBtn = document.getElementById('sf-top-save-btn');
            if (topBtn) {
                topBtn.innerHTML = '<i class="fas fa-save"></i> Save';
                topBtn.style.backgroundColor = '';
                topBtn.style.color = '';
                topBtn.onclick = window.sfOverwriteSoul;
            }
        }
    } catch(e) {}
};


window.sfOverwriteSoul = function() {
    if (!window.sfState.activeSoulId) {
        if (window.showToast) window.showToast("No active Global Preset selected for overwrite.", "error");
        return;
    }
    window.hecosConfirm("Do you want to overwrite the active Global Preset with these settings?", function() {
        window.sfSaveInlineToActive();
    });
};


window.sfDeleteSoul = function() {
    const soulId = window.sfState.activeSoulId;
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
                await window.sfLoadData();
                document.getElementById('sf-status-msg').textContent = "Global Preset deleted.";
                setTimeout(() => document.getElementById('sf-status-msg').textContent = "", 3000);
            } else {
                if (window.showToast) window.showToast("Error during deletion.", "error");
            }
        } catch(e) {
            if (window.showToast) window.showToast("Error during deletion.", "error");
        }
    });
};


