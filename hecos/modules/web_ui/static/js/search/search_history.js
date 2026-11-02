/**
 * search_history.js
 * Session history retrieval, sidebar list rendering, real-time live synchronization,
 * and past session detail loader for Deep Search.
 */
(function() {
  const state = window.SearchState;
  const api = window.SearchAPI;

  let _lastSessionsDigest = '';
  let _isLoading = false;

  function escapeHtml(str) {
    if (!str) return '';
    return String(str).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  async function loadHistory(force = false) {
    const historyListEl = document.getElementById('history-list');
    if (!historyListEl || !api || !api.getSessions || _isLoading) return;
    
    _isLoading = true;
    try {
      const res = await api.getSessions(40);
      if (res.ok && res.sessions) {
        const digest = res.sessions.map(s => `${s.id}:${s.total_results}`).join('|');
        
        // If nothing changed in the sessions list, only update active highlight
        if (!force && digest === _lastSessionsDigest) {
          historyListEl.querySelectorAll('.history-item').forEach(el => {
            const sid = el.getAttribute('data-session-id');
            el.classList.toggle('active', sid === state.activeSessionId);
          });
          return;
        }

        const isInitial = !_lastSessionsDigest;
        _lastSessionsDigest = digest;

        const prevScrollTop = historyListEl.scrollTop;
        historyListEl.innerHTML = res.sessions.map((s, idx) => `
          <div class="history-item ${s.id === state.activeSessionId ? 'active' : ''} ${(!isInitial && idx === 0) ? 'history-item-new' : ''}" 
               data-session-id="${s.id}" 
               onclick="window.loadSession('${s.id}')">
            <div class="history-query">${escapeHtml(s.query)}</div>
            <div class="history-meta">
              <span class="history-mode-pill">${escapeHtml((s.mode || 'web').toUpperCase())}</span>
              <span>&bull;</span>
              <span>${s.total_results} res.</span>
              <span>&bull;</span>
              <span>${escapeHtml((s.created_at || '').split(' ')[1] || '')}</span>
            </div>
          </div>
        `).join('');

        historyListEl.scrollTop = prevScrollTop;
      }
    } catch (e) {
      console.error('[SearchHistory] Failed to load history:', e);
    } finally {
      _isLoading = false;
    }
  }

  async function loadSession(sessionId) {
    if (!api || !api.getSessionDetail) return;
    try {
      const res = await api.getSessionDetail(sessionId);
      if (res.ok && res.session) {
        const s = res.session;
        state.activeSessionId = s.id;
        state.currentQuery = s.query;
        state.currentMode = s.mode;
        state.results = s.results || [];
        state.activeEngine = null;

        const searchInput = document.getElementById('search-input');
        if (searchInput) searchInput.value = s.query;

        // Set active mode pill
        const modePills = document.querySelectorAll('.mode-pill');
        modePills.forEach(p => {
          p.classList.toggle('active', p.dataset.mode === s.mode);
        });

        // Rebuild persistent engine chips from saved session
        const engineCounts = {};
        state.results.forEach(r => {
          const eng = r.engine_id || r.metadata?.engine_id || r.engine || 'web';
          engineCounts[eng] = (engineCounts[eng] || 0) + 1;
        });

        const streamBar = document.getElementById('stream-live-bar');
        const streamBadges = document.getElementById('stream-badges');
        const streamStatusIcon = document.getElementById('stream-status-icon');
        const streamStatusText = document.getElementById('stream-status-text');
        const btnClearEngine = document.getElementById('btn-clear-engine-filter');

        if (streamBar) streamBar.classList.add('active');
        if (streamStatusIcon) {
          streamStatusIcon.className = 'fas fa-circle-check';
          streamStatusIcon.style.color = 'var(--accent-emerald)';
        }
        if (streamStatusText) {
          streamStatusText.innerText = 'Engines used in this session (click to filter):';
        }
        if (btnClearEngine) {
          btnClearEngine.style.display = 'none';
        }

        if (streamBadges) {
          streamBadges.innerHTML = Object.entries(engineCounts).map(([eng, count]) => `
            <button class="engine-chip done" id="chip-${eng}" data-engine="${eng}" onclick="window.filterByEngine('${eng}')" title="Filter by ${eng} (${count} results)">
              <i class="fas fa-check"></i> ${eng} <span class="chip-count">(${count})</span>
            </button>
          `).join('');
        }

        const filters = window.SearchFilters;
        const copilot = window.SearchCopilot;
        if (filters) {
          filters.updateFilterCounts();
          if (filters.renderGranularProviderChips) {
            filters.renderGranularProviderChips();
          }
          filters.renderCurrentView();
        }
        if (copilot && copilot.update) {
          copilot.update(state.results, s.query, s.mode);
        }

        document.querySelectorAll('.history-item').forEach(it => {
          it.classList.toggle('active', it.getAttribute('data-session-id') === s.id);
        });
      }
    } catch (e) {
      console.error('[SearchHistory] Load session detail error:', e);
    }
  }

  // ── Real-Time Auto-Sync Listeners ───────────────────────────────────────────
  // 1. Cross-tab BroadcastChannel (instant push when a search completes in another tab)
  if (typeof BroadcastChannel !== 'undefined') {
    try {
      const bc = new BroadcastChannel('hecos_netsearch_channel');
      bc.onmessage = function(event) {
        if (event.data && (event.data.type === 'new_session' || event.data.type === 'session_updated')) {
          loadHistory(true);
        }
      };
    } catch (e) {}
  }

  // 2. Storage event fallback (for cross-window sync)
  window.addEventListener('storage', function(e) {
    if (e.key === 'hecos_netsearch_event') {
      loadHistory(true);
    }
  });

  // 3. Tab visibility / Window Focus: refresh immediately when returning to Net Search tab
  window.addEventListener('focus', function() {
    loadHistory();
  });
  document.addEventListener('visibilitychange', function() {
    if (document.visibilityState === 'visible') {
      loadHistory();
    }
  });

  // 4. Background Poller: every 3 seconds while page is active
  setInterval(function() {
    if (document.visibilityState === 'visible') {
      loadHistory();
    }
  }, 3000);

  window.SearchHistory = {
    loadHistory,
    loadSession
  };

  // Global window alias
  window.loadHistory = loadHistory;
  window.loadSession = loadSession;
})();
