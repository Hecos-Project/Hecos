// ─── Quick Links & Bookmarks ─────────────────────────────────────────────────

async function loadQuickLinks() {
  const body = document.getElementById("quick-links-body");
  try {
    const res  = await fetch("/drive/api/quick_links");
    const data = await res.json();

    if (!data.ok || !data.groups || !data.groups.length) {
      const noLinksMsg = window.t ? window.t('webui_drive_no_links') : 'No links available.';
      body.innerHTML = `<div class="sb-empty">${noLinksMsg}</div>`;
      return;
    }

    let html = "";
    
    // -- My Bookmarks (from localStorage) --
    const bookmarks = getBookmarks();
    if (bookmarks.length > 0) {
      html += `<div class="ql-group">
        <div class="ql-group-title" style="color:var(--accent);">⭐ Preferiti / Bookmarks</div>
        ${bookmarks.map(item => `
          <div class="ql-item" onclick="openQuickLink('${esc(item.path)}', false)">
            <span class="ql-icon" style="color:var(--accent);">📌</span>
            <span class="ql-name" title="${esc(item.path)}">${esc(item.name)}</span>
            <span class="ql-edit" style="color:#e74c3c; cursor:pointer; margin-left:auto; padding:0 6px;" title="Rimuovi" onclick="event.stopPropagation(); removeBookmark('${esc(item.path)}')"><i class="fas fa-times"></i></span>
          </div>
        `).join("")}
      </div>`;
    }

    data.groups.forEach(grp => {
      html += `<div class="ql-group">
        <div class="ql-group-title">⭐ ${esc(grp.title)}</div>
        ${grp.items.map(item => `
          <div class="ql-item" onclick="openQuickLink('${esc(item.path)}', ${item.path.includes('.')})">
            <span class="ql-icon">${esc(grp.icon || '📄')}</span>
            <span class="ql-name" title="${esc(item.name)}">${esc(item.name)}</span>
            ${item.path.includes('.') && isEditable(item.name) 
              ? `<span class="ql-edit" title="Modifica" onclick="event.stopPropagation(); openEditor('${esc(item.path)}')">✏️</span>` 
              : ''}
          </div>
        `).join("")}
      </div>`;
    });
    body.innerHTML = html;
  } catch (e) {
    console.error("[Drive] Quick Links error:", e);
    body.innerHTML = `<div class="sb-empty" style="color:var(--danger)">Errore caricamento.</div>`;
  }
}

function openQuickLink(path, isFile) {
  if (isFile) {
    if (isEditable(path)) {
      openEditor(path);
    } else {
      showMsg("⚠️ Estensione non supportata dall'editor.", "err");
    }
  } else {
    navigateTo(path);
  }
}

function getBookmarks() {
  try { return JSON.parse(localStorage.getItem('hecos_drive_bookmarks')) || []; }
  catch(e) { return []; }
}

function saveBookmarks(b) {
  localStorage.setItem('hecos_drive_bookmarks', JSON.stringify(b));
  loadQuickLinks(); 
}

function updateBookmarkIcon() {
  const btn = document.getElementById("btn-bookmark");
  if (!btn) return;
  if (!currentAbsPath) { btn.style.visibility = 'hidden'; return; }
  btn.style.visibility = 'visible';
  const bookmarks = getBookmarks();
  const isBookmarked = bookmarks.some(b => b.path === currentAbsPath);
  btn.innerHTML = isBookmarked ? '<i class="fas fa-star" style="color:#f1c40f"></i>' : '<i class="far fa-star"></i>';
}

function toggleBookmark() {
  if (!currentAbsPath) return;
  const bookmarks = getBookmarks();
  const idx = bookmarks.findIndex(b => b.path === currentAbsPath);
  if (idx >= 0) {
    bookmarks.splice(idx, 1);
  } else {
    const parts = currentAbsPath.replace(/\\/g, '/').split('/').filter(Boolean);
    const name = parts.length > 0 ? parts[parts.length - 1] : "Root";
    bookmarks.push({ name: name, path: currentAbsPath });
  }
  saveBookmarks(bookmarks);
  updateBookmarkIcon();
}

function removeBookmark(path) {
  const bookmarks = getBookmarks();
  const newB = bookmarks.filter(b => b.path !== path);
  saveBookmarks(newB);
  updateBookmarkIcon();
}
