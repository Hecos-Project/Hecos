/**
 * Hecos Config UI Manifest
 * Centralized registry for configuration modules, icons, and categories.
 * Reference keys are English (INTELLIGENCE, MULTIMEDIA, CONNECTIVITY, RESOURCES, AUTOMATION, SYSTEM)
 * with full backward compatibility for legacy Italian category identifiers.
 */

window.HUB_CATEGORY_ALIASES = {
    'INTELLIGENCE': 'INTELLIGENCE',
    'INTELLIGENZA': 'INTELLIGENCE',
    'MULTIMEDIA':   'MULTIMEDIA',
    'CONNECTIVITY': 'CONNECTIVITY',
    'CONNETTIVITÀ': 'CONNECTIVITY',
    'CONNETTIVITA': 'CONNECTIVITY',
    'RESOURCES':    'RESOURCES',
    'RISORSE':      'RESOURCES',
    'DOCUMENTS':    'RESOURCES',
    'AUTOMATION':   'AUTOMATION',
    'AUTOMAZIONE':  'AUTOMATION',
    'SYSTEM':       'SYSTEM',
    'SISTEMA':      'SYSTEM'
};

// Canonical category map by package/tab ID (ensures clean placement even for older pre-built .hpkg archives)
window.HUB_CANONICAL_PKG_CAT = {
    // INTELLIGENCE
    'backend':            'INTELLIGENCE',
    'keymanager':         'INTELLIGENCE',
    'ia':                 'INTELLIGENCE',
    'filters':            'INTELLIGENCE',
    'memory':             'INTELLIGENCE',
    'agent':              'INTELLIGENCE',
    'vision':             'INTELLIGENCE',
    'payload':            'INTELLIGENCE',

    // MULTIMEDIA
    'voice':              'MULTIMEDIA',
    'voice_forge':        'MULTIMEDIA',
    'voice-forge':        'MULTIMEDIA',
    'image_gen':          'MULTIMEDIA',
    'igen':               'MULTIMEDIA',
    'media_player':       'MULTIMEDIA',
    'presenter':          'MULTIMEDIA',
    'playbooks':          'MULTIMEDIA',
    'themes_pack':        'MULTIMEDIA',
    'themes':             'MULTIMEDIA',
    'webcam':             'MULTIMEDIA',

    // CONNECTIVITY
    'sysnet':             'CONNECTIVITY',
    'net_search':         'CONNECTIVITY',
    'netsearch':          'CONNECTIVITY',
    'browser_automation': 'CONNECTIVITY',
    'browser':            'CONNECTIVITY',
    'sys_net':            'CONNECTIVITY',
    'sys_net_panel':      'CONNECTIVITY',
    'mcp_bridge':         'CONNECTIVITY',
    'mcp':                'CONNECTIVITY',
    'mail':               'CONNECTIVITY',
    'messenger':          'CONNECTIVITY',
    'contacts':           'CONNECTIVITY',
    'remote_triggers':    'CONNECTIVITY',
    'remote-triggers':    'CONNECTIVITY',
    'remote_access_pro':  'CONNECTIVITY',
    'weather_pro':        'CONNECTIVITY',
    'map':                'CONNECTIVITY',

    // RESOURCES
    'drive':              'RESOURCES',
    'document_reader':    'RESOURCES',
    'document_maker':     'RESOURCES',
    'templates':          'RESOURCES',
    'calendar':           'RESOURCES',
    'reminder':           'RESOURCES',
    'lists':              'RESOURCES',

    // AUTOMATION
    'action-plans':       'AUTOMATION',
    'executor':           'AUTOMATION',
    'hdcs':               'AUTOMATION',
    'flows':              'AUTOMATION',
    'pc_automation':      'AUTOMATION',
    'automation':         'AUTOMATION',
    'coder':              'AUTOMATION',
    'builder_studio':     'AUTOMATION',
    'builder':            'AUTOMATION',

    // SYSTEM
    'system':             'SYSTEM',
    'hpm-settings':       'SYSTEM',
    'packages':           'SYSTEM',
    'plugins':            'SYSTEM',
    'users':              'SYSTEM',
    'privacy':            'SYSTEM',
    'logs':               'SYSTEM',
    'chat_ui':            'SYSTEM',
    'shortcuts':          'SYSTEM',
    'help':               'SYSTEM',
    'global_backup':      'SYSTEM',
    'backup_panel':       'SYSTEM',
    'backup':             'SYSTEM',
    'notifications':      'SYSTEM'
};

