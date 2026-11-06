/**
 * chat_media_zoom.js
 * Controls full-chat expansion / zoom for document previews (PDF, HTML) and VLC launcher.
 */

window.openInVlc = function(filePath) {
  if (window.HecosUI && window.HecosUI.showToast) {
    window.HecosUI.showToast("Launching VLC...", "info");
  }

  fetch('/api/open_in_vlc', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path: decodeURIComponent(filePath) })
  })
  .then(res => res.json())
  .then(data => {
    if (!data.ok) {
      console.error("[VLC] Error:", data.error);
      if (window.HecosUI && window.HecosUI.showToast) {
        window.HecosUI.showToast("Unable to open video with VLC.", "error");
      } else {
        alert("Error launching video: " + data.error);
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
      window.HecosUI.showToast("Network error while launching video.", "error");
    }
  });
};

// ── Preview Zoom / Full-Chat Expansion ──────────────────────────────────────
window.togglePdfPreviewZoom = function(previewId) {
  const el = document.getElementById(previewId);
  if (!el) return;

  const isExpanded = el.classList.toggle('expanded');

  // Find all zoom buttons targeting this previewId
  const zoomBtns = document.querySelectorAll(`[data-preview-id="${previewId}"], .chat-file-zoom-btn[onclick*="${previewId}"]`);

  // Overrides on parent bubble to prevent backdrop-filter stacking context traps
  const msgBubble = el.closest('.msg-bubble');
  const msgEl = el.closest('.msg');

  if (isExpanded) {
    if (msgBubble) msgBubble.classList.add('has-expanded-preview');
    if (msgEl) msgEl.classList.add('has-expanded-preview');
    document.body.classList.add('preview-zoomed');

    zoomBtns.forEach(btn => {
      const icon = btn.querySelector('i');
      const label = btn.querySelector('.zoom-label') || btn;
      if (icon) icon.className = 'fas fa-compress-arrows-alt';
      if (label && label !== btn) label.textContent = 'Collapse';
      btn.setAttribute('title', 'Restore normal size (Esc)');
    });

    const bar = el.querySelector('.chat-pdf-preview-bar, .chat-html-preview-bar');
    if (bar && !bar.querySelector('.chat-preview-close-btn')) {
      const closeBtn = document.createElement('button');
      closeBtn.className = 'chat-preview-close-btn';
      closeBtn.innerHTML = '<i class="fas fa-times"></i> <span style="font-size:0.85em;font-weight:600;">Close</span>';
      closeBtn.title = 'Close expanded preview (Esc)';
      closeBtn.style.cssText = 'background:rgba(239,68,68,0.2);border:1px solid rgba(239,68,68,0.4);color:#fca5a5;border-radius:4px;padding:3px 10px;cursor:pointer;font-size:0.85em;display:inline-flex;align-items:center;gap:5px;';
      closeBtn.onclick = function(e) {
        e.stopPropagation();
        window.togglePdfPreviewZoom(previewId);
      };
      bar.appendChild(closeBtn);
    }
  } else {
    if (msgBubble) msgBubble.classList.remove('has-expanded-preview');
    if (msgEl) msgEl.classList.remove('has-expanded-preview');
    document.body.classList.remove('preview-zoomed');

    zoomBtns.forEach(btn => {
      const icon = btn.querySelector('i');
      const label = btn.querySelector('.zoom-label') || btn;
      if (icon) icon.className = 'fas fa-expand-arrows-alt';
      if (label && label !== btn) label.textContent = 'Zoom';
      btn.setAttribute('title', 'Expand preview in chat');
    });

    const closeBtn = el.querySelector('.chat-preview-close-btn');
    if (closeBtn) closeBtn.remove();
  }
};

// Global Esc listener to exit preview zoom
if (!window._pdfZoomEscBound) {
  window._pdfZoomEscBound = true;
  document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
      const expanded = document.querySelector('.chat-pdf-preview.expanded, .chat-html-preview.expanded');
      if (expanded) {
        window.togglePdfPreviewZoom(expanded.id);
      }
    }
  });
}

