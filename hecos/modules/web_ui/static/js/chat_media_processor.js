/**
 * MODULE: chat_media_processor.js
 * PURPOSE: Processes raw HTML from Markdown to enrich local files, videos, and images natively in the chat.
 */

window.processAiMedia = function(html) {
  // We use DOMParser to safely traverse and modify the HTML tree
  const parser = new DOMParser();
  const doc = parser.parseFromString(html, 'text/html');

  // Helper to check if URL is a local file link
  function isLocalLink(url) {
    if (!url) return false;
    return url.startsWith('file://') || /^[a-zA-Z]:[\\/]/.test(url) || url.startsWith('http://localhost') || url.startsWith('https://localhost');
  }
  
  function getSafeLocalUrl(rawUrl) {
    let clean = rawUrl;
    if (clean.startsWith('file:///')) clean = clean.substring(8);
    else if (clean.startsWith('file://')) clean = clean.substring(7);
    
    // We only rewrite true local paths that aren't already API endpoints
    if (clean.startsWith('/api/') || clean.startsWith('http://') || clean.startsWith('https://')) return clean;
    
    return `/api/local_file?path=${encodeURIComponent(clean)}`;
  }

  // 1. Process <a> tags (Videos and Generic Files)
  const links = doc.querySelectorAll('a');
  links.forEach(a => {
    const href = a.getAttribute('href');
    if (!href) return;

    // Is it a YouTube video?
    const ytMatch = href.match(/(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/(?:[^\/\n\s]+\/\S+\/|(?:v|e(?:mbed)?)\/|\S*?[?&]v=)|youtu\.be\/)([a-zA-Z0-9_-]{11})/);
    if (ytMatch && ytMatch[1]) {
      const ytId = ytMatch[1];
      const iframe = document.createElement('iframe');
      iframe.src = `https://www.youtube.com/embed/${ytId}`;
      iframe.width = '100%';
      iframe.height = '315';
      iframe.style.border = 'none';
      iframe.style.borderRadius = '8px';
      iframe.style.marginTop = '10px';
      iframe.allow = 'accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture';
      iframe.allowFullscreen = true;
      a.replaceWith(iframe);
      return;
    }

    // Is it a video file?
    const NATIVE_VIDEO_EXTS = /\.(mp4|webm|ogg|mov)$/i;
    const ALL_VIDEO_EXTS    = /\.(mp4|webm|ogg|mov|avi|mkv|m4v|ts|flv|3gp|wmv|mpeg|mpg)$/i;
    if (ALL_VIDEO_EXTS.test(href)) {
      const src = isLocalLink(href) ? getSafeLocalUrl(href) : href;
      const fileName = href.split(/[\\/]/).pop() || 'Video';
      const isNative = NATIVE_VIDEO_EXTS.test(href);

      if (isNative) {
        // Browser can play natively — use HTML5 video element
        const video = document.createElement('video');
        video.controls = true;
        video.src = src;
        video.style.maxWidth = '100%';
        video.style.borderRadius = '8px';
        video.style.marginTop = '10px';
        a.replaceWith(video);
      } else {
        // Format not natively supported (e.g. MKV, AVI, WMV...)
        // Show a rich card with an inline player attempt + external fallbacks
        const card = document.createElement('div');
        card.className = 'chat-video-card';
        const extIcon = href.match(/\.mkv$/i) ? '🎬' : '🎥';
        const extName = (href.match(/\.([a-z0-9]+)$/i) || ['','?'])[1].toUpperCase();
        const rawPath = href.startsWith('file:///') ? href.slice(8)
                      : href.startsWith('file://') ? href.slice(7)
                      : href;
        const safeRawPath = rawPath.replace(/\\/g, '\\\\').replace(/'/g, "\\'");
        const videoId = 'vid_' + Math.random().toString(36).slice(2, 9);

        card.innerHTML = `
          <div class="chat-video-card-header">
            <span class="chat-video-card-icon">${extIcon}</span>
            <div class="chat-video-card-info">
              <div class="chat-video-card-name" title="${fileName}">${fileName}</div>
              <div class="chat-video-card-meta">${extName} — Streaming via Hecos</div>
            </div>
          </div>
          <div class="chat-video-inline-player" id="player-wrap-${videoId}" style="display:none;">
            <video id="${videoId}" controls style="width:100%; border-radius:8px; background:#000; margin-top:8px;">
              <source src="${src}" type="video/mp4">
              <source src="${src}" type="video/webm">
              <source src="${src}">
            </video>
            <div class="chat-video-card-hint" style="margin-top:4px;">
              <i class="fas fa-info-circle"></i>
              Se il video non parte, usa <strong>Apri con VLC</strong> oppure <strong>Scarica</strong>.
            </div>
          </div>
          <div class="chat-video-card-actions">
            <button onclick="(function(){
              var w=document.getElementById('player-wrap-${videoId}');
              var v=document.getElementById('${videoId}');
              if(w.style.display==='none'){w.style.display='block'; v.play().catch(function(){});}
              else{w.style.display='none'; v.pause();}
            })()" class="chat-video-btn chat-video-btn-open">
              <i class="fas fa-play"></i> Riproduci qui
            </button>
            <button onclick="window.openInVlc('${safeRawPath}')" class="chat-video-btn chat-video-btn-open" style="background:rgba(255,120,0,0.18); border-color:rgba(255,120,0,0.35); color:#ff7800;">
              <i class="fas fa-external-link-alt"></i> Apri con VLC
            </button>
            <a href="${src}" download="${fileName}" class="chat-video-btn chat-video-btn-dl">
              <i class="fas fa-download"></i> Scarica
            </a>
          </div>
        `;
        a.replaceWith(card);
      }
      return;
    }

    // Is it a generic local file?
    if (isLocalLink(href)) {
      const src = getSafeLocalUrl(href);
      const fileName = href.split(/[\\/]/).pop() || 'Local File';
      
      const card = document.createElement('div');
      card.className = 'chat-file-card';
      card.innerHTML = `
        <div class="chat-file-icon"><i class="fas fa-file-alt"></i></div>
        <div class="chat-file-details">
          <div class="chat-file-name">${fileName}</div>
          <div class="chat-file-action"><a href="${src}" target="_blank" download>Open / Download</a></div>
        </div>
      `;
      a.replaceWith(card);
    }
  });

  // 2. Process <img> tags (Images)
  const imgs = doc.querySelectorAll('img');
  imgs.forEach(img => {
    const src = img.getAttribute('src');
    if (!src) return;
    
    const isLocal = isLocalLink(src);
    const safeSrc = isLocal ? getSafeLocalUrl(src) : src;
    const alt = img.getAttribute('alt') || src.split(/[\\/]/).pop() || 'Image';
    
    // We replace it with the rich gallery wrapper if it isn't already inside one
    if (!img.closest('.chat-img-wrap')) {
      const wrapper = document.createElement('div');
      wrapper.className = 'chat-img-wrap';
      wrapper.setAttribute('draggable', 'true');
      wrapper.setAttribute('data-img-url', safeSrc);
      wrapper.setAttribute('data-img-name', alt);
      
      wrapper.innerHTML = `
        <img src="${safeSrc}" alt="${alt}" loading="lazy"
             onerror="this.parentElement.style.display='none'"
             onclick="if(window.openLightbox) window.openLightbox('${safeSrc}')"
             ondblclick="if(window.openChatGallery) window.openChatGallery('${safeSrc}'); return false;">
        <div class="chat-img-overlay">
          <button class="img-action-btn" onclick="downloadChatImage('${safeSrc}','${alt}')">⬇ Scarica</button>
          <button class="img-action-btn" onclick="openLightbox('${safeSrc}')">🔍 Zoom</button>
          <button class="img-action-btn" onclick="openChatGallery('${safeSrc}')">🖼 Gallery</button>
          <button class="img-action-btn" onclick="openMediaFolder()" title="Open local media folder">📁 Folder</button>
        </div>
      `;
      img.replaceWith(wrapper);
    }
  });

  // ── 3. Scan text nodes for bare absolute Windows/Unix paths not wrapped in <a> ──
  // The AI often outputs paths like "(C:\Hecos\...\file.pdf)" that marked.js won't linkify.
  // We walk all text nodes, find these bare paths, and replace them with rich file cards.
  const IMG_EXTS = /\.(png|jpe?g|gif|webp|bmp|svg)$/i;
  const VIDEO_EXTS = /\.(mp4|webm|ogg|mov|avi|mkv)$/i;
  // Matches absolute Windows paths: C:\path\to\file.ext or C:/path/to/file.ext
  // Stops at whitespace, quotes, angle brackets, closing parens/brackets
  const PATH_RE = /([A-Za-z]:[\\/][^\s'"<>\)\]]+)/g;

  function _makeBareFileCard(rawPath) {
    const cleanPath = rawPath.replace(/\\/g, '/').replace(/\/+$/, '');
    const fileName = cleanPath.split('/').pop() || rawPath;
    const ext = (fileName.match(/\.([a-z0-9]+)$/i) || ['', ''])[1].toLowerCase();
    const apiUrl = `/api/local_file?path=${encodeURIComponent(rawPath)}`;

    if (IMG_EXTS.test(fileName)) {
      // Inline image
      return `<div class="chat-img-wrap" data-img-url="${apiUrl}" data-img-name="${fileName}">
        <img src="${apiUrl}" alt="${fileName}" loading="lazy"
             onerror="this.parentElement.style.display='none'"
             onclick="if(window.openLightbox) window.openLightbox('${apiUrl}')">
      </div>`;
    }

    if (VIDEO_EXTS.test(fileName)) {
      // Inline video
      return `<video controls style="max-width:100%;border-radius:8px;margin-top:8px;" src="${apiUrl}"></video>`;
    }

    // Determine icon by extension
    const iconMap = { pdf: 'fa-file-pdf', html: 'fa-file-code', htm: 'fa-file-code',
                      doc: 'fa-file-word', docx: 'fa-file-word', xls: 'fa-file-excel',
                      xlsx: 'fa-file-excel', ppt: 'fa-file-powerpoint', pptx: 'fa-file-powerpoint',
                      txt: 'fa-file-alt', csv: 'fa-file-csv', json: 'fa-file-code',
                      md: 'fa-file-alt' };
    const iconClass = iconMap[ext] || 'fa-file-alt';
    const colorMap = { pdf: '#e74c3c', html: '#3498db', htm: '#3498db',
                       doc: '#2980b9', docx: '#2980b9', xls: '#27ae60',
                       xlsx: '#27ae60', ppt: '#e67e22', pptx: '#e67e22' };
    const iconColor = colorMap[ext] || 'var(--accent)';

    // For PDF/HTML, offer an "Open" button linking to the API serve endpoint
    const serveUrl = (ext === 'html' || ext === 'htm') ? `/api/serve_html?path=${encodeURIComponent(rawPath)}` : apiUrl;
    
    const openBtn = (ext === 'pdf' || ext === 'html' || ext === 'htm')
      ? `<a href="${serveUrl}" target="_blank" style="margin-left:8px; padding:4px 10px; border-radius:5px; background:rgba(108,140,255,0.18); border:1px solid rgba(108,140,255,0.35); color:var(--accent); font-size:0.8em; text-decoration:none; font-weight:600;">
          <i class="fas fa-external-link-alt"></i> Open
        </a>`
      : '';
    const dlBtn = `<a href="${apiUrl}" download="${fileName}" style="padding:4px 10px; border-radius:5px; background:rgba(108,140,255,0.12); border:1px solid rgba(108,140,255,0.25); color:var(--muted); font-size:0.8em; text-decoration:none;">
        <i class="fas fa-download"></i> Download
      </a>`;

    let cardHtml = `<div class="chat-file-card" style="display:flex;align-items:center;gap:10px;padding:10px 14px;background:var(--bg2);border:1px solid var(--border-color);border-radius:10px;margin:6px 0;">
      <div class="chat-file-icon" style="font-size:1.6em;color:${iconColor};"><i class="fas ${iconClass}"></i></div>
      <div class="chat-file-details" style="flex:1;min-width:0;">
        <div class="chat-file-name" style="font-weight:600;font-size:0.9em;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="${rawPath}">${fileName}</div>
        <div class="chat-file-action" style="display:flex;gap:6px;margin-top:5px;">${openBtn}${dlBtn}</div>
      </div>
    </div>`;

    // Add inline iframe preview for HTML
    if (ext === 'html' || ext === 'htm') {
      const iframeId = 'preview_' + Math.random().toString(36).substring(2, 10);
      cardHtml += `
      <div class="chat-html-preview" style="margin-top: 8px; border: 1px solid var(--border-color); border-radius: 8px; overflow: hidden; background: #fff;">
        <div style="background: var(--bg3); padding: 4px 8px; font-size: 0.75em; color: var(--muted); display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border-color);">
          <span>Preview: ${fileName}</span>
          <button onclick="document.getElementById('${iframeId}').src=document.getElementById('${iframeId}').src" style="background:none;border:none;color:var(--accent);cursor:pointer;"><i class="fas fa-sync-alt"></i></button>
        </div>
        <iframe id="${iframeId}" src="${serveUrl}" style="width: 100%; height: 350px; border: none; display: block;" sandbox="allow-same-origin allow-scripts allow-popups"></iframe>
      </div>`;
    }

    return cardHtml;
  }

  // Walk the parsed DOM's text nodes and replace bare paths
  function _processTextNodes(node) {
    if (node.nodeType === Node.TEXT_NODE) {
      const text = node.textContent;
      if (!PATH_RE.test(text)) return;
      PATH_RE.lastIndex = 0; // Reset regex state
      const parts = [];
      let lastIdx = 0;
      let m;
      while ((m = PATH_RE.exec(text)) !== null) {
        const rawPath = m[1] || m[0];
        // Skip if path doesn't have a file extension (likely just a directory reference)
        if (!/\.[a-z0-9]{2,5}$/i.test(rawPath)) {
          // Still keep text up to here as-is by NOT updating lastIdx
          continue;
        }
        if (lastIdx < m.index) parts.push(document.createTextNode(text.slice(lastIdx, m.index)));
        const span = document.createElement('span');
        span.innerHTML = _makeBareFileCard(rawPath);
        parts.push(span);
        lastIdx = m.index + m[0].length;
      }
      PATH_RE.lastIndex = 0;
      if (parts.length === 0) return; // No matches found, leave as-is
      if (lastIdx < text.length) parts.push(document.createTextNode(text.slice(lastIdx)));
      const frag = document.createDocumentFragment();
      parts.forEach(p => frag.appendChild(p));
      node.parentNode.replaceChild(frag, node);
    } else if (node.nodeType === Node.ELEMENT_NODE) {
      // Don't process inside <a>, <pre>, <code>, or elements we already transformed
      if (['A','PRE','CODE','SCRIPT','STYLE'].includes(node.tagName)) return;
      if (node.classList && (node.classList.contains('chat-file-card') || node.classList.contains('chat-img-wrap') || node.classList.contains('chat-video-card'))) return;
      // Must snapshot childNodes before iteration since we may mutate the list
      Array.from(node.childNodes).forEach(_processTextNodes);
    }
  }
  _processTextNodes(doc.body);

  // Maintain the legacy [[IMG:...]] support for backwards compatibility
  let finalHtml = doc.body.innerHTML;
  if (typeof window.processAiImages === 'function') {
      finalHtml = window.processAiImages(finalHtml);
  }

  return finalHtml;
};

window.openInVlc = function(filePath) {
  // Mostra un feedback all'utente
  if (window.HecosUI && window.HecosUI.showToast) {
    window.HecosUI.showToast("Avvio VLC in corso...", "info");
  }

  fetch('/api/open_in_vlc', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path: decodeURIComponent(filePath) })
  })
  .then(res => res.json())
  .then(data => {
    if (!data.ok) {
      console.error("[VLC] Errore:", data.error);
      if (window.HecosUI && window.HecosUI.showToast) {
        window.HecosUI.showToast("Impossibile avviare il video con VLC.", "error");
      } else {
        alert("Errore avvio video: " + data.error);
      }
    } else if (data.message) {
      if (window.HecosUI && window.HecosUI.showToast) {
        window.HecosUI.showToast(data.message, "success");
      }
    }
  })
  .catch(err => {
    console.error("[VLC] Network error:", err);
    if (window.HecosUI && window.HecosUI.showToast) {
      window.HecosUI.showToast("Errore di rete durante l'avvio del video.", "error");
    }
  });
};
