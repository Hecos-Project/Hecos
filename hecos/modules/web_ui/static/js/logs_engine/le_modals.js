// --- File Management UI and Actions ---
window.openLogDeleteModal = async function() {
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

window.closeLogDeleteModal = function() {
    const el = document.getElementById('log-delete-modal');
    if (el) el.style.display = 'none';
}

window.deleteSelectedLogs = async function(all = false) {
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
            window.closeLogDeleteModal();
            if (window.refreshLogFiles) window.refreshLogFiles();
        } else {
            const errMsg = window.t ? window.t('webui_conf_logs_delete_err') : "Error during deletion:";
            alert(`❌ ${errMsg} ${data.error}`);
        }
    } catch(e) {
        alert("Errore di rete: " + e.message);
    }
}

window.openRawLog = function(id) {
    const w = window.activeLogWindows.find(win => win.id === id);
    if (!w || w.source === 'LIVE') return;
    window.open(`/api/logs/raw/${w.source}`, '_blank');
}
