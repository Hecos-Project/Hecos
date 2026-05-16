/**
 * cal_events.js
 * ─────────────────────────────────────────────────────────────────────────────
 * Hecos Calendar — Events UI Forms, Popup, Date Picking, Save/Delete
 * ─────────────────────────────────────────────────────────────────────────────
 */

(function () {
    const s = window.hcal_state;
    const hcalT = window.hcalTranslations || {};

    function setView(view) {
        if (s.calendar) s.calendar.changeView(view);
        document.querySelectorAll('.cal-view-btn').forEach(b => b.classList.remove('active-view'));
        const map = { dayGridMonth: 'cal-btn-month', timeGridWeek: 'cal-btn-week', listWeek: 'cal-btn-list' };
        if (map[view]) document.getElementById(map[view])?.classList.add('active-view');
    }

    function openNewEventForm(prefilledStart) {
        cancelForm();
        document.getElementById('cal-add-form').style.display = 'block';
        document.getElementById('cal-form-title').innerHTML   = '<i class="fas fa-plus"></i> ' + (hcalT.addEvent || 'Add');
        document.getElementById('cal-submit-btn').textContent = hcalT.addEvent || 'Add';
        document.getElementById('cal-f-title').focus();

        if (prefilledStart) {
            document.getElementById('cal-f-start').value         = prefilledStart;
            document.getElementById('cal-f-start-display').value = window.hcal._fmt(prefilledStart);
        }

        const cb   = document.getElementById('cal-f-remind');
        const opts = document.getElementById('cal-reminder-options');
        if (cb && opts) {
            cb.onchange = () => { opts.style.display = cb.checked ? 'block' : 'none'; };
            opts.style.display = cb.checked ? 'block' : 'none';
        }
    }

    function editEvent(id) {
        const ev = s.calendar.getEventById(id);
        if (!ev) return;

        document.getElementById('cal-event-popup').style.display = 'none';
        cancelForm();

        s.currentEditId = id;
        document.getElementById('cal-add-form').style.display   = 'block';
        document.getElementById('cal-form-title').innerHTML      = '<i class="fas fa-edit"></i> ' + (hcalT.edit || 'Edit');
        document.getElementById('cal-submit-btn').textContent    = hcalT.save || 'Save';

        document.getElementById('cal-f-title').value             = ev.title;
        document.getElementById('cal-f-start').value             = ev.startStr;
        document.getElementById('cal-f-start-display').value     = window.hcal._fmt(ev.startStr);
        document.getElementById('cal-f-end').value               = ev.endStr || '';
        document.getElementById('cal-f-end-display').value       = ev.endStr ? window.hcal._fmt(ev.endStr) : '';
        document.getElementById('cal-f-color').value             = ev.backgroundColor || '#3498db';
        document.getElementById('cal-f-allday').checked          = ev.allDay;
        document.getElementById('cal-f-notes').value             = ev.extendedProps.notes || '';

        const hasRemind = ev.extendedProps.has_reminder;
        const cb   = document.getElementById('cal-f-remind');
        const opts = document.getElementById('cal-reminder-options');
        if (cb) {
            cb.checked = hasRemind;
            if (opts) {
                opts.style.display = hasRemind ? 'block' : 'none';
                cb.onchange = () => { opts.style.display = cb.checked ? 'block' : 'none'; };
            }
        }
        if (hasRemind) {
            const isInt  = ev.extendedProps.interactive;
            const radios = document.getElementsByName('cal-remind-type');
            radios.forEach(r => { if (r.value === (isInt ? 'interactive' : 'simple')) r.checked = true; });
        }

        document.getElementById('cal-add-form').scrollIntoView({ behavior: 'smooth' });
    }

    function cancelForm() {
        s.currentEditId = null;
        document.getElementById('cal-add-form').style.display   = 'none';
        document.getElementById('cal-form-title').innerHTML      = '<i class="fas fa-plus"></i> ' + (hcalT.newEvent || 'New');
        document.getElementById('cal-submit-btn').textContent    = hcalT.addEvent || 'Add';

        ['cal-f-title', 'cal-f-start', 'cal-f-start-display', 'cal-f-end', 'cal-f-end-display', 'cal-f-notes']
            .forEach(id => { const el = document.getElementById(id); if (el) el.value = ''; });

        const cb = document.getElementById('cal-f-remind');
        if (cb) {
            cb.checked = false;
            document.getElementById('cal-reminder-options').style.display = 'none';
        }
    }

    function pickStart() {
        if (!window.HecosWheelPicker) return;
        HecosWheelPicker.open({
            mode     : 'datetime',
            locale   : document.getElementById('cal-set-locale')?.value || 'it',
            onConfirm: (iso) => {
                document.getElementById('cal-f-start').value         = iso;
                document.getElementById('cal-f-start-display').value = window.hcal._fmt(iso);
            }
        });
    }

    function pickEnd() {
        if (!window.HecosWheelPicker) return;
        HecosWheelPicker.open({
            mode     : 'datetime',
            locale   : document.getElementById('cal-set-locale')?.value || 'it',
            onConfirm: (iso) => {
                document.getElementById('cal-f-end').value         = iso;
                document.getElementById('cal-f-end-display').value = window.hcal._fmt(iso);
            }
        });
    }

    function submitForm() {
        const btn      = document.getElementById('cal-submit-btn');
        if (btn && btn.disabled) return; // Prevent multiple clicks

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

        if (!title || !start) { msg.style.color = '#e05'; msg.textContent = hcalT.msgError || 'Error'; return; }

        let originalBtnHtml = '';
        if (btn) {
            originalBtnHtml = btn.innerHTML;
            btn.disabled = true;
            btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
        }

        const url    = s.currentEditId ? `/api/ext/calendar/events/${s.currentEditId}` : '/api/ext/calendar/events';
        const method = s.currentEditId ? 'PUT' : 'POST';

        fetch(url, {
            method  : method,
            headers : { 'Content-Type': 'application/json' },
            body    : JSON.stringify({ title, start, end, color, allDay, notes, remindMe, interactive })
        })
        .then(r => r.json())
        .then(data => {
            msg.style.color = data.ok ? 'var(--accent)' : '#e05';
            msg.innerHTML   = data.ok
                ? '<i class="fas fa-check-circle"></i> ' + (hcalT.msgSaved || 'Saved')
                : (data.error || hcalT.msgError || 'Error');
            if (data.ok) {
                if (s.calendar) s.calendar.refetchEvents();
                if (window.calendarWidget) calendarWidget.refresh();
                if (remindMe && window.reminderWidget) reminderWidget.refresh();
                setTimeout(cancelForm, 1200);
            }
        })
        .catch(() => { msg.style.color = '#e05'; msg.textContent = hcalT.msgError || 'Error'; })
        .finally(() => {
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = originalBtnHtml;
            }
        });
    }

    function deleteEvent(id) {
        if (!confirm('Delete this event?')) return;
        fetch(`/api/ext/calendar/events/${id}`, { method: 'DELETE' })
            .then(r => r.json())
            .then(data => {
                if (data.ok) {
                    document.getElementById('cal-event-popup').style.display = 'none';
                    if (s.calendar) s.calendar.refetchEvents();
                    if (window.calendarWidget) calendarWidget.refresh();
                }
            });
    }

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
            <div class="pop-time">📅 ${window.hcal._fmt(ev.startStr)}${ev.endStr ? ' → ' + window.hcal._fmt(ev.endStr) : ''}</div>
            ${notes ? `<div class="pop-notes">${notes}</div>` : ''}
            <div class="pop-actions" style="margin-top:12px; display:flex; gap:8px;">
                <button class="pop-edit" onclick="hcal.editEvent('${ev.id}')" style="background:var(--accent); color:white; border:none; padding:4px 10px; border-radius:4px; font-size:12px; cursor:pointer;"><i class="fas fa-edit"></i> ${hcalT.edit || 'Edit'}</button>
                <button class="pop-delete" onclick="hcal.deleteEvent('${ev.id}')"><i class="fas fa-trash-alt"></i> ${hcalT.delete || 'Delete'}</button>
                <button class="pop-close" onclick="document.getElementById('cal-event-popup').style.display='none'">${hcalT.cancel || 'Cancel'}</button>
            </div>
        `;
        popup.style.display = 'block';
        const r = info.el.getBoundingClientRect();
        popup.style.top  = (r.bottom + 6) + 'px';
        popup.style.left = Math.min(r.left, window.innerWidth - 340) + 'px';
    }

    Object.assign(window.hcal, {
        setView, openNewEventForm, editEvent, cancelForm,
        pickStart, pickEnd, submitForm, deleteEvent, _showPopup
    });

})();