window.normalizeHubCategory = function(rawCat, modId, modType) {
    const cleanId = String(modId || '').trim().toLowerCase();
    if (cleanId && window.HUB_CANONICAL_PKG_CAT[cleanId]) {
        return window.HUB_CANONICAL_PKG_CAT[cleanId];
    }
    const upper = String(rawCat || '').trim().toUpperCase();
    if (upper && window.HUB_CATEGORY_ALIASES[upper]) {
        return window.HUB_CATEGORY_ALIASES[upper];
    }
    const t = String(modType || '').trim().toLowerCase();
    if (t === 'library') return 'RESOURCES';
    if (t === 'theme' || t === 'playbook') return 'MULTIMEDIA';
    if (t === 'persona') return 'INTELLIGENCE';
    if (t === 'skill_pack') return 'AUTOMATION';
    return 'SYSTEM';
};

window.CONFIG_HUB = {
    // Categories definition (English canonical keys -> i18n keys)
    categories: {
        'INTELLIGENCE': { label: 'hub_cat_intelligence', fallback: 'Intelligence', icon: '<i class="fas fa-brain"></i>',       order: 1 },
        'MULTIMEDIA':   { label: 'hub_cat_multimedia',   fallback: 'Multimedia',   icon: '<i class="fas fa-photo-film"></i>',  order: 2 },
        'CONNECTIVITY': { label: 'hub_cat_connectivity', fallback: 'Connectivity', icon: '<i class="fas fa-globe"></i>',       order: 3 },
        'RESOURCES':    { label: 'hub_cat_resources',    fallback: 'Resources',    icon: '<i class="fas fa-folder-open"></i>', order: 4 },
        'AUTOMATION':   { label: 'hub_cat_automation',   fallback: 'Automation',   icon: '<i class="fas fa-gears"></i>',       order: 5 },
        'SYSTEM':       { label: 'hub_cat_system',       fallback: 'System',       icon: '<i class="fas fa-sliders"></i>',     order: 6 }
    },

    // Core Modules (built-in Central Hub panels)
    modules: [
        // 1. INTELLIGENCE
        { id: 'backend',      label: 'hub_mod_backend',        descKey: 'hub_desc_backend',      icon: '<i class="fas fa-microchip"></i>',        cat: 'INTELLIGENCE', pluginTag: 'MODELS', isCore: true },
        { id: 'keymanager',   label: 'hub_mod_keymanager',     descKey: 'hub_desc_keymanager',   icon: '<i class="fas fa-key"></i>',              cat: 'INTELLIGENCE', isCore: true },
        { id: 'ia',           label: 'hub_mod_persona',        descKey: 'hub_desc_persona',      icon: '<i class="fas fa-masks-theater"></i>',    cat: 'INTELLIGENCE', isCore: true },
        { id: 'filters',      label: 'hub_mod_filters',        descKey: 'hub_desc_filters',      icon: '<i class="fas fa-filter"></i>',           cat: 'INTELLIGENCE', isCore: true },
        { id: 'memory',       label: 'hub_mod_memory',         descKey: 'hub_desc_memory',       icon: '<i class="fas fa-database"></i>',         cat: 'INTELLIGENCE', pluginTag: 'MEMORY', isCore: true },
        { id: 'agent',        label: 'hub_mod_agent',          descKey: 'hub_desc_agent',        icon: '<i class="fas fa-robot"></i>',            cat: 'INTELLIGENCE', isCore: true },
        { id: 'vision',       label: 'hub_mod_vision',         descKey: 'hub_desc_vision',       icon: '<i class="fas fa-eye"></i>',              cat: 'INTELLIGENCE', isCore: true },
        { id: 'payload',      label: 'hub_mod_payload',        descKey: 'hub_desc_payload',      icon: '<i class="fas fa-sliders"></i>',          cat: 'INTELLIGENCE', isCore: true },

        // 2. MULTIMEDIA
        { id: 'voice',        label: 'hub_mod_voice',          descKey: 'hub_desc_voice',        icon: '<i class="fas fa-microphone-lines"></i>', cat: 'MULTIMEDIA', isCore: true },
        { id: 'presenter',    label: 'hub_mod_presenter',      descKey: 'hub_desc_presenter',    icon: '<i class="fas fa-chalkboard-user"></i>',  cat: 'MULTIMEDIA', isCore: true },

        // 3. CONNECTIVITY
        { id: 'sysnet',       label: 'hub_mod_web_server',     descKey: 'hub_desc_sysnet',       icon: '<i class="fas fa-server"></i>',           cat: 'CONNECTIVITY', isCore: true },

        // 5. AUTOMATION
        { id: 'action-plans', label: 'hub_mod_action_plans',   descKey: 'hub_desc_action_plans', icon: '<i class="fas fa-route"></i>',            cat: 'AUTOMATION', pluginTag: 'ACTION_PLANS', isCore: true },
        { id: 'executor',     label: 'hub_mod_executor',       descKey: 'hub_desc_executor',     icon: '<i class="fas fa-terminal"></i>',         cat: 'AUTOMATION', pluginTag: 'EXECUTOR', isCore: true },
        { id: 'hdcs',         label: 'hub_mod_hdcs',           descKey: 'hub_desc_hdcs',         icon: '<i class="fas fa-hashtag"></i>',          cat: 'AUTOMATION', pluginTag: 'HDCS', isCore: true },

        // 6. SYSTEM
        { id: 'system',       label: 'hub_mod_system',         descKey: 'hub_desc_system',       icon: '<i class="fas fa-sliders"></i>',          cat: 'SYSTEM', isCore: true },
        { id: 'hpm-settings', label: 'hub_mod_hpm_settings',   descKey: 'hub_desc_hpm_settings', icon: '<i class="fas fa-box-open"></i>',         cat: 'SYSTEM', isCore: true },
        { id: 'users',        label: 'hub_mod_users',          descKey: 'hub_desc_users',        icon: '<i class="fas fa-users"></i>',            cat: 'SYSTEM', adminOnly: true, isCore: true },
        { id: 'privacy',      label: 'hub_mod_privacy',        descKey: 'hub_desc_privacy',      icon: '<i class="fas fa-shield-halved"></i>',    cat: 'SYSTEM', isCore: true },
        { id: 'logs',         label: 'hub_mod_logs',           descKey: 'hub_desc_logs',         icon: '<i class="fas fa-scroll"></i>',           cat: 'SYSTEM', isCore: true },
        { id: 'chat_ui',      label: 'hub_mod_chat_ui',        descKey: 'hub_desc_chat_ui',      icon: '<i class="fas fa-comment-dots"></i>',     cat: 'SYSTEM', isCore: true },
        { id: 'shortcuts',    label: 'hub_mod_shortcuts',      descKey: 'hub_desc_shortcuts',    icon: '<i class="fas fa-keyboard"></i>',         cat: 'SYSTEM', isCore: true },
        { id: 'help',         label: 'webui_help_about_title', descKey: 'hub_desc_help',         icon: '<i class="fas fa-circle-question"></i>',  cat: 'SYSTEM', pluginTag: 'HELP', isCore: true }
    ],

    // Fallback Icons based on keywords (for MCP or new plugins)
    iconMap: {
        'search':   '<i class="fas fa-magnifying-glass"></i>',
        'google':   '<i class="fas fa-magnifying-glass"></i>',
        'github':   '<i class="fab fa-github"></i>',
        'maps':     '<i class="fas fa-map-location-dot"></i>',
        'weather':  '<i class="fas fa-cloud-sun"></i>',
        'file':     '<i class="fas fa-file-lines"></i>',
        'drive':    '<i class="fas fa-hard-drive"></i>',
        'tools':    '<i class="fas fa-wrench"></i>',
        'image':    '<i class="fas fa-image"></i>',
        'audio':    '<i class="fas fa-volume-high"></i>',
        'voice':    '<i class="fas fa-microphone-lines"></i>',
        'security': '<i class="fas fa-shield-halved"></i>',
        'network':  '<i class="fas fa-network-wired"></i>',
        'database': '<i class="fas fa-database"></i>',
        'code':     '<i class="fas fa-code"></i>'
    },

    // Plugins that should NOT be shown in the Module Manager UI
    internalTags: [
        'WEB_UI',
        'HELP',
        'PLUGINS',
        'WIDGETS'
    ]
};

