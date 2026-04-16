/**
 * Zentra Drive — Media Viewer Extension v1.0
 * Provides:
 *   - Inline thumbnails in the file list (4 size modes)
 *   - Fullscreen media player / lightbox with playlist nav (arrows + swipe)
 */
(function () {
  'use strict';

  // ─── Config ────────────────────────────────────────────────────────────────
  const IMAGE_EXTS = new Set(['jpg','jpeg','png','gif','webp','bmp','svg','avif']);
  const VIDEO_EXTS = new Set(['mp4','webm','ogg','ogv','mov','m4v','mkv']);
  const AUDIO_EXTS = new Set(['mp3','wav','ogg','oga','flac','aac','m4a','opus']);

  const SIZES = ['none', 'small', 'medium', 'large'];
  const SIZE_LABELS = { none: '✕', small: 'S', medium: 'M', large: 'L' };
  const LS_KEY = 'zentra_mv_size';

  // ─── State ─────────────────────────────────────────────────────────────────
  let currentSize    = localStorage.getItem(LS_KEY) || 'small';
  let playlist       = [];  // [{name, path, type}, ...]
  let playlistIndex  = 0;
  let touchStartX    = 0;
  let touchStartY    = 0;

  // ─── Helpers ───────────────────────────────────────────────────────────────
  function extOf(name) { return (name.split('.').pop() || '').toLowerCase(); }
  function mediaType(name) {
    const e = extOf(name);
    if (IMAGE_EXTS.has(e)) return 'image';
    if (VIDEO_EXTS.has(e)) return 'video';
    if (AUDIO_EXTS.has(e)) return 'audio';
    return null;
  }
  function viewUrl(path) { return `/drive/api/media/view?path=${encodeURIComponent(path)}`; }

  // ─── Toolbar "Preview Size" picker ─────────────────────────────────────────
  function injectSizePicker() {
    if (document.getElementById('mv-size-picker')) return;
    const toolbar = document.getElementById('toolbar');
    if (!toolbar) return;

    const pick = document.createElement('div');
    pick.id = 'mv-size-picker';
    pick.innerHTML = `<span>🖼️</span>` + SIZES.map(s =>
      `<button class="mv-size-btn${s === currentSize ? ' active' : ''}" data-size="${s}">${SIZE_LABELS[s]}</button>`
    ).join('');
    toolbar.appendChild(pick);

    pick.addEventListener('click', e => {
      const btn = e.target.closest('.mv-size-btn');
      if (!btn) return;
      currentSize = btn.dataset.size;
      localStorage.setItem(LS_KEY, currentSize);
      pick.querySelectorAll('.mv-size-btn').forEach(b => b.classList.toggle('active', b.dataset.size === currentSize));
      applySize();
    });
  }

  function applySize() {
    const tbody = document.getElementById('file-tbody');
    if (!tbody) return;
    const table = tbody.closest('table');
    if (table) {
      table.classList.remove(...SIZES.map(s => 'mv-size-' + s));
      if (currentSize !== 'none') table.classList.add('mv-size-' + currentSize);
    }
    if (currentSize === 'none') {
      tbody.querySelectorAll('.mv-thumb-wrap').forEach(el => { el.style.display = 'none'; });
    } else {
      tbody.querySelectorAll('.mv-thumb-wrap').forEach(el => { el.style.display = ''; });
    }
  }

  // ─── Thumbnail injection into file table ───────────────────────────────────
  function injectThumbnails(entries, dirPath) {
    const tbody = document.getElementById('file-tbody');
    if (!tbody) return;

    const rows = tbody.querySelectorAll('tr');
    rows.forEach((row, i) => {
      if (i >= entries.length) return;
      const entry = entries[i];
      if (entry.is_dir) return;
      const type = mediaType(entry.name);
      if (!type) return;

      const nameCell = row.querySelector('.name-cell');
      if (!nameCell) return;

      // Already injected?
      if (nameCell.querySelector('.mv-thumb-wrap')) return;

      const wrap = document.createElement('span');
      wrap.className = 'mv-thumb-wrap';
      wrap.title = `Anteprima: ${entry.name}`;
      wrap.onclick = (e) => { e.stopPropagation(); openLightbox(entry.path, dirPath); };

      if (type === 'image') {
        wrap.innerHTML = `<img src="${viewUrl(entry.path)}" alt="${entry.name}" loading="lazy">`;
      } else if (type === 'video') {
        wrap.innerHTML = `<img src="${viewUrl(entry.path)}" alt="${entry.name}" loading="lazy"><span class="mv-play-badge">▶</span>`;
        // No poster available via API — just show a dark bg with play icon
        const img = wrap.querySelector('img');
        img.onerror = () => { img.style.display='none'; wrap.querySelector('.mv-play-badge').style.opacity='1'; };
      } else if (type === 'audio') {
        wrap.innerHTML = `<span class="mv-thumb-icon">🎵</span>`;
      }

      // Insert thumb before the file name icon
      const icon = nameCell.querySelector('.icon');
      if (icon) nameCell.insertBefore(wrap, icon);
      else nameCell.prepend(wrap);
    });

    applySize();
  }

  // ─── Lightbox / Player ─────────────────────────────────────────────────────
  function buildLightbox() {
    if (document.getElementById('mv-lightbox')) return;

    const lb = document.createElement('div');
    lb.id = 'mv-lightbox';
    lb.setAttribute('role', 'dialog');
    lb.setAttribute('aria-modal', 'true');
    lb.innerHTML = `
      <div id="mv-lb-header">
        <span id="mv-lb-title">—</span>
        <span id="mv-lb-counter"></span>
        <button id="mv-lb-close" title="Chiudi (ESC)">✕ Chiudi</button>
      </div>
      <button class="mv-lb-nav" id="mv-lb-prev" title="Precedente (←)">‹</button>
      <div id="mv-lb-stage"></div>
      <button class="mv-lb-nav" id="mv-lb-next" title="Successivo (→)">›</button>
      <div id="mv-lb-filmstrip"></div>
    `;
    document.body.appendChild(lb);

    document.getElementById('mv-lb-close').onclick = closeLightbox;
    document.getElementById('mv-lb-prev').onclick  = () => navigate(-1);
    document.getElementById('mv-lb-next').onclick  = () => navigate(+1);

    // Touch swipe
    lb.addEventListener('touchstart', e => {
      touchStartX = e.touches[0].clientX;
      touchStartY = e.touches[0].clientY;
    }, { passive: true });
    lb.addEventListener('touchend', e => {
      const dx = e.changedTouches[0].clientX - touchStartX;
      const dy = e.changedTouches[0].clientY - touchStartY;
      if (Math.abs(dx) > Math.abs(dy) && Math.abs(dx) > 40) {
        navigate(dx < 0 ? +1 : -1);
      }
    }, { passive: true });
  }

  async function openLightbox(startPath, dirPath) {
    buildLightbox();

    // Load playlist from server
    try {
      const res  = await fetch(`/drive/api/media/list_media?path=${encodeURIComponent(dirPath)}`);
      const data = await res.json();
      playlist = data.ok ? data.entries : [];
    } catch { playlist = []; }

    // Find start index
    playlistIndex = playlist.findIndex(e => e.path === startPath || e.path.endsWith('/' + startPath));
    if (playlistIndex < 0) playlistIndex = 0;

    renderLightbox();
    document.getElementById('mv-lightbox').classList.add('open');
    document.addEventListener('keydown', onKeyDown);
  }

  function closeLightbox() {
    const lb = document.getElementById('mv-lightbox');
    if (!lb) return;
    lb.classList.remove('open');
    // Stop any playing media
    const stage = document.getElementById('mv-lb-stage');
    if (stage) {
      stage.querySelectorAll('video, audio').forEach(m => { m.pause(); m.src = ''; });
      stage.innerHTML = '';
    }
    document.removeEventListener('keydown', onKeyDown);
  }

  function navigate(delta) {
    if (!playlist.length) return;
    playlistIndex = (playlistIndex + delta + playlist.length) % playlist.length;
    renderLightbox();
  }

  function renderLightbox() {
    const item = playlist[playlistIndex];
    if (!item) return;

    // Header
    document.getElementById('mv-lb-title').textContent = item.name;
    document.getElementById('mv-lb-counter').textContent = `${playlistIndex + 1} / ${playlist.length}`;

    // Stage
    const stage = document.getElementById('mv-lb-stage');
    // Stop previous media
    stage.querySelectorAll('video, audio').forEach(m => { m.pause(); m.src = ''; });

    const url = `/drive/api/media/view?path=${encodeURIComponent(item.path)}`;

    if (item.type === 'image') {
      stage.innerHTML = `<img src="${url}" alt="${item.name}">`;
    } else if (item.type === 'video') {
      stage.innerHTML = `<video src="${url}" controls autoplay playsinline></video>`;
    } else if (item.type === 'audio') {
      stage.innerHTML = `
        <div id="mv-lb-audio-cover">
          <div class="mv-audio-icon">🎵</div>
          <div class="mv-audio-name">${item.name}</div>
          <audio src="${url}" controls autoplay></audio>
        </div>`;
    }

    // Nav buttons
    const prev = document.getElementById('mv-lb-prev');
    const next = document.getElementById('mv-lb-next');
    if (prev) prev.disabled = playlist.length <= 1;
    if (next) next.disabled = playlist.length <= 1;

    // Filmstrip
    renderFilmstrip();
  }

  function renderFilmstrip() {
    const strip = document.getElementById('mv-lb-filmstrip');
    if (!strip) return;
    strip.innerHTML = '';

    const useThumbs = playlist.length <= 20;

    playlist.forEach((item, i) => {
      if (useThumbs) {
        const th = document.createElement('div');
        th.className = 'mv-film-thumb' + (i === playlistIndex ? ' active' : '');
        th.title = item.name;
        if (item.type === 'image') {
          const url = `/drive/api/media/view?path=${encodeURIComponent(item.path)}`;
          th.innerHTML = `<img src="${url}" loading="lazy">`;
        } else if (item.type === 'video') {
          th.textContent = '🎬';
        } else {
          th.textContent = '🎵';
        }
        th.onclick = () => { playlistIndex = i; renderLightbox(); };
        strip.appendChild(th);
      } else {
        const dot = document.createElement('div');
        dot.className = 'mv-film-dot' + (i === playlistIndex ? ' active' : '');
        dot.title = item.name;
        dot.onclick = () => { playlistIndex = i; renderLightbox(); };
        strip.appendChild(dot);
      }
    });

    // Scroll active into view
    const active = strip.querySelector('.active');
    if (active) active.scrollIntoView({ block: 'nearest', inline: 'center', behavior: 'smooth' });
  }

  function onKeyDown(e) {
    if (e.key === 'Escape')     { closeLightbox(); }
    else if (e.key === 'ArrowLeft')  { navigate(-1); }
    else if (e.key === 'ArrowRight') { navigate(+1); }
  }

  // ─── Public API (hook called by drive.js) ──────────────────────────────────
  window.DriveMediaViewer = {
    onTableRendered(entries, currentPath) {
      injectSizePicker();
      injectThumbnails(entries, currentPath);
    }
  };

  // Inject CSS
  const link = document.createElement('link');
  link.rel = 'stylesheet';
  link.href = '/media_viewer_static/css/media_viewer.css';
  document.head.appendChild(link);

  // Init picker after DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', injectSizePicker);
  } else {
    injectSizePicker();
  }

})();
