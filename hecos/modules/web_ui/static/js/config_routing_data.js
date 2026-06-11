/**
 * config_routing_data.js
 * Data Layer for Hecos Routing Overrides Pro Panel
 */

window.routingData = {
    overrides: {},
    defaults: {},

    /**
     * Load current user overrides from YAML
     */
    async loadOverrides() {
        try {
            const res = await fetch('/hecos/config/routing');
            if (res.ok) {
                this.overrides = await res.json();
            } else {
                console.error("[RoutingData] Error loading overrides:", await res.text());
                this.overrides = {};
            }
        } catch (e) {
            console.error("[RoutingData] Exception loading overrides:", e);
            this.overrides = {};
        }
    },

    /**
     * Load default instructions from registry.json
     */
    async loadDefaults() {
        try {
            const res = await fetch('/hecos/config/routing/defaults');
            if (res.ok) {
                this.defaults = await res.json();
            } else {
                console.error("[RoutingData] Error loading defaults:", await res.text());
                this.defaults = {};
            }
        } catch (e) {
            console.error("[RoutingData] Exception loading defaults:", e);
            this.defaults = {};
        }
    },

    /**
     * Load both overrides and defaults in parallel
     */
    async loadAll() {
        await Promise.all([
            this.loadOverrides(),
            this.loadDefaults()
        ]);
        return {
            overrides: this.overrides,
            defaults: this.defaults
        };
    },

    /**
     * Save the current state of overrides
     */
    async saveOverrides(newOverrides) {
        try {
            const res = await fetch('/hecos/config/routing', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(newOverrides)
            });
            return res.ok;
        } catch (e) {
            console.error("[RoutingData] Exception saving overrides:", e);
            return false;
        }
    },

    /**
     * Reset all overrides to registry defaults with automatic backup
     */
    async resetAllToDefaults() {
        try {
            const res = await fetch('/hecos/config/routing/reset', { method: 'POST' });
            return res.ok;
        } catch (e) {
            console.error("[RoutingData] Exception resetting defaults:", e);
            return false;
        }
    },

    /**
     * Fetch the raw YAML string of the current overrides for backup modal
     */
    async fetchBackupText() {
        try {
            const res = await fetch('/hecos/config/routing/backup');
            if (res.ok) {
                const data = await res.json();
                return data.yaml || "";
            }
            return "";
        } catch (e) {
            console.error("[RoutingData] Exception fetching backup:", e);
            return "";
        }
    }
};
