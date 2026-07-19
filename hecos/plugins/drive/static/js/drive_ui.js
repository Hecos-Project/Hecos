// ─── UI Rendering ────────────────────────────────────────────────────────────

function renderBreadcrumb(crumbs, rootLabel) {
  const bar = document.getElementById("path-bar");
  const rootDisplay = rootLabel || (window.t ? "🏠 " + window.t('webui_drive_root_label') : "🏠 Drive");
  let html = `<span class="crumb" onclick="navigateTo('')" title="${rootLabel}">${rootDisplay}</span>`;
  crumbs.forEach((c, i) => {
    const isLast = i === crumbs.length - 1;
    html += `<span class="sep">/</span>`;
    html += isLast
      ? `<span class="crumb current">${esc(c.name)}</span>`
      : `<span class="crumb" onclick="navigateTo('${esc(c.path)}')" title="${esc(c.abs || c.path)}">${esc(c.name)}</span>`;
  });
  bar.innerHTML = html;
}

function updateLocationBar(path, entries, absPath, rootLabel) {
  const dispPath = absPath || (path ? "/" + path.replace(/\\/g, "/") : rootLabel || "/");
  document.getElementById("loc-path").textContent = dispPath;

  const dirs  = entries.filter(e => e.is_dir).length;
  const files = entries.filter(e => !e.is_dir).length;
  const dirsFilesMsg = window.t ? window.t('webui_drive_dirs_files', {dirs, files}) : `${dirs} folders · ${files} files`;
  document.getElementById("loc-count").textContent = dirsFilesMsg;

  const dropzoneTpl = window.t ? window.t('webui_drive_upload_to') : 'Drop files here to upload to:';
  document.getElementById("dropzone").textContent =
    `⬆️  ${dropzoneTpl}  ${dispPath}`;
    
  if (typeof updateBookmarkIcon === "function") {
    updateBookmarkIcon();
  }
}

const EDITABLE_EXTS = new Set([
  'py','js','ts','json','yaml','yml','toml','html','htm','css','scss',
  'sh','bat','ps1','md','txt','ini','cfg','conf','log','xml','env'
]);
function isEditable(name) {
  const ext = name.split('.').pop().toLowerCase();
  return EDITABLE_EXTS.has(ext);
}
function openEditor(path) {
  window.open(`/drive/editor?path=${encodeURIComponent(path)}`, '_blank');
}

function isPreviewable(name) {
  return typeof window.HecosMediaPlayer !== 'undefined';
}

function sortBy(key) {
  sortAsc = (sortKey === key) ? !sortAsc : true;
  sortKey = key;
  renderTable();
}

function renderTable() {
  const entries = [...allEntries].sort((a, b) => {
    if (a.is_dir !== b.is_dir) return a.is_dir ? -1 : 1;
    let va = (a[sortKey] ?? "");
    let vb = (b[sortKey] ?? "");
    if (typeof va === "string") va = va.toLowerCase();
    if (typeof vb === "string") vb = vb.toLowerCase();
    if (va < vb) return sortAsc ? -1 : 1;
    if (va > vb) return sortAsc ?  1 : -1;
    return 0;
  });

  if (!entries.length) {
    const emptyMsg = window.t ? window.t('webui_drive_empty') : 'Folder empty';
    setTbody(`<tr class="empty-row"><td colspan="4">📂 ${emptyMsg}</td></tr>`);
    updateStatusBar();
    return;
  }

  setTbody(entries.map(e => {
    const icon    = e.is_dir ? "📁" : fileIcon(e.name);
    const sizeStr = e.is_dir ? "—" : formatSize(e.size);
    const dateStr = e.modified ? new Date(e.modified * 1000).toLocaleString() : "—";
    const action  = e.is_dir
      ? `ondblclick="navigateTo('${esc(e.path)}')" onclick="void(0)"`
      : `onclick="downloadFile('${esc(e.path)}')"`;

    return `<tr>
      <td class="name-cell" ${action}>
        <span class="icon">${icon}</span>
        <span class="fname" title="${esc(e.name)}">${esc(e.name)}</span>
        ${e.is_dir ? `<span style="font-size:10px;color:var(--muted);margin-left:6px;">▶</span>` : ""}
      </td>
      <td class="size-cell">${sizeStr}</td>
      <td class="date-cell">${dateStr}</td>
      <td class="actions-cell">
        ${e.is_dir
          ? `<button onclick="navigateTo('${esc(e.path)}')" title="Apri">📂</button>`
          : `<button onclick="downloadFile('${esc(e.path)}')" title="Scarica">⬇️</button>`}
        ${!e.is_dir && isEditable(e.name)
          ? `<button onclick="openEditor('${esc(e.path)}')" title="${window.t ? window.t('webui_drive_edit') : 'Edit'}" style="color:var(--accent);">✏️</button>`
          : ''}
        <button onclick="deleteItem('${esc(e.path)}','${esc(e.name)}')" title="${window.t ? window.t('webui_conf_logs_delete') : 'Delete'}">🗑️</button>
      </td>
    </tr>`;
  }).join(""));

  updateStatusBar();

  // Notify the Hecos Media Player to inject Drive thumbnails
  if (typeof window.HecosMediaPlayer?.injectDriveThumbnails === 'function') {
    window.HecosMediaPlayer.injectDriveThumbnails(allEntries, currentPath);
  }
}

