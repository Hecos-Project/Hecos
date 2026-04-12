/**
 * ZENTRA — Remote Triggers Client v1.0
 * ======================================
 * Intercepts hardware key events from the iPhone/Android:
 *   - Media Play/Pause button (Bluetooth headphones/MediaSession)
 *   - Volume keys (where allowed by browser)
 * 
 * Also listens for SSE events of type "remote_ptt" pushed by the
 * backend webhook endpoints (Arduino/ESP32/USB buttons via HTTP).
 *
 * When a trigger fires, this script calls the WebUI's microphone 
 * start/stop API.
 */

(function () {
  'use strict';

  // ── Guard: only load once ──────────────────────────────────────────────────
  if (window._zentraRemoteTriggersLoaded) return;
  window._zentraRemoteTriggersLoaded = true;

  const LOG_TAG = '[RemoteTriggers]';

  /**
   * Helper to safely get plugin settings from the global Zentra config.
   * Returns default if not found.
   */
  function getSetting(key, defaultValue) {
    try {
      if (window.cfg && window.cfg.plugins && window.cfg.plugins.REMOTE_TRIGGERS) {
        const settings = window.cfg.plugins.REMOTE_TRIGGERS.settings || {};
        return settings[key] !== undefined ? settings[key] : defaultValue;
      }
    } catch (e) {}
    return defaultValue;
  }

  function log(msg) {
    console.log(LOG_TAG, msg);
    if (!window._zenrtDebugLog) window._zenrtDebugLog = [];
    window._zenrtDebugLog.push(`${new Date().toISOString()} ${msg}`);
  }

  function beep(freq, dur) {
    if (getSetting('feedback_sounds', true)) {
      if (window._webptt_beep) window._webptt_beep(freq, dur);
    }
  }

  function updateVisualIndicator(active) {
    if (!getSetting('visual_indicator', true)) return;
    let el = document.getElementById('zenrt-indicator');
    if (!el) {
      el = document.createElement('div');
      el.id = 'zenrt-indicator';
      el.style = 'position:fixed; top:10px; right:10px; width:12px; height:12px; background:red; border-radius:50%; z-index:9999; display:none; box-shadow:0 0 10px rgba(255,0,0,0.8); pointer-events:none;';
      document.body.appendChild(el);
    }
    el.style.display = active ? 'block' : 'none';
    if (active) {
      el.animate([ { opacity: 0.4 }, { opacity: 1 } ], { duration: 500, iterations: Infinity });
    }
  }

  function startListening() {
    log('START signal received → activating microphone');
    beep(880, 0.1); 
    updateVisualIndicator(true);
    window.isTouchHold = true;
    if (typeof window.startWebAudioRecording === 'function') {
      window.startWebAudioRecording();
    }
    if (navigator.mediaSession) {
      navigator.mediaSession.playbackState = 'playing';
    }
  }

  function stopListening() {
    log('STOP signal received → deactivating microphone');
    beep(440, 0.1);
    updateVisualIndicator(false);
    window.isTouchHold = false;
    window.isLockedMode = false;
    if (typeof window.stopWebAudioRecording === 'function') {
      window.stopWebAudioRecording();
    }
    if (navigator.mediaSession) {
      navigator.mediaSession.playbackState = 'paused';
    }
  }

  function toggleListening() {
    if (window.isWebAudioRecording) stopListening();
    else { window.isLockedMode = true; startListening(); }
  }

  // ── 2. Volume Loop hack (Android) ────────────────────────────────────────
  function setupVolumeLoop() {
    if (!getSetting('enable_volume_loop', false)) return;
    
    log('Initializing Volume Loop hack...');
    const audio = document.createElement('audio');
    audio.loop = true;
    audio.src = 'data:audio/wav;base64,UklGRigAAABXQVZFRm10IBAAAAABAAEARKwAAIhYAQACABAAZGF0YQQAAAAAAA==';
    document.body.appendChild(audio);

    let lastVol = 0.5;
    audio.volume = lastVol;

    const onVol = () => {
      const cur = audio.volume;
      log(`Volume: ${cur}`);
      if (cur > lastVol) startListening();
      else if (cur < lastVol) stopListening();
      
      setTimeout(() => { audio.volume = 0.5; lastVol = 0.5; }, 100);
    };

    audio.addEventListener('volumechange', onVol);
    window.addEventListener('volumechange', onVol);

    const unlock = () => {
      audio.play().then(() => log('Volume Loop Audio Playing')).catch(e => log('Play failed: ' + e));
      if (navigator.mediaSession) navigator.mediaSession.playbackState = 'playing';
      document.removeEventListener('click', unlock);
    };
    document.addEventListener('click', unlock);
  }

  // ── 3. MediaSession API ───────────────────────────────────────────────────
  function setupMediaSession() {
    if (!('mediaSession' in navigator)) {
      log('MediaSession API not available.');
      return;
    }

    const unlock = () => {
      log('User interaction detected → Warming up audio/mic');
      if (window._zenrtAudioCtx && window._zenrtAudioCtx.state === 'suspended') {
        window._zenrtAudioCtx.resume().then(() => log('AudioContext resumed'));
      }
      // WARMUP MICROPHONE FOR iOS
      if (typeof window.initWebAudio === 'function') {
        window.initWebAudio().then(ok => log(`Mic Warmup status: ${ok}`));
      }
      document.removeEventListener('touchstart', unlock);
      document.removeEventListener('click', unlock);
    };
    document.addEventListener('touchstart', unlock);
    document.addEventListener('click', unlock);

    try {
      const ctx = new (window.AudioContext || window.webkitAudioContext)();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      gain.gain.setValueAtTime(0, ctx.currentTime); 
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start();
      window._zenrtAudioCtx = ctx;
    } catch (e) {}

    navigator.mediaSession.metadata = new MediaMetadata({ title: 'Zentra PTT', artist: 'Remote Trigger' });
    navigator.mediaSession.setActionHandler('play', startListening);
    navigator.mediaSession.setActionHandler('pause', stopListening);
    
    // Set initial state to paused to prevent auto-triggering on mobile
    navigator.mediaSession.playbackState = 'paused';
    log('MediaSession handlers installed.');
  }

  // ── Debug Overlay ─────────────────────────────────────────────────────────
  function setupDebugOverlay() {
    const btn = document.getElementById('web-ptt-btn');
    if (!btn) return;
    
    let clicks = 0;
    btn.addEventListener('click', () => {
      clicks++;
      if (clicks === 4) {
        showDebugOverlay();
        clicks = 0;
      }
      setTimeout(() => { clicks = 0; }, 2000);
    });
  }

  function showDebugOverlay() {
    let overlay = document.getElementById('zenrt-debug-overlay');
    if (overlay) { overlay.remove(); return; }

    overlay = document.createElement('div');
    overlay.id = 'zenrt-debug-overlay';
    overlay.style = 'position:fixed; bottom:80px; left:10px; right:10px; background:rgba(0,0,0,0.85); color:#0f0; font-family:monospace; font-size:10px; padding:10px; border-radius:8px; z-index:10000; max-height:200px; overflow-y:auto; border:1px solid #060;';
    
    const update = () => {
      const logs = (window._zenrtDebugLog || []).slice(-15);
      overlay.innerHTML = '<b>RT DEBUG (4-clicks PTT)</b><br>' + logs.join('<br>');
    };
    
    document.body.appendChild(overlay);
    setInterval(update, 1000);
    update();
  }

  // ── 4. Volume Key Interception ───────────────────────────────────────────
  function setupVolumeKeys() {
    const handler = function (e) {
      const code = e.keyCode || e.which;
      const isUp   = (code === 24 || e.key === 'AudioVolumeUp' || e.key === 'VolumeUp' || code === 175);
      const isDown = (code === 25 || e.key === 'AudioVolumeDown' || e.key === 'VolumeDown' || code === 174);

      if (isUp || isDown) {
        log(`Key detected: ${e.key} (code: ${code})`);
        if (window.showToast) window.showToast(`[RT] Key: ${e.key} (c:${code})`);
        
        if (getSetting('enable_volume_keys', true)) {
          // IMPORTANT: don't prevent if we are in Call Mode? No, should keep it.
          e.preventDefault();
          e.stopImmediatePropagation();
          if (isUp) startListening(); else stopListening();
        }
      }
    };
    window.addEventListener('keydown', handler, { capture: true, passive: false });
    document.addEventListener('keydown', handler, { capture: true, passive: false });
    log('Volume key listeners attached.');
  }

  // ── Boot ───────────────────────────────────────────────────────────────────
  function boot() {
    // Safety check: do not initialize if plugin is disabled in config
    if (window.cfg && window.cfg.plugins && window.cfg.plugins.REMOTE_TRIGGERS) {
      if (window.cfg.plugins.REMOTE_TRIGGERS.enabled === false) {
        log('Plugin is DISABLED in config. Aborting boot.');
        return;
      }
    }

    log('Booting Remote Triggers 2.0...');
    setupMediaSession();
    setupVolumeKeys();
    setupVolumeLoop();
    setupDebugOverlay();
    log('Boot complete.');
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
