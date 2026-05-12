/**
 * Hecos v0.18.2 - Config UI Manifest
 * Centralized registry for configuration modules, icons, and categories.
 */

window.CONFIG_HUB = {
    // Categories definition
    categories: {
        'INTELLIGENZA': { label: 'hub_cat_intelligenza', icon: '<i class="fas fa-brain"></i>', order: 1 },
        'MULTIMEDIA':   { label: 'hub_cat_multimedia',   icon: '<i class="fas fa-compact-disc"></i>', order: 2 },
        'CONNETTIVITÀ': { label: 'hub_cat_connettivita', icon: '<i class="fas fa-network-wired"></i>', order: 3 },
        'RISORSE':      { label: 'hub_cat_risorse',      icon: '<i class="fas fa-folder-open"></i>', order: 4 },
        'SISTEMA':      { label: 'hub_cat_sistema',      icon: '<i class="fas fa-cogs"></i>', order: 5 }
    },

    // Core Modules (not discovered via plugin loader)
    modules: [
        { id: 'backend',   label: 'hub_mod_backend',      icon: '<i class="fas fa-server"></i>', cat: 'INTELLIGENZA', pluginTag: 'MODELS', isCore: true },

        { id: 'keymanager',label: 'hub_mod_keymanager',   icon: '<i class="fas fa-key"></i>', cat: 'INTELLIGENZA', isCore: true },
        { id: 'routing',   label: 'hub_mod_routing',      icon: '<i class="fas fa-route"></i>', cat: 'INTELLIGENZA', isCore: true },
        { id: 'ia',        label: 'hub_mod_persona',      icon: '<i class="fas fa-user-astronaut"></i>', cat: 'INTELLIGENZA', isCore: true },
        { id: 'filters',   label: 'hub_mod_filters',      icon: '<i class="fas fa-filter"></i>', cat: 'INTELLIGENZA', isCore: true },
        { id: 'memory',    label: 'hub_mod_memory',       icon: '<i class="fas fa-memory"></i>', cat: 'INTELLIGENZA', pluginTag: 'MEMORY', isCore: true },
        { id: 'agent',     label: 'hub_mod_agent',        icon: '<i class="fas fa-robot"></i>', cat: 'INTELLIGENZA', isCore: true },
        
        { id: 'voice',     label: 'hub_mod_voice',        icon: '<i class="fas fa-microphone-alt"></i>', cat: 'MULTIMEDIA' },
        { id: 'aesthetics',label: 'hub_mod_aesthetics',   icon: '<i class="fas fa-palette"></i>', cat: 'MULTIMEDIA', isCore: true },
        { id: 'media',         label: 'webui_mp_title',   icon: '<i class="fas fa-music"></i>', cat: 'MULTIMEDIA', pluginTag: 'MEDIA_PLAYER' },
        { id: 'igen',      label: 'hub_mod_igen',         icon: '<i class="fas fa-image"></i>', cat: 'MULTIMEDIA', pluginTag: 'IMAGE_GEN' },
        
        { id: 'mcp',       label: 'hub_mod_mcp',          icon: '<i class="fas fa-plug"></i>', cat: 'CONNETTIVITÀ', pluginTag: 'MCP_BRIDGE', isCore: true },
        { id: 'bridge',    label: 'hub_mod_bridge',       icon: '<i class="fas fa-project-diagram"></i>', cat: 'CONNETTIVITÀ', isCore: true },
        { id: 'remote-triggers', label: 'hub_mod_triggers', icon: '<i class="fas fa-mobile-alt"></i>', cat: 'CONNETTIVITÀ', pluginTag: 'REMOTE_TRIGGERS' },
        
        { id: 'drive',             label: 'hub_mod_drive',        icon: '<i class="fas fa-hdd"></i>', cat: 'RISORSE', pluginTag: 'DRIVE' },
        { id: 'drive-editor',     label: 'hub_mod_editor',       icon: '<i class="fas fa-edit"></i>', cat: 'RISORSE', pluginTag: 'DRIVE_EDITOR',      parentPluginTag: 'DRIVE', isExtension: true },
        { id: 'payload',          label: 'hub_mod_payload',      icon: '<i class="fas fa-box-open"></i>', cat: 'RISORSE' },
        { id: 'studio',           label: 'hub_mod_studio',       icon: '<i class="fas fa-drafting-pencil"></i>', cat: 'RISORSE' },
        
        { id: 'sysnet',    label: 'hub_mod_sysnet',       icon: '<i class="fas fa-globe-europe"></i>', cat: 'SISTEMA', pluginTag: 'SYS_NET', isCore: true },
        { id: 'web',       label: 'hub_mod_web',          icon: '<i class="fas fa-globe"></i>', cat: 'SISTEMA', pluginTag: 'WEB' },
        { id: 'webcam',    label: 'hub_mod_webcam',       icon: '<i class="fas fa-camera"></i>', cat: 'SISTEMA', pluginTag: 'WEBCAM' },
        { id: 'reminder',  label: 'ext_reminder_title',   icon: '<i class="fas fa-clock"></i>', cat: 'SISTEMA', pluginTag: 'REMINDER' },
        { id: 'calendar',  label: 'ext_calendar_title',   icon: '<i class="fas fa-calendar-alt"></i>', cat: 'SISTEMA', pluginTag: 'CALENDAR' },
        { id: 'automation',label: 'hub_mod_automation',  icon: '<i class="fas fa-magic"></i>', cat: 'SISTEMA', pluginTag: 'AUTOMATION', isCore: true },
        { id: 'browser',   label: 'hub_mod_browser',     icon: '<i class="fas fa-window-maximize"></i>', cat: 'SISTEMA', pluginTag: 'BROWSER', isCore: true },
        { id: 'executor',  label: 'hub_mod_executor',     icon: '<i class="fas fa-bolt"></i>', cat: 'SISTEMA', pluginTag: 'EXECUTOR', isCore: true },
        { id: 'dashboard', label: 'hub_mod_dashboard',    icon: '<i class="fas fa-chart-line"></i>', cat: 'SISTEMA', pluginTag: 'DASHBOARD', isCore: true },
        { id: 'domotica',  label: 'hub_mod_domotica',     icon: '<i class="fas fa-home"></i>', cat: 'SISTEMA', pluginTag: 'DOMOTICA' },

        { id: 'widgets',   label: 'hub_mod_widgets',      icon: '<i class="fas fa-cubes"></i>', cat: 'SISTEMA', isCore: true },
        { id: 'webui',     label: 'hub_mod_webui',        icon: '<i class="fas fa-desktop"></i>', cat: 'SISTEMA', pluginTag: 'WEB_UI', isCore: true },
        { id: 'help',      label: 'webui_help_about_title', icon: '<i class="fas fa-question-circle"></i>', cat: 'SISTEMA', pluginTag: 'HELP', isCore: true },
        { id: 'users',     label: 'hub_mod_users',        icon: '<i class="fas fa-users-cog"></i>', cat: 'SISTEMA', adminOnly: true, pluginTag: 'USERS' },
        { id: 'security',  label: 'hub_mod_security',     icon: '<i class="fas fa-shield-alt"></i>', cat: 'SISTEMA', adminOnly: true },
        { id: 'plugins',   label: 'hub_mod_plugins',      icon: '<i class="fas fa-puzzle-piece"></i>', cat: 'SISTEMA' },
        { id: 'system',    label: 'hub_mod_system',       icon: '<i class="fas fa-cog"></i>', cat: 'SISTEMA' },
        { id: 'logs',      label: 'hub_mod_logs',         icon: '<i class="fas fa-terminal"></i>', cat: 'SISTEMA' },
        { id: 'privacy',   label: 'hub_mod_privacy',      icon: '<i class="fas fa-user-secret"></i>', cat: 'SISTEMA' }
    ],

    // Fallback Icons based on keywords (for MCP or new plugins)
    iconMap: {
        'search': '<i class="fas fa-search"></i>',
        'google': '<i class="fas fa-search"></i>',
        'github': '<i class="fab fa-github"></i>',
        'maps':   '<i class="fas fa-map-marked-alt"></i>',
        'weather':'<i class="fas fa-cloud-sun"></i>',
        'file':   '<i class="fas fa-file-alt"></i>',
        'drive':  '<i class="fas fa-hdd"></i>',
        'tools':  '<i class="fas fa-tools"></i>',
        'image':  '<i class="fas fa-image"></i>',
        'audio':  '<i class="fas fa-volume-up"></i>',
        'voice':  '<i class="fas fa-microphone-alt"></i>',
        'security':'<i class="fas fa-shield-alt"></i>',
        'network': '<i class="fas fa-network-wired"></i>',
        'database':'<i class="fas fa-database"></i>',
        'code':    '<i class="fas fa-code"></i>'
    },

    // Plugins that should NOT be shown in the Module Manager UI
    internalTags: [
        'WEB_UI',
        'HELP'
    ]
};

