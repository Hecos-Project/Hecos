/**
 * Zentra Drive v2.1 — Professional File Manager
 * FTP-style: left tree sidebar + right file list
 */

// ─── State ───────────────────────────────────────────────────────────────────
let currentPath = "";        // currently visible directory (relative to drive root)
let allEntries  = [];        // all entries for the current directory
let sortKey     = "name";
let sortAsc     = true;
let treeData    = {};        // path → [dir entries], lazy cache

// Safe unique ID for DOM nodes (works with Unicode paths)
function pathId(path) {
  return "n" + [...(path || "ROOT")].reduce((h, c) => (Math.imul(31, h) + c.charCodeAt(0)) | 0, 0).toString(16).replace("-", "m");
}

// ─── Init is now at the end of the file

// ─── Load directory ──────────────────────────────────────────────────────────
async function loadDir(path) {
  currentPath = path;
  const msgLoading = window.t ? window.t('webui_conf_msg_loading') : 'Loading...';
  setTbody(`<tr class="empty-row"><td colspan="4">⏳ ${msgLoading}</td></tr>`);

  try {
    const res  = await fetch(`/drive/api/list?path=${encodeURIComponent(path)}`);
    const data = await res.json();

    if (!data.ok) { showMsg("❌ " + (data.error || "Error"), "err"); return; }

    allEntries = data.entries;

    // Store absolute path context
    currentAbsPath   = data.abs_path   || "";
    currentRootLabel = data.root_label || "";

    // Store dirs in tree cache for this path
    treeData[path] = data.entries.filter(e => e.is_dir);

    renderBreadcrumb(data.breadcrumb || [], data.root_label || "");
    renderTable();
    updateLocationBar(path, data.entries, data.abs_path, data.root_label);

    // Rebuild the entire tree from what we know
    renderTree();

  } catch (e) {
    showMsg("Errore di rete: " + e, "err");
    setTbody(`<tr class="empty-row"><td colspan="4">❌ ${e}</td></tr>`);
  }
}

function navigateTo(path) { loadDir(path); }

function goUp() {
  if (!currentPath) return;
  const parts = currentPath.replace(/\\/g, "/").split("/").filter(Boolean);
  parts.pop();
  loadDir(parts.join("/"));
}

// ─── State extras ────────────────────────────────────────────────────────────
let currentRootLabel = "";   // e.g. "C:/"  – set from API response
let currentAbsPath   = "";   // full absolute path of current dir

