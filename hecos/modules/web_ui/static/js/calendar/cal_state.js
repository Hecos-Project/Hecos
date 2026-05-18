/**
 * cal_state.js
 * ─────────────────────────────────────────────────────────────────────────────
 * Hecos Calendar — Shared State and Namespace
 * ─────────────────────────────────────────────────────────────────────────────
 */

window.hcal_state = {
    calendar: null,
    localeStr: 'en-US',
    dayColors: {},
    dayPickers: {},
    bgPicker: null,
    syncUrls: [],
    currentEditId: null,
    saveTimeout: null
};

// Expose public API boundary early so other files can attach methods
window.hcal = window.hcal || {};
