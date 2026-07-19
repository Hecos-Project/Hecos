// ─── Drive UI — Rendering & Events ────────────────────────────────────────────
// All interaction is handled via data-* attributes + event delegation.
// This avoids HTML-inline JS string escaping issues entirely.

const IMG_EXTS   = new Set(['jpg','jpeg','png','gif','webp','bmp','svg']);
const VIDEO_EXTS = new Set(['mp4','webm','mov','avi','mkv']);
const MEDIA_EXTS = new Set([...IMG_EXTS, ...VIDEO_EXTS]);

// ── View Mode ────────────────────────────────────────────────────────────────
let currentDriveViewMode = localStorage.getItem('hecos_drive_view') || 'list';

function setViewMode(mode) {
  currentDriveViewMode = mode;
  localStorage.setItem('hecos_drive_view', mode);
  document.querySelectorAll('#view-mode-toggles .btn').forEach(b => b.classList.remove('active'));
  const btn = document.getElementById('vm-' + mode);
  if (btn) btn.classList.add('active');
  renderTable();
}

document.addEventListener('DOMContentLoaded', () => {
  // Set active button state on first load
  const btn = document.getElementById('vm-' + currentDriveViewMode);
  if (btn) btn.classList.add('active');
  // Install delegated event listeners on the main container
  _installDriveEvents();
  // Build the built-in slideshow modal
  _buildDriveSlideshow();
});

// ── Helpers ──────────────────────────────────────────────────────────────────

function renderBreadcrumb(crumbs, rootLabel) {
  const bar = document.getElementById('path-bar');
  const rootDisplay = rootLabel || (window.t ? '🏠 ' + window.t('webui_drive_root_label') : '🏠 Drive');
  let html = `<span class="crumb" data-nav-path="" title="${rootDisplay}">${rootDisplay}</span>`;
  crumbs.forEach((c, i) => {
    html += `<span class="sep">/</span>`;
    html += (i === crumbs.length - 1)
      ? `<span class="crumb current">${esc(c.name)}</span>`
      : `<span class="crumb" data-nav-path="${esc(c.path)}" title="${esc(c.abs || c.path)}">${esc(c.name)}</span>`;
  });
  bar.innerHTML = html;
}

function updateLocationBar(path, entries, absPath, rootLabel) {
  const dispPath = absPath || (path ? '/' + path.replace(/\\/g, '/') : rootLabel || '/');
  document.getElementById('loc-path').textContent = dispPath;
  const dirs  = entries.filter(e => e.is_dir).length;
  const files = entries.filter(e => !e.is_dir).length;
  document.getElementById('loc-count').textContent =
    window.t ? window.t('webui_drive_dirs_files', {dirs, files}) : `${dirs} folders · ${files} files`;
  const dropzoneTpl = window.t ? window.t('webui_drive_upload_to') : 'Drop files here to upload to:';
  document.getElementById('dropzone').textContent = `⬆️  ${dropzoneTpl}  ${dispPath}`;
  if (typeof updateBookmarkIcon === 'function') updateBookmarkIcon();
}

const EDITABLE_EXTS = new Set([
  'py','js','ts','json','yaml','yml','toml','html','htm','css','scss',
  'sh','bat','ps1','md','txt','ini','cfg','conf','log','xml','env'
]);
function isEditable(name) { return EDITABLE_EXTS.has(name.split('.').pop().toLowerCase()); }
function openEditor(path) { window.open(`/drive/editor?path=${encodeURIComponent(path)}`, '_blank'); }

function sortBy(key) {
  sortAsc = (sortKey === key) ? !sortAsc : true;
  sortKey = key;
  renderTable();
}

// ── Render ───────────────────────────────────────────────────────────────────

function renderTable() {
  const entries = [...allEntries].sort((a, b) => {
    if (a.is_dir !== b.is_dir) return a.is_dir ? -1 : 1;
    let va = (a[sortKey] ?? ''), vb = (b[sortKey] ?? '');
    if (typeof va === 'string') va = va.toLowerCase();
    if (typeof vb === 'string') vb = vb.toLowerCase();
    return (va < vb ? -1 : va > vb ? 1 : 0) * (sortAsc ? 1 : -1);
  });

  if (!entries.length) {
    const msg = window.t ? window.t('webui_drive_empty') : 'Folder empty';
    document.getElementById('file-scroll').innerHTML =
      `<table><tbody><tr class="empty-row"><td colspan="4">📂 ${msg}</td></tr></tbody></table>`;
    updateStatusBar();
    return;
  }

  if (currentDriveViewMode !== 'list') {
    _renderGrid(entries);
  } else {
    _renderList(entries);
  }

  updateStatusBar();
}

