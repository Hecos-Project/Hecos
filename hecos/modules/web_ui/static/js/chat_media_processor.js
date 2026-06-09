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

    // Is it a local video?
    if (/\.(mp4|webm|ogg|mov|avi)$/i.test(href)) {
      const src = isLocalLink(href) ? getSafeLocalUrl(href) : href;
      const video = document.createElement('video');
      video.controls = true;
      video.src = src;
      video.style.maxWidth = '100%';
      video.style.borderRadius = '8px';
      video.style.marginTop = '10px';
      a.replaceWith(video);
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

  // Maintain the legacy [[IMG:...]] support for backwards compatibility
  let finalHtml = doc.body.innerHTML;
  if (typeof window.processAiImages === 'function') {
      finalHtml = window.processAiImages(finalHtml);
  }

  return finalHtml;
};
