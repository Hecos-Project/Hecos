/**
 * MODULE: chat_image_viewer.js
 * PURPOSE: Handle AI image rendering, single-click lightbox, and
 *          double-click gallery (powered by hecos_gallery.js).
 *
 * HOW AI SENDS IMAGES:
 * - The AI includes [[IMG:filename.ext]] or [[IMG:https://...]] tags.
 * - renderMarkdown() calls processAiImages() to replace those tags with
 *   rendered <img> inside a .chat-img-wrap container.
 * - Files are served by routes_chat.py at /api/images/<filename>.
 *
 * CLICK BEHAVIOUR:
 * - Single click → classic full-screen lightbox (single image).
 * - Double click → HecosGallery with all chat images + filmstrip.
 */

// ── Gallery helper — collects all chat images for the media player ────────────
function _getChatGalleryItems() {
  return Array.from(document.querySelectorAll('.chat-img-wrap')).map(wrap => ({
    name: wrap.dataset.imgName || 'Image',
    type: 'image',
    url:  wrap.dataset.imgUrl  || wrap.querySelector('img')?.src || ''
  }));
}

// ── Open gallery (button click / double-click on image) ────────────────────────
window.openChatGallery = async function(url) {
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

  if (window.HecosGallery) {
      window.HecosGallery.open(items, idx, {
          title: '<i class="fas fa-images"></i> Chat Gallery',
          extraActions: (item) => {
              return window.HecosGallery.button('⚙️ Manage', () => window.open('/hecos/config/ui#ia', '_blank'));
          }
      });
  }
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

// ── Open persona folder directly ───────────────────────────────────────────────
window.openPersonaMediaFolder = async function(persona) {
  if (!persona) return;
  try {
    const res = await fetch('/api/persona/media/open-folder', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ persona: persona })
    });
    const data = await res.json();
    if (!data.ok) console.error("Error opening persona folder:", data.error);
  } catch (err) {
    console.error("Failed to call API:", err);
  }
};

