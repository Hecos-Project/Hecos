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

// ── Self-contained Image Gallery ──────────────────────────────────────────────

function _ensureGalleryModal() {
  if (document.getElementById('hg-gallery-modal')) return;

  const style = document.createElement('style');
  style.textContent = `
    #hg-gallery-modal {
      display:none; position:fixed; inset:0; z-index:99999;
      background:rgba(0,0,0,0.92); flex-direction:column;
      align-items:center; justify-content:center;
      animation:hg-fadein 0.2s ease;
    }
    #hg-gallery-modal.open { display:flex; }
    @keyframes hg-fadein { from{opacity:0} to{opacity:1} }

    #hg-gallery-main {
      position:relative; display:flex; align-items:center;
      justify-content:center; width:100%; flex:1;
    }
    #hg-gallery-img {
      max-width:90vw; max-height:75vh; border-radius:8px;
      object-fit:contain; box-shadow:0 8px 48px #000a;
      transition:opacity .15s ease;
    }
    #hg-gallery-prev, #hg-gallery-next {
      position:absolute; top:50%; transform:translateY(-50%);
      background:rgba(255,255,255,0.08); border:1px solid rgba(255,255,255,0.15);
      color:#fff; font-size:22px; padding:10px 16px; border-radius:10px;
      cursor:pointer; transition:background .2s;
      backdrop-filter:blur(4px); user-select:none;
    }
    #hg-gallery-prev:hover, #hg-gallery-next:hover { background:rgba(255,255,255,0.2); }
    #hg-gallery-prev { left:16px; }
    #hg-gallery-next { right:16px; }
    #hg-gallery-close {
      position:absolute; top:14px; right:18px;
      background:rgba(255,255,255,0.08); border:1px solid rgba(255,255,255,0.15);
      color:#fff; font-size:18px; padding:5px 12px; border-radius:8px;
      cursor:pointer; z-index:1;
    }
    #hg-gallery-close:hover { background:rgba(255,80,80,0.3); }
    #hg-gallery-counter {
      position:absolute; top:14px; left:50%; transform:translateX(-50%);
      color:rgba(255,255,255,0.7); font-size:13px; font-weight:500;
      background:rgba(0,0,0,0.4); padding:4px 12px; border-radius:20px;
    }
    #hg-gallery-name {
      color:rgba(255,255,255,0.6); font-size:12px; margin-top:10px;
      max-width:80vw; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;
    }
    #hg-gallery-filmstrip {
      display:flex; gap:8px; padding:10px 16px; overflow-x:auto;
      max-width:90vw; margin-top:4px;
    }
    .hg-strip-thumb {
      width:56px; height:56px; border-radius:6px; object-fit:cover;
      cursor:pointer; opacity:0.5; border:2px solid transparent;
      transition:opacity .15s, border-color .15s; flex-shrink:0;
    }
    .hg-strip-thumb.active { opacity:1; border-color:#fff; }
    .hg-strip-thumb:hover { opacity:0.85; }
    #hg-gallery-actions {
      display:flex; gap:10px; margin-top:8px; margin-bottom:10px;
    }
    .hg-act-btn {
      background:rgba(255,255,255,0.08); border:1px solid rgba(255,255,255,0.15);
      color:#fff; padding:6px 14px; border-radius:8px; cursor:pointer;
      font-size:12px; transition:background .2s;
    }
    .hg-act-btn:hover { background:rgba(255,255,255,0.2); }
  `;
  document.head.appendChild(style);

  const modal = document.createElement('div');
  modal.id = 'hg-gallery-modal';
  modal.innerHTML = `
    <div id="hg-gallery-main">
      <button id="hg-gallery-close">✕</button>
      <div id="hg-gallery-counter"></div>
      <button id="hg-gallery-prev">‹</button>
      <img id="hg-gallery-img" src="" alt="">
      <video id="hg-gallery-vid" src="" controls autoplay style="display:none; max-width:90vw; max-height:75vh; border-radius:8px; box-shadow:0 8px 48px #000a; outline:none;"></video>
      <button id="hg-gallery-next">›</button>
    </div>
    <div id="hg-gallery-name"></div>
    <div id="hg-gallery-actions">
      <button class="hg-act-btn" id="hg-act-download">⬇ Scarica</button>
      <button class="hg-act-btn" id="hg-act-folder">📁 Apri cartella</button>
    </div>
    <div id="hg-gallery-filmstrip"></div>
  `;
  document.body.appendChild(modal);

  // Wire up controls
  let _items = [], _idx = 0;

  function _show(index) {
    if (!_items.length) return;
    _idx = (index + _items.length) % _items.length;
    const item = _items[_idx];
    const img = document.getElementById('hg-gallery-img');
    const vid = document.getElementById('hg-gallery-vid');
    
    // Check if it's a video
    const isVideo = item.url.match(/\.(mp4|webm|avi|mov)$/i);
    
    if (isVideo) {
      img.style.display = 'none';
      img.src = '';
      vid.style.display = 'block';
      vid.src = item.url;
      vid.play().catch(() => {});
    } else {
      vid.style.display = 'none';
      vid.pause();
      vid.src = '';
      img.style.display = 'block';
      img.style.opacity = '0';
      img.src = item.url;
      img.onload = () => { img.style.opacity = '1'; };
    }
    
    document.getElementById('hg-gallery-name').textContent = item.name || '';
    document.getElementById('hg-gallery-counter').textContent = `${_idx + 1} / ${_items.length}`;
    document.querySelectorAll('.hg-strip-thumb').forEach((t, i) => {
      t.classList.toggle('active', i === _idx);
      if (i === _idx) t.scrollIntoView({ behavior:'smooth', inline:'nearest', block:'nearest' });
    });
  }

  window._hg_gallery_show = _show;
  window._hg_gallery_open = function(items, startIdx) {
    _items = items;
    const strip = document.getElementById('hg-gallery-filmstrip');
    strip.innerHTML = '';
    items.forEach((item, i) => {
      const th = document.createElement('img');
      th.src = item.url;
      th.className = 'hg-strip-thumb';
      th.onclick = () => _show(i);
      strip.appendChild(th);
    });
    _show(startIdx || 0);
    modal.classList.add('open');
  };

  document.getElementById('hg-gallery-close').onclick = () => {
    modal.classList.remove('open');
    document.getElementById('hg-gallery-vid').pause();
  };
  document.getElementById('hg-gallery-prev').onclick  = () => _show(_idx - 1);
  document.getElementById('hg-gallery-next').onclick  = () => _show(_idx + 1);
  modal.addEventListener('click', e => { 
    if (e.target === modal) {
      modal.classList.remove('open');
      document.getElementById('hg-gallery-vid').pause();
    }
  });

  document.getElementById('hg-act-download').onclick = () => {
    if (!_items[_idx]) return;
    const a = document.createElement('a');
    a.href = _items[_idx].url; a.download = _items[_idx].name || 'media';
    document.body.appendChild(a); a.click(); document.body.removeChild(a);
  };
  document.getElementById('hg-act-folder').onclick = () => {
    fetch('/api/open_media_folder', { method:'POST' }).catch(() => {});
  };

  document.addEventListener('keydown', e => {
    if (!modal.classList.contains('open')) return;
    if (e.key === 'ArrowLeft')  _show(_idx - 1);
    if (e.key === 'ArrowRight') _show(_idx + 1);
    if (e.key === 'Escape') {
      modal.classList.remove('open');
      document.getElementById('hg-gallery-vid').pause();
    }
  });
}

// ── Open gallery (button click / double-click on image) ────────────────────────
window.openChatGallery = async function(url) {
  _ensureGalleryModal();

  let items = [];
  try {
    const res = await fetch('/api/images');
    if (res.ok) {
      const images = await res.json();
      if (Array.isArray(images) && images.length) {
        items = images.map(img => ({ name: img.name, url: img.url }));
      }
    }
  } catch (err) {
    console.warn('[Gallery] /api/images failed, falling back to chat images.', err);
  }

  if (!items.length) {
    items = _getChatGalleryItems();
  }

  if (!items.length) {
    if (window.showToast) window.showToast('📭 Nessuna immagine trovata.', 'info');
    return;
  }

  let idx = 0;
  if (url) {
    const rawName = url.split('?')[0].split('/').pop();
    const found = items.findIndex(item =>
      item.url === url ||
      item.url.endsWith(rawName) ||
      item.name === rawName
    );
    if (found >= 0) idx = found;
  }

  window._hg_gallery_open(items, idx);
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
