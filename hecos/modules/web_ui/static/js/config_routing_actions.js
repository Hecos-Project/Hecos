/**
 * config_routing_actions.js
 * Actions and Event Handlers Layer for Hecos Routing Overrides Pro Panel
 */

window.routingActions = {
    /**
     * Triggered when a textarea content changes
     */
    onOverrideChange(tag, newText) {
        if (!window.routingData.overrides) {
            window.routingData.overrides = {};
        }
        
        // If it perfectly matches default, we might consider removing it, 
        // but it's safer to just let the user save it as-is, or hit Reset.
        // For now, we always record it as an override if they typed.
        window.routingData.overrides[tag] = newText;
        window.routingRender.updateCardBadge(tag);
    },

    /**
     * Reset a single plugin's override back to default
     */
    onResetSinglePlugin(tag) {
        if (!window.routingData.overrides) return;
        
        const defaults = window.routingData.defaults || {};
        const defaultText = defaults[tag] || '';

        // Remove from overrides
        delete window.routingData.overrides[tag];

        // Reset textarea visual
        const textarea = document.getElementById(`routing-input-${tag}`);
        if (textarea) {
            textarea.value = defaultText;
        }

        // Reset badge
        window.routingRender.updateCardBadge(tag);
        
        // Non salviamo automaticamente, l'utente deve premere Salva
    },

    /**
     * Reset ALL plugins to default (calls backend API which auto-backups)
     */
    async onResetAllPlugins() {
        if (confirm(t('webui_conf_routing_reset_confirm'))) {
            const ok = await window.routingData.resetAllToDefaults();
            if (ok) {
                // Ricarica tutto
                await window.routingLogic.initRoutingPanel();
                if (window.showToast) window.showToast("All routing overrides reset. Backup saved.");
            } else {
                alert("Failed to reset routing overrides.");
            }
        }
    },

    /**
     * Save all current overrides to backend
     */
    async onSaveAll() {
        // Pulisce quelli che sono identici al default o vuoti (se il default è vuoto)
        const overridesToSave = {};
        const currentOverrides = window.routingData.overrides || {};
        const defaults = window.routingData.defaults || {};

        for (const [tag, text] of Object.entries(currentOverrides)) {
            const defaultText = defaults[tag] || '';
            // Save only if it's different from default.
            // If it's empty but default is NOT empty, we still save it (means user wants to disable the instruction).
            if (text !== defaultText) {
                overridesToSave[tag] = text;
            }
        }

        const ok = await window.routingData.saveOverrides(overridesToSave);
        if (ok) {
            // Update local state to matched cleaned version
            window.routingData.overrides = overridesToSave;
            window.routingRender.renderAllCards();
            if (window.showToast) window.showToast("Routing overrides saved successfully.");
        } else {
            alert("Failed to save routing overrides.");
        }
    },

    /**
     * Show backup modal by fetching current raw YAML
     */
    async onShowBackup() {
        const yaml = await window.routingData.fetchBackupText();
        window.routingRender.showBackupModal(yaml);
    },

    /**
     * Add a custom tag block that wasn't in the registry
     */
    onAddCustomTag() {
        const customTag = prompt("Enter the new TAG name (e.g. MY_PLUGIN):");
        if (customTag && customTag.trim() !== '') {
            const tag = customTag.trim().toUpperCase();
            if (!window.routingData.overrides) window.routingData.overrides = {};
            if (!(tag in window.routingData.overrides)) {
                window.routingData.overrides[tag] = "";
                // Rerender all to sort properly
                window.routingRender.renderAllCards();
                
                // Scroll to it
                setTimeout(() => {
                    const el = document.getElementById(`routing-card-${tag}`);
                    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }, 100);
            }
        }
    }
};
