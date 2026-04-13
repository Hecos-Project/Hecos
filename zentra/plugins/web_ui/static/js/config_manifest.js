/**
 * Zentra Core v0.18.0 - Config UI Manifest
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
        { id: 'backend',   label: 'hub_mod_backend',      icon: '🧠', cat: 'INTELLIGENZA' },
        { id: 'llm',       label: 'hub_mod_llm',          icon: '🔑', cat: 'INTELLIGENZA' },
        { id: 'keymanager',label: 'hub_mod_keymanager',   icon: '🔐', cat: 'INTELLIGENZA' },
        { id: 'routing',   label: 'hub_mod_routing',      icon: '🚦', cat: 'INTELLIGENZA' },
        { id: 'ia',        label: 'hub_mod_persona',      icon: '🎭', cat: 'INTELLIGENZA' },
        { id: 'memory',    label: 'hub_mod_memory',       icon: '🧠', cat: 'INTELLIGENZA' },
        { id: 'neural-link', label: 'hub_mod_neural_link', icon: '🧠', cat: 'INTELLIGENZA', pluginTag: 'NEURAL_LINK' },
        
        { id: 'voice',     label: 'hub_mod_voice',        icon: '🎙️', cat: 'MULTIMEDIA' },
        { id: 'media',     label: 'hub_mod_media',        icon: '🖼️', cat: 'MULTIMEDIA' },
        { id: 'igen',      label: 'hub_mod_igen',         icon: '🎨', cat: 'MULTIMEDIA', pluginTag: 'IMAGE_GEN' },
        { id: 'roleplay_elite', label: 'hub_mod_roleplay_elite', icon: '🎭', cat: 'MULTIMEDIA', pluginTag: 'ROLEPLAY_ELITE' },
        
        { id: 'mcp',       label: 'hub_mod_mcp',          icon: '🔌', cat: 'CONNETTIVITÀ', pluginTag: 'MCP_BRIDGE' },
        { id: 'bridge',    label: 'hub_mod_bridge',       icon: '🌉', cat: 'CONNETTIVITÀ' },
        { id: 'remote-triggers', label: 'hub_mod_triggers', icon: '📱', cat: 'CONNETTIVITÀ', pluginTag: 'REMOTE_TRIGGERS' },
        
        { id: 'drive',     label: 'hub_mod_drive',        icon: '🗂️', cat: 'RISORSE', pluginTag: 'DRIVE' },
        { id: 'drive-editor', label: 'hub_mod_editor',    icon: '📝', cat: 'RISORSE', pluginTag: 'DRIVE_EDITOR' },
        { id: 'payload',   label: 'hub_mod_payload',      icon: '📦', cat: 'RISORSE' },
        { id: 'studio',    label: 'hub_mod_studio',       icon: '🛠️', cat: 'RISORSE' },
        
        { id: 'sysnet',    label: 'hub_mod_sysnet',       icon: '🌐', cat: 'SISTEMA' },
        { id: 'web',       label: 'hub_mod_web',          icon: '🌍', cat: 'SISTEMA', pluginTag: 'WEB' },
        { id: 'webcam',    label: 'hub_mod_webcam',       icon: '📷', cat: 'SISTEMA', pluginTag: 'WEBCAM' },
        { id: 'executor',  label: 'hub_mod_executor',     icon: '⚡', cat: 'SISTEMA', pluginTag: 'EXECUTOR' },
        { id: 'dashboard', label: 'hub_mod_dashboard',    icon: '📊', cat: 'SISTEMA', pluginTag: 'DASHBOARD' },
        { id: 'domotica',  label: 'hub_mod_domotica',     icon: '🏠', cat: 'SISTEMA', pluginTag: 'DOMOTICA' },
        { id: 'webui',     label: 'hub_mod_webui',        icon: '🌐', cat: 'SISTEMA', pluginTag: 'WEB_UI' },
        { id: 'system',    label: 'hub_mod_system',       icon: '⚙️', cat: 'SISTEMA' },
        { id: 'users',     label: 'hub_mod_users',        icon: '👥', cat: 'SISTEMA', adminOnly: true },
        { id: 'security',  label: 'hub_mod_security',     icon: '🛡️', cat: 'SISTEMA', adminOnly: true },
        { id: 'plugins',   label: 'hub_mod_plugins',      icon: '🧩', cat: 'SISTEMA' },
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
        'vision': '👁️',
        'audio':  '🎙️',
        'voice':  '🗣️',
        'security':'🛡️',
        'network': '🌐',
        'database':'🗄️',
        'code':    '💻'
    }
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
    'NEURAL_LINK': 'neural-link',
    'DASHBOARD': 'dashboard',
    'DOMOTICA': 'domotica',
    'EXECUTOR': 'executor',
    'ROLEPLAY_ELITE': 'roleplay_elite',
    'WEB': 'web',
    'WEBCAM': 'webcam',
    'DRIVE_EDITOR': 'drive-editor'
};
