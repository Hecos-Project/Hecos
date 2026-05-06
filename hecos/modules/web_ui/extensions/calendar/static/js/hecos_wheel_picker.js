/**
 * HecosWheelPicker — Shared datetime tumbler component
 * Usage: HecosWheelPicker.open({ onConfirm: (isoString) => {}, mode: 'datetime' })
 * Requires no external dependencies.
 */
(function(global) {
  'use strict';

  const ITEM_H = 40; // px height of each item in the wheel

  function _pad(n) { return String(n).padStart(2, '0'); }

  function _buildColumn(id, items, selectedIndex) {
    const col = document.createElement('div');
    col.className = 'hwp-col';
    col.dataset.id = id;

    const track = document.createElement('div');
    track.className = 'hwp-track';

    items.forEach((item, i) => {
      const el = document.createElement('div');
      el.className = 'hwp-item';
      el.textContent = item.label;
      el.dataset.value = item.value;
      track.appendChild(el);
    });

    col.appendChild(track);

    // Scroll to initial selection after mount
    requestAnimationFrame(() => {
      track.scrollTop = selectedIndex * ITEM_H;
    });

    return { col, track };
  }

  function _readSelected(track) {
    const top = track.scrollTop;
    const index = Math.round(top / ITEM_H);
    const items = track.querySelectorAll('.hwp-item');
    return items[Math.min(index, items.length - 1)]?.dataset.value || null;
  }

  function _generateDays(year, month) {
    const days = new Date(year, month, 0).getDate();
    return Array.from({ length: days }, (_, i) => ({ label: _pad(i + 1), value: _pad(i + 1) }));
  }

  function open(opts = {}) {
    const mode = opts.mode || 'datetime'; // 'datetime' or 'time'
    const onConfirm = opts.onConfirm || (() => {});
    const onCancel = opts.onCancel || (() => {});

    const now = opts.initial ? new Date(opts.initial) : new Date();

    // Destroy any existing picker
    const existing = document.getElementById('hwp-overlay');
    if (existing) existing.remove();

    // ── Overlay ────────────────────────────────────────────────────────────────
    const overlay = document.createElement('div');
    overlay.id = 'hwp-overlay';
    overlay.innerHTML = `
      <div id="hwp-modal">
        <div id="hwp-header">
          <span id="hwp-title">📅 ${mode === 'time' ? 'Select Time' : 'Select Date & Time'}</span>
          <button id="hwp-close">✕</button>
        </div>
        <div id="hwp-wheels-wrap">
          <div id="hwp-wheels"></div>
          <div id="hwp-highlight"></div>
        </div>
        <div id="hwp-footer">
          <button id="hwp-cancel">Cancel</button>
          <button id="hwp-confirm">Confirm</button>
        </div>
      </div>
    `;
    document.body.appendChild(overlay);

    const wheelsEl = overlay.querySelector('#hwp-wheels');
    let state = {
      year:   now.getFullYear(),
      month:  now.getMonth() + 1,
      day:    now.getDate(),
      hour:   now.getHours(),
      minute: now.getMinutes(),
    };

    const tracks = {};
    const colKeys = [];
    let activeColIdx = 0;

    function _setActiveCol(idx) {
      if (idx < 0) idx = 0;
      if (idx >= colKeys.length) idx = colKeys.length - 1;
      activeColIdx = idx;
      
      wheelsEl.querySelectorAll('.hwp-col').forEach(c => c.classList.remove('hwp-col-active'));
      const activeKey = colKeys[activeColIdx];
      const activeDiv = wheelsEl.querySelector(`.hwp-col[data-id="${activeKey}"]`);
      if (activeDiv) activeDiv.classList.add('hwp-col-active');
    }

    function build() {
      wheelsEl.innerHTML = '';

      if (mode === 'datetime') {
        // Year column (current year + next 5)
        const years = Array.from({length: 6}, (_, i) => {
          const y = now.getFullYear() + i;
          return { label: String(y), value: String(y) };
        });
        const { col: yCol, track: yTrk } = _buildColumn('year', years, years.findIndex(y => parseInt(y.value) === state.year));
        wheelsEl.appendChild(yCol);
        tracks.year = yTrk;

        // Month column
        const months = Array.from({length: 12}, (_, i) => ({ label: _pad(i+1), value: _pad(i+1) }));
        const { col: mCol, track: mTrk } = _buildColumn('month', months, state.month - 1);
        wheelsEl.appendChild(mCol);
        tracks.month = mTrk;

        // Day column
        const days = _generateDays(state.year, state.month);
        const { col: dCol, track: dTrk } = _buildColumn('day', days, state.day - 1);
        wheelsEl.appendChild(dCol);
        tracks.day = dTrk;

        // Separator label
        const sep = document.createElement('div');
        sep.className = 'hwp-sep';
        sep.textContent = '—';
        wheelsEl.appendChild(sep);
      }

      // Hour column
      const hours = Array.from({length: 24}, (_, i) => ({ label: _pad(i), value: _pad(i) }));
      const { col: hCol, track: hTrk } = _buildColumn('hour', hours, state.hour);
      wheelsEl.appendChild(hCol);
      tracks.hour = hTrk;

      // Colon separator
      const colon = document.createElement('div');
      colon.className = 'hwp-sep';
      colon.textContent = ':';
      wheelsEl.appendChild(colon);

      // Minute column
      const minutes = Array.from({length: 60}, (_, i) => ({ label: _pad(i), value: _pad(i) }));
      const { col: mEl, track: minTrk } = _buildColumn('minute', minutes, state.minute);
      wheelsEl.appendChild(mEl);
      tracks.minute = minTrk;

      // Register ordered keys for keyboard navigation
      if (mode === 'datetime') {
          colKeys.push('year', 'month', 'day', 'hour', 'minute');
      } else {
          colKeys.push('hour', 'minute');
      }

      // Attach scroll listeners and click-to-activate
      Object.entries(tracks).forEach(([key, trk]) => {
        let timer;
        
        // Let user click a column to make it active
        trk.parentElement.addEventListener('mousedown', () => {
          _setActiveCol(colKeys.indexOf(key));
        });

        trk.addEventListener('scroll', () => {
          clearTimeout(timer);
          timer = setTimeout(() => {
            state[key] = _readSelected(trk);
            // If month/year changed, rebuild day column
            if ((key === 'month' || key === 'year') && mode === 'datetime') {
              const dayTrack = tracks.day;
              const newDays = _generateDays(parseInt(state.year), parseInt(state.month));
              dayTrack.innerHTML = '';
              newDays.forEach(d => {
                const el = document.createElement('div');
                el.className = 'hwp-item'; el.textContent = d.label; el.dataset.value = d.value;
                dayTrack.appendChild(el);
              });
            }
          }, 150);
        });
      });
    }

    build();
    _setActiveCol(0);

    // Keyboard Navigation
    function _handleKeydown(e) {
      if (e.key === 'ArrowLeft') {
        e.preventDefault();
        _setActiveCol(activeColIdx - 1);
      } else if (e.key === 'ArrowRight') {
        e.preventDefault();
        _setActiveCol(activeColIdx + 1);
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        const trk = tracks[colKeys[activeColIdx]];
        if (trk) trk.scrollTop -= ITEM_H;
      } else if (e.key === 'ArrowDown') {
        e.preventDefault();
        const trk = tracks[colKeys[activeColIdx]];
        if (trk) trk.scrollTop += ITEM_H;
      } else if (e.key === 'Enter') {
        e.preventDefault();
        overlay.querySelector('#hwp-confirm').click();
      } else if (e.key === 'Escape') {
        e.preventDefault();
        overlay.querySelector('#hwp-cancel').click();
      }
    }
    document.addEventListener('keydown', _handleKeydown);

    // ── Confirm ────────────────────────────────────────────────────────────────
    overlay.querySelector('#hwp-confirm').addEventListener('click', () => {
      // Read final values
      const vals = {};
      Object.entries(tracks).forEach(([key, trk]) => { vals[key] = _readSelected(trk); });

      let iso;
      if (mode === 'time') {
        const today = new Date();
        iso = `${today.getFullYear()}-${_pad(today.getMonth()+1)}-${_pad(today.getDate())}T${vals.hour}:${vals.minute}:00`;
      } else {
        iso = `${vals.year}-${vals.month}-${vals.day}T${vals.hour}:${vals.minute}:00`;
      }
      overlay.remove();
      document.removeEventListener('keydown', _handleKeydown);
      onConfirm(iso);
    });

    const _close = () => { overlay.remove(); document.removeEventListener('keydown', _handleKeydown); onCancel(); };

    overlay.querySelector('#hwp-cancel').addEventListener('click', _close);
    overlay.querySelector('#hwp-close').addEventListener('click',  _close);
    overlay.addEventListener('click', (e) => { if (e.target === overlay) _close(); });
  }

  global.HecosWheelPicker = { open };

})(window);
