/**
 * chat_status_tracker.js
 * ─────────────────────────────────────────────────────────────────────────────
 * Tracks per-session activity ('idle' | 'running' | 'speaking' | 'stopped' | 'error')
 * across chats and browser tabs via HecosAudioBus, drives sidebar LEDs, updates
 * the browser tab title prefix, and renders the Topbar Audio Origin Pill.
 */
(function () {
  'use strict';
  if (window.HecosChatStatus) return;

  const STATUS_PRIORITY = {
    speaking: 4,
    running: 3,
    error: 2,
    stopped: 1,
    idle: 0
  };

  const VALID_STATUSES = new Set(['idle', 'running', 'speaking', 'stopped', 'error']);
  const DEFAULT_TTL_MS = 120000;
  const TRANSIENT_DECAY_MS = 4500;
  const REMOTE_AUDIO_CLAIM_TTL_MS = 65000;

  const _localStates = new Map();
  const _remoteStates = new Map();
  const _decayTimers = new Map();
  const _streamingSessions = new Set();
  const _inputBusySessions = new Set();

  let _baseTitle = (document.title || 'Hecos').replace(/^((?:🔊|⏳)\s*)+/, '');
  let _lastPillSignature = '';

  function _normalizeStatus(status) {
    return VALID_STATUSES.has(status) ? status : 'idle';
  }

  function _localTabId() {
    return (window.HecosAudioBus && window.HecosAudioBus.tabId) || window.hecosTabId || 'local';
  }

  function resolveSessionTitle(sessionId, fallback = '') {
    if (sessionId && window.chatHistoryState && Array.isArray(window.chatHistoryState.sessions)) {
      const found = window.chatHistoryState.sessions.find((s) => s && s.id === sessionId);
      if (found && found.title) return found.title;
    }
    return fallback || (sessionId ? `Chat ${String(sessionId).slice(0, 6)}` : 'Chat');
  }

  function resolvePersonaName(fallback = '') {
    const raw = fallback || window.HecosPersonaName || '';
    if (!raw) return 'Urania';
    return String(raw).replace(/\.yaml$/i, '').replace(/_/g, ' ').trim() || 'Urania';
  }

  function _clearDecayTimer(sessionId) {
    if (!sessionId) return;
    const tid = _decayTimers.get(sessionId);
    if (tid) {
      clearTimeout(tid);
      _decayTimers.delete(sessionId);
    }
  }

  function _pruneExpired(map) {
    const now = Date.now();
    for (const [k, entry] of map.entries()) {
      const ttl = entry.ttlMs || DEFAULT_TTL_MS;
      if (now - (entry.updatedAt || 0) > ttl) {
        map.delete(k);
      }
    }
  }

  function _pickHigher(a, b) {
    if (!a) return b || null;
    if (!b) return a;
    const pa = STATUS_PRIORITY[a.status] || 0;
    const pb = STATUS_PRIORITY[b.status] || 0;
    if (pa !== pb) return pb > pa ? b : a;
    return (b.updatedAt || 0) >= (a.updatedAt || 0) ? b : a;
  }

  function getSessionState(sessionId) {
    if (!sessionId) return { status: 'idle' };
    _pruneExpired(_remoteStates);
    const localEntry = _localStates.get(sessionId);
    const remoteEntry = _remoteStates.get(sessionId);
    return _pickHigher(localEntry, remoteEntry) || { status: 'idle', sessionId };
  }

  function _publishLocal(entry) {
    if (!window.HecosAudioBus || typeof window.HecosAudioBus.publishChatState !== 'function') return;
    window.HecosAudioBus.publishChatState({
      sessionId: entry.sessionId,
      sessionTitle: entry.sessionTitle || '',
      personaName: entry.personaName || '',
      status: entry.status,
      ttlMs: entry.ttlMs || DEFAULT_TTL_MS
    });
  }

  function setLocalState(sessionId, status, meta = {}) {
    const key = sessionId || '__local_voice__';
    const normStatus = _normalizeStatus(status);
    const m = (meta && typeof meta === 'object') ? meta : {};
    _clearDecayTimer(key);

    if (normStatus === 'idle') {
      const prev = _localStates.get(key);
      _localStates.delete(key);
      if (prev || sessionId) {
        _publishLocal({
          sessionId: key,
          sessionTitle: prev?.sessionTitle || m.sessionTitle || '',
          personaName: prev?.personaName || m.personaName || '',
          status: 'idle',
          ttlMs: DEFAULT_TTL_MS
        });
      }
      _refreshAllIndicators();
      return;
    }

    const entry = {
      sessionId: key,
      status: normStatus,
      sessionTitle: resolveSessionTitle(sessionId, m.sessionTitle),
      personaName: resolvePersonaName(m.personaName),
      ownerTabId: _localTabId(),
      isRemoteTab: false,
      updatedAt: Date.now(),
      ttlMs: m.ttlMs || DEFAULT_TTL_MS
    };
    _localStates.set(key, entry);
    _publishLocal(entry);

    if (normStatus === 'stopped' || normStatus === 'error') {
      const delay = m.decayMs || TRANSIENT_DECAY_MS;
      const timer = setTimeout(() => {
        _decayTimers.delete(key);
        const cur = _localStates.get(key);
        if (cur && cur.status === normStatus) {
          setLocalState(sessionId, 'idle');
        }
      }, delay);
      _decayTimers.set(key, timer);
    }

    _refreshAllIndicators();
  }

  function markStreamStart(sessionId, meta = {}) {
    if (sessionId) {
      _streamingSessions.add(sessionId);
      _inputBusySessions.add(sessionId);
    }
    setLocalState(sessionId, 'running', meta);
    syncActiveViewControls();
  }

  function markInputReady(sessionId) {
    if (sessionId) _inputBusySessions.delete(sessionId);
    syncActiveViewControls();
  }

  function markStreamEnd(sessionId, outcome = 'done', meta = {}) {
    if (sessionId) {
      _streamingSessions.delete(sessionId);
      _inputBusySessions.delete(sessionId);
    }
    if (outcome === 'error') {
      setLocalState(sessionId, 'error', { decayMs: 5000, ...meta });
    } else if (outcome === 'stopped') {
      setLocalState(sessionId, 'stopped', { decayMs: 4000, ...meta });
    } else {
      const key = sessionId || '__local_voice__';
      const cur = _localStates.get(key);
      // Do not clobber active TTS 'speaking' when text SSE closes with 'done'
      if (!cur || cur.status === 'running') {
        setLocalState(sessionId, 'idle', meta);
      } else {
        _refreshAllIndicators();
      }
    }
    syncActiveViewControls();
  }

  function isSessionStreaming(sessionId) {
    return !!(sessionId && _inputBusySessions.has(sessionId));
  }

  function syncActiveViewControls() {
    const activeSid = window.chatHistoryState?.activeSessionId || null;
    const activeStreaming = isSessionStreaming(activeSid);
    window.isStreaming = activeStreaming;
    if (window.sendBtn) window.sendBtn.disabled = activeStreaming;
    if (typeof window.updateStopAllBtn === 'function') window.updateStopAllBtn();
    _refreshAllIndicators();
  }

  function _clearSpeakingStatesLocal() {
    for (const [k, entry] of _localStates.entries()) {
      if (entry.status === 'speaking') {
        if (_streamingSessions.has(k)) {
          setLocalState(k === '__local_voice__' ? null : k, 'running', entry);
        } else {
          setLocalState(k === '__local_voice__' ? null : k, 'idle', entry);
        }
      }
    }
  }

  function _applyRemoteMessage(msg) {
    if (!msg || typeof msg !== 'object') return;
    const key = msg.sessionId || (msg.owner ? `__remote_${msg.owner}__` : null);
    if (!key) return;

    const normStatus = _normalizeStatus(msg.status);
    if (normStatus === 'idle') {
      _remoteStates.delete(key);
      _refreshAllIndicators();
      return;
    }

    _remoteStates.set(key, {
      sessionId: msg.sessionId || null,
      remoteKey: key,
      status: normStatus,
      sessionTitle: msg.sessionTitle || resolveSessionTitle(msg.sessionId, msg.owner === 'net_search' ? 'Net Search' : 'Chat'),
      personaName: msg.personaName || (msg.owner === 'net_search' ? 'Copilot' : 'Urania'),
      ownerTabId: msg.tabId || 'remote',
      isRemoteTab: true,
      updatedAt: Date.now(),
      ttlMs: msg.ttlMs || DEFAULT_TTL_MS
    });
    _refreshAllIndicators();
  }

  function noteRemoteOrBackgroundAudio(sessionId, ev = {}) {
    if (!sessionId) return;
    _remoteStates.set(sessionId, {
      sessionId,
      remoteKey: sessionId,
      status: 'speaking',
      sessionTitle: resolveSessionTitle(sessionId, ev.session_title || ''),
      personaName: resolvePersonaName(ev.persona_name || ''),
      ownerTabId: (ev && ev.tab_id) || 'backend',
      isRemoteTab: Boolean(ev && ev.tab_id && ev.tab_id !== _localTabId()),
      updatedAt: Date.now(),
      ttlMs: REMOTE_AUDIO_CLAIM_TTL_MS
    });
    _refreshAllIndicators();
  }

  function _getActiveOriginCandidate() {
    _pruneExpired(_remoteStates);
    const activeSid = window.chatHistoryState?.activeSessionId || null;
    const localTab = _localTabId();

    const candidates = [];
    for (const entry of _localStates.values()) {
      if (entry.status === 'speaking' || entry.status === 'running') {
        candidates.push(entry);
      }
    }
    for (const entry of _remoteStates.values()) {
      if (entry.status === 'speaking' || entry.status === 'running') {
        candidates.push(entry);
      }
    }
    if (!candidates.length) return null;

    // Filter to entries that originate from a different chat OR a different browser tab
    const external = candidates.filter((entry) => {
      if (entry.status === 'speaking') {
        if (entry.isRemoteTab && entry.ownerTabId !== localTab) return true;
        return !!(entry.sessionId && activeSid && entry.sessionId !== activeSid);
      }
      if (entry.status === 'running') {
        return !!(entry.sessionId && activeSid && entry.sessionId !== activeSid);
      }
      return false;
    });

    if (!external.length) return null;
    external.sort((a, b) => {
      const diff = (STATUS_PRIORITY[b.status] || 0) - (STATUS_PRIORITY[a.status] || 0);
      if (diff !== 0) return diff;
      return (b.updatedAt || 0) - (a.updatedAt || 0);
    });
    return external[0];
  }

  function stopOriginAudioOrStream(origin) {
    if (origin && origin.status === 'speaking') {
      if (typeof window.stopAudioPlayback === 'function') window.stopAudioPlayback();
      if (window.HecosAudioBus) window.HecosAudioBus.stopAll('origin_pill');
      fetch('/api/audio/speaking/stop', { method: 'POST' }).catch(() => {});
      fetch('/api/audio/stop', { method: 'POST' }).catch(() => {});
      _clearSpeakingStatesLocal();
      for (const [k, entry] of _remoteStates.entries()) {
        if (entry.status === 'speaking') _remoteStates.delete(k);
      }
      _refreshAllIndicators();
      return;
    }
    if (origin && origin.status === 'running') {
      fetch('/api/system/stop', { method: 'POST' }).catch(() => {});
      if (origin.sessionId && !origin.isRemoteTab) {
        markStreamEnd(origin.sessionId, 'stopped');
      }
    }
  }

  function _updateDocumentTitle() {
    const cleanCurrent = (document.title || '').replace(/^((?:🔊|⏳)\s*)+/, '');
    if (cleanCurrent && cleanCurrent !== _baseTitle) {
      _baseTitle = cleanCurrent;
    }

    let hasSpeaking = false;
    let hasRunning = false;
    for (const entry of _localStates.values()) {
      if (entry.status === 'speaking') hasSpeaking = true;
      else if (entry.status === 'running') hasRunning = true;
    }

    const prefix = hasSpeaking ? '🔊 ' : (hasRunning ? '⏳ ' : '');
    const desired = prefix + _baseTitle;
    if (document.title !== desired) {
      document.title = desired;
    }
  }

  function _renderOriginPill() {
    const pill = document.getElementById('topbar-audio-origin-pill');
    if (!pill) return;

    const origin = _getActiveOriginCandidate();
    if (!origin) {
      if (_lastPillSignature !== 'hidden') {
        pill.style.display = 'none';
        pill.innerHTML = '';
        _lastPillSignature = 'hidden';
      }
      return;
    }

    const title = origin.sessionId
      ? resolveSessionTitle(origin.sessionId, origin.sessionTitle)
      : (origin.sessionTitle || 'Altra scheda');
    const persona = origin.personaName || 'Urania';
    const sig = `${origin.status}|${origin.sessionId || ''}|${title}|${persona}|${origin.ownerTabId || ''}`;
    if (sig === _lastPillSignature && pill.style.display !== 'none') return;
    _lastPillSignature = sig;

    pill.innerHTML = '';
    pill.style.display = 'inline-flex';
    pill.dataset.status = origin.status;
    pill.dataset.originSessionId = origin.sessionId || '';

    const dot = document.createElement('span');
    dot.className = `chat-status-led is-${origin.status}`;
    pill.appendChild(dot);

    const label = document.createElement('span');
    label.className = 'topbar-audio-origin-text';
    if (origin.status === 'speaking') {
      label.textContent = `🔊 ${persona} · ${title}`;
      pill.title = `${persona} sta parlando in "${title}"`;
    } else {
      label.textContent = `⏳ ${title}`;
      pill.title = `Elaborazione in corso in "${title}"`;
    }
    pill.appendChild(label);

    if (origin.sessionId && typeof window.activateChatSession === 'function') {
      const goBtn = document.createElement('button');
      goBtn.type = 'button';
      goBtn.className = 'topbar-audio-origin-btn is-go';
      goBtn.textContent = 'Vai';
      goBtn.title = `Passa alla chat "${title}"`;
      goBtn.onclick = (e) => {
        e.stopPropagation();
        window.activateChatSession(origin.sessionId);
      };
      pill.appendChild(goBtn);
    }

    const stopBtn = document.createElement('button');
    stopBtn.type = 'button';
    stopBtn.className = 'topbar-audio-origin-btn is-stop';
    stopBtn.textContent = 'Stop';
    stopBtn.title = origin.status === 'speaking' ? 'Ferma voce' : 'Interrompi generazione';
    stopBtn.onclick = (e) => {
      e.stopPropagation();
      stopOriginAudioOrStream(origin);
    };
    pill.appendChild(stopBtn);
  }

  function _refreshAllIndicators() {
    _updateDocumentTitle();
    _renderOriginPill();
    if (typeof window.updateChatSessionLeds === 'function') {
      window.updateChatSessionLeds();
    }
  }

  function _reBroadcastLocalStates() {
    for (const entry of _localStates.values()) {
      if (entry.status === 'running' || entry.status === 'speaking') {
        entry.updatedAt = Date.now();
        _publishLocal(entry);
      }
    }
  }

  if (window.HecosAudioBus) {
    if (typeof window.HecosAudioBus.onChatState === 'function') {
      window.HecosAudioBus.onChatState((msg) => {
        _applyRemoteMessage(msg);
      });
    }
    if (typeof window.HecosAudioBus.onClaim === 'function') {
      window.HecosAudioBus.onClaim((msg) => {
        // Clear any remote stale speaking entry before recording the new speaker claim
        for (const [k, entry] of _remoteStates.entries()) {
          if (entry.status === 'speaking' && entry.ownerTabId !== msg.tabId) {
            _remoteStates.delete(k);
          }
        }
        _applyRemoteMessage({
          ...msg,
          status: 'speaking',
          ttlMs: REMOTE_AUDIO_CLAIM_TTL_MS
        });
      });
    }
    if (typeof window.HecosAudioBus.onStopAll === 'function') {
      window.HecosAudioBus.onStopAll(() => {
        for (const [k, entry] of _remoteStates.entries()) {
          if (entry.status === 'speaking') _remoteStates.delete(k);
        }
        _clearSpeakingStatesLocal();
        _refreshAllIndicators();
      });
    }
    if (typeof window.HecosAudioBus.onChatStateRequest === 'function') {
      window.HecosAudioBus.onChatStateRequest(() => {
        _reBroadcastLocalStates();
      });
    }
    if (typeof window.HecosAudioBus.requestChatStates === 'function') {
      setTimeout(() => window.HecosAudioBus.requestChatStates(), 50);
    }
  }

  function _clearOwnedOnUnload() {
    for (const [k, entry] of _localStates.entries()) {
      _publishLocal({ ...entry, sessionId: k, status: 'idle' });
    }
    _localStates.clear();
  }

  window.addEventListener('beforeunload', _clearOwnedOnUnload);
  window.addEventListener('pagehide', _clearOwnedOnUnload);

  function _startTrackerInterval() {
    if (!window._hecosStatusTicker) {
      window._hecosStatusTicker = setInterval(() => {
        _reBroadcastLocalStates();
        _refreshAllIndicators();
      }, 15000);
    }
    _refreshAllIndicators();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', _startTrackerInterval);
  } else {
    _startTrackerInterval();
  }

  window.HecosChatStatus = {
    setLocalState,
    markStreamStart,
    markInputReady,
    markStreamEnd,
    clearSpeakingLocal: _clearSpeakingStatesLocal,
    isSessionStreaming,
    syncActiveViewControls,
    getSessionState,
    noteRemoteOrBackgroundAudio,
    stopOriginAudioOrStream,
    resolveSessionTitle,
    resolvePersonaName,
    refresh: _refreshAllIndicators
  };
})();
