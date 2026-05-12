/**
 * Hecos v0.18.2 - Config UI Manifest
 * Centralized registry for configuration modules, icons, and categories.
 */

window.CONFIG_HUB = {
    // Categories definition
    categories: {
        'INTELLIGENZA': { label: 'hub_cat_intelligenza', icon: '🧠', order: 1 },
        'MULTIMEDIA':   { label: 'hub_cat_multimedia',   icon: '🎨', order: 2 },
        'CONNETTIVITÀ': { label: 'hub_cat_connettivita', icon: '🌐', order: 3 },
        'RISORSE':      { label: 'hub_cat_risorse',      icon: '📁', order: 4 },
        'SISTEMA':      { label: 'hub_cat_sistema',      icon: '🛡️', order: 5 }
    },

    // Core Modules (not discovered via plugin loader)
    modules: [
        { id: 'backend',   label: 'hub_mod_backend',      icon: '🧠', cat: 'INTELLIGENZA', pluginTag: 'MODELS', isCore: true },

        { id: 'keymanager',label: 'hub_mod_keymanager',   icon: '🔐', cat: 'INTELLIGENZA', isCore: true },
        { id: 'routing',   label: 'hub_mod_routing',      icon: '🚦', cat: 'INTELLIGENZA', isCore: true },
        { id: 'ia',        label: 'hub_mod_persona',      icon: '🎭', cat: 'INTELLIGENZA', isCore: true },
        { id: 'filters',   label: 'hub_mod_filters',      icon: '📝', cat: 'INTELLIGENZA', isCore: true },
        { id: 'memory',    label: 'hub_mod_memory',       icon: '🧠', cat: 'INTELLIGENZA', pluginTag: 'MEMORY', isCore: true },
        { id: 'agent',     label: 'hub_mod_agent',        icon: '🤖', cat: 'INTELLIGENZA', isCore: true },
        
        { id: 'voice',     label: 'hub_mod_voice',        icon: '🎙️', cat: 'MULTIMEDIA' },
        { id: 'aesthetics',label: 'hub_mod_aesthetics',   icon: '🎨', cat: 'MULTIMEDIA', isCore: true },
        { id: 'media',         label: 'webui_mp_title',   icon: '🎵', cat: 'MULTIMEDIA', pluginTag: 'MEDIA_PLAYER' },
        { id: 'igen',      label: 'hub_mod_igen',         icon: '🎨', cat: 'MULTIMEDIA', pluginTag: 'IMAGE_GEN' },
        
        { id: 'mcp',       label: 'hub_mod_mcp',          icon: '🔌', cat: 'CONNETTIVITÀ', pluginTag: 'MCP_BRIDGE', isCore: true },
        { id: 'bridge',    label: 'hub_mod_bridge',       icon: '🌉', cat: 'CONNETTIVITÀ', isCore: true },
        { id: 'remote-triggers', label: 'hub_mod_triggers', icon: '📱', cat: 'CONNETTIVITÀ', pluginTag: 'REMOTE_TRIGGERS' },
        
        { id: 'drive',             label: 'hub_mod_drive',        icon: '🗂️', cat: 'RISORSE', pluginTag: 'DRIVE' },
        { id: 'drive-editor',     label: 'hub_mod_editor',       icon: '📝', cat: 'RISORSE', pluginTag: 'DRIVE_EDITOR',      parentPluginTag: 'DRIVE', isExtension: true },
        { id: 'payload',          label: 'hub_mod_payload',      icon: '📦', cat: 'RISORSE' },
        { id: 'studio',           label: 'hub_mod_studio',       icon: '🛠️', cat: 'RISORSE' },
        
        { id: 'sysnet',    label: 'hub_mod_sysnet',       icon: '🌐', cat: 'SISTEMA', pluginTag: 'SYS_NET', isCore: true },
        { id: 'web',       label: 'hub_mod_web',          icon: '🌍', cat: 'SISTEMA', pluginTag: 'WEB' },
        { id: 'webcam',    label: 'hub_mod_webcam',       icon: '📷', cat: 'SISTEMA', pluginTag: 'WEBCAM' },
        { id: 'reminder',  label: 'ext_reminder_title',   icon: '⏰', cat: 'SISTEMA', pluginTag: 'REMINDER' },
        { id: 'calendar',  label: 'ext_calendar_title',   icon: '📅', cat: 'SISTEMA', pluginTag: 'CALENDAR' },
        { id: 'automation',label: 'PC Automation',        icon: '🖱️', cat: 'SISTEMA', pluginTag: 'AUTOMATION', isCore: true },
        { id: 'browser',   label: 'AI Browser',           icon: '🌐', cat: 'SISTEMA', pluginTag: 'BROWSER', isCore: true },
        { id: 'executor',  label: 'hub_mod_executor',     icon: '⚡', cat: 'SISTEMA', pluginTag: 'EXECUTOR', isCore: true },
        { id: 'dashboard', label: 'hub_mod_dashboard',    icon: '📊', cat: 'SISTEMA', pluginTag: 'DASHBOARD', isCore: true },
        { id: 'domotica',  label: 'hub_mod_domotica',     icon: '🏠', cat: 'SISTEMA', pluginTag: 'DOMOTICA' },

        { id: 'widgets',   label: 'hub_mod_widgets',      icon: '🧩', cat: 'SISTEMA', isCore: true },
        { id: 'webui',     label: 'hub_mod_webui',        icon: '🌐', cat: 'SISTEMA', pluginTag: 'WEB_UI', isCore: true },
        { id: 'help',      label: 'webui_help_about_title', icon: '❓', cat: 'SISTEMA', pluginTag: 'HELP', isCore: true },
        { id: 'users',     label: 'hub_mod_users',        icon: '👥', cat: 'SISTEMA', adminOnly: true, pluginTag: 'USERS' },
        { id: 'security',  label: 'hub_mod_security',     icon: '🛡️', cat: 'SISTEMA', adminOnly: true },
        { id: 'plugins',   label: 'hub_mod_plugins',      icon: '🧩', cat: 'SISTEMA' },
        { id: 'system',    label: 'hub_mod_system',       icon: '⚙️', cat: 'SISTEMA' },
        { id: 'logs',      label: 'hub_mod_logs',         icon: '📜', cat: 'SISTEMA' },
        { id: 'privacy',   label: 'hub_mod_privacy',      icon: '🕵️', cat: 'SISTEMA' }
    ],

    // Fallback Icons based on keywords (for MCP or new plugins)
    iconMap: {
        'search': '🔍',
        'google': '🔍',
        'github': '🐙',
        'maps':   '🗺️',
        'weather':'🌤️',
        'file':   '📂',
        'drive':  '🗂️',
        'tools':  '🛠️',
        'image':  '🎨',
        'audio':  '🎙️',
        'voice':  '🗣️',
        'security':'🛡️',
        'network': '🌐',
        'database':'🗄️',
        'code':    '💻'
    },

    // Plugins that should NOT be shown in the Module Manager UI
    internalTags: [
        'WEB_UI',
        'HELP'
    ]
};

window.getIconForModule = function(id, name, metaIcon) {
    if (metaIcon) return metaIcon;
    const item = window.CONFIG_HUB.modules.find(m => m.id === id);
    if (item) return item.icon;
    
    // Guess by name
    const lower = (name || id || '').toLowerCase();
    for (const [kw, icon] of Object.entries(window.CONFIG_HUB.iconMap)) {
        if (lower.includes(kw)) return icon;
    }
    return '🧩'; // Default
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
