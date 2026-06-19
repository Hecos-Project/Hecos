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

    // ── Backup / Restore ────────────────────────────────────────────────────────
    async function backupEvents() {
        try {
            if (window.toast) window.toast('info', 'Preparing calendar backup...');
            const res = await fetch('/api/ext/calendar/backup');
            if (!res.ok) throw new Error('Backup request failed');
            const data = await res.json();
            if (!data.ok) throw new Error(data.error || 'Backup failed');

            const defaultFilename = `hecos_calendar_backup_${new Date().toISOString().split('T')[0]}.json`;
            const content = JSON.stringify(data, null, 2);

            if (window.showSaveFilePicker) {
                try {
                    const fileHandle = await window.showSaveFilePicker({
                        suggestedName: defaultFilename,
                        types: [{ description: 'JSON Files', accept: { 'application/json': ['.json'] } }]
                    });
                    const writable = await fileHandle.createWritable();
                    await writable.write(content);
                    await writable.close();
                } catch (err) {
                    if (err.name === 'AbortError') return;
                    throw err;
                }
            } else {
                const blob = new Blob([content], { type: 'application/json' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url; a.download = defaultFilename;
                document.body.appendChild(a); a.click();
                document.body.removeChild(a); URL.revokeObjectURL(url);
            }

            if (window.toast) window.toast('success', `Backup di ${data.count} eventi completato`);
        } catch (err) {
            console.error('[CALENDAR] Backup error:', err);
            if (window.toast) window.toast('error', err.message);
            else alert('Backup error: ' + err.message);
        }
    }

    async function restoreEvents(event) {
        const file = event.target.files[0];
        if (!file) return;
        event.target.value = '';

        let mode = 'duplicate';
        const msg = "Ripristino backup calendario.\n\nOK = Aggiungi come copie (sicuro)\nAnnulla = Sostituisci tutto (cancella gli eventi esistenti)";
        if (!confirm(msg)) {
            mode = 'replace';
            if (!confirm('⚠️ Attenzione: TUTTI gli eventi esistenti verranno cancellati. Continuare?')) return;
        }

        try {
            const text = await file.text();
            const payload = JSON.parse(text);
            if (!payload.events || !Array.isArray(payload.events)) {
                throw new Error("File non valido. Assicurati che sia un backup JSON di Hecos Calendar.");
            }

            if (window.toast) window.toast('info', `Ripristino di ${payload.events.length} eventi...`);

            const res = await fetch('/api/ext/calendar/restore', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ events: payload.events, mode })
            });
            const result = await res.json();
            if (!result.ok) throw new Error(result.error || 'Restore failed');

            if (window.toast) window.toast('success', `Ripristinati ${result.restored_count} eventi`);
            
            // Refresh calendar UI
            if (s.calendar) s.calendar.refetchEvents();
            if (window.calendarWidget) window.calendarWidget.refresh();

        } catch (err) {
            console.error('[CALENDAR] Restore error:', err);
            if (window.toast) window.toast('error', err.message);
            else alert('Restore error: ' + err.message);
        }
    }

    // Attach to namespace
    Object.assign(window.hcal, {
        _applyDayColors,
        _hexToRgba,
        _fmt,
        backupEvents,
        restoreEvents
    });
})();