window.getIconForModule = function(id, name, metaIcon) {
    if (metaIcon && metaIcon.includes('<i ') && !metaIcon.includes('fa-puzzle-piece')) return metaIcon;

    const extIcons = {
        'netsearch':           '<i class="fas fa-satellite-dish"></i>',
        'net_search':          '<i class="fas fa-satellite-dish"></i>',
        'media_player_widget': '<i class="fas fa-music"></i>',
        'quick_links':         '<i class="fas fa-bolt"></i>',
        'calendar':            '<i class="fas fa-calendar-days"></i>',
        'emoticons':           '<i class="fas fa-face-smile"></i>',
        'weather_widget':      '<i class="fas fa-cloud-sun"></i>',
        'telemetry_widget':    '<i class="fas fa-gauge-high"></i>',
        'weather':             '<i class="fas fa-cloud-sun"></i>',
        'dashboard':           '<i class="fas fa-gauge-high"></i>'
    };
    if (extIcons[id]) return extIcons[id];

    const item = window.CONFIG_HUB.modules.find(m => m.id === id);
    if (item) return item.icon;

    const lower = (name || id || '').toLowerCase();
    for (const [kw, icon] of Object.entries(window.CONFIG_HUB.iconMap)) {
        if (lower.includes(kw)) return icon;
    }
    return '<i class="fas fa-puzzle-piece"></i>';
};

