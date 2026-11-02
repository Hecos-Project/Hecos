/**
 * search_state.js
 * Central state store for Deep Search UI.
 */
window.SearchState = {
  currentQuery: '',
  currentMode: 'clear',
  activeSessionId: null,
  get currentSessionId() { return this.activeSessionId; },
  set currentSessionId(v) { this.activeSessionId = v; },
  activeSession: null,
  results: [],
  runningEngines: new Set(),
  activeEventSource: null,
  torOnline: false,
  torIp: '',
  torPort: null,
  safeSearch: false,
  darkBypass: true,
  localOnly: false,
  searchLimit: (function () {
    try {
      const v = typeof localStorage !== 'undefined' && localStorage.getItem('hecos_netsearch_depth');
      const n = parseInt(v);
      return (!isNaN(n) && n >= 0) ? n : 250;
    } catch (e) {
      return 250;
    }
  })(),
  activeFilter: 'all', // all, images, videos, audio, files, dark, osint
  activeEngine: null,
  activeProvider: null,
  isStreamCollapsed: (function () {
    try {
      if (typeof localStorage === 'undefined') return true;
      const saved = localStorage.getItem('hecos_stream_collapsed');
      if (saved === null) return true; // Default: compresso
      return saved === 'true';
    } catch (e) {
      return true;
    }
  })(),
  engineStats: {},
  providerStats: {},
  excludedProviders: [],  // Provider IDs excluded by user (-youtube, etc.)
  viewMode: (function () {
    try {
      return (typeof localStorage !== 'undefined' && localStorage.getItem('hecos_search_view_mode')) || 'scroll';
    } catch (e) {
      return 'scroll';
    }
  })(), // 'scroll' | 'paging'
  currentPage: 1,
  pageSize: 25,
  scrollRenderCount: 40,
  backendPage: 1,
  isFetchingMore: false,
  autoFetchMore: (function () {
    try {
      if (typeof localStorage === 'undefined') return true;
      return localStorage.getItem('hecos_netsearch_autofetch') !== 'false';
    } catch (e) {
      return true;
    }
  })(),

  resetResults() {
    this.results = [];
    this.runningEngines.clear();
    this.engineStats = {};
    this.providerStats = {};
    this.activeEngine = null;
    this.activeProvider = null;
    this.excludedProviders = [];  // Reset exclusions on each new search
    this.currentPage = 1;
    this.scrollRenderCount = 40;
    this.backendPage = 1;
    this.isFetchingMore = false;
    if (this.activeEventSource) {
      this.activeEventSource.close();
      this.activeEventSource = null;
    }
  },

  addResults(newItems, engineId = null) {
    const seen = new Map();
    this.results.forEach(r => { if (r.url) seen.set(r.url, r); });
    for (const item of newItems) {
      if (engineId && !item.engine_id) {
        item.engine_id = engineId;
      }
      if (item.url && seen.has(item.url)) {
        // Record engine attribution in metadata if duplicate
        const existing = seen.get(item.url);
        if (engineId) {
          existing.metadata = existing.metadata || {};
          existing.metadata.engine_ids = existing.metadata.engine_ids || [existing.engine_id || ''];
          if (!existing.metadata.engine_ids.includes(engineId)) {
            existing.metadata.engine_ids.push(engineId);
          }
        }
      } else {
        if (engineId) {
          item.metadata = item.metadata || {};
          item.metadata.engine_ids = item.metadata.engine_ids || [engineId];
        }
        this.results.push(item);
        if (item.url) seen.set(item.url, item);
      }
    }
  }
};