function _fileExt(name) { return name.split('.').pop().toLowerCase(); }

function _renderGrid(entries) {
  const isLg = currentDriveViewMode === 'grid-lg';
  const gridClass = isLg ? 'drive-grid-lg' : 'drive-grid-sm';

  const html = '<div class="' + gridClass + '">' + entries.map(e => {
    const ext = _fileExt(e.name);
    let preview = '';
    if (e.is_dir) {
      preview = '<div class="grid-icon">📁</div>';
    } else if (IMG_EXTS.has(ext)) {
      preview = `<img src="/drive/api/view?path=${encodeURIComponent(e.path)}" loading="lazy" style="width:100%;height:100%;object-fit:cover;" onerror="this.parentElement.innerHTML='<div class=grid-icon>${fileIcon(e.name)}</div>'" />`;
    } else if (VIDEO_EXTS.has(ext)) {
      preview = `<video src="/drive/api/view?path=${encodeURIComponent(e.path)}" preload="none" muted style="width:100%;height:100%;object-fit:cover;"></video><div class="play-overlay">▶</div>`;
    } else {
      preview = `<div class="grid-icon">${fileIcon(e.name)}</div>`;
    }

    const isMedia = MEDIA_EXTS.has(ext);
    const type = e.is_dir ? 'dir' : (isMedia ? 'media' : 'file');

    return `<div class="grid-item"
        data-drive-action="${type}"
        data-path="${esc(e.path)}"
        data-name="${esc(e.name)}"
        title="${esc(e.name)}\n${e.is_dir ? '' : formatSize(e.size)}">
      <div class="grid-thumb">${preview}</div>
      <div class="grid-label">${esc(e.name)}</div>
      <div class="grid-actions">
        ${e.is_dir ? `<button class="drive-btn-open" data-path="${esc(e.path)}" title="${window.t ? window.t('webui_drive_root_hint') : 'Open'}">📂</button>` : ''}
        ${!e.is_dir ? `<button class="drive-btn-dl" data-path="${esc(e.path)}" data-name="${esc(e.name)}" title="Download">⬇️</button>` : ''}
        ${!e.is_dir && isEditable(e.name) ? `<button class="drive-btn-edit" data-path="${esc(e.path)}" title="${window.t ? window.t('webui_drive_edit') : 'Edit'}" style="color:var(--accent)">✏️</button>` : ''}
        <button class="drive-btn-del" data-path="${esc(e.path)}" data-name="${esc(e.name)}" title="${window.t ? window.t('webui_conf_logs_delete') : 'Delete'}">🗑️</button>
      </div>
    </div>`;
  }).join('') + '</div>';

  document.getElementById('file-scroll').innerHTML = html;
}

function _renderList(entries) {
  const colName = window.t ? window.t('webui_chat_name') : 'Name';
  const colSize = (window.t && window.t('webui_sysnet_proxy_port') === 'Porta') ? 'Dimensione' : 'Size';
  const colMod  = (window.t && window.t('webui_sysnet_proxy_port') === 'Porta') ? 'Modificato' : 'Modified';
  const colAct  = window.t ? window.t('webui_conf_logs_actions') : 'Actions';

  let html = `<table><thead><tr>
    <th onclick="sortBy('name')">${colName} ↕</th>
    <th onclick="sortBy('size')">${colSize} ↕</th>
    <th onclick="sortBy('modified')">${colMod} ↕</th>
    <th>${colAct}</th>
  </tr></thead><tbody>`;

  html += entries.map(e => {
    const ext = _fileExt(e.name);
    const isMedia = MEDIA_EXTS.has(ext);
    const type = e.is_dir ? 'dir' : (isMedia ? 'media' : 'file');

    return `<tr>
      <td class="name-cell" style="cursor:pointer;"
          data-drive-action="${type}"
          data-path="${esc(e.path)}"
          data-name="${esc(e.name)}">
        <span class="icon">${e.is_dir ? '📁' : fileIcon(e.name)}</span>
        <span class="fname" title="${esc(e.name)}">${esc(e.name)}</span>
        ${e.is_dir ? '<span style="font-size:10px;color:var(--muted);margin-left:6px;">▶</span>' : ''}
      </td>
      <td class="size-cell">${e.is_dir ? '—' : formatSize(e.size)}</td>
      <td class="date-cell">${e.modified ? new Date(e.modified * 1000).toLocaleString() : '—'}</td>
      <td class="actions-cell">
        ${e.is_dir
          ? `<button class="drive-btn-open" data-path="${esc(e.path)}" title="Open">📂</button>`
          : `<button class="drive-btn-dl" data-path="${esc(e.path)}" data-name="${esc(e.name)}" title="Download">⬇️</button>`}
        ${!e.is_dir && isEditable(e.name)
          ? `<button class="drive-btn-edit" data-path="${esc(e.path)}" title="${window.t ? window.t('webui_drive_edit') : 'Edit'}" style="color:var(--accent)">✏️</button>`
          : ''}
        <button class="drive-btn-del" data-path="${esc(e.path)}" data-name="${esc(e.name)}" title="Delete">🗑️</button>
      </td>
    </tr>`;
  }).join('');

  html += '</tbody></table>';
  document.getElementById('file-scroll').innerHTML = html;
}

