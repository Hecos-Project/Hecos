/**
 * Quick Config HUD - API Logic
 * Handles saving the partial config to the backend.
 */

window.qcSaveConfigAPI = async function(payload) {
    const statusEl = document.getElementById('qc-sync-status');
    if (statusEl) {
        statusEl.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saving...';
        statusEl.className = 'qc-sync-status visible saving';
    }

    try {
        const response = await fetch('/hecos/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (response.ok) {
            const data = await response.json();
            if (data.ok) {
                const now = new Date();
                const timeStr = now.getHours().toString().padStart(2, '0') + ':' + 
                              now.getMinutes().toString().padStart(2, '0') + ':' + 
                              now.getSeconds().toString().padStart(2, '0');
                
                if (statusEl) {
                    statusEl.innerHTML = `<i class="fas fa-check-circle"></i> Synced at ${timeStr}`;
                    statusEl.className = 'qc-sync-status visible success';
                }
                
                // Trigger UI refresh in the main chat
                if (window.refreshStatus) {
                    window.refreshStatus();
                }
                
                // Hide success message after 3 seconds
                setTimeout(() => {
                    if (statusEl && statusEl.classList.contains('success')) {
                        statusEl.classList.remove('visible');
                    }
                }, 3000);
            } else {
                throw new Error("Save returned not ok");
            }
        } else {
            throw new Error(`HTTP error ${response.status}`);
        }
    } catch (e) {
        console.error("QC Save failed:", e);
        if (statusEl) {
            statusEl.innerHTML = '<i class="fas fa-exclamation-triangle"></i> Save Failed';
            statusEl.className = 'qc-sync-status visible error';
        }
    }
};
