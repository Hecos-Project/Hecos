/**
 * calendar_panel.js
 * ─────────────────────────────────────────────────────────────────────────────
 * Hecos Calendar — Full Config Panel Logic
 * Loaded after _calendar_translations.html exposes window.hcalTranslations,
 * and after fullcalendar.min.js + hecos_wheel_picker.js are loaded.
 * ─────────────────────────────────────────────────────────────────────────────
 */
(function () {
    const hcalT = window.hcalTranslations || {};

    let _calendar   = null;
    let _localeStr  = 'en-US';
    let _dayColors  = {};
    let _dayPickers = {};
    let _bgPicker   = null;

    // ─────────────────────────────────────────────────────────────────────────
    // Color Utilities
    // ─────────────────────────────────────────────────────────────────────────

    function _applyDayColors(colors) {
        _dayColors = colors || {};
        let styleEl = document.getElementById('cal-dynamic-styles');
        if (!styleEl) {
            styleEl = document.createElement('style');
            styleEl.id = 'cal-dynamic-styles';
            document.head.appendChild(styleEl);
        }
        let css = '';
        const dayMap = ['sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat'];
        for (let i = 0; i < 7; i++) {
            const col = _dayColors[i];
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
                return 'transparent'; // guard against invalid 8-9 char hex strings
            }
            return `rgba(${r},${g},${b},${alpha})`;
        } catch (e) { return hex; }
    }

    function _fmt(iso) {
        if (!iso) return '';
        try {
            const d = new Date(iso);
            return d.toLocaleDateString(_localeStr, { weekday: 'short', day: '2-digit', month: 'short', year: 'numeric' })
                + ' ' + d.toLocaleTimeString(_localeStr, { hour: '2-digit', minute: '2-digit' });
        } catch (e) { return iso; }
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Initialisation
    // ─────────────────────────────────────────────────────────────────────────

    async function init() {
        const el = document.getElementById('hecos-fullcalendar');
        if (!el || !window.FullCalendar) return;

        let localeStr = 'en-US';
        try {
            const resp = await fetch('/hecos/config');
            const data = await resp.json();
            const calCfg = (data.extensions || {}).calendar || {};
            localeStr  = calCfg.calendar_locale || 'en-US';
            _localeStr = localeStr;

            _applyDayColors(calCfg.day_colors);

            // Populate locale / country dropdowns
            const locEl = document.getElementById('cal-set-locale');
            const cntEl = document.getElementById('cal-set-country');
            if (calCfg.calendar_locale && locEl.querySelector(`option[value="${calCfg.calendar_locale}"]`)) {
                locEl.value = calCfg.calendar_locale;
            }
            if (calCfg.calendar_country && cntEl.querySelector(`option[value="${calCfg.calendar_country}"]`)) {
                cntEl.value = calCfg.calendar_country;
            }

            // Aesthetic picker — calendar background
            _bgPicker = new HecosAestheticPicker('cal-bg-picker-container', {
                initialColor  : calCfg.bg_color || '',
                initialImage  : calCfg.bg_image || '',
                colorLabel    : 'Colore Sfondo Calendario',
                showHex       : false,
                onColorChange : () => saveSettings(),
                onImageChange : () => saveSettings(),
                onClearImage  : () => saveSettings(),
                onReset       : (p) => {
                    console.log('[HCAL] Resetting background aesthetic...');
                    p.currentColor = '';
                    p.currentImage = '';
                    p.render();
                    saveSettings();
                }
            });

            // Aesthetic pickers — day colour grid
            const grid = document.getElementById('cal-days-aesthetic-grid');
            grid.innerHTML = '';
            for (let i = 0; i < 7; i++) {
                const dayDiv = document.createElement('div');
                dayDiv.id = `cal-day-picker-${i}`;
                grid.appendChild(dayDiv);

                let col = calCfg.day_colors ? calCfg.day_colors[i] : '';
                // Convert rgba → hex for the picker UI
                if (col && col.startsWith('rgba')) {
                    const m = col.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/);
                    if (m) {
                        const r = parseInt(m[1]).toString(16).padStart(2, '0');
                        const g = parseInt(m[2]).toString(16).padStart(2, '0');
                        const b = parseInt(m[3]).toString(16).padStart(2, '0');
                        col = `#${r}${g}${b}`;
                    }
                }

                _dayPickers[i] = new HecosAestheticPicker(dayDiv, {
                    initialColor  : col || '',
                    showImage     : false,
                    showHex       : false,
                    colorLabel    : (typeof t === 'function' ? t(`day_${i}`) : null) || `Giorno ${i}`,
                    onColorChange : () => saveSettings(),
                    onColorLive   : () => previewColors(),
                    onReset       : (p) => {
                        console.log('[HCAL] Resetting day aesthetic index...');
                        p.currentColor = '';
                        p.render();
                        previewColors();
                        saveSettings();
                    }
                });
            }

            _syncUrls = calCfg.calendar_sync_urls || [];
            _renderSyncList();

        } catch (e) { console.warn('Calendar config fetch error:', e); }

        // FullCalendar instance
        _calendar = new FullCalendar.Calendar(el, {
            locale      : localeStr,
            initialView : 'dayGridMonth',
            headerToolbar: { left: 'prev,next today', center: 'title', right: '' },
            height      : 'auto',
            eventSources: [
                {
                    events: function (fetchInfo, successCallback, failureCallback) {
                        fetch(`/api/ext/calendar/events?start=${fetchInfo.startStr}&end=${fetchInfo.endStr}`)
                            .then(r => r.json())
                            .then(data => successCallback(data.ok ? data.events : []))
                            .catch(failureCallback);
                    }
                },
                {
                    events: function (fetchInfo, successCallback, failureCallback) {
                        fetch(`/api/ext/calendar/holidays?start=${fetchInfo.startStr}&end=${fetchInfo.endStr}`)
                            .then(r => r.json())
                            .then(data => {
                                if (data && data.error) {
                                    console.error('Holidays Python Error:', data.error);
                                    document.getElementById('cal-form-msg').innerHTML =
                                        `<span style="color:#e74c3c;">Holiday Fetch Error: ${data.error}</span>`;
                                }
                                successCallback(Array.isArray(data) ? data : []);
                            })
                            .catch(failureCallback);
                    }
                }
            ],
            eventClick : function (info) { _showPopup(info); },
            dateClick  : function (info) { openNewEventForm(info.dateStr + 'T09:00:00'); },
        });
        _calendar.render();

        // Fix FullCalendar sizing when initialised inside a hidden tab
        const tabEl = document.getElementById('tab-calendar');
        if (tabEl) {
            const observer = new MutationObserver((mutations) => {
                mutations.forEach((mutation) => {
                    if (mutation.attributeName === 'class' && tabEl.classList.contains('active')) {
                        setTimeout(() => { if (_calendar) _calendar.render(); }, 50);
                    }
                });
            });
            observer.observe(tabEl, { attributes: true });
        }
    }

    // ─────────────────────────────────────────────────────────────────────────
    // View Controls
    // ─────────────────────────────────────────────────────────────────────────

    function setView(view) {
        if (_calendar) _calendar.changeView(view);
        document.querySelectorAll('.cal-view-btn').forEach(b => b.classList.remove('active-view'));
        const map = { dayGridMonth: 'cal-btn-month', timeGridWeek: 'cal-btn-week', listWeek: 'cal-btn-list' };
        if (map[view]) document.getElementById(map[view])?.classList.add('active-view');
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Event Form (Add / Edit)
    // ─────────────────────────────────────────────────────────────────────────

    function openNewEventForm(prefilledStart) {
        hcal.cancelForm();
        document.getElementById('cal-add-form').style.display = 'block';
        document.getElementById('cal-form-title').innerHTML   = '<i class="fas fa-plus"></i> ' + hcalT.addEvent;
        document.getElementById('cal-submit-btn').textContent = hcalT.addEvent;
        document.getElementById('cal-f-title').focus();

        if (prefilledStart) {
            document.getElementById('cal-f-start').value         = prefilledStart;
            document.getElementById('cal-f-start-display').value = _fmt(prefilledStart);
        }

        const cb   = document.getElementById('cal-f-remind');
        const opts = document.getElementById('cal-reminder-options');
        if (cb && opts) {
            cb.onchange = () => { opts.style.display = cb.checked ? 'block' : 'none'; };
            opts.style.display = cb.checked ? 'block' : 'none';
        }
    }

    let _currentEditId = null;

    function editEvent(id) {
        const ev = _calendar.getEventById(id);
        if (!ev) return;

        document.getElementById('cal-event-popup').style.display = 'none';
        hcal.cancelForm();

        _currentEditId = id;
        document.getElementById('cal-add-form').style.display   = 'block';
        document.getElementById('cal-form-title').innerHTML      = '<i class="fas fa-edit"></i> ' + hcalT.edit;
        document.getElementById('cal-submit-btn').textContent    = hcalT.save;

        document.getElementById('cal-f-title').value             = ev.title;
        document.getElementById('cal-f-start').value             = ev.startStr;
        document.getElementById('cal-f-start-display').value     = _fmt(ev.startStr);
        document.getElementById('cal-f-end').value               = ev.endStr || '';
        document.getElementById('cal-f-end-display').value       = ev.endStr ? _fmt(ev.endStr) : '';
        document.getElementById('cal-f-color').value             = ev.backgroundColor || '#3498db';
        document.getElementById('cal-f-allday').checked          = ev.allDay;
        document.getElementById('cal-f-notes').value             = ev.extendedProps.notes || '';

        const hasRemind = ev.extendedProps.has_reminder;
        const cb   = document.getElementById('cal-f-remind');
        const opts = document.getElementById('cal-reminder-options');
        if (cb) {
            cb.checked = hasRemind;
            if (opts) opts.style.display = hasRemind ? 'block' : 'none';
        }
        if (hasRemind) {
            const isInt  = ev.extendedProps.interactive;
            const radios = document.getElementsByName('cal-remind-type');
            radios.forEach(r => { if (r.value === (isInt ? 'interactive' : 'simple')) r.checked = true; });
        }

        document.getElementById('cal-add-form').scrollIntoView({ behavior: 'smooth' });
    }

    function cancelForm() {
        _currentEditId = null;
        document.getElementById('cal-add-form').style.display   = 'none';
        document.getElementById('cal-form-title').innerHTML      = '<i class="fas fa-plus"></i> ' + hcalT.newEvent;
        document.getElementById('cal-submit-btn').textContent    = hcalT.addEvent;

        ['cal-f-title', 'cal-f-start', 'cal-f-start-display', 'cal-f-end', 'cal-f-end-display', 'cal-f-notes']
            .forEach(id => { const el = document.getElementById(id); if (el) el.value = ''; });

        const cb = document.getElementById('cal-f-remind');
        if (cb) {
            cb.checked = false;
            document.getElementById('cal-reminder-options').style.display = 'none';
        }
    }

    function pickStart() {
        HecosWheelPicker.open({
            mode     : 'datetime',
            locale   : document.getElementById('cal-set-locale')?.value || 'it',
            onConfirm: (iso) => {
                document.getElementById('cal-f-start').value         = iso;
                document.getElementById('cal-f-start-display').value = _fmt(iso);
            }
        });
    }

    function pickEnd() {
        HecosWheelPicker.open({
            mode     : 'datetime',
            locale   : document.getElementById('cal-set-locale')?.value || 'it',
            onConfirm: (iso) => {
                document.getElementById('cal-f-end').value         = iso;
                document.getElementById('cal-f-end-display').value = _fmt(iso);
            }
        });
    }

    function submitForm() {
        const title    = (document.getElementById('cal-f-title').value  || '').trim();
        const start    = (document.getElementById('cal-f-start').value  || '').trim();
        const end      = (document.getElementById('cal-f-end').value    || '').trim() || null;
        const color    = document.getElementById('cal-f-color').value;
        const allDay   = document.getElementById('cal-f-allday').checked;
        const remindMe = document.getElementById('cal-f-remind').checked;
        const rType    = document.querySelector('input[name="cal-remind-type"]:checked')?.value;
        const interactive = (rType === 'interactive');
        const notes    = (document.getElementById('cal-f-notes').value  || '').trim() || null;
        const msg      = document.getElementById('cal-form-msg');

        if (!title || !start) { msg.style.color = '#e05'; msg.textContent = hcalT.msgError; return; }

        const url    = _currentEditId ? `/api/ext/calendar/events/${_currentEditId}` : '/api/ext/calendar/events';
        const method = _currentEditId ? 'PUT' : 'POST';

        fetch(url, {
            method  : method,
            headers : { 'Content-Type': 'application/json' },
            body    : JSON.stringify({ title, start, end, color, allDay, notes, remindMe, interactive })
        })
        .then(r => r.json())
        .then(data => {
            msg.style.color = data.ok ? 'var(--accent)' : '#e05';
            msg.innerHTML   = data.ok
                ? '<i class="fas fa-check-circle"></i> ' + hcalT.msgSaved
                : (data.error || hcalT.msgError);
            if (data.ok) {
                if (_calendar) _calendar.refetchEvents();
                if (window.calendarWidget) calendarWidget.refresh();
                if (remindMe && window.reminderWidget) reminderWidget.refresh();
                setTimeout(cancelForm, 1200);
            }
        })
        .catch(() => { msg.style.color = '#e05'; msg.textContent = hcalT.msgError; });
    }

    function deleteEvent(id) {
        if (!confirm('Delete this event?')) return;
        fetch(`/api/ext/calendar/events/${id}`, { method: 'DELETE' })
            .then(r => r.json())
            .then(data => {
                if (data.ok) {
                    document.getElementById('cal-event-popup').style.display = 'none';
                    if (_calendar) _calendar.refetchEvents();
                    if (window.calendarWidget) calendarWidget.refresh();
                }
            });
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Event Popup
    // ─────────────────────────────────────────────────────────────────────────

    function _showPopup(info) {
        const popup      = document.getElementById('cal-event-popup');
        const ev         = info.event;
        const notes      = ev.extendedProps?.notes || '';
        const hasReminder = ev.extendedProps?.has_reminder;

        popup.innerHTML = `
            <div class="pop-title" style="display:flex; align-items:center; justify-content:space-between;">
                ${ev.title}
                ${hasReminder ? '<span title="Reminder Active" style="color:#f1c40f; font-size:14px;"><i class="fas fa-bell"></i></span>' : ''}
            </div>
            <div class="pop-time">📅 ${_fmt(ev.startStr)}${ev.endStr ? ' → ' + _fmt(ev.endStr) : ''}</div>
            ${notes ? `<div class="pop-notes">${notes}</div>` : ''}
            <div class="pop-actions" style="margin-top:12px; display:flex; gap:8px;">
                <button class="pop-edit" onclick="hcal.editEvent('${ev.id}')" style="background:var(--accent); color:white; border:none; padding:4px 10px; border-radius:4px; font-size:12px; cursor:pointer;"><i class="fas fa-edit"></i> ${hcalT.edit}</button>
                <button class="pop-delete" onclick="hcal.deleteEvent('${ev.id}')"><i class="fas fa-trash-alt"></i> ${hcalT.delete}</button>
                <button class="pop-close" onclick="document.getElementById('cal-event-popup').style.display='none'">${hcalT.cancel}</button>
            </div>
        `;
        popup.style.display = 'block';
        const r = info.el.getBoundingClientRect();
        popup.style.top  = (r.bottom + 6) + 'px';
        popup.style.left = Math.min(r.left, window.innerWidth - 340) + 'px';
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Colour Settings
    // ─────────────────────────────────────────────────────────────────────────

    function previewColors() {
        const dayColors = [];
        for (let i = 0; i < 7; i++) {
            if (_dayPickers[i]) {
                const hex = _dayPickers[i].currentColor;
                dayColors[i] = _hexToRgba(hex, (i === 0 ? 0.35 : i === 1 ? 0.25 : 0.2));
            }
        }
        _applyDayColors(dayColors);
    }

    let _saveTimeout = null;
    function handleColorInput() {
        previewColors();
        clearTimeout(_saveTimeout);
        _saveTimeout = setTimeout(saveSettings, 1500);
    }

    function saveSettings() {
        const locale  = document.getElementById('cal-set-locale').value;
        const country = document.getElementById('cal-set-country').value;

        const dayColors = ['', '', '', '', '', '', ''];
        for (let i = 0; i < 7; i++) {
            if (_dayPickers[i]) {
                const hex = _dayPickers[i].currentColor;
                dayColors[i] = _hexToRgba(hex, (i === 0 ? 0.35 : i === 1 ? 0.25 : 0.2));
            }
        }

        const bg_color = _bgPicker ? _bgPicker.currentColor : '';
        const bg_image = _bgPicker ? _bgPicker.currentImage : '';

        const statusEl = document.getElementById('cal-settings-status');
        if (statusEl) {
            statusEl.style.color   = 'var(--muted)';
            statusEl.style.opacity = '1';
            statusEl.innerHTML     = '<i class="fas fa-sync-alt fa-spin"></i> Salvataggio...';
        }

        fetch('/hecos/config', {
            method  : 'POST',
            headers : { 'Content-Type': 'application/json' },
            body    : JSON.stringify({
                extensions: {
                    calendar: {
                        calendar_locale   : locale,
                        calendar_country  : country,
                        day_colors        : dayColors,
                        bg_color          : bg_color,
                        bg_image          : bg_image,
                        calendar_sync_urls: _syncUrls
                    }
                }
            })
        })
        .then(r => r.json())
        .then(d => {
            if (statusEl) {
                if (d.ok) {
                    statusEl.style.color = 'var(--green)';
                    statusEl.innerHTML   = '<i class="fas fa-check"></i> Salvato';
                    setTimeout(() => { statusEl.style.opacity = '0'; }, 3000);
                } else {
                    statusEl.style.color = '#ff5c6c';
                    statusEl.innerHTML   = `<i class="fas fa-exclamation-triangle"></i> Errore: ${d.error || 'Server error'}`;
                }
            }
            if (d.ok) {
                // CRITICAL: Keep window.cfg in sync to prevent stale calendar data
                // overwriting this POST via config_mapper.js buildPayload().
                if (window.cfg) {
                    window.cfg.extensions = window.cfg.extensions || {};
                    window.cfg.extensions.calendar = {
                        calendar_locale   : locale,
                        calendar_country  : country,
                        day_colors        : dayColors,
                        bg_color          : bg_color,
                        bg_image          : bg_image,
                        calendar_sync_urls: _syncUrls
                    };
                }

                _applyDayColors(dayColors);

                // Apply background to card for instant visual feedback
                const card = document.getElementById('tab-calendar')?.querySelector('.card');
                if (card) {
                    if (bg_image) {
                        card.style.backgroundImage    = `url('/media/file?path=${encodeURIComponent(bg_image)}')`;
                        card.style.backgroundSize     = 'cover';
                        card.style.backgroundPosition = 'center';
                    } else {
                        card.style.backgroundImage    = 'none';
                        card.style.backgroundColor   = bg_color || '';
                    }
                }

                if (_calendar) {
                    _calendar.setOption('locale', locale);
                    _calendar.refetchEvents();
                    _calendar.render();
                }

                const status = document.getElementById('cal-sync-status');
                if (status) {
                    status.style.opacity = '1';
                    setTimeout(() => { status.style.opacity = '0'; }, 2000);
                }
            }
        })
        .catch(e => console.error('CALENDAR: Auto-save failed', e));
    }

    function toggleColorSettings() {
        const panel    = document.getElementById('cal-color-settings');
        const btn      = document.getElementById('cal-btn-colors');
        const isHidden = panel.style.display === 'none';
        panel.style.display = isHidden ? 'block' : 'none';
        btn.classList.toggle('active-view', isHidden);
    }

    function toggleSyncSettings() {
        const panel    = document.getElementById('cal-sync-settings');
        const btn      = document.getElementById('cal-btn-sync');
        const isHidden = panel.style.display === 'none';
        panel.style.display = isHidden ? 'block' : 'none';
        btn.classList.toggle('active-view', isHidden);
    }

    // ─────────────────────────────────────────────────────────────────────────
    // iCal Sync URL Management
    // ─────────────────────────────────────────────────────────────────────────

    let _syncUrls = [];

    function _renderSyncList() {
        const list = document.getElementById('cal-sync-list');
        if (!list) return;
        if (_syncUrls.length === 0) {
            list.innerHTML = '<div style="font-size:11px; color:rgba(255,255,255,0.2); font-style:italic;">Nessun calendario esterno configurato.</div>';
            return;
        }
        list.innerHTML = _syncUrls.map((url, idx) => `
            <div style="display:flex; justify-content:space-between; align-items:center; background:rgba(255,255,255,0.03); padding:6px 10px; border-radius:4px; border:1px solid rgba(255,255,255,0.05);">
                <div style="font-size:11px; color:var(--muted); overflow:hidden; text-overflow:ellipsis; white-space:nowrap; flex:1;">${url}</div>
                <button onclick="hcal.removeSyncUrl(${idx})" style="background:none; border:none; color:#e05; cursor:pointer; font-size:14px; margin-left:10px;">&times;</button>
            </div>
        `).join('');
    }

    function addSyncUrl() {
        const input = document.getElementById('cal-sync-new-url');
        const url   = (input.value || '').trim();
        if (!url) return;
        if (!url.startsWith('http')) { alert('URL non valido.'); return; }
        _syncUrls.push(url);
        input.value = '';
        _renderSyncList();
        saveSettings();
    }

    function removeSyncUrl(idx) {
        if (!confirm('Rimuovere questo calendario?')) return;
        _syncUrls.splice(idx, 1);
        _renderSyncList();
        saveSettings();
    }

    function runManualSync() {
        const btn          = document.getElementById('btn-sync-now');
        const originalText = btn.textContent;
        btn.textContent    = 'Syncing...';
        btn.disabled       = true;

        fetch('/api/ext/calendar/sync', { method: 'POST' })
        .then(r => r.json())
        .then(d => {
            btn.innerHTML = d.ok
                ? '<i class="fas fa-check-circle"></i> Done'
                : '<i class="fas fa-exclamation-circle"></i> Error';
            if (d.ok && _calendar) _calendar.refetchEvents();
            if (d.ok && window.calendarWidget) calendarWidget.refresh();
            setTimeout(() => { btn.textContent = originalText; btn.disabled = false; }, 2000);
        })
        .catch(() => {
            btn.innerHTML = '<i class="fas fa-exclamation-circle"></i> Fail';
            btn.disabled  = false;
            setTimeout(() => { btn.textContent = originalText; }, 2000);
        });
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Global Reset
    // ─────────────────────────────────────────────────────────────────────────

    function resetAllAesthetics() {
        if (!confirm('Ripristinare TUTTI i colori e lo sfondo ai valori predefiniti?')) return;
        console.log('[HCAL] Global reset triggered...');
        for (let i = 0; i < 7; i++) {
            if (_dayPickers[i]) { _dayPickers[i].currentColor = ''; _dayPickers[i].render(); }
        }
        if (_bgPicker) { _bgPicker.currentColor = ''; _bgPicker.currentImage = ''; _bgPicker.render(); }
        previewColors();
        saveSettings();
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Global Event Listeners & Bootstrap
    // ─────────────────────────────────────────────────────────────────────────

    // Close popup on outside click
    document.addEventListener('click', function (e) {
        const popup = document.getElementById('cal-event-popup');
        if (popup && !popup.contains(e.target) && !e.target.closest('.fc-event'))
            popup.style.display = 'none';
    });

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        setTimeout(init, 100);
    }

    // Public API
    window.hcal = {
        setView, openNewEventForm, editEvent, cancelForm,
        pickStart, pickEnd, submitForm, deleteEvent,
        saveSettings, previewColors, handleColorInput,
        toggleColorSettings, toggleSyncSettings,
        addSyncUrl, removeSyncUrl, runManualSync,
        refresh: () => { if (_calendar) _calendar.refetchEvents(); },
        resetAllAesthetics
    };
})();
