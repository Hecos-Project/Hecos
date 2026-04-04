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

// ─── Init ────────────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  initDropzone();
  loadDir(""); // kick off from root
});

// ─── Load directory ──────────────────────────────────────────────────────────
async function loadDir(path) {
  currentPath = path;
  setTbody(`<tr class="empty-row"><td colspan="4">⏳ Caricamento...</td></tr>`);

  try {
    const res  = await fetch(`/drive/api/list?path=${encodeURIComponent(path)}`);
    const data = await res.json();

    if (!data.ok) { showMsg("❌ " + data.error, "err"); return; }

    allEntries = data.entries;

    // Store dirs in tree cache for this path
    treeData[path] = data.entries.filter(e => e.is_dir);

    renderBreadcrumb(data.breadcrumb || []);
    renderTable();
    updateLocationBar(path, data.entries);

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

// ─── Breadcrumb (top toolbar) ─────────────────────────────────────────────────
function renderBreadcrumb(crumbs) {
  const bar = document.getElementById("path-bar");
  let html = `<span class="crumb" onclick="navigateTo('')">🏠 Drive</span>`;
  crumbs.forEach((c, i) => {
    const isLast = i === crumbs.length - 1;
    html += `<span class="sep">/</span>`;
    html += isLast
      ? `<span class="crumb current">${esc(c.name)}</span>`
      : `<span class="crumb" onclick="navigateTo('${esc(c.path)}')">${esc(c.name)}</span>`;
  });
  bar.innerHTML = html;
}

// ─── Location bar ────────────────────────────────────────────────────────────
function updateLocationBar(path, entries) {
  const dispPath = path ? "/" + path.replace(/\\/g, "/") : "/  (root)";
  document.getElementById("loc-path").textContent = dispPath;

  const dirs  = entries.filter(e => e.is_dir).length;
  const files = entries.filter(e => !e.is_dir).length;
  document.getElementById("loc-count").textContent = `${dirs} cart. · ${files} file`;

  document.getElementById("dropzone").textContent =
    `⬆️  Trascina file qui per caricarli in:  ${dispPath}`;
}

// ─── File table ───────────────────────────────────────────────────────────────
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
    setTbody(`<tr class="empty-row"><td colspan="4">📂 Cartella vuota</td></tr>`);
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
        <button onclick="deleteItem('${esc(e.path)}','${esc(e.name)}')" title="Elimina">🗑️</button>
      </td>
    </tr>`;
  }).join(""));

  updateStatusBar();
}

function setTbody(html) {
  document.getElementById("file-tbody").innerHTML = html;
}

function updateStatusBar() {
  const dirs  = allEntries.filter(e => e.is_dir).length;
  const files = allEntries.filter(e => !e.is_dir).length;
  document.getElementById("sb-info").textContent = `${dirs} cartelle  ·  ${files} file`;
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
  label.textContent = `Caricamento in ${dest} ...`;

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
    label.textContent = "✅ Upload completato!";
    showMsg(`✅ ${files.length} file caricati in ${dest}`, "ok");
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
  if (!confirm(`Eliminare "${name}"?\nL'operazione è irreversibile.`)) return;
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
      showMsg(`📁 Cartella "${name}" creata in ${currentPath || "/"}`, "ok");
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
  el.textContent = text; el.className = type;
  clearTimeout(_msgT);
  _msgT = setTimeout(() => { el.className = ""; el.textContent = ""; }, 5000);
}
