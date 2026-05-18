/**
 * cal_init.js
 * ─────────────────────────────────────────────────────────────────────────────
 * Hecos Calendar — FullCalendar Bootloader and Initial Fetch
 * ─────────────────────────────────────────────────────────────────────────────
 */

(function () {
    const s = window.hcal_state;

    async function init() {
        const el = document.getElementById('hecos-fullcalendar');
        if (!el || !window.FullCalendar) return;

        try {
            const resp = await fetch('/hecos/config');
            const data = await resp.json();
            const calCfg = (data.extensions || {}).calendar || {};
            
            s.localeStr  = calCfg.calendar_locale || 'en-US';
            window.hcal._applyDayColors(calCfg.day_colors);

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
            if (window.HecosAestheticPicker) {
                s.bgPicker = new HecosAestheticPicker('cal-bg-picker-container', {
                    initialColor  : calCfg.bg_color || '',
                    initialImage  : calCfg.bg_image || '',
                    colorLabel    : 'Colore Sfondo Calendario',
                    showHex       : false,
                    onColorChange : () => window.hcal.saveSettings(),
                    onImageChange : () => window.hcal.saveSettings(),
                    onClearImage  : () => window.hcal.saveSettings(),
                    onReset       : (p) => {
                        console.log('[HCAL] Resetting background aesthetic...');
                        p.currentColor = '';
                        p.currentImage = '';
                        p.render();
                        window.hcal.saveSettings();
                    }
                });

                // Aesthetic pickers — day colour grid
                const grid = document.getElementById('cal-days-aesthetic-grid');
                if (grid) {
                    grid.innerHTML = '';
                    for (let i = 0; i < 7; i++) {
                        const dayDiv = document.createElement('div');
                        dayDiv.id = `cal-day-picker-${i}`;
                        grid.appendChild(dayDiv);

                        let col = calCfg.day_colors ? calCfg.day_colors[i] : '';
                        if (col && col.startsWith('rgba')) {
                            const m = col.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/);
                            if (m) {
                                const r = parseInt(m[1]).toString(16).padStart(2, '0');
                                const g = parseInt(m[2]).toString(16).padStart(2, '0');
                                const b = parseInt(m[3]).toString(16).padStart(2, '0');
                                col = `#${r}${g}${b}`;
                            }
                        }

                        s.dayPickers[i] = new HecosAestheticPicker(dayDiv, {
                            initialColor  : col || '',
                            showImage     : false,
                            showHex       : false,
                            colorLabel    : (typeof t === 'function' ? window.t(`day_${i}`) : null) || `Giorno ${i}`,
                            onColorChange : () => window.hcal.saveSettings(),
                            onColorLive   : () => window.hcal.previewColors(),
                            onReset       : (p) => {
                                console.log('[HCAL] Resetting day aesthetic index...');
                                p.currentColor = '';
                                p.render();
                                window.hcal.previewColors();
                                window.hcal.saveSettings();
                            }
                        });
                    }
                }
            }

            s.syncUrls = calCfg.calendar_sync_urls || [];
            window.hcal._renderSyncList();

        } catch (e) { console.warn('Calendar config fetch error:', e); }

        // FullCalendar instance
        s.calendar = new FullCalendar.Calendar(el, {
            locale      : s.localeStr,
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
                                    const msg = document.getElementById('cal-form-msg');
                                    if (msg) msg.innerHTML = `<span style="color:#e74c3c;">Holiday Fetch Error: ${data.error}</span>`;
                                }
                                successCallback(Array.isArray(data) ? data : []);
                            })
                            .catch(failureCallback);
                    }
                }
            ],
            eventClick : function (info) { window.hcal._showPopup(info); },
            dateClick  : function (info) { window.hcal.openNewEventForm(info.dateStr + 'T09:00:00'); },
        });
        s.calendar.render();

        // Fix FullCalendar sizing when initialised inside a hidden tab
        const tabEl = document.getElementById('tab-calendar');
        if (tabEl) {
            const observer = new MutationObserver((mutations) => {
                mutations.forEach((mutation) => {
                    if (mutation.attributeName === 'class' && tabEl.classList.contains('active')) {
                        setTimeout(() => { if (s.calendar) s.calendar.render(); }, 50);
                    }
                });
            });
            observer.observe(tabEl, { attributes: true });
        }
    }

    // Bind public refresh function mapping to state
    window.hcal.refresh = () => { if (s.calendar) s.calendar.refetchEvents(); };

    // Initialise on load
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        setTimeout(init, 100);
    }

    // Close popup on outside click
    document.addEventListener('click', function (e) {
        const popup = document.getElementById('cal-event-popup');
        if (popup && !popup.contains(e.target) && !e.target.closest('.fc-event')) {
            popup.style.display = 'none';
        }
    });

})();
