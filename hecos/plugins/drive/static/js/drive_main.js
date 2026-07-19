// ─── Initialization ────────────────────────────────────────────────────────────

function initDropzone() {
  const zone = document.getElementById("dropzone");
  if (!zone) return;
  zone.addEventListener("dragover",  e => { e.preventDefault(); zone.classList.add("drag-over"); });
  zone.addEventListener("dragleave", ()  => zone.classList.remove("drag-over"));
  zone.addEventListener("drop", e => {
    e.preventDefault(); zone.classList.remove("drag-over");
    uploadFiles(e.dataTransfer.files);
  });
}

document.addEventListener("DOMContentLoaded", () => {
  initDropzone();
  const urlParams = new URLSearchParams(window.location.search);
  const startRoot = urlParams.get("root") || "";
  
  if (typeof loadDir === "function") {
    loadDir(startRoot); 
  }
  if (typeof loadDrives === "function") {
    loadDrives(); 
  }
  if (typeof loadQuickLinks === "function") {
    loadQuickLinks(); // Load quick links on startup
  }
});
