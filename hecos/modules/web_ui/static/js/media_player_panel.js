/**
 * media_player_panel.js
 * ─────────────────────────────────────────────────────────────────────────────
 * Hecos Media Player — Config Page Logic
 * Handles player status polling, playback control, playlist management,
 * folder scanning, and settings save.
 * Reads window.mpI18N for translated strings (injected by the template).
 * ─────────────────────────────────────────────────────────────────────────────
 */

// ─────────────────────────────────────────────────────────────────────────────
// Player Status Polling
// ─────────────────────────────────────────────────────────────────────────────

let _mpPollTimer = null;

function mpStartPolling() {
    if (_mpPollTimer) return;
    _mpPollTimer = setInterval(mpPollStatus, 3000);
    mpPollStatus();
}

async function mpPollStatus() {
    try {
        const r = await fetch('/api/media_player/status');
        const d = await r.json();
        if (!d.ok) return;

        const name = d.track ? d.track.name : '—';
        const icon = d.track
            ? (d.track.type === 'video' ? '<i class="fas fa-film"></i>'
             : d.track.type === 'audio' ? '<i class="fas fa-music"></i>'
             : '<i class="fas fa-image"></i>')
            : '<i class="fas fa-music"></i>';

        document.getElementById('mp-track-name').textContent = name;
        document.getElementById('mp-track-icon').innerHTML   = icon;

        const fmt = s => `${Math.floor(s/60)}:${String(Math.floor(s%60)).padStart(2,'0')}`;
        document.getElementById('mp-track-pos').textContent =
            d.length > 0 ? `${fmt(d.position)} / ${fmt(d.length)}` : '';

        const playBtn = document.getElementById('mp-play-btn');
        if (playBtn) playBtn.innerHTML = d.playing ? '<i class="fas fa-pause"></i>' : '<i class="fas fa-play"></i>';

        const idx = d.queue_idx + 1, total = d.queue_len;
        document.getElementById('mp-queue-info').textContent =
            total > 0 ? `Track ${idx}/${total}${d.shuffle ? '  (RANDOM)' : ''}${d.repeat ? '  (LOOP)' : ''}` : '';

        if (d.volume >= 0) {
            document.getElementById('mp-vol-slider').value      = d.volume;
            document.getElementById('mp-vol-label').textContent = d.volume + '%';
        }
    } catch (_) {}
}

// ─────────────────────────────────────────────────────────────────────────────
// Playback Control
// ─────────────────────────────────────────────────────────────────────────────

async function mpControl(action, extra = {}) {
    const body = { action, ...extra };
    try {
        const r = await fetch('/api/media_player/control', {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify(body),
        });
        const d = await r.json();
        mpShowMsg(d.message || (d.ok
            ? '<i class="fas fa-check-circle"></i> OK'
            : '<i class="fas fa-exclamation-circle"></i> ' + d.error));
        mpPollStatus();
    } catch (e) {
        mpShowMsg('<i class="fas fa-exclamation-circle"></i> ' + e);
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// Playlist Management
// ─────────────────────────────────────────────────────────────────────────────

async function mpCreatePlaylist() {
    const name = document.getElementById('mp-new-name').value.trim();
    if (!name) return;
    const r = await fetch('/api/media_player/playlists', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ name, items: [] }),
    });
    const d = await r.json();
    mpShowMsg(d.ok
        ? `<i class="fas fa-check-circle"></i> Playlist "${name}" created.`
        : '<i class="fas fa-exclamation-circle"></i> ' + d.error);
    document.getElementById('mp-new-name').value = '';
    mpLoadPlaylists();
}

async function mpDeletePlaylist(name) {
    if (!confirm(`Delete playlist "${name}"?`)) return;
    const r = await fetch(`/api/media_player/playlists/${encodeURIComponent(name)}`, { method: 'DELETE' });
    const d = await r.json();
    mpShowMsg(d.ok
        ? `<i class="fas fa-trash-alt"></i> Playlist "${name}" deleted.`
        : '<i class="fas fa-exclamation-circle"></i> ' + d.error);
    mpLoadPlaylists();
}

