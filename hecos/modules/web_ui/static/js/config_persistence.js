/**
 * Hecos WebUI - Persistence Logic
 * Handles saving to backend, reboots, and initial loading.
 */

async function saveConfig(silent = false) {
  if (window.isInitialLoading) return;
  if (!silent) setSaveMsg(window.I18N?.msg_saving || 'Saving...', 'muted');
  
  try {
    const payload = buildPayload();
    payload._force_restart = !silent;

    const audioPayload = (typeof buildAudioPayload === 'function') ? buildAudioPayload() : {};
    const mediaPayload = (typeof buildMediaPayload === 'function') ? buildMediaPayload() : {};
    
    const [resCfg, resAud, resMed, resAgent] = await Promise.all([
      fetch('/hecos/config', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) }),
      fetch('/api/audio/config', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(audioPayload) }),
      fetch('/hecos/api/config/media', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(mediaPayload) }),
      fetch('/hecos/config/agent', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(window.cfg.agent || {}) })
    ]);

    const data = await resCfg.json();
    if (data.ok) {
       console.log("[PERSISTENCE] Config saved successfully.");
       window.cfg = payload; // Update in-memory to prevent stale state
       if (!silent) {
           setSaveMsg(window.I18N?.msg_saved || 'Saved', 'ok');
           if (typeof isRestartNeeded === 'function' && isRestartNeeded()) {
               if (confirm("Riavviare Hecos ora per applicare i cambiamenti critici?")) rebootSystem();
           }
       } else {
           setSaveMsg('✓ Synced', 'ok');
           setTimeout(() => setSaveMsg('', 'muted'), 3000);
       }
    } else {
       setSaveMsg('Error saving config.', 'err');
    }
  } catch (e) {
    console.error("Save error:", e);
    setSaveMsg('Fetch error: ' + e, 'err');
  }
}

async function rebootSystem() {
  setSaveMsg('Rebooting...', 'err');
  try {
    const res = await fetch("/api/system/reboot", { method: "POST" });
    if (res.ok) setTimeout(() => location.reload(), 5000);
  } catch (e) { setSaveMsg("Network error during reboot", 'err'); }
}

async function initAll(attempt = 1) {
    window.isInitialLoading = true;
    setSaveMsg('Loading...', 'muted');
    try {
        if (Object.keys(window.cfg || {}).length === 0) {
            const [rOpts, rCfg, rAgent] = await Promise.all([
                fetch('/hecos/options'),
                fetch('/hecos/config'),
                fetch('/hecos/config/agent')
            ]);
            window.sysOptions = await rOpts.json();
            window.cfg = await rCfg.json();
            window.cfg.agent = await rAgent.json();
        }
        
        renderConfigHub(window.viewMode);
        showTab(window.activeTab, true);
        populateUI();
        window.isInitialLoading = false;
        setSaveMsg('Synced', 'ok');
        
        // Background metadata
        fetch('/api/plugins/registry').then(r => r.json()).then(reg => {
            if (typeof mergeRegistry === 'function') mergeRegistry(reg);
            renderConfigHub();
        });
    } catch (e) {
        if (attempt < 3) setTimeout(() => initAll(attempt + 1), 2000);
        else setSaveMsg('Init failed', 'err');
    }
}

window.saveConfig = saveConfig;
window.initAll = initAll;
window.rebootSystem = rebootSystem;
