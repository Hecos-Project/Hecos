// ─── Helpers & Utilities ─────────────────────────────────────────────────────

// Safe unique ID for DOM nodes (works with Unicode paths)
function pathId(path) {
  return "n" + [...(path || "ROOT")].reduce((h, c) => (Math.imul(31, h) + c.charCodeAt(0)) | 0, 0).toString(16).replace("-", "m");
}

function formatSize(b) {
  if (b == null) return "—";
  if (b < 1024) return `${b} B`;
  if (b < 1048576) return `${(b / 1024).toFixed(1)} KB`;
  if (b < 1073741824) return `${(b / 1048576).toFixed(1)} MB`;
  return `${(b / 1073741824).toFixed(2)} GB`;
}

function fileIcon(name) {
  const ext = name.split(".").pop().toLowerCase();
  return ({
    pdf: "📄", txt: "📝", md: "📝", doc: "📝", docx: "📝",
    jpg: "🖼️", jpeg: "🖼️", png: "🖼️", gif: "🖼️", webp: "🖼️",
    mp3: "🎵", wav: "🎵", ogg: "🎵", flac: "🎵", aac: "🎵",
    mp4: "🎬", mkv: "🎬", avi: "🎬", mov: "🎬",
    zip: "📦", tar: "📦", gz: "📦", rar: "📦", "7z": "📦",
    py: "🐍", js: "⚙️", html: "🌐", css: "🎨", json: "📋", yaml: "📋",
    sh: "🖥️", bat: "🖥️", exe: "🔧"
  })[ext] || "📄";
}

function esc(str) {
  return String(str)
    .replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/'/g, "&#39;")
    .replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

let _msgT;
function showMsg(text, type) {
  const el = document.getElementById("drive-msg");
  if (!el) return;
  el.textContent = text; el.className = type;
  clearTimeout(_msgT);
  _msgT = setTimeout(() => { el.className = ""; el.textContent = ""; }, 5000);
}
