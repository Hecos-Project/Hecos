/**
 * Hecos Media Player — Core Module (media_player.js)
 * Version: 1.0.0
 *
 * Public API:
 *   HecosMediaPlayer.open(items, startIndex)
 *     items: Array of { name, type, url, path? }
 *       - url  → direct URL string (used by Chat images)
 *       - path → Drive-relative path (used by Drive)
 *     startIndex: integer
 *
 *   HecosMediaPlayer.openFromDrive(path, dirPath)
 *     Opens the player by fetching the playlist from the Drive API.
 *
 * Dependencies (loaded as separate submodules):
 *   player_image.js, player_video.js, player_audio.js, player_filmstrip.js
 */

(function (global) {
  'use strict';

  // ─── State ──────────────────────────────────────────────────────────────────
  var _playlist    = [];
  var _index       = 0;
  var _touchStartX = 0;
  var _touchStartY = 0;

  // ─── URL builder ────────────────────────────────────────────────────────────
  function _urlFor(item) {
    if (item.url)  return item.url;
    if (item.path) return '/api/media_player/view?path=' + encodeURIComponent(item.path);
    return '';
  }

  // ─── Lightbox DOM ───────────────────────────────────────────────────────────
  function _buildLightbox() {
    if (document.getElementById('hmp-lightbox')) return;

    var lb = document.createElement('div');
    lb.id = 'hmp-lightbox';
    lb.setAttribute('role', 'dialog');
    lb.setAttribute('aria-modal', 'true');
    lb.innerHTML =
      '<div id="hmp-header">' +
        '<span id="hmp-title">—</span>' +
        '<span id="hmp-counter"></span>' +
        '<button id="hmp-close" title="Close (ESC)">✕ Close</button>' +
      '</div>' +
      '<button class="hmp-nav" id="hmp-prev" title="Previous (←)">‹</button>' +
      '<div id="hmp-stage"></div>' +
      '<button class="hmp-nav" id="hmp-next" title="Next (→)">›</button>' +
      '<div id="hmp-filmstrip"></div>';

    document.body.appendChild(lb);

    document.getElementById('hmp-close').onclick = _close;
    document.getElementById('hmp-prev').onclick  = function () { _navigate(-1); };
    document.getElementById('hmp-next').onclick  = function () { _navigate(+1); };

    // Touch / swipe
    lb.addEventListener('touchstart', function (e) {
      _touchStartX = e.touches[0].clientX;
      _touchStartY = e.touches[0].clientY;
    }, { passive: true });

    lb.addEventListener('touchend', function (e) {
      var dx = e.changedTouches[0].clientX - _touchStartX;
      var dy = e.changedTouches[0].clientY - _touchStartY;
      if (Math.abs(dx) > Math.abs(dy) && Math.abs(dx) > 40) {
        _navigate(dx < 0 ? +1 : -1);
      }
    }, { passive: true });

    // Click backdrop to close
    lb.addEventListener('click', function (e) {
      if (e.target === lb) _close();
    });
  }

  // ─── Open / Close ───────────────────────────────────────────────────────────
  function _open(items, startIndex) {
    _buildLightbox();
    _playlist = items || [];
    _index    = Math.max(0, Math.min(startIndex || 0, _playlist.length - 1));
    _render();
    document.getElementById('hmp-lightbox').classList.add('open');
    document.addEventListener('keydown', _onKey);
  }

  function _close() {
    var lb = document.getElementById('hmp-lightbox');
    if (!lb) return;
    lb.classList.remove('open');
    var stage = document.getElementById('hmp-stage');
    if (stage) {
      stage.querySelectorAll('video, audio').forEach(function (m) {
        m.pause(); m.src = '';
      });
      stage.innerHTML = '';
    }
    document.removeEventListener('keydown', _onKey);
  }

  // ─── Navigation ─────────────────────────────────────────────────────────────
  function _navigate(delta) {
    if (!_playlist.length) return;
    _index = (_index + delta + _playlist.length) % _playlist.length;
    _render();
  }

  // ─── Render ─────────────────────────────────────────────────────────────────
  function _render() {
    var item = _playlist[_index];
    if (!item) return;

    // Header
    document.getElementById('hmp-title').textContent   = item.name || '—';
    document.getElementById('hmp-counter').textContent = (_index + 1) + ' / ' + _playlist.length;

    // Stage — delegate to type submodule
    var stage = document.getElementById('hmp-stage');
    stage.querySelectorAll('video, audio').forEach(function (m) { m.pause(); m.src = ''; });
    stage.innerHTML = '';

    var url = _urlFor(item);
    var type = item.type || 'image';

    if (window.HMPImage && type === 'image') {
      window.HMPImage.render(stage, url, item.name);
    } else if (window.HMPVideo && type === 'video') {
      window.HMPVideo.render(stage, url);
    } else if (window.HMPAudio && type === 'audio') {
      window.HMPAudio.render(stage, url, item.name);
    } else {
      // Fallback — basic img for images, raw link for others
      if (type === 'image') {
        stage.innerHTML = '<img src="' + url + '" alt="' + (item.name || '') + '">';
      } else {
        stage.innerHTML = '<a href="' + url + '" target="_blank" style="color:var(--accent)">⬇ Download: ' + (item.name || url) + '</a>';
      }
    }

    // Nav buttons
    var prev = document.getElementById('hmp-prev');
    var next = document.getElementById('hmp-next');
    if (prev) prev.disabled = _playlist.length <= 1;
    if (next) next.disabled = _playlist.length <= 1;

    // Filmstrip
    if (window.HMPFilmstrip) {
      window.HMPFilmstrip.render(
        document.getElementById('hmp-filmstrip'),
        _playlist, _index, _urlFor,
        function (i) { _index = i; _render(); }
      );
    }
  }

  // ─── Keyboard ───────────────────────────────────────────────────────────────
  function _onKey(e) {
    if      (e.key === 'Escape')     { _close(); }
    else if (e.key === 'ArrowLeft')  { _navigate(-1); }
    else if (e.key === 'ArrowRight') { _navigate(+1); }
  }

  // ─── Drive integration (fetch playlist from API) ─────────────────────────────
  async function _openFromDrive(startPath, dirPath) {
    _buildLightbox();
    var playlist = [];
    try {
      var res  = await fetch('/api/media_player/list?path=' + encodeURIComponent(dirPath));
      var data = await res.json();
      playlist = data.ok ? data.entries : [];
    } catch (_) { playlist = []; }

    // Build items list with Drive paths
    var items = playlist.map(function (e) {
      return { name: e.name, type: e.type, path: e.path };
    });

    var idx = items.findIndex(function (e) {
      return e.path === startPath || (startPath && startPath.endsWith('/' + e.path));
    });

    _open(items, idx >= 0 ? idx : 0);
  }

  // ─── Drive: Size picker toolbar ─────────────────────────────────────────────
  var _SIZES      = ['none', 'small', 'medium', 'large'];
  var _SIZE_LABELS = { none: '✕', small: 'S', medium: 'M', large: 'L' };
  var _LS_THUMB   = 'hecos_mp_drive_size';
  var _driveSize  = localStorage.getItem(_LS_THUMB) || 'small';

  function _injectSizePicker() {
    if (document.getElementById('mv-size-picker')) return;
    var toolbar = document.getElementById('toolbar');
    if (!toolbar) return;

    var pick = document.createElement('div');
    pick.id = 'mv-size-picker';
    pick.innerHTML = '<span>🖼️</span>' + _SIZES.map(function (s) {
      return '<button class="mv-size-btn' + (s === _driveSize ? ' active' : '') +
             '" data-size="' + s + '">' + _SIZE_LABELS[s] + '</button>';
    }).join('');
    toolbar.appendChild(pick);

    pick.addEventListener('click', function (e) {
      var btn = e.target.closest('.mv-size-btn');
      if (!btn) return;
      _driveSize = btn.dataset.size;
      localStorage.setItem(_LS_THUMB, _driveSize);
      pick.querySelectorAll('.mv-size-btn').forEach(function (b) {
        b.classList.toggle('active', b.dataset.size === _driveSize);
      });
      _applyDriveSize();
    });
  }

  function _applyDriveSize() {
    var tbody = document.getElementById('file-tbody');
    if (!tbody) return;
    var table = tbody.closest('table');
    if (table) {
      _SIZES.forEach(function (s) { table.classList.remove('mv-size-' + s); });
      if (_driveSize !== 'none') table.classList.add('mv-size-' + _driveSize);
    }
    tbody.querySelectorAll('.hmp-thumb-wrap').forEach(function (el) {
      el.style.display = _driveSize === 'none' ? 'none' : '';
    });
  }

  // ─── Drive: Thumbnail injection ─────────────────────────────────────────────
  var IMAGE_EXTS = new Set(['jpg','jpeg','png','gif','webp','bmp','svg','avif']);
  var VIDEO_EXTS = new Set(['mp4','webm','ogg','ogv','mov','m4v','mkv']);
  var AUDIO_EXTS = new Set(['mp3','wav','ogg','oga','flac','aac','m4a','opus']);

  function _extOf(name) { return (name.split('.').pop() || '').toLowerCase(); }
  function _mediaType(name) {
    var e = _extOf(name);
    if (IMAGE_EXTS.has(e)) return 'image';
    if (VIDEO_EXTS.has(e)) return 'video';
    if (AUDIO_EXTS.has(e)) return 'audio';
    return null;
  }

  function _injectDriveThumbnails(entries, dirPath) {
    _injectSizePicker();
    var tbody = document.getElementById('file-tbody');
    if (!tbody) return;
    var rows = tbody.querySelectorAll('tr');
    rows.forEach(function (row, i) {
      if (i >= entries.length) return;
      var entry = entries[i];
      if (entry.is_dir) return;
      var type = _mediaType(entry.name);
      if (!type) return;
      var nameCell = row.querySelector('.name-cell');
      if (!nameCell) return;
      if (nameCell.querySelector('.hmp-thumb-wrap')) return;

      var wrap = document.createElement('span');
      wrap.className = 'hmp-thumb-wrap';
      wrap.title = entry.name;
      wrap.addEventListener('click', function (e) {
        e.stopPropagation();
        _openFromDrive(entry.path, dirPath);
      });

      if (type === 'image') {
        var url = '/api/media_player/view?path=' + encodeURIComponent(entry.path);
        wrap.innerHTML = '<img src="' + url + '" alt="' + entry.name + '" loading="lazy">';
      } else if (type === 'video') {
        wrap.innerHTML = '<span class="hmp-thumb-icon">🎬</span>';
      } else {
        wrap.innerHTML = '<span class="hmp-thumb-icon">🎵</span>';
      }

      var icon = nameCell.querySelector('.icon');
      if (icon) nameCell.insertBefore(wrap, icon);
      else nameCell.prepend(wrap);
    });
    _applyDriveSize();
  }

  // ─── CSS self-injection ──────────────────────────────────────────────────────
  (function _injectCss() {
    if (document.getElementById('hmp-css')) return;
    var link = document.createElement('link');
    link.id   = 'hmp-css';
    link.rel  = 'stylesheet';
    link.href = '/media_player_static/css/media_player.css';
    document.head.appendChild(link);
  })();

  // ─── Public API ─────────────────────────────────────────────────────────────
  global.HecosMediaPlayer = {
    open:                  _open,
    openFromDrive:         _openFromDrive,
    close:                 _close,
    navigate:              _navigate,
    injectDriveThumbnails: _injectDriveThumbnails,
  };

})(window);
