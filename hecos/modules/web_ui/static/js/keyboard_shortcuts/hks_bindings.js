/**
 * hks_bindings.js — Hecos Keyboard Shortcuts Binding Manager
 * ─────────────────────────────────────────────────────────────────────────────
 * Manages the mapping between action IDs and keyboard combos.
 * Persists bindings to localStorage and optionally syncs with the backend.
 *
 * API (window.HKS_BINDINGS):
 *   getAll()                    → { actionId: 'combo', ... }
 *   get(actionId)               → 'combo' | null
 *   set(actionId, combo)        → { ok, conflict? }
 *   reset(actionId)             → restores default for one action
 *   resetAll()                  → restores all defaults
 *   save()                      → persist to localStorage + backend
 *   load()                      → load from localStorage (or backend)
 *   getDefaults()               → returns default bindings object
 *   getConflicts()              → list of [combo, [actionIds]] conflicts
 *
 * Dependencies: hks_core.js (must be loaded first)
 * ─────────────────────────────────────────────────────────────────────────────
 */

(function () {
    'use strict';

    const STORAGE_KEY   = 'hecos_hks_bindings';
    const PREFS_KEY     = 'hecos_hks_prefs';
    const VERSION_KEY   = 'hecos_hks_version';
    const BINDINGS_VER  = '3'; // ← increment this whenever DEFAULTS change

    // ── Default bindings ──────────────────────────────────────────────────────
    // Inspired by Linux terminal function key conventions.

    const DEFAULTS = {
        'nav.packages':      'f1',
        'nav.backend':       'f2',
        'nav.ia':            'f3',
        'ui.toggle_mic':     'f4',
        'ui.toggle_voice':   'f6',
        'nav.hub':           'f7',
        'ui.toggle_ptt':     'f8',
        'sys.reboot':        'f9',
        
        'nav.chat':          'f10',
        'nav.home':          'f11',
        'ui.open_hdcs':      'f12',
        
        'ui.ptt_trigger':    'ctrl+shift',
        'nav.drive':         'ctrl+shift+d',
        'nav.flows':         'ctrl+shift+f',
        'ui.toggle_room':    'ctrl+shift+r',
        'ui.toggle_sidebar': 'ctrl+b',
        'ui.new_chat':       'ctrl+enter',
        
        'ui.show_cheatsheet':'?',
        'nav.shortcuts':     'ctrl+,',
        'ui.close_modal':    'escape',
        'ui.copy_last':      'ctrl+shift+c',
        'ui.toggle_history': 'ctrl+shift+h',
        'ui.focus_input':    'ctrl+shift+i',
        'focus.next':        'ctrl+tab',
        'focus.prev':        'ctrl+shift+tab'
    };

    // Default preferences
    const DEFAULT_PREFS = {
        toastEnabled: true,
        fKeysEnabled: true,
        tabCycleEnabled: true
    };

    // ── State ─────────────────────────────────────────────────────────────────

    let _bindings = Object.assign({}, DEFAULTS);
    let _prefs    = Object.assign({}, DEFAULT_PREFS);

    // ── Helpers ───────────────────────────────────────────────────────────────

    /**
     * Load bindings from localStorage.
     */
    function _loadFromStorage() {
        try {
            // ── Version guard: if DEFAULTS changed, wipe old bindings ──────────
            const savedVer = localStorage.getItem(VERSION_KEY);
            if (savedVer !== BINDINGS_VER) {
                console.log('[HKS Bindings] Bindings version mismatch (saved:', savedVer, '→ current:', BINDINGS_VER, ') — resetting to defaults.');
                _bindings = Object.assign({}, DEFAULTS);
                localStorage.removeItem(STORAGE_KEY);
                localStorage.setItem(VERSION_KEY, BINDINGS_VER);
            } else {
                const raw = localStorage.getItem(STORAGE_KEY);
                if (raw) {
                    const saved = JSON.parse(raw);
                    // User-customized bindings take priority, but only for keys
                    // that still exist in DEFAULTS (orphaned bindings are dropped)
                    const clean = {};
                    for (const id of Object.keys(DEFAULTS)) {
                        clean[id] = (saved[id] !== undefined) ? saved[id] : DEFAULTS[id];
                    }
                    _bindings = clean;
                } else {
                    _bindings = Object.assign({}, DEFAULTS);
                }
            }
        } catch (e) {
            console.warn('[HKS Bindings] Could not load from storage:', e);
            _bindings = Object.assign({}, DEFAULTS);
        }

        try {
            const rawPrefs = localStorage.getItem(PREFS_KEY);
            if (rawPrefs) {
                _prefs = Object.assign({}, DEFAULT_PREFS, JSON.parse(rawPrefs));
            }
        } catch (e) {
            _prefs = Object.assign({}, DEFAULT_PREFS);
        }
    }

    /**
     * Save bindings to localStorage.
     */
    function _saveToStorage() {
        try {
            localStorage.setItem(STORAGE_KEY, JSON.stringify(_bindings));
            localStorage.setItem(PREFS_KEY, JSON.stringify(_prefs));
            localStorage.setItem(VERSION_KEY, BINDINGS_VER);
        } catch (e) {
            console.warn('[HKS Bindings] Could not save to storage:', e);
        }
    }

    /**
     * Sync bindings with the backend (non-blocking).
     */
    async function _syncWithBackend(bindings) {
        try {
            await fetch('/api/shortcuts/bindings', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ bindings, prefs: _prefs })
            });
        } catch (e) {
            // Backend sync failure is non-fatal — localStorage is the source of truth
            console.debug('[HKS Bindings] Backend sync skipped (offline?):', e.message);
        }
    }

    /**
     * Load bindings from backend (fallback if localStorage is empty).
     */
    async function _loadFromBackend() {
        try {
            const res = await fetch('/api/shortcuts/bindings');
            if (!res.ok) return;
            const data = await res.json();
            if (data.ok && data.bindings) {
                _bindings = Object.assign({}, DEFAULTS, data.bindings);
                if (data.prefs) _prefs = Object.assign({}, DEFAULT_PREFS, data.prefs);
                _saveToStorage();
            }
        } catch (e) {
            console.debug('[HKS Bindings] Backend load skipped:', e.message);
        }
    }

    /**
     * Detect conflicts: return a map of combo → [actionIds] for combos used by 2+.
     */
    function _detectConflicts(bindings) {
        const comboToActions = {};
        for (const [id, combo] of Object.entries(bindings)) {
            if (!combo) continue;
            if (!comboToActions[combo]) comboToActions[combo] = [];
            comboToActions[combo].push(id);
        }
        const conflicts = [];
        for (const [combo, ids] of Object.entries(comboToActions)) {
            if (ids.length > 1) conflicts.push({ combo, actions: ids });
        }
        return conflicts;
    }

    // ── Public API ────────────────────────────────────────────────────────────

    window.HKS_BINDINGS = {

        /**
         * Initialize: load from storage, optionally sync with backend.
         */
        init() {
            _loadFromStorage();
            // If no local bindings, try backend
            const hasLocal = localStorage.getItem(STORAGE_KEY) !== null;
            if (!hasLocal) {
                _loadFromBackend();
            }
            console.log('[HKS Bindings] Loaded. Active bindings:', Object.keys(_bindings).length);
        },

        /**
         * Get all current bindings.
         */
        getAll() { return Object.assign({}, _bindings); },

        /**
         * Get the combo for a specific action.
         */
        get(actionId) { return _bindings[actionId] || null; },

        /**
         * Assign a new combo to an action.
         * @returns { ok: bool, conflict?: { combo, actions: [id, id] } }
         */
        set(actionId, combo) {
            if (!combo) {
                _bindings[actionId] = null;
                _saveToStorage();
                return { ok: true };
            }

            // Check for conflict with other actions
            const existing = Object.entries(_bindings).find(
                ([id, c]) => c === combo && id !== actionId
            );
            if (existing) {
                return {
                    ok: false,
                    conflict: { combo, conflictWith: existing[0] }
                };
            }

            _bindings[actionId] = combo;
            _saveToStorage();
            return { ok: true };
        },

        /**
         * Set a combo, overwriting any existing conflict.
         */
        forceSet(actionId, combo) {
            // Remove this combo from any action that currently has it
            for (const [id, c] of Object.entries(_bindings)) {
                if (c === combo && id !== actionId) {
                    _bindings[id] = null;
                }
            }
            _bindings[actionId] = combo;
            _saveToStorage();
            return { ok: true };
        },

        /**
         * Reset a single action to its default binding.
         */
        reset(actionId) {
            _bindings[actionId] = DEFAULTS[actionId] || null;
            _saveToStorage();
        },

        /**
         * Reset all bindings to defaults.
         */
        resetAll() {
            _bindings = Object.assign({}, DEFAULTS);
            _saveToStorage();
            _syncWithBackend(_bindings);
            console.log('[HKS Bindings] Reset to defaults.');
        },

        /**
         * Persist to localStorage and sync with backend.
         */
        save() {
            _saveToStorage();
            _syncWithBackend(_bindings);
        },

        /**
         * Reload from localStorage (useful after external changes).
         */
        load() {
            _loadFromStorage();
        },

        /**
         * Get the default binding for an action.
         */
        getDefault(actionId) { return DEFAULTS[actionId] || null; },

        /**
         * Get all defaults.
         */
        getDefaults() { return Object.assign({}, DEFAULTS); },

        /**
         * Get list of conflicts in current bindings.
         */
        getConflicts() { return _detectConflicts(_bindings); },

        /**
         * Get/set user preferences.
         */
        getPrefs() { return Object.assign({}, _prefs); },

        setPrefs(newPrefs) {
            _prefs = Object.assign({}, _prefs, newPrefs);
            _saveToStorage();
            _syncWithBackend(_bindings);
        },

        getPref(key) { return _prefs[key]; },
        setPref(key, value) { this.setPrefs({ [key]: value }); },

        /**
         * Format a combo string for display as keyboard keys.
         * e.g. 'ctrl+shift+k' → 'Ctrl+Shift+K'
         */
        formatCombo(combo) {
            if (!combo) return '—';
            return combo.split('+').map(part => {
                if (part === 'ctrl')  return 'Ctrl';
                if (part === 'alt')   return 'Alt';
                if (part === 'shift') return 'Shift';
                if (part.startsWith('f') && !isNaN(part.slice(1))) return part.toUpperCase();
                return part.toUpperCase().length === 1 ? part.toUpperCase() : part;
            }).join('+');
        }
    };

    // Auto-initialize
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => window.HKS_BINDINGS.init());
    } else {
        window.HKS_BINDINGS.init();
    }

})();
