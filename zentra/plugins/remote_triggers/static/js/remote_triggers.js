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

  function log(msg) {
    console.log(LOG_TAG, msg);
  }

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

  // ── Core PTT Bridge ────────────────────────────────────────────────────────
  // Interacts with the native WebUI audio recorder.

  function startListening() {
    log('START signal received → activating microphone');
    if (typeof window._webpttStartRecording === 'function') {
      window._webpttStartRecording();
    } else if (typeof window.togglePTT === 'function') {
      if (!window._zenrtIsRecording) {
        window.togglePTT();
        window._zenrtIsRecording = true;
      }
    }
  }

  function stopListening() {
    log('STOP signal received → deactivating microphone');
    if (typeof window._webpttStopRecording === 'function') {
      window._webpttStopRecording();
      window._zenrtIsRecording = false;
    } else if (typeof window.togglePTT === 'function' && window._zenrtIsRecording) {
      window.togglePTT();
      window._zenrtIsRecording = false;
    }
  }

  function toggleListening() {
    log('TOGGLE signal received');
    if (window._zenrtIsRecording) {
      stopListening();
    } else {
      startListening();
    }
  }

  window._zenrtIsRecording = false;

  // ── 1. SSE Listener — Backend Webhooks ─────────────────────────────────────
  // Listens for PTT events broadcasted by the Flask backend.
  function handleRemotePttEvent(data) {
    const action = data.action || 'toggle';
    if (action === 'start') startListening();
    else if (action === 'stop') stopListening();
    else toggleListening();
  }

  if (!window._zentraSSEHandlers) window._zentraSSEHandlers = {};
  window._zentraSSEHandlers['remote_ptt'] = handleRemotePttEvent;
  log('SSE handler registered for type: remote_ptt');

  // ── 2. MediaSession API — Bluetooth/Headphone Buttons ─────────────────────
  // Intercepts Play/Pause from hardware buttons (e.g. iPhone).
  function setupMediaSession() {
    if (!('mediaSession' in navigator)) {
      log('MediaSession API not available.');
      return;
    }

    if (!getSetting('enable_mediasession', true)) {
      log('MediaSession feature disabled in settings.');
      return;
    }

    // Create a silent audio node to "own" the media session
    try {
      const ctx = new (window.AudioContext || window.webkitAudioContext)();
      const oscillator = ctx.createOscillator();
      const gainNode = ctx.createGain();
      gainNode.gain.setValueAtTime(0, ctx.currentTime); 
      oscillator.connect(gainNode);
      gainNode.connect(ctx.destination);
      oscillator.start();
      ctx.suspend();
      window._zenrtAudioCtx = ctx;
    } catch (e) {
      log('AudioContext initialization failed: ' + e);
    }

    navigator.mediaSession.metadata = new MediaMetadata({
      title: 'Zentra',
      artist: 'Remote Trigger Enabled',
      album: 'AI Assistant',
    });

    navigator.mediaSession.setActionHandler('play', function () {
      log('Hardware: PLAY pressed → PTT START');
      if (window._zenrtAudioCtx) window._zenrtAudioCtx.resume();
      startListening();
    });

    navigator.mediaSession.setActionHandler('pause', function () {
      log('Hardware: PAUSE pressed → PTT STOP');
      stopListening();
    });

    try {
      navigator.mediaSession.setActionHandler('nexttrack', function () {
        log('Hardware: NEXT pressed → PTT TOGGLE');
        toggleListening();
      });
    } catch (e) {}

    navigator.mediaSession.playbackState = 'paused';
    log('MediaSession handlers installed.');
  }

  // ── 3. Volume Key Interception ───────────────────────────────────────────
  // Intercepts volume keys on focus (Android Chrome primarily).
  function setupVolumeKeys() {
    if (!getSetting('enable_volume_keys', true)) {
      log('Volume key interception disabled in settings.');
      return;
    }

    document.addEventListener('keydown', function (e) {
      if (e.keyCode === 175 || e.key === 'AudioVolumeUp') {
        e.preventDefault();
        log('Key: Volume UP → PTT START');
        startListening();
      } else if (e.keyCode === 174 || e.key === 'AudioVolumeDown') {
        e.preventDefault();
        log('Key: Volume DOWN → PTT STOP');
        stopListening();
      }
    }, { passive: false });
    log('Volume key listener attached.');
  }

  // ── Boot ───────────────────────────────────────────────────────────────────
  function boot() {
    log('Initializing...');
    setupMediaSession();
    setupVolumeKeys();
    log('Plugin ready.');
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }

})();
