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
  const chatStateListeners = [];
  const chatStateReqListeners = [];
  let _seq = 0;
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

  function _notify(listeners, label, msg) {
    listeners.forEach((fn) => {
      try { fn(msg); } catch (e) { console.warn(`[AudioBus] ${label} error:`, e); }
    });
  }

  function _handleMessage(msg) {
    if (!msg || typeof msg !== 'object') return;
    if (msg.tabId === tabId) return; // Ignore our own echoes

    const dispatchMap = {
      tts_claim: [claimListeners, 'onClaim'],
      tts_stop_all: [stopListeners, 'onStopAll'],
      mic_claim: [micClaimListeners, 'onMicClaim'],
      backend_ptt: [backendPttListeners, 'onBackendPtt'],
      chat_state: [chatStateListeners, 'onChatState'],
      chat_state_req: [chatStateReqListeners, 'onChatStateRequest'],
    };
    const target = dispatchMap[msg.type];
    if (target) _notify(target[0], target[1], msg);
  }

  window.HecosAudioBus = {
    tabId,

    /**
     * Announce that `owner` in this tab is claiming active TTS generation/playback.
     * Other tabs receive this and pause/cancel their own local audio players.
     */
    claim(owner, meta = {}) {
      const m = (meta && typeof meta === 'object') ? meta : {};
      const msg = {
        type: 'tts_claim',
        owner: owner || 'unknown',
        tabId,
        playbackId: m.playbackId || ('pb_' + Date.now()),
        sessionId: m.sessionId || null,
        sessionTitle: m.sessionTitle || '',
        personaName: m.personaName || '',
        seq: ++_seq,
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
        seq: ++_seq,
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
        seq: ++_seq,
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
        seq: ++_seq,
        ts: Date.now()
      });
    },

    /**
     * Broadcast per-session chat activity ('idle'|'running'|'speaking'|'stopped'|'error') to other tabs.
     */
    publishChatState(payload = {}) {
      const p = (payload && typeof payload === 'object') ? payload : {};
      _dispatch({
        type: 'chat_state',
        tabId,
        sessionId: p.sessionId || null,
        sessionTitle: p.sessionTitle || '',
        personaName: p.personaName || '',
        status: p.status || 'idle',
        ttlMs: p.ttlMs || 120000,
        seq: ++_seq,
        ts: Date.now()
      });
    },

    /**
     * Ask active tabs to replay their current non-idle session states.
     */
    requestChatStates() {
      _dispatch({
        type: 'chat_state_req',
        tabId,
        seq: ++_seq,
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
    },

    onChatState(fn) {
      if (typeof fn === 'function') chatStateListeners.push(fn);
    },

    onChatStateRequest(fn) {
      if (typeof fn === 'function') chatStateReqListeners.push(fn);
    }
  };
})();

