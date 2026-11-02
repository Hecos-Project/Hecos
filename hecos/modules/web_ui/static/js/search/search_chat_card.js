/**
 * search_chat_card.js
 * Injected into Hecos Chat UI to transform [[HSEARCH:<id>]] and [[HMEDIA:<id>]] tokens
 * into beautiful, interactive, media-rich Net Search cards with live media previews.
 */
(function () {
  'use strict';

  const HSEARCH_REGEX = /\[\[HSEARCH:([a-zA-Z0-9_-]+)\]\]/g;
  const HMEDIA_REGEX = /\[\[HMEDIA:([a-zA-Z0-9_-]+)\]\]/g;
  const sessionCache = new Map();

  function escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  function formatDuration(ms) {
    if (!ms && ms !== 0) return '';
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(1)}s`;
  }

  // ── Render Shell ─────────────────────────────────────────────────────────────
  function renderSearchCard(sessionId, isMediaMode) {
    const cardId = `hsearch-card-${sessionId}`;
    return `
      <div class="hsearch-chat-card" id="${cardId}" data-session-id="${sessionId}" data-media-priority="${isMediaMode ? '1' : '0'}">
        <div class="hsearch-card-header">
          <div class="hsearch-card-title">
            <span class="hsearch-icon"><i class="fas fa-satellite-dish"></i></span>
            <span class="hsearch-title-text" id="${cardId}-title">Net Search</span>
            <span class="hsearch-badge-live" id="${cardId}-badge">Searching...</span>
          </div>
          <div class="hsearch-card-actions">
            <button class="hsearch-btn-toggle" onclick="window.toggleHSearchSources('${sessionId}')" title="Toggle sources">
              <i class="fas fa-list-ul"></i> <span id="${cardId}-toggle-lbl">Sources</span>
              <i class="fas fa-chevron-down" id="${cardId}-icon"></i>
            </button>
            <a href="/search?session=${sessionId}" target="_blank" class="hsearch-btn-open" title="Open in Net Search console">
              <i class="fas fa-external-link-alt"></i> Console
            </a>
          </div>
        </div>

        <!-- Media Previews Section (auto-visible if media found) -->
        <div class="hsearch-media-section" id="${cardId}-media" style="display:none;"></div>

        <!-- Collapsible Sources / Web Results -->
        <div class="hsearch-card-content" id="${cardId}-content" style="display:none;">
          <div class="hsearch-loading"><i class="fas fa-spinner fa-spin"></i> Loading source details...</div>
        </div>

        <!-- Footer Quick Bar -->
        <div class="hsearch-card-footer" id="${cardId}-footer" style="display:none;">
          <div class="hsearch-footer-meta" id="${cardId}-footer-meta"></div>
          <button class="hsearch-btn-copy" onclick="window.copyHSearchReport('${sessionId}')" title="Copy report to clipboard">
            <i class="fas fa-copy"></i> Copy report
          </button>
        </div>
      </div>
    `;
  }

  // ── Session Data Fetcher ─────────────────────────────────────────────────────
  async function fetchSession(sessionId) {
    if (sessionCache.has(sessionId)) {
      return sessionCache.get(sessionId);
    }
    try {
      const res = await fetch(`/api/hsearch/sessions/${sessionId}`);
      const data = await res.json();
      if (data.ok && data.session) {
        sessionCache.set(sessionId, data.session);
        return data.session;
      }
    } catch (e) {
      console.warn(`[NetSearchChatCard] Failed to fetch session ${sessionId}:`, e);
    }
    return null;
  }

  // ── Build Media Previews (Anti-Arlecchino, matches Core chat) ────────────────
  function buildMediaHtml(session, cardId, maxPreview = 6) {
    const results = session.results || [];
    const mediaItems = [];

    results.forEach((r, idx) => {
      const cat = (r.category || '').toLowerCase();
      const eng = (r.engine || '').toLowerCase();
      const url = r.url || '';
      const mUrl = r.media_url || '';
      const thumb = r.thumbnail_url || (cat === 'images' ? url : '');

      const isVideo = cat === 'videos' || eng.includes('video') || eng === 'dailymotion' || eng === 'peertube' || /\.(mp4|webm|mkv|mov|avi)$/i.test(mUrl || url) || /(youtube\.com\/watch|youtu\.be|dailymotion\.com|vimeo\.com)/i.test(url);
      const isAudio = cat === 'audio' || /\.(mp3|wav|ogg|m4a|flac)$/i.test(mUrl || url);
      const isImage = !isVideo && !isAudio && (cat === 'images' || Boolean(thumb));
      const isFile = cat === 'files' || /\.(pdf|docx?|xlsx?|zip|rar|7z|tar\.gz|epub|mobi)$/i.test(url);

      if (isVideo || isAudio || isImage || isFile) {
        mediaItems.push({
          idx: idx + 1,
          type: isVideo ? 'video' : isAudio ? 'audio' : isFile ? 'file' : 'image',
          result: r,
          thumb: thumb,
          mediaUrl: mUrl || url,
          isVideo, isAudio, isImage, isFile
        });
      }
    });

    if (mediaItems.length === 0) return '';

    const visibleItems = mediaItems.slice(0, maxPreview);
    const hiddenCount = mediaItems.length - maxPreview;

    const videos = visibleItems.filter(m => m.type === 'video');
    const images = visibleItems.filter(m => m.type === 'image');
    const audios = visibleItems.filter(m => m.type === 'audio');
    const files = visibleItems.filter(m => m.type === 'file');

    let html = `
      <div class="hsearch-media-header">
        <span class="hsearch-media-title"><i class="fas fa-photo-video"></i> Media Previews Found (${mediaItems.length})</span>
      </div>
    `;

    // 1. Videos
    if (videos.length > 0) {
      html += `<div class="hsearch-video-grid">`;
      videos.forEach(v => {
        const r = v.result;
        const dur = r.metadata && r.metadata.duration ? r.metadata.duration : '';
        const safeThumb = v.thumb ? escapeHtml(v.thumb) : '';
        const safeUrl = escapeHtml(r.url);
        const safeMedia = escapeHtml(v.mediaUrl);
        const safeTitle = escapeHtml(r.title || 'Video');
        const engName = escapeHtml(r.engine || 'video');
        const vidId = `vid-${session.id}-${v.idx}`;

        const isDirectStream = /\.(mp4|webm|ogg)$/i.test(v.mediaUrl);

        html += `
          <div class="hsearch-video-card" id="${vidId}-card">
            <div class="hsearch-video-thumb" onclick="window.playHSearchVideo('${session.id}', ${v.idx})">
              ${safeThumb ? `<img src="${safeThumb}" alt="${safeTitle}" loading="lazy" onerror="this.style.display='none';">` : `<div class="hsearch-video-placeholder"><i class="fas fa-film"></i></div>`}
              <div class="hsearch-video-play-overlay"><i class="fas fa-play"></i></div>
              ${dur ? `<span class="hsearch-duration-pill">${escapeHtml(dur)}</span>` : ''}
              <span class="hsearch-engine-pill">${engName}</span>
            </div>
            <div class="hsearch-video-info">
              <a href="${safeUrl}" target="_blank" class="hsearch-video-title" title="${safeTitle}">${safeTitle}</a>
              <div class="hsearch-video-actions">
                <button class="hsearch-vbtn hsearch-vbtn-play" onclick="window.playHSearchVideo('${session.id}', ${v.idx})">
                  <i class="fas fa-play"></i> Watch
                </button>
                <a href="${safeUrl}" target="_blank" class="hsearch-vbtn hsearch-vbtn-link">
                  <i class="fas fa-external-link-alt"></i> Source
                </a>
              </div>
            </div>
            <div class="hsearch-video-inline-player" id="${vidId}-player" style="display:none;"></div>
          </div>
        `;
      });
      html += `</div>`;
    }

    // 2. Images Wall (Core photo-wall style)
    if (images.length > 0) {
      html += `<div class="hsearch-photo-wall">`;
      images.forEach(img => {
        const r = img.result;
        const thumbUrl = img.thumb || r.url;
        const fullUrl = r.media_url || r.url;
        const safeTitle = escapeHtml(r.title || 'Immagine');

        html += `
          <div class="hsearch-img-wrap" onclick="window.openHSearchLightbox('${escapeHtml(fullUrl)}')" title="${safeTitle}">
            <img src="${escapeHtml(thumbUrl)}" alt="${safeTitle}" loading="lazy" onerror="this.parentElement.style.display='none';">
            <div class="hsearch-img-overlay">
              <span class="hsearch-img-title">${safeTitle}</span>
              <span class="hsearch-img-btn"><i class="fas fa-expand"></i></span>
            </div>
          </div>
        `;
      });
      html += `</div>`;
    }

    // 3. Audio Tracks
    if (audios.length > 0) {
      html += `<div class="hsearch-audio-list">`;
      audios.forEach(aud => {
        const r = aud.result;
        const safeTitle = escapeHtml(r.title || 'Audio Track');
        const safeAudio = escapeHtml(aud.mediaUrl);
        html += `
          <div class="hsearch-audio-card">
            <div class="hsearch-audio-info">
              <span class="hsearch-audio-icon"><i class="fas fa-music"></i></span>
              <span class="hsearch-audio-title">${safeTitle}</span>
              <span class="hsearch-engine-pill">${escapeHtml(r.engine)}</span>
            </div>
            <audio controls preload="none" class="hsearch-audio-player">
              <source src="${safeAudio}">
              Your browser does not support audio playback.
            </audio>
          </div>
        `;
      });
      html += `</div>`;
    }

    // 4. Downloadable Files (PDF, ZIP, etc.)
    if (files.length > 0) {
      html += `<div class="hsearch-files-list">`;
      files.forEach(f => {
        const r = f.result;
        const ext = (r.url.split('.').pop() || 'file').toUpperCase().slice(0, 5);
        html += `
          <div class="hsearch-file-card">
            <div class="hsearch-file-icon"><i class="fas fa-file-download"></i></div>
            <div class="hsearch-file-details">
              <a href="${escapeHtml(r.url)}" target="_blank" class="hsearch-file-name">${escapeHtml(r.title || r.url)}</a>
              <span class="hsearch-file-meta"><span class="hsearch-ext-badge">${ext}</span> ${escapeHtml(r.engine)}</span>
            </div>
            <a href="${escapeHtml(r.url)}" target="_blank" download class="hsearch-file-btn">
              <i class="fas fa-download"></i> Download
            </a>
          </div>
        `;
      });
      html += `</div>`;
    }

    // "Show all media" expander
    if (hiddenCount > 0) {
      html += `
        <div class="hsearch-more-media">
          <a href="/search?session=${session.id}&tab=media" target="_blank" class="hsearch-btn-more">
            <i class="fas fa-th"></i> Show ${hiddenCount} more media in console
          </a>
        </div>
      `;
    }

    return html;
  }

  // ── Populate Card with Session Data ──────────────────────────────────────────
  async function populateCard(sessionId) {
    const card = document.getElementById(`hsearch-card-${sessionId}`);
    if (!card || card.dataset.populated === 'true') return;

    const s = await fetchSession(sessionId);
    if (!s) {
      const badge = document.getElementById(`hsearch-card-${sessionId}-badge`);
      if (badge) badge.innerText = 'Sessione terminata';
      return;
    }

    card.dataset.populated = 'true';

    // Update Header
    const titleEl = document.getElementById(`hsearch-card-${sessionId}-title`);
    const badgeEl = document.getElementById(`hsearch-card-${sessionId}-badge`);
    if (titleEl && s.query) {
      titleEl.innerText = s.query.length > 34 ? s.query.slice(0, 32) + '...' : s.query;
      titleEl.title = `Query: ${s.query}`;
    }
    if (badgeEl) {
      badgeEl.innerText = `${s.total_results} sources (${formatDuration(s.duration_ms)})`;
    }

    // Media Section
    const mediaEl = document.getElementById(`hsearch-card-${sessionId}-media`);
    if (mediaEl) {
      const mediaHtml = buildMediaHtml(s, `hsearch-card-${sessionId}`);
      if (mediaHtml) {
        mediaEl.innerHTML = mediaHtml;
        mediaEl.style.display = 'block';
      }
    }

    // Populate Sources Content
    const contentEl = document.getElementById(`hsearch-card-${sessionId}-content`);
    if (contentEl) {
      if (s.results && s.results.length > 0) {
        contentEl.innerHTML = s.results.map((r, i) => `
          <div class="hsearch-item-row">
            <span class="hsearch-num">[${i + 1}]</span>
            <div class="hsearch-item-text">
              <a href="${escapeHtml(r.url)}" target="_blank" class="hsearch-link">${escapeHtml(r.title || r.url)}</a>
              ${r.snippet ? `<div class="hsearch-snippet">${escapeHtml(r.snippet)}</div>` : ''}
              <div class="hsearch-sub">
                <span class="hsearch-eng">${escapeHtml(r.engine || 'web')}</span>
                <span class="hsearch-net">${r.network === 'tor' || (r.url && r.url.includes('.onion')) ? '🧅 Tor' : '🌐 Clear'}</span>
                <span class="hsearch-url">${escapeHtml(r.url)}</span>
              </div>
            </div>
          </div>
        `).join('');
      } else {
        contentEl.innerHTML = '<div style="padding:10px; font-size:12px; color:var(--muted);">No links saved for this session.</div>';
      }
    }

    // Footer
    const footerEl = document.getElementById(`hsearch-card-${sessionId}-footer`);
    const metaEl = document.getElementById(`hsearch-card-${sessionId}-footer-meta`);
    if (footerEl && metaEl) {
      const engines = [...new Set((s.results || []).map(r => r.engine).filter(Boolean))].slice(0, 4).join(', ');
      metaEl.innerText = engines ? `Engines: ${engines}` : '';
      footerEl.style.display = 'flex';
    }
  }

  // ── Global Window Interactivity Handlers ─────────────────────────────────────
  window.toggleHSearchSources = function (sessionId) {
    const content = document.getElementById(`hsearch-card-${sessionId}-content`);
    const icon = document.getElementById(`hsearch-card-${sessionId}-icon`);
    const toggleLbl = document.getElementById(`hsearch-card-${sessionId}-toggle-lbl`);
    if (!content) return;

    if (content.style.display === 'none') {
      content.style.display = 'block';
      if (icon) icon.className = 'fas fa-chevron-up';
      if (toggleLbl) toggleLbl.innerText = 'Close';
      populateCard(sessionId);
    } else {
      content.style.display = 'none';
      if (icon) icon.className = 'fas fa-chevron-down';
      if (toggleLbl) toggleLbl.innerText = 'Sources';
    }
  };

  window.openHSearchLightbox = function (url) {
    if (typeof window.openLightbox === 'function') {
      window.openLightbox(url);
      return;
    }
    // Fallback Lightbox
    let lb = document.getElementById('hsearch-fallback-lightbox');
    if (!lb) {
      lb = document.createElement('div');
      lb.id = 'hsearch-fallback-lightbox';
      lb.className = 'hsearch-lightbox-modal';
      lb.innerHTML = `
        <span class="hsearch-lightbox-close" onclick="this.parentElement.style.display='none'">✕</span>
        <img id="hsearch-fallback-lightbox-img" src="" alt="Fullscreen Preview">
      `;
      lb.onclick = (e) => { if (e.target === lb) lb.style.display = 'none'; };
      document.body.appendChild(lb);
    }
    const img = document.getElementById('hsearch-fallback-lightbox-img');
    if (img) img.src = url;
    lb.style.display = 'flex';
  };

  window.playHSearchVideo = function (sessionId, idx) {
    const s = sessionCache.get(sessionId);
    if (!s || !s.results || !s.results[idx - 1]) return;
    const r = s.results[idx - 1];
    const playerWrap = document.getElementById(`vid-${sessionId}-${idx}-player`);
    if (!playerWrap) return;

    if (playerWrap.style.display === 'block') {
      playerWrap.style.display = 'none';
      playerWrap.innerHTML = '';
      return;
    }

    const url = r.media_url || r.url;

    // 1. Direct HTML5 video
    if (/\.(mp4|webm|ogg)$/i.test(url)) {
      playerWrap.innerHTML = `
        <video controls autoplay style="width:100%; border-radius:8px; max-height:360px; background:#000;">
          <source src="${escapeHtml(url)}">
        </video>
      `;
      playerWrap.style.display = 'block';
      return;
    }

    // 2. YouTube embed
    const ytMatch = url.match(/(?:youtube\.com\/watch\?v=|youtu\.be\/)([a-zA-Z0-9_-]{11})/);
    if (ytMatch) {
      playerWrap.innerHTML = `
        <div style="position:relative; padding-bottom:56.25%; height:0; overflow:hidden; border-radius:8px;">
          <iframe src="https://www.youtube.com/embed/${ytMatch[1]}?autoplay=1" 
                  style="position:absolute; top:0; left:0; width:100%; height:100%; border:0;" 
                  allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" 
                  allowfullscreen></iframe>
        </div>
      `;
      playerWrap.style.display = 'block';
      return;
    }

    // 3. PeerTube embed
    if (url.includes('/w/') || url.includes('/videos/watch/')) {
      const embedUrl = url.replace('/videos/watch/', '/videos/embed/').replace('/w/', '/videos/embed/');
      playerWrap.innerHTML = `
        <div style="position:relative; padding-bottom:56.25%; height:0; overflow:hidden; border-radius:8px;">
          <iframe src="${escapeHtml(embedUrl)}?autoplay=1" 
                  style="position:absolute; top:0; left:0; width:100%; height:100%; border:0;" 
                  sandbox="allow-same-origin allow-scripts allow-popups" 
                  allowfullscreen></iframe>
        </div>
      `;
      playerWrap.style.display = 'block';
      return;
    }

    // Default: Open in new tab safely
    window.open(url, '_blank', 'noopener,noreferrer');
  };

  window.copyHSearchReport = function (sessionId) {
    const s = sessionCache.get(sessionId);
    if (!s) return;
    let md = `### 🔍 Net Search Results: "${s.query}"\n`;
    (s.results || []).forEach((r, i) => {
      md += `\n[${i + 1}] **${r.title}**\n- Link: ${r.url}\n- Engine: ${r.engine} (${r.network})\n`;
      if (r.snippet) md += `> ${r.snippet}\n`;
    });
    navigator.clipboard.writeText(md).then(() => {
      const btn = document.querySelector(`#hsearch-card-${sessionId} .hsearch-btn-copy`);
      if (btn) {
        const orig = btn.innerHTML;
        btn.innerHTML = `<i class="fas fa-check"></i> Copied!`;
        setTimeout(() => { btn.innerHTML = orig; }, 2000);
      }
    });
  };

  // ── Process Chat Messages ───────────────────────────────────────────────────
  function processChatMessages() {
    const bubbles = document.querySelectorAll('.message-content, .msg-text, .bubble-content, .assistant-message, .chat-message');
    bubbles.forEach(bubble => {
      let content = bubble.innerHTML;
      let changed = false;

      // Handle [[HSEARCH:id]]
      if (content.includes('[[HSEARCH:')) {
        content = content.replace(HSEARCH_REGEX, (match, sid) => {
          setTimeout(() => populateCard(sid), 50);
          return renderSearchCard(sid, false);
        });
        changed = true;
      }

      // Handle [[HMEDIA:id]]
      if (content.includes('[[HMEDIA:')) {
        content = content.replace(HMEDIA_REGEX, (match, sid) => {
          if (content.includes(`data-session-id="${sid}"`)) {
            return '';
          }
          setTimeout(() => populateCard(sid), 50);
          return renderSearchCard(sid, true);
        });
        changed = true;
      }

      if (changed) {
        bubble.innerHTML = content;
      }
    });
  }

  // ── Injected CSS Stylesheet ──────────────────────────────────────────────────
  const style = document.createElement('style');
  style.id = 'hsearch-chat-card-styles';
  style.textContent = `
    /* Hecos Net Search Rich Chat Card */
    .hsearch-chat-card {
      margin: 12px 0;
      background: var(--bg2, #0f172a);
      border: 1px solid rgba(var(--accent-rgb, 6, 182, 212), 0.28);
      border-radius: var(--radius, 12px);
      overflow: hidden;
      font-family: inherit;
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.35);
      transition: border-color 0.2s ease, box-shadow 0.2s ease;
    }
    .hsearch-chat-card:hover {
      border-color: rgba(var(--accent-rgb, 6, 182, 212), 0.45);
    }

    /* Header */
    .hsearch-card-header {
      padding: 10px 14px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      background: rgba(var(--accent-rgb, 6, 182, 212), 0.08);
      border-bottom: 1px solid rgba(255, 255, 255, 0.06);
    }
    .hsearch-card-title {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 13px;
      font-weight: 600;
      color: var(--accent, #38bdf8);
      min-width: 0;
    }
    .hsearch-title-text {
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      max-width: 220px;
    }
    .hsearch-icon {
      color: var(--accent, #06b6d4);
      font-size: 14px;
    }
    .hsearch-badge-live {
      font-size: 10px;
      padding: 2px 8px;
      border-radius: 12px; /* DATA PILL */
      background: rgba(var(--accent-rgb, 6, 182, 212), 0.18);
      color: var(--accent, #67e8f9);
      font-weight: 500;
      white-space: nowrap;
    }

    /* Action buttons in header */
    .hsearch-card-actions {
      display: flex;
      align-items: center;
      gap: 6px;
    }
    .hsearch-btn-toggle, .hsearch-btn-open, .hsearch-btn-copy, .hsearch-btn-more {
      padding: 5px 10px;
      border-radius: 6px; /* Rectangular with rounded corners */
      background: rgba(255, 255, 255, 0.06);
      border: 1px solid rgba(255, 255, 255, 0.12);
      color: var(--text, #cbd5e1);
      font-size: 11px;
      font-weight: 500;
      cursor: pointer;
      text-decoration: none;
      display: inline-flex;
      align-items: center;
      gap: 5px;
      transition: background 0.15s, color 0.15s, transform 0.1s;
    }
    .hsearch-btn-toggle:hover, .hsearch-btn-open:hover, .hsearch-btn-copy:hover, .hsearch-btn-more:hover {
      background: rgba(var(--accent-rgb, 6, 182, 212), 0.2);
      border-color: rgba(var(--accent-rgb, 6, 182, 212), 0.4);
      color: #fff;
    }

    /* ── Media Section ────────────────────────────────── */
    .hsearch-media-section {
      padding: 12px 14px;
      background: rgba(0, 0, 0, 0.2);
      border-bottom: 1px solid rgba(255, 255, 255, 0.05);
    }
    .hsearch-media-header {
      margin-bottom: 10px;
      font-size: 11px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      color: var(--muted, #94a3b8);
      display: flex;
      align-items: center;
      gap: 6px;
    }

    /* 1. Video Grid */
    .hsearch-video-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
      gap: 10px;
      margin-bottom: 10px;
    }
    .hsearch-video-card {
      background: rgba(255, 255, 255, 0.03);
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: 8px;
      overflow: hidden;
      display: flex;
      flex-direction: column;
    }
    .hsearch-video-thumb {
      position: relative;
      width: 100%;
      height: 105px;
      background: #000;
      cursor: pointer;
      overflow: hidden;
    }
    .hsearch-video-thumb img {
      width: 100%;
      height: 100%;
      object-fit: cover;
      transition: transform 0.2s ease;
    }
    .hsearch-video-thumb:hover img {
      transform: scale(1.05);
    }
    .hsearch-video-placeholder {
      width: 100%;
      height: 100%;
      display: flex;
      align-items: center;
      justify-content: center;
      color: #475569;
      font-size: 24px;
    }
    .hsearch-video-play-overlay {
      position: absolute;
      inset: 0;
      display: flex;
      align-items: center;
      justify-content: center;
      background: rgba(0, 0, 0, 0.35);
      color: #fff;
      font-size: 20px;
      opacity: 0.85;
      transition: opacity 0.2s, background 0.2s;
    }
    .hsearch-video-thumb:hover .hsearch-video-play-overlay {
      opacity: 1;
      background: rgba(var(--accent-rgb, 6, 182, 212), 0.4);
    }
    .hsearch-duration-pill {
      position: absolute;
      bottom: 5px;
      right: 5px;
      background: rgba(0, 0, 0, 0.8);
      color: #fff;
      font-size: 9px;
      padding: 1px 5px;
      border-radius: 4px;
      font-family: var(--font-mono, monospace);
    }
    .hsearch-engine-pill {
      position: absolute;
      top: 5px;
      left: 5px;
      background: rgba(0, 0, 0, 0.7);
      color: var(--accent, #38bdf8);
      font-size: 9px;
      padding: 1px 6px;
      border-radius: 10px; /* DATA PILL */
      text-transform: capitalize;
    }
    .hsearch-video-info {
      padding: 8px;
      display: flex;
      flex-direction: column;
      gap: 6px;
      flex: 1;
    }
    .hsearch-video-title {
      font-size: 11px;
      font-weight: 500;
      color: var(--text, #e2e8f0);
      text-decoration: none;
      line-height: 1.3;
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }
    .hsearch-video-title:hover {
      color: var(--accent, #38bdf8);
    }
    .hsearch-video-actions {
      display: flex;
      gap: 6px;
      margin-top: auto;
    }
    .hsearch-vbtn {
      padding: 3px 8px;
      border-radius: 5px;
      font-size: 10px;
      font-weight: 500;
      cursor: pointer;
      text-decoration: none;
      display: inline-flex;
      align-items: center;
      gap: 4px;
      border: 1px solid transparent;
    }
    .hsearch-vbtn-play {
      background: rgba(var(--accent-rgb, 6, 182, 212), 0.2);
      border-color: rgba(var(--accent-rgb, 6, 182, 212), 0.35);
      color: var(--accent, #38bdf8);
    }
    .hsearch-vbtn-play:hover {
      background: rgba(var(--accent-rgb, 6, 182, 212), 0.35);
    }
    .hsearch-vbtn-link {
      background: rgba(255, 255, 255, 0.05);
      border-color: rgba(255, 255, 255, 0.1);
      color: var(--muted, #94a3b8);
    }
    .hsearch-video-inline-player {
      padding: 8px;
      background: #000;
      border-top: 1px solid rgba(255, 255, 255, 0.08);
    }

    /* 2. Photo Wall */
    .hsearch-photo-wall {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(110px, 1fr));
      gap: 8px;
      margin-bottom: 10px;
    }
    .hsearch-img-wrap {
      position: relative;
      height: 90px;
      border-radius: 8px;
      overflow: hidden;
      background: #000;
      cursor: pointer;
      border: 1px solid rgba(255, 255, 255, 0.06);
    }
    .hsearch-img-wrap img {
      width: 100%;
      height: 100%;
      object-fit: cover;
      transition: transform 0.2s ease;
    }
    .hsearch-img-wrap:hover img {
      transform: scale(1.08);
    }
    .hsearch-img-overlay {
      position: absolute;
      inset: 0;
      background: linear-gradient(180deg, rgba(0,0,0,0) 40%, rgba(0,0,0,0.85) 100%);
      opacity: 0;
      transition: opacity 0.2s;
      display: flex;
      align-items: flex-end;
      justify-content: space-between;
      padding: 6px;
    }
    .hsearch-img-wrap:hover .hsearch-img-overlay {
      opacity: 1;
    }
    .hsearch-img-title {
      font-size: 9px;
      color: #fff;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      max-width: 75%;
    }
    .hsearch-img-btn {
      color: var(--accent, #38bdf8);
      font-size: 10px;
    }

    /* 3. Audio List */
    .hsearch-audio-list {
      display: flex;
      flex-direction: column;
      gap: 6px;
      margin-bottom: 10px;
    }
    .hsearch-audio-card {
      background: rgba(255, 255, 255, 0.04);
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: 8px;
      padding: 8px 10px;
      display: flex;
      flex-direction: column;
      gap: 6px;
    }
    .hsearch-audio-info {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 11px;
      color: var(--text, #e2e8f0);
    }
    .hsearch-audio-icon {
      color: var(--accent, #06b6d4);
    }
    .hsearch-audio-title {
      font-weight: 500;
      flex: 1;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .hsearch-audio-player {
      width: 100%;
      height: 28px;
    }

    /* 4. Files List */
    .hsearch-files-list {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
      gap: 8px;
      margin-bottom: 10px;
    }
    .hsearch-file-card {
      background: rgba(255, 255, 255, 0.04);
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: 8px;
      padding: 8px 10px;
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .hsearch-file-icon {
      font-size: 20px;
      color: var(--accent, #06b6d4);
    }
    .hsearch-file-details {
      display: flex;
      flex-direction: column;
      gap: 2px;
      min-width: 0;
      flex: 1;
    }
    .hsearch-file-name {
      font-size: 11px;
      font-weight: 500;
      color: var(--text, #e2e8f0);
      text-decoration: none;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .hsearch-file-name:hover {
      color: var(--accent, #38bdf8);
      text-decoration: underline;
    }
    .hsearch-file-meta {
      font-size: 10px;
      color: var(--muted, #94a3b8);
      display: flex;
      align-items: center;
      gap: 6px;
    }
    .hsearch-ext-badge {
      background: rgba(var(--accent-rgb, 6, 182, 212), 0.2);
      color: var(--accent, #38bdf8);
      padding: 1px 4px;
      border-radius: 4px;
      font-weight: 600;
      font-size: 8px;
    }
    .hsearch-file-btn {
      padding: 4px 8px;
      border-radius: 5px;
      font-size: 10px;
      background: rgba(255, 255, 255, 0.06);
      border: 1px solid rgba(255, 255, 255, 0.12);
      color: var(--text, #e2e8f0);
      text-decoration: none;
      display: inline-flex;
      align-items: center;
      gap: 4px;
      white-space: nowrap;
    }
    .hsearch-file-btn:hover {
      background: rgba(var(--accent-rgb, 6, 182, 212), 0.25);
      color: #fff;
    }

    /* Expander link */
    .hsearch-more-media {
      text-align: center;
      margin-top: 6px;
    }
    .hsearch-btn-more {
      width: 100%;
      justify-content: center;
    }

    /* ── Sources Accordion ────────────────────────────── */
    .hsearch-card-content {
      padding: 12px 14px;
      max-height: 260px;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 8px;
      background: rgba(0, 0, 0, 0.35);
      border-top: 1px solid rgba(255, 255, 255, 0.04);
    }
    .hsearch-item-row {
      display: flex;
      align-items: flex-start;
      gap: 8px;
      font-size: 12px;
      padding-bottom: 6px;
      border-bottom: 1px solid rgba(255, 255, 255, 0.03);
    }
    .hsearch-item-row:last-child {
      border-bottom: none;
      padding-bottom: 0;
    }
    .hsearch-num {
      color: var(--accent, #06b6d4);
      font-weight: bold;
      font-size: 11px;
      margin-top: 1px;
    }
    .hsearch-item-text {
      flex: 1;
      min-width: 0;
    }
    .hsearch-link {
      color: var(--accent, #7dd3fc);
      text-decoration: none;
      font-weight: 500;
      line-height: 1.3;
    }
    .hsearch-link:hover {
      text-decoration: underline;
    }
    .hsearch-snippet {
      font-size: 11px;
      color: var(--muted, #94a3b8);
      margin: 3px 0;
      line-height: 1.35;
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }
    .hsearch-sub {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 10px;
      color: var(--muted, #64748b);
      margin-top: 2px;
    }
    .hsearch-net {
      color: #c084fc;
    }
    .hsearch-url {
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      max-width: 250px;
    }

    /* Footer */
    .hsearch-card-footer {
      padding: 8px 14px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      background: rgba(0, 0, 0, 0.25);
      border-top: 1px solid rgba(255, 255, 255, 0.04);
      font-size: 10px;
    }
    .hsearch-footer-meta {
      color: var(--muted, #64748b);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      max-width: 60%;
    }

    /* Fallback Lightbox Modal */
    .hsearch-lightbox-modal {
      position: fixed;
      inset: 0;
      background: rgba(0, 0, 0, 0.9);
      display: none;
      align-items: center;
      justify-content: center;
      z-index: 10001;
      cursor: zoom-out;
    }
    .hsearch-lightbox-modal img {
      max-width: 90vw;
      max-height: 90vh;
      border-radius: 8px;
      object-fit: contain;
      box-shadow: 0 0 40px rgba(0,0,0,0.8);
      cursor: default;
    }
    .hsearch-lightbox-close {
      position: absolute;
      top: 20px;
      right: 25px;
      font-size: 28px;
      color: #fff;
      cursor: pointer;
      opacity: 0.8;
      transition: opacity 0.15s;
    }
    .hsearch-lightbox-close:hover {
      opacity: 1;
    }
  `;
  document.head.appendChild(style);

  // ── Auto Initialization & DOM Observer ──────────────────────────────────────
  document.addEventListener('DOMContentLoaded', processChatMessages);
  const observer = new MutationObserver(processChatMessages);
  observer.observe(document.body, { childList: true, subtree: true });
})();