function setTbody(html) {
  document.getElementById('file-tbody').innerHTML = html;
}

function updateStatusBar() {
  const dirs  = allEntries.filter(e => e.is_dir).length;
  const files = allEntries.filter(e => !e.is_dir).length;
  document.getElementById('sb-info').textContent =
    window.t ? window.t('webui_drive_dirs_files', {dirs, files}) : `${dirs} folders · ${files} files`;
}

// ── Event Delegation ─────────────────────────────────────────────────────────
// One listener on file-scroll handles ALL clicks/dblclicks via data-* attributes.
// Avoids ALL inline-JS escaping issues.

let _lastClickTime = 0;
let _lastClickPath = '';

function _installDriveEvents() {
  const scroll = document.getElementById('file-scroll');
  if (!scroll) return;

  // Use 'click' with manual double-click detection (more reliable than 'dblclick' in innerHTML)
  scroll.addEventListener('click', e => {
    // Action buttons (download, edit, delete, open-folder) — stop propagation
    const btnOpen = e.target.closest('.drive-btn-open');
    if (btnOpen) { navigateTo(btnOpen.dataset.path); return; }

    const btnDl = e.target.closest('.drive-btn-dl');
    if (btnDl) { downloadFile(btnDl.dataset.path); return; }

    const btnEdit = e.target.closest('.drive-btn-edit');
    if (btnEdit) { openEditor(btnEdit.dataset.path); return; }

    const btnDel = e.target.closest('.drive-btn-del');
    if (btnDel) { deleteItem(btnDel.dataset.path, btnDel.dataset.name); return; }

    // Item click — manual dblclick detection (300ms window)
    const item = e.target.closest('[data-drive-action]');
    if (!item) return;

    const now = Date.now();
    const path = item.dataset.path;
    const action = item.dataset.driveAction;

    if (now - _lastClickTime < 300 && _lastClickPath === path) {
      // DOUBLE CLICK
      _lastClickTime = 0;
      _lastClickPath = '';
      if (action === 'dir') {
        navigateTo(path);
      } else if (action === 'media') {
        _driveOpenSlideshow(path);
      } else {
        downloadFile(path);
      }
    } else {
      // SINGLE CLICK — just record for potential double-click
      _lastClickTime = now;
      _lastClickPath = path;
    }
  });

  // Also handle breadcrumb nav clicks via delegation on path-bar
  const pathBar = document.getElementById('path-bar');
  if (pathBar) {
    pathBar.addEventListener('click', e => {
      const crumb = e.target.closest('[data-nav-path]');
      if (crumb) navigateTo(crumb.dataset.navPath);
    });
  }
}

// ── Built-in Drive Slideshow ─────────────────────────────────────────────────
// Lightweight viewer: keyboard arrows, filmstrip, download button, ESC to close.

