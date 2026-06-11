/**
 * config_routing_logic.js
 * Orchestrator Layer for Hecos Routing Overrides Pro Panel
 */

window.routingLogic = {
    /**
     * Initializes the routing panel: fetches data and renders cards.
     */
    async initRoutingPanel() {
        if (!window.routingData || !window.routingRender) {
            console.warn("[RoutingLogic] Missing dependencies (Data or Render layer).");
            return;
        }

        try {
            await window.routingData.loadAll();
            window.routingRender.renderAllCards();
        } catch (e) {
            console.error("[RoutingLogic] Initialization error:", e);
        }
    }
};

// Hook into the main initAll
const originalInitAll = window.initAll;
window.initAll = async function() {
    if (originalInitAll) await originalInitAll();
    await window.routingLogic.initRoutingPanel();
};
