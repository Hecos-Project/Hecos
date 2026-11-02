/**
 * search_main.js
 * Main orchestrator and controller for Hecos Deep Search page.
 * Wires together SearchFilters, SearchStream, SearchHistory, and SearchModals.
 */
function initSearchMain() {
  const state = window.SearchState;
  const api = window.SearchAPI;
  const filters = window.SearchFilters;
  const stream = window.SearchStream;
  const history = window.SearchHistory;
  const modals = window.SearchModals;

  const searchInput = document.getElementById('search-input');
  const searchBtn = document.getElementById('search-submit');
  const modePills = document.querySelectorAll('.mode-pill');

  // ── Sync Tor Config from Server ───────────────────────────────────────────
  if (api && api.getConfig) {
    api.getConfig().then(data => {
      if (data && data.ok && data.config) {
        const tor = data.config.tor || {};
        window.currentTorAction = tor.onion_action || 'hecos_viewer';
        window.torBrowserPath = tor.tor_browser_path || '';
      }
    }).catch(() => { });
  }

  // ── Mode Switcher & Subtabs Initialization ────────────────────────────────
  const activeInitialPill = document.querySelector('.mode-pill.active');
  if (activeInitialPill && activeInitialPill.dataset.mode) {
    state.currentMode = activeInitialPill.dataset.mode;
  }
  const activeInitialFilter = document.querySelector('.filter-tab.active');
  if (activeInitialFilter && activeInitialFilter.dataset.filter) {
    state.activeFilter = activeInitialFilter.dataset.filter;
  }

  // Ensure contextual tabs match initial mode
  if (filters && filters.renderFilterTabsForMode) {
    filters.renderFilterTabsForMode(state.currentMode, true);
  }

  modePills.forEach(pill => {
    pill.addEventListener('click', () => {
      modePills.forEach(p => p.classList.remove('active'));
      pill.classList.add('active');
      state.currentMode = pill.dataset.mode;

      // Auto-switch contextual filter tabs for the selected mode
      if (filters && filters.renderFilterTabsForMode) {
        filters.renderFilterTabsForMode(state.currentMode, false);
      }

      if (state.currentQuery && stream && stream.executeSearch) {
        stream.executeSearch(state.currentQuery, state.currentMode);
      }
    });
  });

  // ── Form Submit ────────────────────────────────────────────────────────────
  if (searchBtn && searchInput) {
    searchBtn.addEventListener('click', () => {
      if (stream && stream.executeSearch) {
        stream.executeSearch(searchInput.value, state.currentMode);
      }
    });

    searchInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        if (stream && stream.executeSearch) {
          stream.executeSearch(searchInput.value, state.currentMode);
        }
      }
    });
  }

  // ── Global Keyboard Shortcuts ──────────────────────────────────────────────
  window.addEventListener('keydown', (e) => {
    if ((e.ctrlKey && e.key === 'k') || (e.key === '/' && document.activeElement !== searchInput)) {
      if (searchInput) {
        e.preventDefault();
        searchInput.focus();
        searchInput.select();
      }
    }
    if (e.key === 'Escape') {
      if (modals && modals.closeAllModals) {
        modals.closeAllModals();
      }
    }
  });

  // ── Initial Subsystems Boot ────────────────────────────────────────────────
  if (filters) {
    filters.updateViewModeButtons();
    filters.initInfiniteScroll();
  }
  if (history && history.loadHistory) {
    history.loadHistory();
  }
  if (modals && modals.refreshTorStatus) {
    modals.refreshTorStatus();
  }

  // Load initial settings (e.g. privacy shield local_only default)
  fetch('/api/hsearch/config').then(r => r.json()).then(data => {
    if (data && data.ok && data.config) {
      if (data.config.local_only && filters && filters.toggleLocalOnly) {
        filters.toggleLocalOnly(true);
      }
    }
  }).catch(() => { });

  // If query passed in URL parameter on load
  const urlParams = new URLSearchParams(window.location.search);
  const qParam = urlParams.get('q');
  let modeParam = urlParams.get('mode');
  if (modeParam === 'media') modeParam = 'clear'; // Graceful backward-compat mapping
  if (qParam && searchInput) {
    searchInput.value = qParam;
    if (modeParam) {
      modePills.forEach(p => p.classList.toggle('active', p.dataset.mode === modeParam));
      state.currentMode = modeParam;
      if (filters && filters.renderFilterTabsForMode) {
        filters.renderFilterTabsForMode(state.currentMode, false);
      }
    }
    if (stream && stream.executeSearch) {
      stream.executeSearch(qParam, modeParam || 'clear');
    }
  }
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initSearchMain);
} else {
  initSearchMain();
}
