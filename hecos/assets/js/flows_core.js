// ── State ────────────────────────────────────────────────────────
let currentFlowId = null;
let currentFlowData = null;
let compiledYaml = null;
let lgraph = null;
let lgcanvas = null;
let cmEditor = null;
let sseSource = null;
let mediaRecorder = null;
let isRecording = false;

// ── Shared Utils ──────────────────────────────────────────────────
function debounce(fn, ms) {
  let t; return (...args) => { clearTimeout(t); t=setTimeout(()=>fn(...args),ms); };
}

// ── Toast ─────────────────────────────────────────────────────────
function toast(type, msg) {
  const icon = type==='ok'?'fa-check-circle':type==='error'?'fa-times-circle':'fa-info-circle';
  const el = document.createElement('div');
  el.className=`toast-item ${type}`;
  el.innerHTML=`<i class="fas ${icon}"></i><span>${msg}</span>`;
  document.getElementById('flows-toast').appendChild(el);
  setTimeout(()=>el.remove(), 4000);
}

// ── Tab switching ─────────────────────────────────────────────────
function initTabs() {
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
      btn.classList.add('active');
      document.getElementById('tab-' + btn.dataset.tab).classList.add('active');
      if (btn.dataset.tab === 'canvas' && lgcanvas) lgcanvas.draw(true, true);
      if (btn.dataset.tab === 'yaml' && cmEditor) cmEditor.refresh();
    });
  });
}

// ── Boot ──────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  initTabs();
  if (typeof initEditor === 'function') initEditor();
  if (typeof initCanvas === 'function') initCanvas();
  if (typeof loadFlowsList === 'function') loadFlowsList();

  // Keyboard shortcut: Ctrl+S to save
  document.addEventListener('keydown', e => {
    if ((e.ctrlKey||e.metaKey) && e.key==='s') { 
      e.preventDefault(); 
      if (typeof saveCurrentFlow === 'function') saveCurrentFlow(); 
    }
  });

  // Flow title rename: sync new name back to YAML on blur or Enter
  const _titleInput = document.getElementById('flow-title');
  if (_titleInput) {
    const _applyRename = () => {
      const newName = _titleInput.value.trim();
      if (!newName || !cmEditor) return;
      const yaml = cmEditor.getValue();
      const updated = yaml.replace(/^name:.*$/m, `name: ${newName}`);
      if (updated !== yaml) cmEditor.setValue(updated);
    };
    _titleInput.addEventListener('blur', _applyRename);
    _titleInput.addEventListener('keydown', e => {
      if (e.key === 'Enter') { e.preventDefault(); _applyRename(); _titleInput.blur(); }
    });
  }
});