function setTbody(html) {
  document.getElementById("file-tbody").innerHTML = html;
}

function updateStatusBar() {
  const dirs  = allEntries.filter(e => e.is_dir).length;
  const files = allEntries.filter(e => !e.is_dir).length;
  const infoMsg = window.t ? window.t('webui_drive_dirs_files', {dirs, files}) : `${dirs} folders · ${files} files`;
  document.getElementById("sb-info").textContent = infoMsg;
}

function renderTree() {
  const root = document.getElementById("tree-root");
  root.innerHTML = buildTreeHTML("", 0);
  // Mark active node
  const activeId = "tn-" + pathId(currentPath);
  const el = document.getElementById(activeId);
  if (el) {
    el.classList.add("active");
    el.scrollIntoView({ block: "nearest" });
  }
}

function buildTreeHTML(path, depth) {
  const dirs = treeData[path] || [];
  if (!dirs.length && path !== "" && !treeData.hasOwnProperty(path)) {
    return ""; // nothing cached yet
  }

  let html = "";
  dirs.forEach(d => {
    const id      = "tn-" + pathId(d.path);
    const isLoaded = treeData.hasOwnProperty(d.path);
    const hasKids  = isLoaded ? treeData[d.path].length > 0 : true; // unknown → assume yes
    const toggle   = hasKids ? (isLoaded ? "▾" : "▸") : "·";

    html += `
      <div class="tree-node" id="${id}" style="--depth:${depth}"
           onclick="treeNodeClick(event, '${esc(d.path)}')">
        <span class="toggle">${toggle}</span>
        <span class="icon">📁</span>
        <span class="label" title="${esc(d.name)}">${esc(d.name)}</span>
      </div>`;

    // Children (only if we have cached data for this node)
    if (isLoaded && treeData[d.path].length > 0) {
      html += `<div class="tree-children">`;
      html += buildTreeHTML(d.path, depth + 1);
      html += `</div>`;
    }
  });
  return html;
}

async function treeNodeClick(event, path) {
  event.stopPropagation();
  // If already loaded, just navigate
  if (treeData.hasOwnProperty(path)) {
    navigateTo(path);
    return;
  }
  // Load this path (which will cache treeData[path] and re-render)
  await loadDir(path);
}

function showMkdirModal() {
  const dest = currentPath ? `/${currentPath.replace(/\\/g, "/")}` : "/  (root)";
  document.getElementById("mkdir-path-hint").textContent = dest;
  document.getElementById("mkdir-name").value = "";
  document.getElementById("mkdir-modal").classList.add("show");
  setTimeout(() => document.getElementById("mkdir-name").focus(), 50);
}
function closeMkdirModal() { document.getElementById("mkdir-modal").classList.remove("show"); }
