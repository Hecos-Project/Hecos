/**
 * search_api.js
 * API communication layer for Hecos Deep Search.
 */
window.SearchAPI = (function () {
  const BASE_URL = '/api/hsearch';

  async function postJson(endpoint, data) {
    const res = await fetch(`${BASE_URL}${endpoint}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    return await res.json();
  }

  async function getJson(endpoint) {
    const res = await fetch(`${BASE_URL}${endpoint}`);
    return await res.json();
  }

  return {
    // ── Search & Streaming ───────────────────────────────────────────────────
    queryStream(params, onEvent, onComplete, onError) {
      const qs = new URLSearchParams({
        q: params.query,
        mode: params.mode || 'clear',
        limit: (params.limit !== undefined && params.limit !== null) ? params.limit : (parseInt(typeof localStorage !== 'undefined' && localStorage.getItem('hecos_netsearch_depth')) || 250),
        page: params.page || 1,
        safe_search: params.safe_search ? 'true' : 'false',
        dark_bypass: params.dark_bypass !== false ? 'true' : 'false',
        local_only: params.local_only ? 'true' : 'false',
        excluded_providers: params.excluded_providers || '',
        language: params.language || '',
        domain_filter: params.domain_filter || '',
        file_types: Array.isArray(params.file_types) ? params.file_types.join(',') : (params.file_types || ''),
        engines: Array.isArray(params.engines) ? params.engines.join(',') : (params.engines || ''),
        time_range: params.time_range || ''
      });

      const es = new EventSource(`${BASE_URL}/query_stream?${qs.toString()}`);

      es.onmessage = function (e) {
        try {
          const data = JSON.parse(e.data);
          if (data.type === 'complete') {
            es.close();
            if (onComplete) onComplete(data);
          } else if (data.type === 'error') {
            es.close();
            if (onError) onError(data.error);
          } else {
            if (onEvent) onEvent(data);
          }
        } catch (err) {
          console.error('[SearchAPI] SSE parse error:', err);
        }
      };

      es.onerror = function (err) {
        es.close();
        if (onError) onError(err);
      };

      return es;
    },

    async query(data) {
      return await postJson('/query', data);
    },

    // ── Sessions & History ───────────────────────────────────────────────────
    async getSessions(limit = 40, favorites = false) {
      return await getJson(`/sessions?limit=${limit}&favorites=${favorites}`);
    },

    async getSessionDetail(sessionId) {
      return await getJson(`/sessions/${sessionId}`);
    },

    async deleteSession(sessionId) {
      const res = await fetch(`${BASE_URL}/sessions/${sessionId}`, { method: 'DELETE' });
      return await res.json();
    },

    async clearSessions() {
      return await postJson('/sessions/clear', {});
    },

    async toggleFavorite(sessionId) {
      return await postJson(`/sessions/${sessionId}/favorite`, {});
    },

    // ── Content Reading / Extraction ─────────────────────────────────────────
    async fetchPageContent(url, maxChars = 5000) {
      return await postJson('/fetch', { url, max_chars: maxChars });
    },

    // ── Components Management ────────────────────────────────────────────────
    async getComponents() {
      return await getJson('/components');
    },

    async installComponent(id) {
      return await postJson(`/components/${id}/install`, {});
    },

    async uninstallComponent(id) {
      return await postJson(`/components/${id}/uninstall`, {});
    },

    async startComponent(id) {
      return await postJson(`/components/${id}/start`, {});
    },

    async stopComponent(id) {
      return await postJson(`/components/${id}/stop`, {});
    },

    // ── Tor Controls ─────────────────────────────────────────────────────────
    async getTorStatus() {
      return await getJson('/tor_status');
    },

    async torNewCircuit() {
      return await postJson('/tor_newnym', {});
    },

    // ── Config ───────────────────────────────────────────────────────────────
    async getConfig() {
      return await getJson('/config');
    },

    async saveConfig(data) {
      return await postJson('/config', data);
    },

    // ── Endpoints & Fallback Nodes ───────────────────────────────────────────
    async getEndpoints() {
      return await getJson('/endpoints');
    },

    async saveEndpoints(data) {
      return await postJson('/endpoints', data);
    },

    async resetEndpoints() {
      return await postJson('/endpoints/reset', {});
    },

    // ── Tor Browser Launcher ────────────────────────────────────────────────
    async openTorBrowser(url) {
      return await postJson('/open_tor_browser', { url });
    },

    async detectTorBrowser() {
      return await getJson('/detect_tor_browser');
    }
  };
})();