window.getIconForModule = function(id, name, metaIcon) {
    if (metaIcon && metaIcon.includes('<i ')) return metaIcon;
    
    // Explicit mapping for widgets/extensions
    const extIcons = {
        'media_player_widget': '<i class="fas fa-music"></i>',
        'quick_links': '<i class="fas fa-bolt"></i>',
        'calendar': '<i class="fas fa-calendar-alt"></i>',
        'reminder': '<i class="fas fa-clock"></i>',
        'emoticons': '<i class="fas fa-smile"></i>'
    };
    if (extIcons[id]) return extIcons[id];

    const item = window.CONFIG_HUB.modules.find(m => m.id === id);
    if (item) return item.icon;
    
    // Guess by name
    const lower = (name || id || '').toLowerCase();
    for (const [kw, icon] of Object.entries(window.CONFIG_HUB.iconMap)) {
        if (lower.includes(kw)) return icon;
    }
    return '<i class="fas fa-puzzle-piece"></i>'; // Default
};

window.CONFIG_HUB.tagMap = {
    'IMAGE_GEN': 'igen',
    'MCP_BRIDGE': 'mcp',
    'DRIVE': 'drive',
    'REMOTE_TRIGGERS': 'remote-triggers',
    'AUTOCODER': 'studio',
    'PLUGIN_STUDIO': 'studio',
    'DASHBOARD': 'dashboard',
    'DOMOTICA': 'domotica',
    'EXECUTOR': 'executor',
    'WEB': 'web',
    'WEBCAM': 'webcam',
    'MEMORY': 'memory',
    'SYS_NET': 'sysnet',
    'MODELS': 'backend',
    'DRIVE_EDITOR': 'drive-editor',
    'REMINDER': 'reminder',
    'CALENDAR': 'calendar',
    'MEDIA_PLAYER': 'media',
    'AUTOMATION': 'automation',
    'BROWSER':    'browser',
    'USERS':      'users'
};

/**
 * The full set of panel IDs that are served lazily via /hecos/config/fragment/<id>.
 * This MUST match the keys in _PANEL_MAP in routes_config.py.
 * Used by renderConfigHub() to show tabs even before a panel has been fetched.
 */
window.LAZY_PANEL_IDS = new Set([
    'backend', 'keymanager', 'routing', 'agent', 'ia', 'filters', 'bridge',
    'memory', 'voice', 'system', 'media', 'aesthetics', 'igen', 'webui',
    'web', 'webcam', 'executor', 'automation', 'dashboard', 'domotica',
    'browser', 'sysnet', 'users', 'security', 'payload', 'plugins',
    'reminder', 'calendar', 'studio', 'mcp', 'remote-triggers',
    'drive', 'drive-editor', 'logs', 'privacy', 'widgets', 'help'
]);