// ── Convert [[IMG:name]] and [[SOUL_MEDIA:name]] tags in AI text to rendered HTML ──────────────
window.processAiImages = function(html) {
  // First handle standard IMG tags
  html = html.replace(/\[\[IMG:([^\]]+)\]\]/g, (match, identifier) => {
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
    <button class="img-action-btn" onclick="downloadChatImage('${url}','${displayTitle}')">⬇ Download</button>
    <button class="img-action-btn" onclick="openLightbox('${url}')">🔍 Zoom</button>
    <button class="img-action-btn" onclick="openChatGallery('${url}')">🖼 Gallery</button>
    <button class="img-action-btn" onclick="openMediaFolder()" title="Open local media folder">📁 Folder</button>
    <button class="img-action-btn" onclick="window.open('/hecos/config/ui#ia', '_blank')" title="Manage Soul Media">⚙️ Manage</button>
  </div>
</div>`;
  });

  // Then handle SOUL_MEDIA tags
  html = html.replace(/\[\[SOUL_MEDIA:([^\]]+)\]\]/g, (match, identifier) => {
    identifier = identifier.trim();
    
    // If asking for the whole gallery
    if (identifier.toLowerCase() === 'all') {
      return `
<div class="chat-media-btn-wrap" style="margin: 10px 0; padding: 12px; background: rgba(108,140,255,0.1); border: 1px solid rgba(108,140,255,0.2); border-radius: 8px; text-align: center;">
  <div style="font-size: 13px; color: var(--text-color); margin-bottom: 8px;"><i class="fas fa-photo-video"></i> <b>Soul Media Gallery</b></div>
  <button class="btn btn-primary" onclick="if(window.openSoulGallery) window.openSoulGallery(); else if(window.openChatGallery) window.openChatGallery();">
    <i class="fas fa-images"></i> Open Gallery
  </button>
  <button class="btn btn-secondary" onclick="window.openPersonaMediaFolder(window.HecosPersonaName || 'Hecos_System_Soul')">
    <i class="fas fa-folder-open"></i> Folder
  </button>
  <button class="btn btn-secondary" onclick="window.open('/hecos/config/ui#ia', '_blank')">
    <i class="fas fa-cog"></i> Manage
  </button>
</div>`;
    }

    // Determine current persona for path
    let personaName = 'Hecos_System_Soul';
    if (window.HecosPersonaName) {
      personaName = window.HecosPersonaName.replace('.yaml', '');
    }
    const isUrl = identifier.startsWith('http://') || identifier.startsWith('https://');
    const url = isUrl ? identifier : `/personas/${encodeURIComponent(personaName)}/media/${encodeURIComponent(identifier)}`;
    const displayTitle = isUrl ? (identifier.split('/').pop() || 'Media') : identifier;
    
    // Check if it's a video/audio by extension
    const isVideo = url.match(/\.(mp4|webm|avi|mov)$/i);
    const isAudio = url.match(/\.(mp3|wav|ogg)$/i);

    let mediaHtml = '';
    if (isVideo) {
      mediaHtml = `<video src="${url}" autoplay loop muted playsinline style="width: 100%; border-radius: 8px;"
                   onclick="if(window.HecosGallery) window.HecosGallery.open([{url:'${url}', name:'${displayTitle}', type:'video'}], 0)"
                   ondblclick="if(window.openSoulGallery) window.openSoulGallery('${url}'); return false;"></video>`;
    } else if (isAudio) {
      mediaHtml = `<audio src="${url}" controls style="width: 100%;"></audio>`;
    } else {
      mediaHtml = `<img src="${url}" alt="${displayTitle}" loading="lazy"
       onerror="this.parentElement.style.display='none'"
       onclick="if(window.openLightbox) window.openLightbox('${url}')"
       ondblclick="if(window.openSoulGallery) window.openSoulGallery('${url}'); return false;">`;
    }

    return `
<div class="chat-img-wrap" draggable="true" data-img-url="${url}" data-img-name="${displayTitle}">
  ${mediaHtml}
  <div class="chat-img-overlay">
    <button class="img-action-btn" onclick="downloadChatImage('${url}','${displayTitle}')">⬇ Download</button>
    ${!isAudio ? `<button class="img-action-btn" onclick="if(window.HecosGallery) window.HecosGallery.open([{url:'${url}', name:'${displayTitle}', type:'${isVideo?'video':'image'}'}], 0)">🔍 Zoom</button>` : ''}
    <button class="img-action-btn" onclick="if(window.openSoulGallery) window.openSoulGallery('${url}')">🖼 Gallery</button>
    <button class="img-action-btn" onclick="window.openPersonaMediaFolder('${personaName}')" title="Open local media folder">📁 Folder</button>
    <button class="img-action-btn" onclick="window.open('/hecos/config/ui#ia', '_blank')" title="Manage Soul Media">⚙️ Manage</button>
  </div>
</div>`;
  });

  return html;
};

// ── Open Soul Media gallery specifically ──────────────────────────────────
window.openSoulGallery = async function(url) {
  let items = [];
  let personaName = 'Hecos_System_Soul';
  if (window.HecosPersonaName) {
    personaName = window.HecosPersonaName;
  }
  
  try {
    const res = await fetch(`/api/persona/media?persona=${encodeURIComponent(personaName)}`);
    if (res.ok) {
      const data = await res.json();
      if (data.ok && data.media && data.media.length) {
        items = data.media; // {name, url, type, is_avatar}
      }
    }
  } catch (err) {
    console.warn('[Gallery] /api/persona/media failed.', err);
  }

  if (!items.length) {
    if (window.showToast) window.showToast('📭 No media found for this Soul.', 'info');
    return;
  }

  let idx = 0;
  if (url) {
    const found = items.findIndex(item => item.url === url || item.url.endsWith(url));
    if (found >= 0) idx = found;
  }

  if (window.HecosGallery) {
      window.HecosGallery.open(items, idx, {
          title: '<i class="fas fa-photo-video"></i> Soul Media',
          onOpenFolder: () => { if(window.openPersonaMediaFolder) window.openPersonaMediaFolder(personaName); },
          extraActions: (item) => {
              return window.HecosGallery.button('⚙️ Manage', () => window.open('/hecos/config/ui#ia', '_blank'));
          }
      });
  }
};

// ── Open User Media gallery specifically ──────────────────────────────────
window.openUserGallery = async function(url) {
  let items = [];
  
  try {
    const res = await fetch(`/hecos/api/users/me/media`);
    if (res.ok) {
      const data = await res.json();
      if (data.ok && data.media && data.media.length) {
        items = data.media;
      }
    }
  } catch (err) {
    console.warn('[Gallery] /hecos/api/users/me/media failed.', err);
  }

  if (!items.length) {
    // If no media, just show the single image passed
    items = [{ url: url || '/assets/Hecos_Logo_NBG.png', name: 'Avatar', type: 'image' }];
  }

  let idx = 0;
  if (url) {
    const found = items.findIndex(item => item.url === url || item.url.endsWith(url));
    if (found >= 0) idx = found;
  }

  if (window.HecosGallery) {
      window.HecosGallery.open(items, idx, {
          title: '<i class="fas fa-photo-video"></i> User Media',
          onOpenFolder: () => {
              fetch('/hecos/api/users/me/media/open-folder', { method: 'POST' }).catch(console.error);
          },
          extraActions: (item) => {
              return window.HecosGallery.button('⚙️ Manage', () => window.open('/hecos/config/ui#users', '_blank'));
          }
      });
  }
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
