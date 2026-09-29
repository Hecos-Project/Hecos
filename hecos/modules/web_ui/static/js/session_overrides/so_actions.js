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


