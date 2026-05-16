/**
 * cal_config.js
 * ─────────────────────────────────────────────────────────────────────────────
 * Hecos Calendar — Aesthetic Pickers, Settings Sync, iCal Management
 * ─────────────────────────────────────────────────────────────────────────────
 */

(function () {
    const s = window.hcal_state;

    function previewColors() {
        const dayColors = [];
        for (let i = 0; i < 7; i++) {
            if (s.dayPickers[i]) {
                const hex = s.dayPickers[i].currentColor;
                dayColors[i] = window.hcal._hexToRgba(hex, (i === 0 ? 0.35 : i === 1 ? 0.25 : 0.2));
            }
        }
        window.hcal._applyDayColors(dayColors);
    }

    function handleColorInput() {
        previewColors();
        clearTimeout(s.saveTimeout);
        s.saveTimeout = setTimeout(saveSettings, 1500);
    }

    function saveSettings() {
        const localeEl = document.getElementById('cal-set-locale');
        const countryEl = document.getElementById('cal-set-country');
        const calC = (window.cfg && window.cfg.extensions) ? window.cfg.extensions.calendar : {};
        const locale = localeEl ? localeEl.value : (calC.calendar_locale || s.localeStr || 'en-US');
        const country = countryEl ? countryEl.value : (calC.calendar_country || 'US');

        const dayColors = ['', '', '', '', '', '', ''];
        for (let i = 0; i < 7; i++) {
            if (s.dayPickers[i]) {
                const hex = s.dayPickers[i].currentColor;
                dayColors[i] = window.hcal._hexToRgba(hex, (i === 0 ? 0.35 : i === 1 ? 0.25 : 0.2));
            }
        }

        const bg_color = s.bgPicker ? s.bgPicker.currentColor : '';
        const bg_image = s.bgPicker ? s.bgPicker.currentImage : '';

        const statusEl = document.getElementById('cal-settings-status');
        if (statusEl) {
            statusEl.style.color   = 'var(--muted)';
            statusEl.style.opacity = '1';
            statusEl.innerHTML     = '<i class="fas fa-sync-alt fa-spin"></i> Salvataggio...';
        }

        const calendarDataToSave = {
            calendar_locale   : locale,
            calendar_country  : country,
            day_colors        : dayColors,
            bg_color          : bg_color,
            bg_image          : bg_image,
            calendar_sync_urls: s.syncUrls
        };

        // CRITICAL: Keep window.cfg in sync synchronously BEFORE the fetch to prevent stale calendar data
        // overwriting this POST via config_mapper.js buildPayload() during a global dashboard save.
        if (window.cfg) {
            window.cfg.extensions = window.cfg.extensions || {};
            window.cfg.extensions.calendar = calendarDataToSave;
        }

        // Post settings deeply inside extension structure
        fetch('/hecos/config', {
            method  : 'POST',
            headers : { 'Content-Type': 'application/json' },
            body    : JSON.stringify({
                extensions: {
                    calendar: calendarDataToSave
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
                window.hcal._applyDayColors(dayColors);

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

                if (s.calendar) {
                    s.calendar.setOption('locale', locale);
                    s.calendar.refetchEvents();
                    s.calendar.render();
                }

                const syncStatus = document.getElementById('cal-sync-status');
                if (syncStatus) {
                    syncStatus.style.opacity = '1';
                    setTimeout(() => { syncStatus.style.opacity = '0'; }, 2000);
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

    function _renderSyncList() {
        const list = document.getElementById('cal-sync-list');
        if (!list) return;
        if (s.syncUrls.length === 0) {
            list.innerHTML = '<div style="font-size:11px; color:rgba(255,255,255,0.2); font-style:italic;">Nessun calendario esterno configurato.</div>';
            return;
        }
        list.innerHTML = s.syncUrls.map((url, idx) => `
            <div style="display:flex; justify-content:space-between; align-items:center; background:rgba(255,255,255,0.03); padding:6px 10px; border-radius:4px; border:1px solid rgba(255,255,255,0.05);">
                <div style="font-size:11px; color:var(--muted); overflow:hidden; text-overflow:ellipsis; white-space:nowrap; flex:1;">${url}</div>
                <button onclick="hcal.removeSyncUrl(${idx})" style="background:none; border:none; color:#e05; cursor:pointer; font-size:14px; margin-left:10px;">&times;</button>
            </div>
        `).join('');
    }

    function addSyncUrl() {
        const input = document.getElementById('cal-sync-new-url');
        if (!input) return;
        const url   = (input.value || '').trim();
        if (!url) return;
        if (!url.startsWith('http')) { alert('URL non valido.'); return; }
        s.syncUrls.push(url);
        input.value = '';
        _renderSyncList();
        saveSettings();
    }

    function removeSyncUrl(idx) {
        if (!confirm('Rimuovere questo calendario?')) return;
        s.syncUrls.splice(idx, 1);
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
            if (d.ok && s.calendar) s.calendar.refetchEvents();
            if (d.ok && window.calendarWidget) calendarWidget.refresh();
            setTimeout(() => { btn.textContent = originalText; btn.disabled = false; }, 2000);
        })
        .catch(() => {
            btn.innerHTML = '<i class="fas fa-exclamation-circle"></i> Fail';
            btn.disabled  = false;
            setTimeout(() => { btn.textContent = originalText; }, 2000);
        });
    }

    function resetAllAesthetics() {
        if (!confirm('Ripristinare TUTTI i colori e lo sfondo ai valori predefiniti?')) return;
        console.log('[HCAL] Global reset triggered...');
        for (let i = 0; i < 7; i++) {
            if (s.dayPickers[i]) { s.dayPickers[i].currentColor = ''; s.dayPickers[i].render(); }
        }
        if (s.bgPicker) { s.bgPicker.currentColor = ''; s.bgPicker.currentImage = ''; s.bgPicker.render(); }
        previewColors();
        saveSettings();
    }

    Object.assign(window.hcal, {
        previewColors, handleColorInput, saveSettings,
        toggleColorSettings, toggleSyncSettings,
        _renderSyncList, addSyncUrl, removeSyncUrl, runManualSync,
        resetAllAesthetics
    });

})();
