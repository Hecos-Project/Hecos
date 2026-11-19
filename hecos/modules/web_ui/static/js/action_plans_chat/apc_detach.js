/**
 * MODULE: action_plans_chat/apc_detach.js
 * PURPOSE: Detachable Action Plan support — both in-page draggable Floating Dock
 *          and external Pop-out Window / New Tab synchronized live via BroadcastChannel.
 */

(function () {
  const ns = (window._HecosActionPlanChat = window._HecosActionPlanChat || {});
  const CHANNEL_NAME = 'hecos_action_plan_sync';
  const UI_STATE_KEY = 'hecos_action_plan_ui_state';
  const FLOAT_HOST_ID = 'ap-floating-host';
  const MIN_FLOAT_W = 380;
  const DEFAULT_FLOAT_W = 620;
  const MIN_STEPS_H = 48;

  let _mode = 'docked'; // 'docked' | 'floating' | 'popout'
  let _channel = null;
  let _popoutWin = null;
  let _popoutWatchTimer = null;
  let _lastViewerHeartbeat = 0;
  let _viewerPlanId = '';
  let _viewerSid = '';
  let _callbacks = {};
  let _initialized = false;
  let _floatRect = null; // { x, y, w }

  function _tr(key, fallbackEn) {
    const val = (window.I18N && window.I18N[key]) || (typeof window.t === 'function' ? window.t(key) : '');
    return (val && val !== key) ? val : fallbackEn;
  }

  function _readStorageState() {
    try {
      return JSON.parse(localStorage.getItem(UI_STATE_KEY) || '{}') || {};
    } catch (_) {
      return {};
    }
  }

  function _saveFloatRectIfPersisted(rect) {
    if (!rect) return;
    const st = _readStorageState();
    if (!st.save) return;
    st.floatRect = {
      x: Math.round(rect.x),
      y: Math.round(rect.y),
      w: Math.round(rect.w),
    };
    try {
      localStorage.setItem(UI_STATE_KEY, JSON.stringify(st));
    } catch (_) {}
  }

  function _clampFloatRect(rect) {
    const vw = Number(window.innerWidth) || 1280;
    const vh = Number(window.innerHeight) || 800;
    const maxW = Math.max(MIN_FLOAT_W, Math.min(980, vw - 24));
    const w = Math.max(MIN_FLOAT_W, Math.min(maxW, Math.round(Number(rect?.w) || DEFAULT_FLOAT_W)));
    const defaultX = Math.max(12, vw - w - 24);
    const defaultY = 64;
    const rawX = Number.isFinite(Number(rect?.x)) ? Number(rect.x) : defaultX;
    const rawY = Number.isFinite(Number(rect?.y)) ? Number(rect.y) : defaultY;
    const x = Math.max(8, Math.min(vw - Math.min(w, 220) - 8, Math.round(rawX)));
    const y = Math.max(8, Math.min(vh - 72, Math.round(rawY)));
    return { x, y, w };
  }

  function _resolveFloatRect() {
    if (_floatRect) {
      _floatRect = _clampFloatRect(_floatRect);
      return _floatRect;
    }
    const st = _readStorageState();
    if (st.save && st.floatRect && typeof st.floatRect === 'object') {
      _floatRect = _clampFloatRect(st.floatRect);
    } else {
      _floatRect = _clampFloatRect(null);
    }
    return _floatRect;
  }

  function _post(msg) {
    if (!_channel) return;
    try {
      _channel.postMessage(msg);
    } catch (_) {}
  }

  function _stopPopoutWatch() {
    if (_popoutWatchTimer) {
      clearInterval(_popoutWatchTimer);
      _popoutWatchTimer = null;
    }
  }

  function _startPopoutWatch() {
    _stopPopoutWatch();
    _popoutWatchTimer = setInterval(() => {
      if (_mode !== 'popout') {
        _stopPopoutWatch();
        return;
      }
      if (_popoutWin && _popoutWin.closed) {
        _popoutWin = null;
        _setMode('docked');
        return;
      }
      // If opened as an external tab without window reference, auto-dock if heartbeats stop (> 9s)
      if (!_popoutWin && _lastViewerHeartbeat > 0 && (Date.now() - _lastViewerHeartbeat) > 9500) {
        _lastViewerHeartbeat = 0;
        _setMode('docked');
      }
    }, 800);
  }

  function removeFloatingHost() {
    const existing = document.getElementById(FLOAT_HOST_ID);
    if (existing) existing.remove();
  }

  function ensureFloatingHost() {
    let host = document.getElementById(FLOAT_HOST_ID);
    const rect = _resolveFloatRect();
    if (!host) {
      host = document.createElement('div');
      host.id = FLOAT_HOST_ID;
      host.className = 'ap-floating-host';
      document.body.appendChild(host);
    }
    host.style.left = `${rect.x}px`;
    host.style.top = `${rect.y}px`;
    host.style.width = `${rect.w}px`;
    return host;
  }

  function _setMode(nextMode) {
    const valid = ['docked', 'floating', 'popout'].includes(nextMode) ? nextMode : 'docked';
    if (valid !== 'floating') {
      removeFloatingHost();
    }
    if (valid !== 'popout') {
      _stopPopoutWatch();
    }
    const changed = _mode !== valid;
    _mode = valid;
    if (changed && typeof _callbacks.onModeChanged === 'function') {
      _callbacks.onModeChanged(_mode);
    }
  }

  function setFloating() {
    if (_mode === 'popout') {
      _post({ type: 'dock_close', planId: _viewerPlanId });
      if (_popoutWin && !_popoutWin.closed) {
        try { _popoutWin.close(); } catch (_) {}
      }
      _popoutWin = null;
    }
    _setMode('floating');
    // Force re-render even if already floating
    if (typeof _callbacks.onModeChanged === 'function') {
      _callbacks.onModeChanged('floating');
    }
  }

  function openPopout(plan, sid, opts = {}) {
    const planId = String(plan?.plan_id || '').trim();
    const sessionId = String(sid || plan?.source_id || '').trim();
    _viewerPlanId = planId;
    _viewerSid = sessionId;

    if (_popoutWin && !_popoutWin.closed && !opts.asTab) {
      try { _popoutWin.focus(); } catch (_) {}
      _setMode('popout');
      _pushLatestStateToViewer();
      return true;
    }

    const qs = new URLSearchParams();
    if (planId) qs.set('plan_id', planId);
    if (sessionId) qs.set('sid', sessionId);
    const url = `/action-plan-viewer${qs.toString() ? '?' + qs.toString() : ''}`;

    let win = null;
    try {
      if (opts.asTab) {
        win = window.open(url, '_blank');
      } else {
        const w = Math.min(1080, Math.max(880, Math.round((window.screen?.availWidth || 1280) * 0.68)));
        const h = Math.min(840, Math.max(620, Math.round((window.screen?.availHeight || 900) * 0.78)));
        const left = Math.max(40, Math.round(((window.screen?.availWidth || 1280) - w) / 2));
        const top = Math.max(40, Math.round(((window.screen?.availHeight || 900) - h) / 2));
        win = window.open(
          url,
          'HecosActionPlanViewer',
          `width=${w},height=${h},left=${left},top=${top},resizable=yes,scrollbars=yes`
        );
      }
    } catch (_) {
      win = null;
    }

    if (!win) {
      if (typeof window.showToast === 'function') {
        window.showToast(_tr('ap_viewer_popup_blocked', 'Popup blocked by browser — allow popups or use Float mode.'));
      }
      return false;
    }

    _popoutWin = win;
    _lastViewerHeartbeat = Date.now();
    _setMode('popout');
    _startPopoutWatch();
    try { win.focus(); } catch (_) {}
    setTimeout(_pushLatestStateToViewer, 250);
    setTimeout(_pushLatestStateToViewer, 900);
    return true;
  }

  function focusDetached() {
    if (_mode === 'floating') {
      const host = document.getElementById(FLOAT_HOST_ID);
      if (host) {
        const rect = _clampFloatRect(_resolveFloatRect());
        _floatRect = rect;
        host.style.left = `${rect.x}px`;
        host.style.top = `${rect.y}px`;
        host.style.width = `${rect.w}px`;
        host.classList.remove('is-focus-pulse');
        void host.offsetWidth;
        host.classList.add('is-focus-pulse');
        setTimeout(() => host.classList.remove('is-focus-pulse'), 750);
      }
      return;
    }
    if (_mode === 'popout') {
      if (_popoutWin && !_popoutWin.closed) {
        try { _popoutWin.focus(); } catch (_) {}
      }
      _post({ type: 'focus_viewer', planId: _viewerPlanId });
    }
  }

  function dockBack(opts = {}) {
    const closePopout = opts.closePopout !== false;
    if (_mode === 'popout' && closePopout) {
      _post({ type: 'dock_close', planId: _viewerPlanId });
      if (_popoutWin && !_popoutWin.closed) {
        try { _popoutWin.close(); } catch (_) {}
      }
    }
    _popoutWin = null;
    _lastViewerHeartbeat = 0;
    _setMode('docked');
  }

  function attachFloatingInteractions(host, card, stepsEl, onHeightChanged) {
    if (!host || !card) return;
    const header = card.querySelector('.agent-plan-header');
    if (header) {
      header.addEventListener('pointerdown', (e) => {
        if (e.button !== undefined && e.button !== 0) return;
        if (
          e.target.closest('button') ||
          e.target.closest('input') ||
          e.target.closest('select') ||
          e.target.closest('label') ||
          e.target.closest('.ap-header-size-controls')
        ) return;

        e.preventDefault();
        const startX = e.clientX;
        const startY = e.clientY;
        const rect = host.getBoundingClientRect();
        const origLeft = rect.left;
        const origTop = rect.top;
        const origW = rect.width;
        let moved = false;

        host.classList.add('is-dragging');
        const prevUserSelect = document.body.style.userSelect;
        const prevCursor = document.body.style.cursor;
        document.body.style.userSelect = 'none';
        document.body.style.cursor = 'grabbing';

        const onMove = (ev) => {
          const dx = ev.clientX - startX;
          const dy = ev.clientY - startY;
          if (!moved && (Math.abs(dx) > 4 || Math.abs(dy) > 4)) {
            moved = true;
          }
          const next = _clampFloatRect({ x: origLeft + dx, y: origTop + dy, w: origW });
          _floatRect = next;
          host.style.left = `${next.x}px`;
          host.style.top = `${next.y}px`;
        };

        const onUp = () => {
          document.removeEventListener('pointermove', onMove);
          document.removeEventListener('pointerup', onUp);
          document.removeEventListener('pointercancel', onUp);
          host.classList.remove('is-dragging');
          document.body.style.userSelect = prevUserSelect;
          document.body.style.cursor = prevCursor;
          if (moved) {
            host.dataset.justDragged = '1';
            setTimeout(() => { delete host.dataset.justDragged; }, 80);
            _saveFloatRectIfPersisted(_floatRect);
          }
        };

        document.addEventListener('pointermove', onMove);
        document.addEventListener('pointerup', onUp);
        document.addEventListener('pointercancel', onUp);
      });
    }

    const cornerHandle = card.querySelector('#ap-float-corner-resize');
    if (cornerHandle) {
      cornerHandle.addEventListener('pointerdown', (e) => {
        if (e.button !== undefined && e.button !== 0) return;
        e.preventDefault();
        e.stopPropagation();

        const startX = e.clientX;
        const startY = e.clientY;
        const rect = host.getBoundingClientRect();
        const startW = Math.round(rect.width);
        const startH = stepsEl ? Math.round(stepsEl.getBoundingClientRect().height || stepsEl.offsetHeight || 160) : 160;
        const maxH = Math.max(260, Math.round((Number(window.innerHeight) || 900) * 0.72));

        host.classList.add('is-resizing');
        card.classList.add('is-resizing');
        const prevUserSelect = document.body.style.userSelect;
        const prevCursor = document.body.style.cursor;
        document.body.style.userSelect = 'none';
        document.body.style.cursor = 'nwse-resize';

        let lastH = startH;
        const onMove = (ev) => {
          const nextRect = _clampFloatRect({
            x: rect.left,
            y: rect.top,
            w: startW + (ev.clientX - startX),
          });
          _floatRect = nextRect;
          host.style.width = `${nextRect.w}px`;

          if (stepsEl) {
            lastH = Math.max(MIN_STEPS_H, Math.min(maxH, Math.round(startH + (ev.clientY - startY))));
            stepsEl.classList.add('is-sized');
            stepsEl.style.height = `${lastH}px`;
            if (typeof onHeightChanged === 'function') {
              onHeightChanged(lastH, false);
            }
          }
        };

        const onUp = () => {
          document.removeEventListener('pointermove', onMove);
          document.removeEventListener('pointerup', onUp);
          document.removeEventListener('pointercancel', onUp);
          host.classList.remove('is-resizing');
          card.classList.remove('is-resizing');
          document.body.style.userSelect = prevUserSelect;
          document.body.style.cursor = prevCursor;
          if (typeof onHeightChanged === 'function') {
            onHeightChanged(lastH, true);
          }
          _saveFloatRectIfPersisted(_floatRect);
        };

        document.addEventListener('pointermove', onMove);
        document.addEventListener('pointerup', onUp);
        document.addEventListener('pointercancel', onUp);
      });
    }
  }

  function _pushLatestStateToViewer() {
    if (typeof _callbacks.onRequestState !== 'function') return;
    const state = _callbacks.onRequestState();
    if (!state) return;
    broadcastPlanUpdate(state);
  }

  function broadcastPlanUpdate(state) {
    if (!state) return;
    _viewerPlanId = String(state.plan?.plan_id || _viewerPlanId || '');
    _viewerSid = String(state.sessionId || state.plan?.source_id || _viewerSid || '');
    _post({
      type: 'plan_update',
      plan: state.plan || null,
      sessionId: _viewerSid,
      isStreaming: Boolean(state.isStreaming),
      presets: Array.isArray(state.presets) ? state.presets : [],
      activeSoulId: String(state.activeSoulId || ''),
      launchingPlanId: String(state.launchingPlanId || ''),
      launchingMode: String(state.launchingMode || 'execute'),
      ts: Date.now(),
    });
  }

  function broadcastCleared(sid) {
    if (_mode === 'floating') {
      removeFloatingHost();
      _mode = 'docked';
    }
    _post({
      type: 'plan_cleared',
      sessionId: String(sid || _viewerSid || ''),
      ts: Date.now(),
    });
  }

  function saveCurrentFloatRect() {
    if (_floatRect) {
      _saveFloatRectIfPersisted(_floatRect);
    }
  }

  function _handleChannelMessage(ev) {
    const msg = ev?.data;
    if (!msg || typeof msg !== 'object') return;

    switch (msg.type) {
      case 'viewer_hello': {
        _lastViewerHeartbeat = Date.now();
        if (msg.planId) _viewerPlanId = String(msg.planId);
        if (msg.sessionId) _viewerSid = String(msg.sessionId);
        if (_mode !== 'popout') {
          _setMode('popout');
          _startPopoutWatch();
        }
        _pushLatestStateToViewer();
        break;
      }
      case 'viewer_heartbeat': {
        _lastViewerHeartbeat = Date.now();
        if (_mode !== 'popout') {
          const state = typeof _callbacks.onRequestState === 'function' ? _callbacks.onRequestState() : null;
          const activePlanId = String(state?.plan?.plan_id || '');
          const activeSid = String(state?.sessionId || '');
          if (
            (msg.planId && activePlanId && msg.planId === activePlanId) ||
            (msg.sessionId && activeSid && msg.sessionId === activeSid)
          ) {
            _setMode('popout');
            _startPopoutWatch();
          }
        }
        break;
      }
      case 'viewer_closed': {
        _popoutWin = null;
        _lastViewerHeartbeat = 0;
        if (_mode === 'popout') {
          _setMode('docked');
        }
        break;
      }
      case 'request_state': {
        _pushLatestStateToViewer();
        break;
      }
      case 'action_execute': {
        if (typeof _callbacks.onRemoteExecute === 'function') {
          _callbacks.onRemoteExecute(msg);
        }
        break;
      }
      case 'action_revise': {
        if (typeof _callbacks.onRemoteRevise === 'function') {
          _callbacks.onRemoteRevise(msg);
        }
        break;
      }
      case 'action_reject': {
        if (typeof _callbacks.onRemoteReject === 'function') {
          _callbacks.onRemoteReject(msg);
        }
        break;
      }
      case 'action_select_preset': {
        if (typeof _callbacks.onRemoteSelectPreset === 'function') {
          _callbacks.onRemoteSelectPreset(msg);
        }
        break;
      }
      case 'action_manual_saved': {
        if (typeof _callbacks.onRemoteManualSaved === 'function') {
          _callbacks.onRemoteManualSaved(msg);
        }
        break;
      }
      case 'action_imported': {
        if (typeof _callbacks.onRemoteImported === 'function') {
          _callbacks.onRemoteImported(msg);
        }
        break;
      }
      case 'action_next_step': {
        if (typeof _callbacks.onRemoteNextStep === 'function') {
          _callbacks.onRemoteNextStep(msg);
        }
        break;
      }
      case 'action_step_toggled': {
        if (typeof _callbacks.onRemoteStepToggled === 'function') {
          _callbacks.onRemoteStepToggled(msg);
        }
        break;
      }
      default:
        break;
    }
  }

  function init(callbacks) {
    _callbacks = { ..._callbacks, ...(callbacks || {}) };
    if (_initialized) return;
    _initialized = true;

    if (typeof BroadcastChannel !== 'undefined') {
      try {
        _channel = new BroadcastChannel(CHANNEL_NAME);
        _channel.addEventListener('message', _handleChannelMessage);
      } catch (_) {
        _channel = null;
      }
    }

    window.addEventListener('resize', () => {
      if (_mode !== 'floating') return;
      const host = document.getElementById(FLOAT_HOST_ID);
      if (!host) return;
      const clamped = _clampFloatRect(_resolveFloatRect());
      _floatRect = clamped;
      host.style.left = `${clamped.x}px`;
      host.style.top = `${clamped.y}px`;
      host.style.width = `${clamped.w}px`;
    });
  }

  ns.detach = {
    init,
    getMode: () => _mode,
    setFloating,
    openPopout,
    focusDetached,
    dockBack,
    ensureFloatingHost,
    removeFloatingHost,
    attachFloatingInteractions,
    broadcastPlanUpdate,
    broadcastCleared,
    saveCurrentFloatRect,
  };
})();
