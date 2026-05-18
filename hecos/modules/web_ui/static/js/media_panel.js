/**
 * media_panel.js
 * ─────────────────────────────────────────────────────────────────────────────
 * Hecos Media Player — Config Panel Logic
 * Reads translations from window.mpT (set by _media_translations.html).
 * ─────────────────────────────────────────────────────────────────────────────
 */

const mpT = window.mpT || {};

let mpLastQueueHash = "";

(function initMPPanel() {
    populateMPSettings();
    mpLoadPlaylists();
    mpRefreshStatus();
    if (window._mpStatusPoll) clearInterval(window._mpStatusPoll);
    window._mpStatusPoll = setInterval(mpRefreshStatus, 5000);
})();

// ─────────────────────────────────────────────────────────────────────────────
// Playback Control
// ─────────────────────────────────────────────────────────────────────────────

function mpControl(action, extra) {
    const body = { action };
    if (extra) Object.assign(body, extra);
    fetch('/api/media_player/control', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
    }).then(r => r.json()).then(d => {
        mpRefreshStatus();
        if (action === 'shuffle' || action === 'repeat') {
            setTimeout(mpRefreshStatus, 200);
        }
    }).catch(e => console.warn('[MP] control error', e));
}

function mpTogglePlay()  { mpControl('pause'); }

function mpSeek(e) {
    const bar   = e.currentTarget;
    const rect  = bar.getBoundingClientRect();
    const percent = (e.clientX - rect.left) / rect.width;
    const total = parseFloat(document.getElementById('mp-time-total').dataset.seconds || 0);
    if (total > 0) mpControl('seek', { position: percent * total });
}

function mpSetVolume(vol) {
    const el = document.getElementById('mp-volume-val');
    if (el) el.textContent = vol;
    mpControl('volume', { volume: parseInt(vol) });
}

// ─────────────────────────────────────────────────────────────────────────────
// Status Polling
// ─────────────────────────────────────────────────────────────────────────────

async function mpRefreshStatus() {
    try {
        const r = await fetch('/api/media_player/status');
        const d = await r.json();
        if (!d.ok) return;

        // Track & Playlist
        document.getElementById('mp-track-name').textContent   = d.track ? d.track.split(/[\\\/]/).pop() : '—';
        document.getElementById('mp-playlist-name').textContent = d.playlist || mpT.noPlaylist;

        // Status Badge
        const badge = document.getElementById('mp-status-badge');
        if     (d.playing) badge.textContent = mpT.playing;
        else if (d.track)  badge.textContent = mpT.paused;
        else               badge.textContent = mpT.idle;
        badge.style.background = d.playing ? 'var(--accent)' : 'var(--bg2)';
        badge.style.color      = d.playing ? 'black' : 'var(--muted)';

        // Play/Pause Button
        document.getElementById('mp-btn-play').innerHTML = d.playing
            ? '<i class="fas fa-pause"></i>'
            : '<i class="fas fa-play"></i>';

        // Progress bar
        const fill      = document.getElementById('mp-progress-fill');
        const timeCurr  = document.getElementById('mp-time-current');
        const timeTotal = document.getElementById('mp-time-total');
        if (fill && d.length > 0) {
            fill.style.width        = ((d.position / d.length) * 100).toFixed(1) + '%';
            timeCurr.textContent    = formatTime(d.position);
            timeTotal.textContent   = formatTime(d.length);
            timeTotal.dataset.seconds = d.length;
        } else {
            if (fill) fill.style.width = '0%';
            timeCurr.textContent  = '0:00';
            timeTotal.textContent = '0:00';
        }

        // Volume
        const volSlider = document.getElementById('mp-volume');
        if (volSlider && d.volume >= 0 && !volSlider.matches(':active')) {
            volSlider.value = d.volume;
            document.getElementById('mp-volume-val').textContent = d.volume;
        }

        // Shuffle / Repeat
        const shBtn = document.getElementById('mp-btn-shuffle');
        const reBtn = document.getElementById('mp-btn-repeat');
        shBtn.style.opacity = d.shuffle ? '1' : '0.5';
        shBtn.style.color   = d.shuffle ? 'var(--accent)' : 'inherit';
        reBtn.style.opacity = d.repeat  ? '1' : '0.5';
        reBtn.style.color   = d.repeat  ? 'var(--accent)' : 'inherit';

        // Auto-refresh queue if visible
        if (document.getElementById('mp-queue-container').style.display === 'block') {
            mpRefreshQueue();
        }
    } catch(e) { console.error("[MP] status error", e); }
}

// ─────────────────────────────────────────────────────────────────────────────
// Queue
// ─────────────────────────────────────────────────────────────────────────────

function mpToggleQueueView() {
    const qc  = document.getElementById('mp-queue-container');
    const btn = document.getElementById('mp-toggle-queue');
    if (qc.style.display === 'none') {
        qc.style.display = 'block';
        btn.textContent  = `${mpT.hideQueue} ▲`;
        mpRefreshQueue();
    } else {
        qc.style.display = 'none';
        btn.textContent  = `${mpT.showQueue} ▼`;
    }
}