async function mpPlayPlaylist(name, shuffle = false) {
    await mpControl('play_playlist', { name, shuffle });
}

async function mpScanFolder() {
    const folder = document.getElementById('mp-scan-folder').value.trim();
    const saveAs = document.getElementById('mp-scan-save-as').value.trim();
    if (!folder) return;

    const r = document.getElementById('mp-scan-result');
    r.textContent = '⏳ Scanning...';
    try {
        const res = await fetch('/api/media_player/control', {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({ action: 'scan_folder', path: folder, save_as: saveAs }),
        });
        const d = await res.json();
        r.innerHTML = d.message || (d.ok
            ? '<i class="fas fa-check-circle"></i> Done'
            : '<i class="fas fa-exclamation-circle"></i> ' + d.error);
        if (saveAs && d.ok) mpLoadPlaylists();
    } catch (e) {
        r.textContent = '<i class="fas fa-exclamation-circle"></i> ' + e;
    }
}

async function mpLoadPlaylists() {
    const wrap = document.getElementById('mp-playlists-wrap');
    const noPlaylistsMsg = (window.mpI18N && window.mpI18N.no_playlists) || 'No playlists yet.';
    try {
        const r = await fetch('/api/media_player/playlists');
        const d = await r.json();
        if (!d.ok || !d.playlists.length) {
            wrap.innerHTML = `<div class="mp-muted" style="padding:12px 0;">${noPlaylistsMsg}</div>`;
            return;
        }
        wrap.innerHTML = d.playlists.map(pl => `
            <div class="mp-playlist-row">
                <span class="mp-pl-name"><i class="fas fa-list-ul"></i> <strong>${esc(pl.name)}</strong></span>
                <span class="mp-muted">${pl.count} tracks</span>
                <div class="mp-pl-actions">
                    <button class="btn btn-primary" onclick="mpPlayPlaylist('${esc(pl.name)}')"><i class="fas fa-play"></i> Play</button>
                    <button class="btn" onclick="mpPlayPlaylist('${esc(pl.name)}', true)"><i class="fas fa-random"></i> Shuffle</button>
                    <button class="btn btn-danger" onclick="mpDeletePlaylist('${esc(pl.name)}')"><i class="fas fa-trash-alt"></i></button>
                </div>
            </div>
        `).join('');
    } catch (e) {
        wrap.innerHTML = `<div style="color:var(--danger)">${e}</div>`;
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// Settings Save
// ─────────────────────────────────────────────────────────────────────────────

async function mpSaveSettings(e) {
    e.preventDefault();
    const form = document.getElementById('mp-settings-form');
    const data = {};
    new FormData(form).forEach((v, k) => { data[k] = v; });
    form.querySelectorAll('input[type=checkbox]').forEach(cb => { data[cb.name] = cb.checked; });

    try {
        const r = await fetch('/api/config/set', {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({ section: 'plugins.MEDIA_PLAYER', values: data }),
        });
        const d = await r.json();
        const msgEl = document.getElementById('mp-save-msg');
        msgEl.textContent = d.ok
            ? '<i class="fas fa-check-circle"></i> Saved!'
            : '<i class="fas fa-exclamation-circle"></i> ' + (d.error || 'Error');
        setTimeout(() => { msgEl.textContent = ''; }, 3000);
    } catch (err) {
        document.getElementById('mp-save-msg').textContent = '<i class="fas fa-exclamation-circle"></i> ' + err;
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────────────

function mpShowMsg(msg) {
    const el = document.getElementById('mp-status-msg');
    if (el) { el.innerHTML = msg; setTimeout(() => { el.innerHTML = ''; }, 4000); }
}

function esc(s) {
    return String(s)
        .replace(/&/g, '&amp;')
        .replace(/"/g, '&quot;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
}

// ─────────────────────────────────────────────────────────────────────────────
// Bootstrap
// ─────────────────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
    mpLoadPlaylists();
    mpStartPolling();

    const slider = document.getElementById('mp-vol-slider');
    if (slider) {
        slider.addEventListener('input', () => {
            document.getElementById('mp-vol-label').textContent = slider.value + '%';
        });
    }
});