function _buildDriveSlideshow() {
  if (document.getElementById('drive-slideshow')) return;

  const style = document.createElement('style');
  style.textContent = `
    #drive-slideshow {
      display: none; position: fixed; inset: 0; z-index: 10000;
      background: rgba(0,0,0,0.93);
      flex-direction: column; align-items: center; justify-content: center;
      animation: dss-fadein .2s ease;
    }
    #drive-slideshow.open { display: flex; }
    @keyframes dss-fadein { from{opacity:0} to{opacity:1} }

    #dss-main {
      position: relative; display: flex; align-items: center; justify-content: center;
      width: 100%; flex: 1; min-height: 0;
    }
    #dss-img {
      max-width: 90vw; max-height: 72vh; border-radius: 10px;
      object-fit: contain; box-shadow: 0 8px 60px #000c;
      transition: opacity .15s;
    }
    #dss-vid {
      max-width: 90vw; max-height: 72vh; border-radius: 10px;
      box-shadow: 0 8px 60px #000c; outline: none;
    }
    #dss-prev, #dss-next {
      position: absolute; top: 50%; transform: translateY(-50%);
      background: rgba(255,255,255,0.07); border: 1px solid rgba(255,255,255,0.15);
      color: #fff; font-size: 24px; padding: 10px 18px; border-radius: 10px;
      cursor: pointer; transition: background .2s; backdrop-filter: blur(4px); user-select: none;
    }
    #dss-prev:hover, #dss-next:hover { background: rgba(255,255,255,0.18); }
    #dss-prev { left: 18px; }
    #dss-next { right: 18px; }
    #dss-close {
      position: absolute; top: 14px; right: 18px;
      background: rgba(255,255,255,0.07); border: 1px solid rgba(255,255,255,0.15);
      color: #fff; font-size: 18px; padding: 5px 13px; border-radius: 8px; cursor: pointer;
    }
    #dss-close:hover { background: rgba(255,60,60,0.35); }
    #dss-counter {
      position: absolute; top: 14px; left: 50%; transform: translateX(-50%);
      color: rgba(255,255,255,0.7); font-size: 13px;
      background: rgba(0,0,0,0.4); padding: 4px 14px; border-radius: 20px;
    }
    #dss-name {
      color: rgba(255,255,255,0.55); font-size: 12px; margin-top: 8px;
      max-width: 80vw; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
    }
    #dss-strip {
      display: flex; gap: 8px; padding: 10px 16px; overflow-x: auto;
      max-width: 92vw; margin-top: 4px;
    }
    #dss-strip img {
      width: 56px; height: 56px; border-radius: 6px; object-fit: cover;
      cursor: pointer; opacity: .45; border: 2px solid transparent;
      transition: opacity .15s, border-color .15s; flex-shrink: 0;
    }
    #dss-strip img.active { opacity: 1; border-color: #fff; }
    #dss-strip img:hover { opacity: .8; }
    #dss-actions { display: flex; gap: 10px; margin-top: 6px; margin-bottom: 8px; }
    .dss-act-btn {
      background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.15);
      color: #fff; padding: 6px 16px; border-radius: 8px; cursor: pointer;
      font-size: 12px; transition: background .2s;
    }
    .dss-act-btn:hover { background: rgba(255,255,255,0.2); }
  `;
  document.head.appendChild(style);

  const modal = document.createElement('div');
  modal.id = 'drive-slideshow';
  modal.innerHTML = `
    <div id="dss-main">
      <button id="dss-close">✕</button>
      <div id="dss-counter"></div>
      <button id="dss-prev">‹</button>
      <img id="dss-img" src="" alt="" />
      <video id="dss-vid" controls autoplay style="display:none;"></video>
      <button id="dss-next">›</button>
    </div>
    <div id="dss-name"></div>
    <div id="dss-actions">
      <button class="dss-act-btn" id="dss-dl">⬇ Download</button>
    </div>
    <div id="dss-strip"></div>
  `;
  document.body.appendChild(modal);

  let _items = [], _idx = 0;

  function _dssShow(index) {
    if (!_items.length) return;
    _idx = (index + _items.length) % _items.length;
    const item = _items[_idx];
    const img = document.getElementById('dss-img');
    const vid = document.getElementById('dss-vid');
    const isVid = VIDEO_EXTS.has(_fileExt(item.name));
    if (isVid) {
      img.style.display = 'none'; img.src = '';
      vid.style.display = ''; vid.src = item.url; vid.play().catch(() => {});
    } else {
      vid.style.display = 'none'; vid.pause(); vid.src = '';
      img.style.display = ''; img.style.opacity = '0';
      img.src = item.url;
      img.onload = () => { img.style.opacity = '1'; };
    }
    document.getElementById('dss-name').textContent = item.name;
    document.getElementById('dss-counter').textContent = `${_idx + 1} / ${_items.length}`;
    document.querySelectorAll('#dss-strip img').forEach((t, i) => {
      t.classList.toggle('active', i === _idx);
      if (i === _idx) t.scrollIntoView({ behavior: 'smooth', inline: 'nearest', block: 'nearest' });
    });
  }

  window._driveOpenSlideshow = function(startPath) {
    const mediaEntries = allEntries.filter(e => !e.is_dir && MEDIA_EXTS.has(_fileExt(e.name)));
    if (!mediaEntries.length) return;
    _items = mediaEntries.map(e => ({
      name: e.name,
      path: e.path,
      url: `/drive/api/view?path=${encodeURIComponent(e.path)}`
    }));
    const strip = document.getElementById('dss-strip');
    strip.innerHTML = '';
    _items.forEach((item, i) => {
      const th = document.createElement('img');
      th.src = item.url;
      th.title = item.name;
      th.onerror = () => { th.style.display = 'none'; };
      th.onclick = () => _dssShow(i);
      strip.appendChild(th);
    });
    const startIdx = _items.findIndex(it => it.path === startPath);
    _dssShow(startIdx >= 0 ? startIdx : 0);
    modal.classList.add('open');
  };

  document.getElementById('dss-close').onclick = () => {
    modal.classList.remove('open');
    document.getElementById('dss-vid').pause();
  };
  document.getElementById('dss-prev').onclick = () => _dssShow(_idx - 1);
  document.getElementById('dss-next').onclick = () => _dssShow(_idx + 1);
  modal.addEventListener('click', e => {
    if (e.target === modal) { modal.classList.remove('open'); document.getElementById('dss-vid').pause(); }
  });
  document.getElementById('dss-dl').onclick = () => {
    if (!_items[_idx]) return;
    downloadFile(_items[_idx].path);
  };
  document.addEventListener('keydown', e => {
    if (!modal.classList.contains('open')) return;
    if (e.key === 'ArrowLeft')  _dssShow(_idx - 1);
    if (e.key === 'ArrowRight') _dssShow(_idx + 1);
    if (e.key === 'Escape') { modal.classList.remove('open'); document.getElementById('dss-vid').pause(); }
  });
}

