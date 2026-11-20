/**
 * chat_search/cs_api.js
 * REST client for /api/chat/search with automatic AbortController cancellation.
 */
(function (global) {
    'use strict';

    let _activeController = null;

    async function fetchChatSearch(params) {
        if (_activeController) {
            try { _activeController.abort(); } catch (_) {}
            _activeController = null;
        }
        const controller = new AbortController();
        _activeController = controller;

        const qs = new URLSearchParams();
        if (params.q) qs.set('q', params.q);
        if (params.scope) qs.set('scope', params.scope);
        if (params.sessionId) qs.set('session_id', params.sessionId);
        qs.set('archived', params.archived ? '1' : '0');
        if (params.role && params.role !== 'all') qs.set('role', params.role);
        if (params.date && params.date !== 'all') qs.set('date', params.date);
        if (params.limit) qs.set('limit', String(params.limit));

        const resp = await fetch(`/api/chat/search?${qs.toString()}`, {
            method: 'GET',
            cache: 'no-store',
            signal: controller.signal,
        });
        const data = await resp.json();
        if (_activeController === controller) {
            _activeController = null;
        }
        return data;
    }

    function abortPendingSearch() {
        if (_activeController) {
            try { _activeController.abort(); } catch (_) {}
            _activeController = null;
        }
    }

    global._hecosChatSearchApi = {
        fetchChatSearch,
        abortPendingSearch,
    };

})(window);
