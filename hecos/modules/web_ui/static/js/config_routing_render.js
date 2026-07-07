/**
 * config_routing_render.js
 * Rendering Layer for Hecos Routing Overrides Pro Panel
 */

window.routingRender = {
    /**
     * Render all plugin cards based on registry defaults and current overrides
     */
    renderAllCards() {
        const container = document.getElementById('routing-cards-list');
        if (!container) return;

        container.innerHTML = '';

        const overrides = window.routingData.overrides || {};
        const defaults = window.routingData.defaults || {};

        // Collect all unique tags safely
        const allTags = new Set([...Object.keys(defaults), ...Object.keys(overrides)]);

        // Sort: BROWSER, AUTOMATION, IMAGE_GEN usually first, then alphabetical
        const sortedTags = Array.from(allTags).sort((a, b) => {
            const highPriority = ['BROWSER', 'AUTOMATION', 'WEBCAM', 'FLOWS'];
            const aPrio = highPriority.indexOf(a);
            const bPrio = highPriority.indexOf(b);
            if (aPrio !== -1 && bPrio !== -1) return aPrio - bPrio;
            if (aPrio !== -1) return -1;
            if (bPrio !== -1) return 1;
            return a.localeCompare(b);
        });

        sortedTags.forEach(tag => {
            const defaultText = defaults[tag] || '';
            const overrideText = overrides[tag] !== undefined ? overrides[tag] : '';
            this.renderSingleCard(container, tag, defaultText, overrideText);
        });
    },

    /**
     * Render a single card and append it to the container
     */
    renderSingleCard(container, tag, defaultText, overrideText) {
        const hasOverride = (overrideText !== '' && overrideText !== null);
        const activeText = hasOverride ? overrideText : defaultText;
        
        // FontAwesome icon map — mirrors config_manifest.js exactly
        const iconMap = {

            'WEBCAM':           '<i class="fas fa-camera"></i>',
            'MEDIA_PLAYER':     '<i class="fas fa-music"></i>',
            'MEMORY':           '<i class="fas fa-memory"></i>',
            'BROWSER':          '<i class="fas fa-window-maximize"></i>',
            'AUTOMATION':       '<i class="fas fa-magic"></i>',
            'EXECUTOR':         '<i class="fas fa-bolt"></i>',
            'FLOWS':            '<i class="fas fa-project-diagram"></i>',
            'WEB':              '<i class="fas fa-globe"></i>',
            'SYS_NET':          '<i class="fas fa-globe-europe"></i>',
            'SYSTEM':           '<i class="fas fa-cogs"></i>',
            'FILE_MANAGER':     '<i class="fas fa-folder-open"></i>',
            'DRIVE':            '<i class="fas fa-hdd"></i>',
            'DRIVE_EDITOR':     '<i class="fas fa-edit"></i>',
            'MAIL':             '<i class="fas fa-envelope"></i>',
            'CONTACTS':         '<i class="fas fa-address-book"></i>',
            'MESSENGER':        '<i class="fab fa-telegram-plane"></i>',
            'REMINDER':         '<i class="fas fa-clock"></i>',
            'CALENDAR':         '<i class="fas fa-calendar-alt"></i>',
            'MCP_BRIDGE':       '<i class="fas fa-plug"></i>',
            'DASHBOARD':        '<i class="fas fa-tachometer-alt"></i>',
            'DOMOTICA':         '<i class="fas fa-home"></i>',
            'USERS':            '<i class="fas fa-users"></i>',
            'MODELS':           '<i class="fas fa-server"></i>',
            'ROLEPLAY':         '<i class="fas fa-theater-masks"></i>',
            'AUTOCODER':        '<i class="fas fa-code"></i>'
        };
        const icon = iconMap[tag] || '<i class="fas fa-puzzle-piece"></i>';

        const card = document.createElement('div');
        card.className = 'card';
        card.style.background = 'var(--bg2)';
        card.style.border = '1px solid var(--border)';
        card.style.padding = '15px';
        card.style.marginBottom = '10px';
        card.style.borderRadius = 'var(--radius)';
        card.id = `routing-card-${tag}`;

        const badgeActiveText = 'ACTIVE OVERRIDE';
        const badgeDefaultText = 'DEFAULT';

        card.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                <div style="display: flex; align-items: center; gap: 10px;">
                    <span style="font-size: 16px; color: var(--accent); width: 20px; text-align: center;">${icon}</span>
                    <span style="font-weight: 600; font-family: monospace; font-size: 14px;">${tag}</span>
                    <span id="routing-badge-${tag}" style="font-size: 10px; padding: 3px 8px; border-radius: 10px; font-weight: bold; background: ${hasOverride ? 'var(--glass-c)' : 'var(--glass)'}; color: ${hasOverride ? 'var(--green)' : 'var(--muted)'}">
                        ${hasOverride ? badgeActiveText : badgeDefaultText}
                    </span>
                </div>
                <button type="button" class="btn btn-secondary" onclick="window.routingActions.onResetSinglePlugin('${tag}')" title="Reset to default" style="padding: 4px 8px;">
                    <i class="fas fa-undo"></i>
                </button>
            </div>
            
            <div style="margin-bottom: 10px;">
                <textarea id="routing-input-${tag}" 
                          oninput="window.routingActions.onOverrideChange('${tag}', this.value)"
                          class="terminal-view" 
                          style="width: 100%; min-height: 80px; font-family: var(--font-mono); font-size: var(--font-size-sm); resize: vertical; padding: 10px; background: var(--bg3); color: var(--text); border: 1px solid var(--border); border-radius: var(--radius);"
                          placeholder="No specific instructions. Type here to add...">${activeText}</textarea>
            </div>

            ${defaultText ? `
            <details style="font-size: 11px; opacity: 0.7;">
                <summary style="cursor: pointer;">System Default</summary>
                <div style="margin-top: 5px; padding: 8px; background: var(--bg3); border: 1px solid var(--border); border-radius: var(--radius); font-family: var(--font-mono); white-space: pre-wrap; color: var(--muted);">${defaultText}</div>
            </details>
            ` : ''}
        `;

        container.appendChild(card);
    },

    /**
     * Update the badge of a specific card without re-rendering everything
     */
    updateCardBadge(tag) {
        const badge = document.getElementById(`routing-badge-${tag}`);
        if (!badge) return;

        const defaults = window.routingData.defaults || {};
        const overrides = window.routingData.overrides || {};
        const defaultText = defaults[tag] || '';
        const currentText = document.getElementById(`routing-input-${tag}`)?.value || '';

        // Se è uguale al default o è vuoto (ed era vuoto il default), non è un override
        let hasOverride = false;
        
        if (tag in overrides) {
            hasOverride = true; // Se è presente nelle chiavi di override (anche se l'utente l'ha lasciato vuoto momentaneamente prima di salvare)
        }

        // Live validation during typing
        if (currentText !== defaultText) {
             hasOverride = true;
        }

        if (hasOverride) {
            badge.style.background = 'var(--glass-c)';
            badge.style.color = 'var(--green)';
            badge.innerText = 'ACTIVE OVERRIDE';
        } else {
            badge.style.background = 'var(--glass)';
            badge.style.color = 'var(--muted)';
            badge.innerText = 'DEFAULT';
        }
    },

    /**
     * Show backup modal
     */
    showBackupModal(yamlText) {
        const modal = document.getElementById('routing-backup-modal');
        const textarea = document.getElementById('routing-backup-textarea');
        if (modal && textarea) {
            textarea.value = yamlText;
            modal.style.display = 'flex';
        }
    }
};