// ─── Drive selector ──────────────────────────────────────────────────────────
async function loadDrives() {
  try {
    const res  = await fetch("/drive/api/drives");
    const data = await res.json();
    if (!data.ok || !data.drives || !data.drives.length) return;

    const tool = document.getElementById("toolbar");
    let sel    = document.getElementById("drive-select");
    if (!sel) {
      sel = document.createElement("select");
      sel.id = "drive-select";
      tool.insertBefore(sel, tool.children[2]); // after ⬆ button
    } else {
      sel.innerHTML = ""; // Clear existing options
    }
    sel.title  = window.t ? window.t('webui_drive_drive_sel_hint') : "Change drive";
    sel.style.cssText = `
      background: rgba(102,252,241,0.08);
      color: var(--accent);
      border: 1px solid var(--border);
      border-radius: 5px;
      padding: 3px 8px;
      font-family: inherit;
      font-size: 12px;
      cursor: pointer;
      margin-right: 6px;
    `;

    data.drives.forEach(d => {
      const opt   = document.createElement("option");
      opt.value   = d.path;
      opt.textContent = `💾 ${d.letter}: — ${d.label}  (${d.free_gb} GB liberi)`;
      sel.appendChild(opt);
    });

    sel.addEventListener("change", async () => {
      // When user picks a different drive, navigate to that drive root (relative = "")
      // We must tell the backend which root to use — for now we trigger reload with path=""
      // and change the config on the fly via the SYSTEM set_configuration tool.
      // Simpler approach: navigate to the drive path relative to its own root.
      // Since the Drive root is currently C:\ we use a "change_root" approach.
      // We signal via a special query param ?drive= so the server knows which root to use.
      // Cleanest: just open /drive and update the UI root via a new query.
      window.location.href = `/drive?root=${encodeURIComponent(sel.value)}`;
    });

    // Pre-select current drive if we know it
    if (currentRootLabel) {
      for (const opt of sel.options) {
        if (currentRootLabel.toLowerCase().startsWith(opt.value.replace(/\//g,"\\").toLowerCase().substring(0,3))) {
          opt.selected = true;
          break;
        }
      }
    }
  } catch (e) {
    console.warn("[Drive] Could not load drive list:", e);
  }
}

// ─── Breadcrumb (top toolbar) ─────────────────────────────────────────────────
function renderBreadcrumb(crumbs, rootLabel) {
  const bar = document.getElementById("path-bar");
  // Show the actual root (e.g. "C:/") as the first clickable crumb
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

// ─── Location bar ────────────────────────────────────────────────────────────
function updateLocationBar(path, entries, absPath, rootLabel) {
  // Show the FULL absolute path (e.g. "C:/Users/Tony/Documents")
  const dispPath = absPath || (path ? "/" + path.replace(/\\/g, "/") : rootLabel || "/");
  document.getElementById("loc-path").textContent = dispPath;

  const dirs  = entries.filter(e => e.is_dir).length;
  const files = entries.filter(e => !e.is_dir).length;
  const dirsFilesMsg = window.t ? window.t('webui_drive_dirs_files', {dirs, files}) : `${dirs} folders · ${files} files`;
  document.getElementById("loc-count").textContent = dirsFilesMsg;

  const dropzoneTpl = window.t ? window.t('webui_drive_upload_to') : 'Drop files here to upload to:';
  document.getElementById("dropzone").textContent =
    `⬆️  ${dropzoneTpl}  ${dispPath}`;
}

// ─── File table ───────────────────────────────────────────────────────────────

// File types the Zentra Code Editor supports
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

// ─── Media Preview — handled by media_viewer extension ──────────────────────
// Stub functions kept here only as fallbacks in case the extension JS hasn't
// loaded yet. The real implementation lives in media_viewer.js.
function isPreviewable(name) {
  return typeof window.DriveMediaViewer !== 'undefined' && false; // extension handles it
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
          ? `<button onclick="openEditor('${esc(e.path)}')" title="${window.t ? window.t('webui_drive_edit') : 'Edit'}" style="color:#58a6ff;">✏️</button>`
          : ''}
        <button onclick="deleteItem('${esc(e.path)}','${esc(e.name)}')" title="${window.t ? window.t('webui_conf_logs_delete') : 'Delete'}">🗑️</button>
      </td>
    </tr>`;
  }).join(""));

  updateStatusBar();

  // Notify the media viewer extension to inject thumbnails
  if (typeof window.DriveMediaViewer?.onTableRendered === 'function') {
    window.DriveMediaViewer.onTableRendered(allEntries, currentPath);
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

// ─── Sidebar Tree ─────────────────────────────────────────────────────────────
/*
  Strategy: build a recursive tree from treeData cache.
  treeData[path] = list of immediate subdirectory entries under `path`.
  Only paths we've visited are expanded in the tree.
  Un-visited paths show a ▸ toggle which, when clicked, loads that dir.
*/

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

// ─── Upload ──────────────────────────────────────────────────────────────────
async function uploadFiles(files) {
  if (!files || !files.length) return;

  const progWrap = document.getElementById("upload-progress");
  const bar      = document.getElementById("upload-bar");
  const label    = document.getElementById("upload-label");
  progWrap.style.display = "block";
  bar.value = 0;

  const dest = currentPath ? `/${currentPath.replace(/\\/g, "/")}` : "/";
  const loadingMsg = window.t ? window.t('webui_conf_msg_loading') : 'Loading...';
  label.textContent = `${loadingMsg} ${dest} ...`;

  const fd = new FormData();
  fd.append("path", currentPath);
  Array.from(files).forEach(f => fd.append("files[]", f));

  try {
    await new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open("POST", "/drive/api/upload");
      xhr.upload.onprogress = e => {
        if (e.lengthComputable) {
          const pct = Math.round(e.loaded / e.total * 100);
          bar.value = pct;
          label.textContent = `${pct}%  —  ${formatSize(e.loaded)} / ${formatSize(e.total)}  →  ${dest}`;
        }
      };
      xhr.onload  = () => { const d = JSON.parse(xhr.responseText); d.ok ? resolve(d) : reject(new Error(d.error)); };
      xhr.onerror = () => reject(new Error("Errore di rete."));
      xhr.send(fd);
    });

    bar.value = 100;
    const okMsg = window.t ? window.t('webui_drive_upload_ok') : 'Upload completed!';
    label.textContent = `✅ ${okMsg}`;
    showMsg(`✅ ${files.length} ${window.t ? window.t('webui_chat_files') : 'files'} ${window.t ? window.t('webui_drive_upload_ok') : 'uploaded'} ${dest}`, "ok");
    setTimeout(() => { progWrap.style.display = "none"; }, 2500);
    loadDir(currentPath);
  } catch (e) {
    showMsg("❌ " + e.message, "err");
    progWrap.style.display = "none";
  }
  document.getElementById("file-input").value = "";
}

// ─── Download ────────────────────────────────────────────────────────────────
function downloadFile(path) {
  const a = document.createElement("a");
  a.href = `/drive/api/download?path=${encodeURIComponent(path)}`;
  a.download = "";
  document.body.appendChild(a); a.click(); document.body.removeChild(a);
}

// ─── Delete ──────────────────────────────────────────────────────────────────
async function deleteItem(path, name) {
  const confirmMsg = window.t ? window.t('webui_drive_delete_confirm', {name}) : `Delete ${name}?`;
  if (!confirm(confirmMsg)) return;
  try {
    const res  = await fetch(`/drive/api/delete?path=${encodeURIComponent(path)}`, { method: "DELETE" });
    const data = await res.json();
    if (data.ok) {
      showMsg(`🗑️ "${name}" eliminato.`, "ok");
      // Invalidate tree cache of parent + current
      const parent = path.replace(/\\/g, "/").split("/").slice(0, -1).join("/");
      delete treeData[parent];
      delete treeData[path];
      loadDir(currentPath);
    } else { showMsg("❌ " + data.error, "err"); }
  } catch (e) { showMsg("Errore di rete: " + e, "err"); }
}

// ─── Mkdir ───────────────────────────────────────────────────────────────────
function showMkdirModal() {
  const dest = currentPath ? `/${currentPath.replace(/\\/g, "/")}` : "/  (root)";
  document.getElementById("mkdir-path-hint").textContent = dest;
  document.getElementById("mkdir-name").value = "";
  document.getElementById("mkdir-modal").classList.add("show");
  setTimeout(() => document.getElementById("mkdir-name").focus(), 50);
}
function closeMkdirModal() { document.getElementById("mkdir-modal").classList.remove("show"); }

async function confirmMkdir() {
  const name = document.getElementById("mkdir-name").value.trim();
  if (!name) return;
  closeMkdirModal();
  try {
    const res  = await fetch("/drive/api/mkdir", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path: currentPath, name })
    });
    const data = await res.json();
    if (data.ok) {
      const successMsg = window.t ? window.t('webui_drive_mkdir_success', {name, path: currentPath || "/"}) : `Folder created`;
      showMsg(`📁 ${successMsg}`, "ok");
      delete treeData[currentPath]; // invalidate cache → tree will expand on next load
      loadDir(currentPath);
    } else { showMsg("❌ " + data.error, "err"); }
  } catch (e) { showMsg("Errore di rete: " + e, "err"); }
}

// ─── Dropzone ────────────────────────────────────────────────────────────────
function initDropzone() {
  const zone = document.getElementById("dropzone");
  zone.addEventListener("dragover",  e => { e.preventDefault(); zone.classList.add("drag-over"); });
  zone.addEventListener("dragleave", ()  => zone.classList.remove("drag-over"));
  zone.addEventListener("drop", e => {
    e.preventDefault(); zone.classList.remove("drag-over");
    uploadFiles(e.dataTransfer.files);
  });
}

// ─── Helpers ─────────────────────────────────────────────────────────────────
function formatSize(b) {
  if (b == null) return "—";
  if (b < 1024)       return `${b} B`;
  if (b < 1048576)    return `${(b/1024).toFixed(1)} KB`;
  if (b < 1073741824) return `${(b/1048576).toFixed(1)} MB`;
  return `${(b/1073741824).toFixed(2)} GB`;
}

function fileIcon(name) {
  const ext = name.split(".").pop().toLowerCase();
  return ({
    pdf:"📄", txt:"📝", md:"📝", doc:"📝", docx:"📝",
    jpg:"🖼️", jpeg:"🖼️", png:"🖼️", gif:"🖼️", webp:"🖼️",
    mp3:"🎵", wav:"🎵", ogg:"🎵", flac:"🎵", aac:"🎵",
    mp4:"🎬", mkv:"🎬", avi:"🎬", mov:"🎬",
    zip:"📦", tar:"📦", gz:"📦", rar:"📦", "7z":"📦",
    py:"🐍", js:"⚙️", html:"🌐", css:"🎨", json:"📋", yaml:"📋",
    sh:"🖥️", bat:"🖥️", exe:"🔧"
  })[ext] || "📄";
}

function esc(str) {
  return String(str)
    .replace(/&/g,"&amp;").replace(/"/g,"&quot;").replace(/'/g,"&#39;")
    .replace(/</g,"&lt;").replace(/>/g,"&gt;");
}

let _msgT;
function showMsg(text, type) {
  const el = document.getElementById("drive-msg");
  if (!el) return;
  el.textContent = text; el.className = type;
  clearTimeout(_msgT);
  _msgT = setTimeout(() => { el.className = ""; el.textContent = ""; }, 5000);
}


// ─── Quick Links ─────────────────────────────────────────────────────────────
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
    data.groups.forEach(grp => {
      html += `<div class="ql-group">
        <div class="ql-group-title">${esc(grp.title)}</div>
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
    // If it's a file, open in editor if supported
    if (isEditable(path)) {
      openEditor(path);
    } else {
      showMsg("⚠️ Estensione non supportata dall'editor.", "err");
    }
  } else {
    // If it's a directory, navigate to it
    navigateTo(path);
  }
}

// Update DOMContentLoaded to include Quick Links
document.addEventListener("DOMContentLoaded", () => {
  initDropzone();
  const urlParams = new URLSearchParams(window.location.search);
  const startRoot = urlParams.get("root") || "";
  loadDir(startRoot); 
  loadDrives(); 
  loadQuickLinks(); // Load quick links on startup
});
