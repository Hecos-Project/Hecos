/**
 * config_core_persistence.js
 * saveConfig — persists all config sections to the backend APIs.
 * Depends on: config_core_utils.js (setSaveMsg), config_mapper.js (buildPayload, buildAgentPayload)
 */

async function saveConfig(silent = false) {
  if (isInitialLoading) return;
  if (!silent) setSaveMsg(I18N.msg_saving || 'Saving...', 'muted');
  try {
    const payload = buildPayload();
    payload._force_restart = !silent;

    const audioPayload = (typeof buildAudioPayload === 'function') ? buildAudioPayload() : {};
    const mediaPayload = (typeof buildMediaPayload === 'function') ? buildMediaPayload() : {};

    const resCfg = await fetch('/hecos/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await resCfg.json();

    const resAud = await fetch('/api/audio/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(audioPayload)
    });
    const audData = await resAud.json();

    const resMed = await fetch('/hecos/api/config/media', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(mediaPayload)
    });
    const medData = await resMed.json();

    const agentPayload = (typeof buildAgentPayload === 'function') ? buildAgentPayload() : {};
    const resAgent = await fetch('/hecos/config/agent', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(agentPayload.agent || {})
    });
    const agentData = await resAgent.json();

    if (data.ok && audData.ok && medData.ok && agentData.ok) {
      // Update in-memory state so subsequent saves don't use stale fallbacks
      window.cfg        = payload;
      window.audioConfig = audioPayload;
      window.mediaConfig = mediaPayload;
      if (window.cfg.agent) window.cfg.agent = agentPayload.agent;

      if (!silent) {
          setSaveMsg(I18N.msg_saved || 'Saved', 'ok');

          if (typeof isRestartNeeded === 'function' && isRestartNeeded()) {
            const reboot = confirm("Hai modificato parametri critici (Porte/HTTPS). Vuoi riavviare Hecos ora per applicare i cambiamenti?\n\n(Altrimenti dovrai riavviare manualmente dopo il salvataggio)");
            if (reboot) {
              rebootSystem();
              return;
            }
          }
      } else {
          const syncedMsg = (I18N.webui_conf_msg_synced || '✓ Changes auto-saved').replace('✅ ', '✓ ');
          setSaveMsg(syncedMsg, 'ok');
          document.querySelectorAll('.save-reset').forEach(el => {
              if (el.type === 'checkbox') el.checked = false;
          });
          setTimeout(() => {
              const msgEl = document.getElementById('save-msg');
              if (msgEl && msgEl.textContent.includes('auto-saved')) {
                  setSaveMsg('', 'muted');
              }
          }, 3500);
      }
    } else {
      setSaveMsg('Error saving config.', 'err');
    }
  } catch (e) {
    setSaveMsg('Fetch error: ' + e, 'err');
  }
}

window.saveConfig = saveConfig;
