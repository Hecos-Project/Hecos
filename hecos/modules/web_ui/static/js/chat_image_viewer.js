/**
 * MODULE: chat_image_viewer.js
 * PURPOSE: Handle AI image rendering, single-click lightbox, and
 *          double-click gallery (powered by HecosMediaPlayer plugin).
 *
 * HOW AI SENDS IMAGES:
 * - The AI includes [[IMG:filename.ext]] or [[IMG:https://...]] tags.
 * - renderMarkdown() calls processAiImages() to replace those tags with
 *   rendered <img> inside a .chat-img-wrap container.
 * - Files are served by routes_chat.py at /api/images/<filename>.
 *
 * CLICK BEHAVIOUR:
 * - Single click → classic full-screen lightbox (single image).
 * - Double click → HecosMediaPlayer gallery with all chat images + filmstrip.
 */

// ── Gallery helper — collects all chat images for the media player ────────────
function _getChatGalleryItems() {
  return Array.from(document.querySelectorAll('.chat-img-wrap')).map(wrap => ({
    name: wrap.dataset.imgName || 'Image',
    type: 'image',
    url:  wrap.dataset.imgUrl  || wrap.querySelector('img')?.src || ''
  }));
}

function _getChatGalleryIndex(url) {
  const items = _getChatGalleryItems();
  const idx = items.findIndex(item => item.url === url);
  return idx >= 0 ? idx : 0;
}

// ── Open gallery (double-click) ───────────────────────────────────────────────
window.openChatGallery = async function(url) {
  let items = [];
  try {
    const res = await fetch('/api/images');
    if (res.ok) {
      const images = await res.json();
      items = images.map(img => ({
        name: img.name,
        type: 'image',
        url: img.url
      }));
    } else {
      items = _getChatGalleryItems();
    }
  } catch (err) {
    console.error("[Gallery] Failed to fetch full image list, falling back to chat images.", err);
    items = _getChatGalleryItems();
  }

  let idx = 0;
  if (url && items.length > 0) {
    let rawPath = url.split("?")[0];
    let decodedName = rawPath.split("/").pop();
    idx = items.findIndex(item => item.url.endsWith(decodedName) || item.name === decodedName || item.url === url);
    if (idx < 0) idx = 0;
  } else if (items.length === 0) {
    console.warn("[Gallery] No images to show.");
    return;
  }

  if (typeof window.HecosMediaPlayer === 'undefined') {
    // Lazy load the media player script and CSS if not already present
    if (!document.getElementById('hmp-css')) {
      const link = document.createElement('link');
      link.id   = 'hmp-css';
      link.rel  = 'stylesheet';
      link.href = '/media_player_static/css/media_player.css';
      document.head.appendChild(link);
    }

    const scripts = [
      '/media_player_static/js/player_image.js',
      '/media_player_static/js/player_video.js',
      '/media_player_static/js/player_audio.js',
      '/media_player_static/js/player_filmstrip.js',
      '/media_player_static/js/media_player.js',
    ];

    // Load scripts sequentially then open
    scripts.reduce((promise, src) => promise.then(() => new Promise((resolve) => {
      if (document.querySelector(`script[src="${src}"]`)) { resolve(); return; }
      const s = document.createElement('script');
      s.src = src;
      s.onload = resolve;
      s.onerror = resolve; // fail silently, open anyway
      document.head.appendChild(s);
    })), Promise.resolve()).then(() => {
      if (typeof window.HecosMediaPlayer !== 'undefined') {
        window.HecosMediaPlayer.open(items, idx);
      }
    });
    return;
  }

  window.HecosMediaPlayer.open(items, idx);
};

// ── Open media folder directly ───────────────────────────────────────────────
window.openMediaFolder = async function() {
  try {
    const res = await fetch('/api/open_media_folder', { method: 'POST' });
    const data = await res.json();
    if (!data.ok) console.error("Error opening folder:", data.error);
  } catch (err) {
    console.error("Failed to call API:", err);
  }
};

// ── Convert [[IMG:name]] tags in AI text to rendered image HTML ──────────────
window.processAiImages = function(html) {
  return html.replace(/\[\[IMG:([^\]]+)\]\]/g, (match, identifier) => {
    identifier = identifier.trim();
    const isUrl = identifier.startsWith('http://') || identifier.startsWith('https://');
    const url = isUrl ? identifier : `/api/images/${encodeURIComponent(identifier)}`;
    const displayTitle = isUrl ? (identifier.split('/').pop() || 'Image') : identifier;

    return `
<div class="chat-img-wrap" draggable="true" data-img-url="${url}" data-img-name="${displayTitle}">
  <img src="${url}" alt="${displayTitle}" loading="lazy"
       onerror="this.parentElement.style.display='none'"
       onclick="if(window.openLightbox) window.openLightbox('${url}')"
       ondblclick="if(window.openChatGallery) window.openChatGallery('${url}'); return false;">
  <div class="chat-img-overlay">
    <button class="img-action-btn" onclick="downloadChatImage('${url}','${displayTitle}')">⬇ Scarica</button>
    <button class="img-action-btn" onclick="openLightbox('${url}')">🔍 Zoom</button>
    <button class="img-action-btn" onclick="openChatGallery('${url}')">🖼 Gallery</button>
    <button class="img-action-btn" onclick="openMediaFolder()" title="Open local media folder">📁 Folder</button>
  </div>
</div>`;
  });
};

// ── Download chat image ───────────────────────────────────────────
window.downloadChatImage = function(url, name) {
  const a = document.createElement('a');
  a.href = url;
  a.download = name;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
};

// ── Single-image lightbox (single click) ─────────────────────────
window.openLightbox = function(url) {
  const lb = document.getElementById('img-lightbox');
  const lbImg = document.getElementById('img-lightbox-img');
  if (!lb || !lbImg) return;
  lbImg.src = url;
  lb.classList.add('open');
};

function closeLightbox() {
  const lb = document.getElementById('img-lightbox');
  if (lb) { lb.classList.remove('open'); }
}

// ── Drag image to OS folder ───────────────────────────────────────
function setupImageDragToFolder() {
  const banner = document.getElementById('img-drop-banner');

  document.addEventListener('dragstart', (e) => {
    const wrap = e.target.closest('.chat-img-wrap');
    if (!wrap) return;
    wrap.classList.add('dragging');
    e.dataTransfer.effectAllowed = 'copy';
    e.dataTransfer.setData('text/plain', wrap.dataset.imgUrl);
    e.dataTransfer.setData('hecos-img-url', wrap.dataset.imgUrl);
    e.dataTransfer.setData('hecos-img-name', wrap.dataset.imgName);
    if (banner) banner.classList.add('active');
  });

  document.addEventListener('dragend', (e) => {
    const wrap = e.target.closest('.chat-img-wrap');
    if (wrap) wrap.classList.remove('dragging');
    if (banner) banner.classList.remove('active');
  });
}

// ── Keyboard shortcuts ─────────────────────────────────────────────
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') closeLightbox();
});

// ── Init ──────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  // Move lightbox and banner to body root
  ['img-lightbox', 'img-drop-banner'].forEach(id => {
    const el = document.getElementById(id);
    if (el && el.parentElement !== document.body) document.body.appendChild(el);
  });

  setupImageDragToFolder();

  // Single-image lightbox controls
  const closeBtn = document.getElementById('img-lightbox-close');
  const lb = document.getElementById('img-lightbox');
  if (closeBtn) closeBtn.addEventListener('click', closeLightbox);
  if (lb) lb.addEventListener('click', (e) => { if (e.target === lb) closeLightbox(); });
});
