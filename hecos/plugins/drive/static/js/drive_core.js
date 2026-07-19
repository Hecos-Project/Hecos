// ─── API & Core Actions ──────────────────────────────────────────────────────

async function loadDir(path) {
  currentPath = path;
  // Show loading state that works in both list and grid modes
  const msgLoading = window.t ? window.t('webui_conf_msg_loading') : 'Loading...';
  document.getElementById('file-scroll').innerHTML =
    `<table><tbody><tr class="empty-row"><td colspan="4">⏳ ${msgLoading}</td></tr></tbody></table>`;

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
  if (!currentPath) return; // already at default root
  if (currentPath.match(/^[a-zA-Z]:\/?$/) || currentPath === "/") return; // already at absolute root

  const parts = currentPath.replace(/\\/g, "/").split("/").filter(Boolean);
  if (currentPath.includes(":/")) {
    parts.pop();
    loadDir(parts.length === 1 ? parts[0] + "/" : parts.join("/"));
  } else {
    parts.pop();
    loadDir(parts.join("/"));
  }
}

function goRoot() {
  let base = "";
  if (currentPath && currentPath.includes(":/")) {
    base = currentPath.split("/")[0] + "/";
  } else if (currentPath && currentPath.startsWith("/")) {
    base = "/";
  }
  loadDir(base);
}

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
      background: var(--bg2);
      color: var(--text);
      border: 1px solid var(--border);
      border-radius: 5px;
      padding: 3px 8px;
      font-family: inherit;
      font-size: 12px;
      cursor: pointer;
      margin-right: 6px;
      outline: none;
    `;

    data.drives.forEach(d => {
      const opt   = document.createElement("option");
      opt.value   = d.path;
      opt.textContent = `💾 ${d.letter}: — ${d.label}  (${d.free_gb} GB liberi)`;
      sel.appendChild(opt);
    });

    sel.addEventListener('change', async () => {
      treeData = {};  // reset tree cache when switching drive
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

function downloadFile(path) {
  const a = document.createElement("a");
  a.href = `/drive/api/download?path=${encodeURIComponent(path)}`;
  a.download = "";
  document.body.appendChild(a); a.click(); document.body.removeChild(a);
}

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
