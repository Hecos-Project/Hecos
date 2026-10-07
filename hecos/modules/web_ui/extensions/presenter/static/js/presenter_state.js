/**
 * Hecos Presenter — Shared State & Constants
 */
(function() {
    'use strict';

    window.HBSPresenterState = {
        displayMode: 'collapsed',
        presenterEnabled: true,
        hideTimeout: null,
        feedHistory: [],
        MAX_FEED: 50,
        presenterHiddenTypes: new Set(),
        presenterSearchQuery: '',
        
        TYPE_META: {
            system_info:     { icon: 'fas fa-info-circle',          color: '#6cb4ee', tooltip: 'System Information' },
            system_status:   { icon: 'fas fa-circle',               color: '#4caf50', iconSize: '9px', tooltip: 'System Status' },
            system_warning:  { icon: 'fas fa-exclamation-triangle', color: '#ffa726', tooltip: 'System Warning' },
            action_confirm:  { icon: 'fas fa-check-circle',         color: '#66bb6a', tooltip: 'Action Confirmed' },
            tip:             { icon: 'fas fa-lightbulb',            color: '#ffd54f', tooltip: 'Helpful Tip' },
            package_event:   { icon: 'fas fa-box-open',             color: '#ab47bc', tooltip: 'Package Event' },
            log_important:   { icon: 'fas fa-clipboard-list',       color: '#ef5350', tooltip: 'Important Log' },
            persona_switched:{ icon: 'fas fa-user-astronaut',       color: '#e040fb', tooltip: 'Persona Switched' },
            new_chat:        { icon: 'fas fa-comments',             color: '#29b6f6', tooltip: 'New Chat Session' },
            user_comment:    { icon: 'fas fa-user',                 color: '#42a5f5', tooltip: "Comment on User's Message" },
            ai_comment:      { icon: 'fas fa-robot',                color: '#ab47bc', tooltip: "Comment on AI's Response" },
            message_exchange:{ icon: 'fas fa-exchange-alt',         color: '#78909c', tooltip: 'Comment on Chat Exchange' },
            test:            { icon: 'fas fa-flask',                color: '#26c6da', tooltip: 'Test Event' },
            briefing:        { icon: 'fas fa-satellite-dish',       color: '#ff7043', tooltip: 'System Briefing' },
            default:         { icon: 'fas fa-bullhorn',             color: '#ff512f', tooltip: 'Notification' }
        }
    };
})();