// ── Tree ─────────────────────────────────────────────────────────────────────

function renderTree() {
  const root = document.getElementById('tree-root');
  let treeBase = '';
  if (Object.keys(treeData).length > 0) {
    treeBase = Object.keys(treeData).reduce((a, b) => a.length <= b.length ? a : b);
  }
  root.innerHTML = buildTreeHTML(treeBase, 0);
  const el = document.getElementById('tn-' + pathId(currentPath));
  if (el) { el.classList.add('active'); el.scrollIntoView({ block: 'nearest' }); }
}

function buildTreeHTML(path, depth) {
  const dirs = treeData[path] || [];
  if (!dirs.length && path !== '' && !Object.prototype.hasOwnProperty.call(treeData, path)) return '';
  let html = '';
  dirs.forEach(d => {
    const id       = 'tn-' + pathId(d.path);
    const isLoaded = Object.prototype.hasOwnProperty.call(treeData, d.path);
    const hasKids  = isLoaded ? treeData[d.path].length > 0 : true;
    const toggle   = hasKids ? (isLoaded ? '▾' : '▸') : '·';
    html += `
      <div class="tree-node" id="${id}" style="--depth:${depth}"
           data-nav-path="${esc(d.path)}" onclick="treeNodeClick(event, '${esc(d.path)}')">
        <span class="toggle">${toggle}</span>
        <span class="icon">📁</span>
        <span class="label" title="${esc(d.name)}">${esc(d.name)}</span>
      </div>`;
    if (isLoaded && treeData[d.path].length > 0) {
      html += `<div class="tree-children">${buildTreeHTML(d.path, depth + 1)}</div>`;
    }
  });
  return html;
}

async function treeNodeClick(event, path) {
  event.stopPropagation();
  if (Object.prototype.hasOwnProperty.call(treeData, path)) { navigateTo(path); return; }
  await loadDir(path);
}

function showMkdirModal() {
  const dest = currentPath ? `/${currentPath.replace(/\\/g, '/')}` : '/  (root)';
  document.getElementById('mkdir-path-hint').textContent = dest;
  document.getElementById('mkdir-name').value = '';
  document.getElementById('mkdir-modal').classList.add('show');
  setTimeout(() => document.getElementById('mkdir-name').focus(), 50);
}
function closeMkdirModal() { document.getElementById('mkdir-modal').classList.remove('show'); }