async function mpRefreshQueue() {
    try {
        const r = await fetch('/api/media_player/queue');
        const d = await r.json();
        if (!d.ok) return;

        const hash = JSON.stringify(d.queue) + d.index;
        if (hash === mpLastQueueHash) return;
        mpLastQueueHash = hash;

        document.getElementById('mp-queue-count').textContent = `${d.queue.length} ${mpT.tracks}`;
        const list = document.getElementById('mp-queue-list');
        list.innerHTML = d.queue.map((item, i) => {
            const active = (i === d.index);
            return `<div onclick="mpControl('play_at', {index:${i}})" style="padding:4px 8px; border-radius:4px; margin-bottom:2px; cursor:pointer; background:${active ? 'rgba(102,252,241,0.1)' : 'transparent'}; color:${active ? 'var(--accent)' : 'inherit'};">
                <span style="opacity:0.5; font-size:10px; min-width:18px; display:inline-block;">${i+1}</span>
                ${item.name}
            </div>`;
        }).join('');
    } catch(e) {}
}

// ─────────────────────────────────────────────────────────────────────────────
// Playlists
// ─────────────────────────────────────────────────────────────────────────────

async function mpLoadPlaylists() {
    try {
        const r    = await fetch('/api/media_player/playlists');
        const d    = await r.json();
        const cont = document.getElementById('mp-playlists-list');
        if (!cont) return;
        if (!d.ok || !d.playlists || d.playlists.length === 0) {
            cont.innerHTML = `<span style="color:var(--muted); font-size:13px;">${mpT.noPlaylists}</span>`;
            return;
        }
        cont.innerHTML = d.playlists.map(pl => `
            <div class="playlist-row" id="pl-${pl.name}">
                <div class="playlist-header" onclick="mpTogglePlaylistItems('${pl.name}')">
                    <span style="font-size:16px;">📂</span>
                    <span class="playlist-title">${pl.name}</span>
                    <span class="playlist-meta">${pl.items ? pl.items.length : 0} ${mpT.tracks}</span>
                    <button class="btn btn-secondary btn-xs btn-circle" style="width:24px; height:24px; padding:0; border:none;" onclick="event.stopPropagation(); mpControl('play_playlist',{name:'${pl.name}'})" title="Play All"><i class="fas fa-play"></i></button>
                    <button class="btn btn-danger btn-xs btn-circle" style="width:24px; height:24px; padding:0; border:none;" onclick="event.stopPropagation(); mpDeletePlaylist('${pl.name}')"><i class="fas fa-trash-alt"></i></button>
                </div>
                <div class="playlist-items" id="pl-items-${pl.name}">
                    <div style="padding:10px; text-align:center; opacity:0.5; font-size:11px;">Loading tracks...</div>
                </div>
            </div>`).join('');
    } catch(e) { console.error("[MP] load playlists error", e); }
}

async function mpTogglePlaylistItems(name) {
    const container = document.getElementById(`pl-items-${name}`);
    if (!container) return;
    if (container.style.display === 'block') { container.style.display = 'none'; return; }

    container.style.display = 'block';
    try {
        const r = await fetch(`/api/media_player/playlists/${encodeURIComponent(name)}`);
        const d = await r.json();
        if (!d.ok || !d.playlist) {
            container.innerHTML = `<div style="padding:10px; color:var(--red); font-size:11px;">Error loading playlist</div>`;
            return;
        }
        const items = d.playlist.items || [];
        if (items.length === 0) {
            container.innerHTML = `<div style="padding:10px; opacity:0.5; font-size:11px;">No tracks in this playlist</div>`;
            return;
        }
        container.innerHTML = `<div style="margin-top:8px;">${items.map((item, i) => `
            <div class="track-row">
                <span style="opacity:0.3; font-size:10px; width:16px;">${i+1}</span>
                <span class="track-name" onclick="mpControl('play_playlist', {name:'${name}', index:${i}})">${item.name}</span>
                <button class="btn btn-ghost btn-xs" onclick="mpRemoveTrackFromPlaylist('${name}', ${i})" style="color:var(--red); opacity:0.6; padding:2px 4px;"><i class="fas fa-trash-alt"></i></button>
            </div>`).join('')}</div>`;
    } catch(e) {
        container.innerHTML = `<div style="padding:10px; color:var(--red); font-size:11px;">Fetch error</div>`;
    }
}

async function mpRemoveTrackFromPlaylist(playlistName, index) {
    const trackLabel = `Track ${index + 1}`;
    const msg = mpT.deleteTrack.replace ? mpT.deleteTrack.replace('{name}', trackLabel) : mpT.deleteTrack;
    if (!confirm(msg)) return;
    try {
        const r = await fetch(`/api/media_player/playlists/${encodeURIComponent(playlistName)}/items/${index}`, { method: 'DELETE' });
        const d = await r.json();
        if (d.ok) {
            await mpLoadPlaylists();
            document.getElementById(`pl-items-${playlistName}`).style.display = 'block';
            mpTogglePlaylistItems(playlistName);
        }
    } catch(e) { console.error("[MP] remove track error", e); }
}