window.CONFIG_HUB.tagMap = {
    'DRIVE':           'drive',
    'EXECUTOR':        'executor',
    'ACTION_PLANS':    'action-plans',
    'WEBCAM':          'webcam',
    'MEMORY':          'memory',
    'MODELS':          'backend',
    'PERSONALITY':     'ia',
    'DRIVE_EDITOR':    'drive-editor',
    'CONTACTS':        'contacts',
    'BROWSER':         'browser',
    'USERS':           'users',
    'FLOWS':           'flows',
    'DOCUMENT_READER': 'document_reader',
    'NETSEARCH':       'netsearch'
};

/**
 * The full set of panel IDs that are served lazily via /hecos/config/fragment/<id>.
 * This MUST match the keys in _PANEL_MAP in routes_config.py.
 * Used by renderConfigHub() to show tabs even before a panel has been fetched.
 */
window.LAZY_PANEL_IDS = new Set([
    'backend', 'keymanager', 'agent', 'ia', 'filters', 'bridge',
    'memory', 'voice', 'document_reader',
    'webcam', 'executor', 'automation',
    'browser', 'netsearch', 'system', 'sysnet', 'users', 'payload', 'plugins',
    'contacts', 'remote-triggers',
    'logs', 'privacy', 'hpm-settings', 'help', 'flows', 'backup', 'shortcuts', 'presenter'
]);

window.SYSTEM_PANELS = [
    'plugins', 'system', 'users',
    'logs', 'privacy', 'hpm-settings', 'help', 'flows', 'backup', 'shortcuts'
];
