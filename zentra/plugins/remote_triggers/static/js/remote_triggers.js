/**
 * ZENTRA — Remote Triggers Client v1.0
 * ======================================
 * Intercepts hardware key events from the iPhone/Android:
 *   - Media Play/Pause button (Bluetooth headphones)
 *   - Volume keys (where allowed by browser)
 * 
 * Also listens for SSE events of type "remote_ptt" pushed by the
 * backend webhook endpoints (Arduino/ESP32/USB buttons via HTTP).
 *
 * When a trigger fires, this script calls window.togglePTT() or
 * directly invokes the WebUI's microphone start/stop API.
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

  // ── Core PTT Bridge ────────────────────────────────────────────────────────
  // Tries to use the existing WebUI PTT functions (window.togglePTT,
  // window._webptt_setButtonState) if they are available.

  function startListening() {
    log('START signal received → activating mic');
    if (typeof window._webpttStartRecording === 'function') {
      window._webpttStartRecording();
    } else if (typeof window.togglePTT === 'function') {
      // Fallback: toggle (if not already recording)
      if (!window._zenrtIsRecording) {
        window.togglePTT();
        window._zenrtIsRecording = true;
      }
    }
  }

  function stopListening() {
    log('STOP signal received → deactivating mic');
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

  // ── 1. SSE Listener — Backend Webhook (Arduino/ESP32/USB) ─────────────────
  // The web_ui SSE stream already exists. We hook into it via the global
  // event dispatcher already set up by chat_events.js.
  function handleRemotePttEvent(data) {
    const action = data.action || 'toggle';
    if (action === 'start') startListening();
    else if (action === 'stop') stopListening();
    else toggleListening();
  }

  // Register our handler in the global SSE dispatcher (chat_events.js calls
  // window._zentraSSEHandlers[type](data) for each incoming event type).
  if (!window._zentraSSEHandlers) window._zentraSSEHandlers = {};
  window._zentraSSEHandlers['remote_ptt'] = handleRemotePttEvent;
  log('SSE handler registered for type: remote_ptt');

  // ── 2. MediaSession API — Bluetooth/Headphone Buttons ─────────────────────
  // Safari iOS and Chrome Android support MediaSession for media hardware keys.
  // We create a silent audio node to "own" the media session so the OS routes
  // the hardware buttons to us instead of another app.
  function setupMediaSession() {
    if (!('mediaSession' in navigator)) {
      log('MediaSession API not available on this browser.');
      return;
    }

    // Create a silent oscillator so the browser treats us as a media player
    // and gives priority to our MediaSession handlers.
    try {
      const ctx = new (window.AudioContext || window.webkitAudioContext)();
      const oscillator = ctx.createOscillator();
      const gainNode = ctx.createGain();
      gainNode.gain.setValueAtTime(0, ctx.currentTime); // silence
      oscillator.connect(gainNode);
      gainNode.connect(ctx.destination);
      oscillator.start();
      // Immediately suspend to not waste CPU — wake it up only when needed
      ctx.suspend();
      window._zenrtAudioCtx = ctx;
    } catch (e) {
      log('Could not create silent AudioContext: ' + e);
    }

    // Set metadata so the lock screen shows "Zentra — listening"
    navigator.mediaSession.metadata = new MediaMetadata({
      title: 'Zentra',
      artist: 'Remote Trigger Active',
      album: 'AI Assistant',
    });

    // 🎯 THE MAGIC: intercept Play/Pause from headphone buttons
    navigator.mediaSession.setActionHandler('play', function () {
      log('MediaSession: PLAY pressed → PTT START');
      // Resume our context to claim media session priority
      if (window._zenrtAudioCtx) window._zenrtAudioCtx.resume();
      startListening();
    });

    navigator.mediaSession.setActionHandler('pause', function () {
      log('MediaSession: PAUSE pressed → PTT STOP');
      stopListening();
    });

    // Some Android headphones also send "nexttrack" / "previoustrack"
    // We can map these to toggle as a bonus
    try {
      navigator.mediaSession.setActionHandler('nexttrack', function () {
        log('MediaSession: NEXT pressed → PTT TOGGLE');
        toggleListening();
      });
    } catch (e) { /* not all browsers support this */ }

    navigator.mediaSession.playbackState = 'paused';
    log('MediaSession handlers installed (Play/Pause → PTT Start/Stop)');
  }

  // ── 3. Volume Key Interception (Android Chrome only) ──────────────────────
  // Note: iOS Safari does NOT allow JS to intercept volume keys in foreground.
  // On Android Chrome, keydown events for volume keys ARE fired when the
  // page has focus. We intercept them here.
  function setupVolumeKeys() {
    document.addEventListener('keydown', function (e) {
      // Android Chrome fires these keyCodes for volume buttons
      if (e.keyCode === 175 || e.key === 'AudioVolumeUp') {
        e.preventDefault();
        log('Volume UP key → PTT START');
        startListening();
      } else if (e.keyCode === 174 || e.key === 'AudioVolumeDown') {
        e.preventDefault();
        log('Volume DOWN key → PTT STOP');
        stopListening();
      }
    }, { passive: false });
    log('Volume key listeners attached (Android Chrome)');
  }

  // ── Boot ───────────────────────────────────────────────────────────────────
  function boot() {
    log('Initializing...');
    setupMediaSession();
    setupVolumeKeys();
    log('Ready. Webhook URLs: /api/remote-triggers/ptt/start | /stop | /toggle');
  }

  // Wait for DOM to be ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }

})();
