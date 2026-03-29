/**
 * MODULE: chat_image_viewer.js
 * PURPOSE: Handle AI image rendering, lightbox, and drag-to-folder.
 * Loaded by chat.html.
 *
 * HOW AI SENDS IMAGES:
 * - The AI includes a special tag in its response: [[IMG:filename.ext]]
 * - renderMarkdown() (in chat.html) calls processAiImages() to replace those
 *   tags with rendered <img> inside a .chat-img-wrap container.
 * - Files must exist under /api/images/<filename> (served by routes_chat.py).
 */

// ── Convert [[IMG:name]] tags in AI text to rendered image HTML ──
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
       onclick="if(window.openLightbox) window.openLightbox('${url}')">
  <div class="chat-img-overlay">
    <button class="img-action-btn" onclick="downloadChatImage('${url}','${displayTitle}')">⬇ Scarica</button>
    <button class="img-action-btn" onclick="openLightbox('${url}')">🔍 Zoom</button>
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

// ── Lightbox ──────────────────────────────────────────────────────
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
// Uses the File System Access API (showDirectoryPicker) where available,
// falls back to a simple download.
function setupImageDragToFolder() {
  const banner = document.getElementById('img-drop-banner');

  // Delegate drag events on dynamically created images inside chat
  document.addEventListener('dragstart', (e) => {
    const wrap = e.target.closest('.chat-img-wrap');
    if (!wrap) return;
    wrap.classList.add('dragging');
    e.dataTransfer.effectAllowed = 'copy';
    e.dataTransfer.setData('text/plain', wrap.dataset.imgUrl);
    e.dataTransfer.setData('zentra-img-url', wrap.dataset.imgUrl);
    e.dataTransfer.setData('zentra-img-name', wrap.dataset.imgName);
    if (banner) banner.classList.add('active');
  });

  document.addEventListener('dragend', (e) => {
    const wrap = e.target.closest('.chat-img-wrap');
    if (wrap) wrap.classList.remove('dragging');
    if (banner) banner.classList.remove('active');
  });
}

// ── ESC closes lightbox ───────────────────────────────────────────
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

  // Lightbox close button
  const closeBtn = document.getElementById('img-lightbox-close');
  const lb = document.getElementById('img-lightbox');
  if (closeBtn) closeBtn.addEventListener('click', closeLightbox);
  if (lb) lb.addEventListener('click', (e) => { if (e.target === lb) closeLightbox(); });
});
