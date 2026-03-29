/**
 * MODULE: chat_input_toolbar.js
 * PURPOSE: Logic for input toolbar (file upload, paste, drag-and-drop)
 * Loaded by chat.html.
 */

// ── Pending attachments ─────────────────────────────────────────
window.pendingAttachments = [];

// ── File Upload ─────────────────────────────────────────────────
function setupFileUploads() {
  const docInput = document.getElementById('file-upload-doc');
  const imgInput = document.getElementById('file-upload-img');
  if (docInput) docInput.addEventListener('change', (e) => handleFiles(e.target.files, 'doc'));
  if (imgInput) imgInput.addEventListener('change', (e) => handleFiles(e.target.files, 'img'));
}

function getFileType(file) {
  const ext = file.name.split('.').pop().toLowerCase();
  return ['png','jpg','jpeg','webp','gif'].includes(ext) ? 'img' : 'doc';
}

function handleFiles(files, type) {
  const arr = Array.from(files);
  if (!arr.length) return;
  arr.forEach(file => {
    const t = type || getFileType(file);
    const entry = { file, type: t, name: file.name, size: file.size };
    window.pendingAttachments.push(entry);
    addUploadChip(entry);
  });
  // Reset file inputs
  const d = document.getElementById('file-upload-doc');
  const i = document.getElementById('file-upload-img');
  if (d) d.value = '';
  if (i) i.value = '';
  if (window.showToast) showToast(`📎 ${arr.length} file allegato/i`);
}

function addUploadChip(entry) {
  const preview = document.getElementById('upload-preview');
  if (!preview) return;
  const chip = document.createElement('div');
  chip.className = 'upload-chip';
  chip.dataset.name = entry.name;
  const icon = entry.type === 'img' ? '🖼' : '📎';
  const sizeKB = Math.round(entry.size / 1024);
  chip.innerHTML = `
    <span>${icon}</span>
    <span title="${entry.name}">${entry.name}</span>
    <span style="color:var(--muted);font-size:10px;">(${sizeKB}KB)</span>
    <span class="upload-chip-remove" title="Rimuovi" onclick="removeAttachment('${CSS.escape(entry.name)}', this.parentElement)">✕</span>
  `;
  preview.appendChild(chip);
}

window.removeAttachment = function(name, chipEl) {
  window.pendingAttachments = window.pendingAttachments.filter(a => a.name !== name);
  if (chipEl) chipEl.remove();
};

// ── Upload & extract context before sending ─────────────────────
async function uploadAndGetContext() {
  if (!window.pendingAttachments.length) return { context: '', images: [] };
  const formData = new FormData();
  window.pendingAttachments.forEach(a => formData.append('files', a.file));
  try {
    const r = await fetch('/api/upload', { method: 'POST', body: formData });
    const data = await r.json();
    if (data.ok) {
      window.pendingAttachments = [];
      document.getElementById('upload-preview').innerHTML = '';
      const ctx = data.context ? '\n\n[CONTESTO ALLEGATO]:\n' + data.context : '';
      return { context: ctx, images: data.images || [] };
    }
  } catch (e) {
    if (window.showToast) showToast('❌ Upload fallito: ' + e.message);
  }
  return { context: '', images: [] };
}
window.getAttachmentContext = uploadAndGetContext;

// ── Paste Modal ─────────────────────────────────────────────────
window.openPasteModal = function() {
  const modal = document.getElementById('paste-modal');
  if (!modal) return;
  modal.classList.add('open');
  // Reset position (remove absolute positioning styles to let flexbox center it)
  const box = document.getElementById('paste-modal-box');
  if (box) { box.style.position = ''; box.style.top = ''; box.style.left = ''; box.style.margin = ''; }
  setTimeout(() => {
    const ta = document.getElementById('paste-modal-textarea');
    if (ta) ta.focus();
  }, 80);
};

window.closePasteModal = function() {
  const modal = document.getElementById('paste-modal');
  if (modal) modal.classList.remove('open');
};

window.confirmPaste = function() {
  const ta = document.getElementById('paste-modal-textarea');
  const userInput = document.getElementById('user-input');
  if (!ta || !userInput) return;
  const text = ta.value.trim();
  if (!text) return;
  const current = userInput.value.trim();
  userInput.value = current ? current + '\n\n' + text : text;
  if (typeof autoResize === 'function') autoResize(userInput);
  ta.value = '';
  closePasteModal();
  userInput.focus();
  if (window.showToast) showToast('✅ Testo incollato nel messaggio');
};

// ESC to close paste modal
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    const modal = document.getElementById('paste-modal');
    if (modal && modal.classList.contains('open')) {
      closePasteModal();
      e.stopPropagation();
    }
  }
});

// ── Modal Dragging ──────────────────────────────────────────────
function setupModalDrag() {
  const handle = document.getElementById('paste-modal-drag-handle');
  const box    = document.getElementById('paste-modal-box');
  if (!handle || !box) return;

  let isDragging = false, startX = 0, startY = 0, origLeft = 0, origTop = 0;

  handle.addEventListener('mousedown', (e) => {
    if (e.target.classList.contains('paste-modal-close') || e.target.tagName === 'BUTTON') return;
    isDragging = true;
    
    // Switch from flex centering to absolute positioning based on current rect
    const rect = box.getBoundingClientRect();
    box.style.position = 'fixed';
    box.style.margin = '0';
    box.style.left = rect.left + 'px';
    box.style.top  = rect.top  + 'px';
    
    origLeft = rect.left;
    origTop  = rect.top;
    startX   = e.clientX;
    startY   = e.clientY;
    e.preventDefault(); // Stop text selection while dragging
  });

  document.addEventListener('mousemove', (e) => {
    if (!isDragging) return;
    const dx = e.clientX - startX;
    const dy = e.clientY - startY;
    // Bound the box to the screen limits
    const newLeft = Math.max(0, Math.min(window.innerWidth - box.offsetWidth, origLeft + dx));
    const newTop = Math.max(0, Math.min(window.innerHeight - box.offsetHeight, origTop + dy));
    box.style.left = newLeft + 'px';
    box.style.top  = newTop + 'px';
  });

  document.addEventListener('mouseup', () => { isDragging = false; });
}

// ── Global Drag & Drop ──────────────────────────────────────────
function setupDragAndDrop() {
  const overlay = document.getElementById('drop-overlay');
  if (!overlay) return;

  let dragCounter = 0;

  document.addEventListener('dragenter', (e) => {
    if (e.dataTransfer && e.dataTransfer.types.includes('Files')) {
      dragCounter++;
      overlay.classList.add('active');
    }
  });

  document.addEventListener('dragleave', (e) => {
    dragCounter--;
    if (dragCounter <= 0) {
      dragCounter = 0;
      overlay.classList.remove('active');
    }
  });

  document.addEventListener('dragover', (e) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'copy';
  });

  document.addEventListener('drop', (e) => {
    e.preventDefault();
    dragCounter = 0;
    overlay.classList.remove('active');
    const files = e.dataTransfer.files;
    if (files && files.length > 0) {
      handleFiles(files, null);
    }
  });
}

// ── Init ────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  // CRITICAL: Move overlay elements to <body> root so they are NOT
  // trapped inside #input-bar's stacking context, which breaks fixed positioning.
  ['paste-modal', 'drop-overlay', 'chat-toast'].forEach(id => {
    const el = document.getElementById(id);
    if (el && el.parentElement !== document.body) {
      document.body.appendChild(el);
    }
  });

  setupFileUploads();
  setupModalDrag();
  setupDragAndDrop();
});
