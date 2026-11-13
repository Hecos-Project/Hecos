/**
 * audio_bus.js
 * Lightweight cross-tab audio coordination bus shared between Hecos Main Chat,
 * Net Search Copilot, and other web modules so multiple browser tabs never
 * synthesize or play TTS audio simultaneously.
 */
(function () {
  'use strict';
  if (window.HecosAudioBus) return;

  const CHANNEL_NAME = 'hecos_audio_bus';
  const STORAGE_KEY = 'hecos_audio_bus_event';
  const tabId = 'tab_' + Math.random().toString(36).slice(2) + '_' + Date.now().toString(36);

  const claimListeners = [];
  const stopListeners = [];
  const micClaimListeners = [];
  const backendPttListeners = [];
  let channel = null;

  try {
    if (typeof BroadcastChannel !== 'undefined') {
      channel = new BroadcastChannel(CHANNEL_NAME);
      channel.onmessage = (ev) => _handleMessage(ev && ev.data);
    }
  } catch (e) { /* Ignore BroadcastChannel restrictions */ }

  window.addEventListener('storage', (ev) => {
    if (ev.key !== STORAGE_KEY || !ev.newValue) return;
    try {
      const msg = JSON.parse(ev.newValue);
      _handleMessage(msg);
    } catch (e) { /* Ignore malformed event */ }
  });

  function _dispatch(msg) {
    try {
      if (channel) channel.postMessage(msg);
    } catch (e) { /* ignore */ }
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(msg));
    } catch (e) { /* ignore */ }
  }

  function _handleMessage(msg) {
    if (!msg || typeof msg !== 'object') return;
    if (msg.tabId === tabId) return; // Ignore our own echoes

    if (msg.type === 'tts_claim') {
      claimListeners.forEach((fn) => {
        try { fn(msg); } catch (e) { console.warn('[AudioBus] onClaim error:', e); }
      });
    } else if (msg.type === 'tts_stop_all') {
      stopListeners.forEach((fn) => {
        try { fn(msg); } catch (e) { console.warn('[AudioBus] onStopAll error:', e); }
      });
    } else if (msg.type === 'mic_claim') {
      micClaimListeners.forEach((fn) => {
        try { fn(msg); } catch (e) { console.warn('[AudioBus] onMicClaim error:', e); }
      });
    } else if (msg.type === 'backend_ptt') {
      backendPttListeners.forEach((fn) => {
        try { fn(msg); } catch (e) { console.warn('[AudioBus] onBackendPtt error:', e); }
      });
    }
  }

  window.HecosAudioBus = {
    tabId,

    /**
     * Announce that `owner` in this tab is claiming active TTS generation/playback.
     * Other tabs receive this and pause/cancel their own local audio players.
     */
    claim(owner, meta = {}) {
      const msg = {
        type: 'tts_claim',
        owner: owner || 'unknown',
        tabId,
        playbackId: (meta && meta.playbackId) || ('pb_' + Date.now()),
        ts: Date.now()
      };
      _dispatch(msg);
      return msg.playbackId;
    },

    /**
     * Broadcast an explicit global stop so every open tab stops its TTS player.
     */
    stopAll(owner) {
      _dispatch({
        type: 'tts_stop_all',
        owner: owner || 'unknown',
        tabId,
        ts: Date.now()
      });
    },

    /**
     * Announce that `owner` in this tab is claiming microphone STT capture.
     * Other tabs cancel any active/locked browser microphone recording cleanly.
     */
    claimMic(owner, meta = {}) {
      const msg = {
        type: 'mic_claim',
        owner: owner || 'unknown',
        tabId,
        captureId: (meta && meta.captureId) || ('mic_' + Date.now()),
        ts: Date.now()
      };
      _dispatch(msg);
      return msg.captureId;
    },

    /**
     * Propagate host hardware PTT state (from Main Chat SSE /api/events) to other tabs.
     */
    notifyBackendPtt(active, source) {
      _dispatch({
        type: 'backend_ptt',
        active: Boolean(active),
        source: source || 'host',
        tabId,
        ts: Date.now()
      });
    },

    onClaim(fn) {
      if (typeof fn === 'function') claimListeners.push(fn);
    },

    onStopAll(fn) {
      if (typeof fn === 'function') stopListeners.push(fn);
    },

    onMicClaim(fn) {
      if (typeof fn === 'function') micClaimListeners.push(fn);
    },

    onBackendPtt(fn) {
      if (typeof fn === 'function') backendPttListeners.push(fn);
    }
  };
})();