async function mpCreatePlaylist() {
    const nameEl = document.getElementById('mp-new-playlist');
    const name   = (nameEl && nameEl.value.trim()) || '';
    if (!name) return;
    await fetch('/api/media_player/playlists', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, items: [] })
    });
    if (nameEl) nameEl.value = '';
    mpLoadPlaylists();
}

async function mpDeletePlaylist(name) {
    if (!confirm(mpT.deleteConfirm.replace ? mpT.deleteConfirm.replace('{name}', name) : mpT.deleteConfirm)) return;
    await fetch('/api/media_player/playlists/' + encodeURIComponent(name), { method: 'DELETE' });
    mpLoadPlaylists();
}

async function mpScanFolder() {
    const folder = (document.getElementById('mp-scan-folder')  || {}).value || '';
    const saveAs = (document.getElementById('mp-scan-save-as') || {}).value || '';
    if (!folder) return;
    try {
        const r = await fetch('/api/media_player/control', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: 'scan_folder', path: folder, save_as: saveAs, recursive: true })
        });
        const d = await r.json();
        if (d.ok) { mpLoadPlaylists(); mpRefreshStatus(); }
        else { alert(`${mpT.scanError}: ${d.error}`); }
    } catch(e) {}
}

// ─────────────────────────────────────────────────────────────────────────────
// File Picker Helpers
// ─────────────────────────────────────────────────────────────────────────────

function mpBrowseRoot() {
    const current = (document.getElementById('mp-cfg-root') || {}).value || 'C:\\';
    if (typeof HecosFilePicker !== 'undefined') {
        HecosFilePicker.open({
            title: mpT.pickerMediaRoot,
            initialPath: current,
            mode: 'folder',
            onSelect: (path) => { document.getElementById('mp-cfg-root').value = path; }
        });
    } else { alert(mpT.filePickerMissing); }
}

function mpBrowseScanFolder() {
    const current = (document.getElementById('mp-scan-folder') || {}).value || 'C:\\';
    if (typeof HecosFilePicker !== 'undefined') {
        HecosFilePicker.open({
            title: mpT.pickerScan,
            initialPath: current,
            mode: 'folder',
            onSelect: (path) => { document.getElementById('mp-scan-folder').value = path; }
        });
    } else { alert(mpT.filePickerMissing); }
}

// ─────────────────────────────────────────────────────────────────────────────
// Config Payload (called by config_mapper.js)
// ─────────────────────────────────────────────────────────────────────────────

function populateMPSettings() {
    const mp  = (typeof mediaConfig !== 'undefined' && mediaConfig && mediaConfig.media_player) ? mediaConfig.media_player : {};
    const setV = (id, val) => { const e = document.getElementById(id); if (e) e.value   = val; };
    const setC = (id, val) => { const e = document.getElementById(id); if (e) e.checked = !!val; };
    setV('mp-cfg-volume',          mp.default_volume ?? 80);
    setV('mp-cfg-backend',         mp.preferred_backend || 'auto');
    setV('mp-cfg-root',            mp.media_root_dir || '');
    setV('mp-cfg-autoload',        mp.autoload_playlist || '');
    setV('mp-cfg-thumb',           mp.drive_thumb_size || 'medium');
    setC('mp-cfg-autoadvance',     mp.auto_advance !== false);
    setC('mp-cfg-shuffle',         mp.shuffle_default ?? false);
    setC('mp-cfg-repeat',          mp.repeat_queue ?? false);
    setC('mp-cfg-autoplay-video',  mp.autoplay_video ?? false);
    setC('mp-cfg-autoplay-audio',  mp.autoplay_audio ?? false);
    setC('mp-cfg-filmstrip',       mp.show_filmstrip !== false);
}

function buildMPPayload() {
    const get = id => { const el = document.getElementById(id); return el ? el.value : null; };
    const ck  = id => { const el = document.getElementById(id); return el ? el.checked : false; };
    return {
        default_volume:    parseInt(get('mp-cfg-volume'))    || 80,
        preferred_backend: get('mp-cfg-backend')             || 'auto',
        media_root_dir:    get('mp-cfg-root')                || '',
        autoload_playlist: get('mp-cfg-autoload')            || '',
        drive_thumb_size:  get('mp-cfg-thumb')               || 'medium',
        auto_advance:      ck('mp-cfg-autoadvance'),
        shuffle_default:   ck('mp-cfg-shuffle'),
        repeat_queue:      ck('mp-cfg-repeat'),
        autoplay_video:    ck('mp-cfg-autoplay-video'),
        autoplay_audio:    ck('mp-cfg-autoplay-audio'),
        show_filmstrip:    ck('mp-cfg-filmstrip'),
    };
}
window.buildMPPayload = buildMPPayload;

// ─────────────────────────────────────────────────────────────────────────────
// Utility
// ─────────────────────────────────────────────────────────────────────────────

function formatTime(s) {
    if (!s || isNaN(s)) return "0:00";
    const m  = Math.floor(s / 60);
    const rs = Math.floor(s % 60);
    return `${m}:${rs < 10 ? '0' : ''}${rs}`;
}
