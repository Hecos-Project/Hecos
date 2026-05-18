/**
 * cal_utils.js
 * ─────────────────────────────────────────────────────────────────────────────
 * Hecos Calendar — Pure helper functions and utilities
 * ─────────────────────────────────────────────────────────────────────────────
 */

(function () {
    const s = window.hcal_state;

    function _applyDayColors(colors) {
        s.dayColors = colors || {};
        let styleEl = document.getElementById('cal-dynamic-styles');
        if (!styleEl) {
            styleEl = document.createElement('style');
            styleEl.id = 'cal-dynamic-styles';
            document.head.appendChild(styleEl);
        }
        let css = '';
        const dayMap = ['sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat'];
        for (let i = 0; i < 7; i++) {
            const col = s.dayColors[i];
            if (col && col !== 'transparent' && col !== '#00000000') {
                css += `#hecos-fullcalendar .fc-day-${dayMap[i]} { background-color: ${col} !important; }\n`;
                css += `#hecos-fullcalendar .fc-day-${dayMap[i]} .fc-daygrid-day-bg { background-color: ${col} !important; }\n`;
                css += `#hecos-fullcalendar .fc-day-${dayMap[i]} .fc-daygrid-day-frame { background-color: transparent !important; }\n`;
            }
        }
        styleEl.textContent = css;
    }

    function _hexToRgba(hex, alpha) {
        if (!hex || hex === 'transparent' || hex.toUpperCase() === '#00000000' || hex.length < 4) return 'transparent';
        if (hex.startsWith('rgba')) return hex;
        let r = 0, g = 0, b = 0;
        try {
            if (hex.length === 4) {
                r = parseInt(hex[1] + hex[1], 16);
                g = parseInt(hex[2] + hex[2], 16);
                b = parseInt(hex[3] + hex[3], 16);
            } else if (hex.length === 7) {
                r = parseInt(hex.substring(1, 3), 16);
                g = parseInt(hex.substring(3, 5), 16);
                b = parseInt(hex.substring(5, 7), 16);
            } else {
                return 'transparent'; // guard against invalid hex strings
            }
            return `rgba(${r},${g},${b},${alpha})`;
        } catch (e) { return hex; }
    }

    function _fmt(iso) {
        if (!iso) return '';
        try {
            const d = new Date(iso);
            return d.toLocaleDateString(s.localeStr, { weekday: 'short', day: '2-digit', month: 'short', year: 'numeric' })
                 + ' ' + d.toLocaleTimeString(s.localeStr, { hour: '2-digit', minute: '2-digit' });
        } catch (e) { return iso; }
    }

    // Attach to namespace
    Object.assign(window.hcal, {
        _applyDayColors,
        _hexToRgba,
        _fmt
    });
})();
