/**
 * editor.js
 * Monaco editor logic for the Zentra code editor
 * Expects FILE_PATH, LANGUAGE, THEME, WORD_WRAP, and SPELL_CHK to be defined globally.
 */

let editor, originalContent;
let isModified = false;

// ── Monaco Bootstrap ─────────────────────────────────────────────────
require.config({ paths: { vs: 'https://cdn.jsdelivr.net/npm/monaco-editor@0.44.0/min/vs' } });
require(['vs/editor/editor.main'], function() {

  // 1. Define static Theme Profiles
  const autoTheme = localStorage.getItem('zentra-ui-auto-theme') === 'true';
  const savedTheme = localStorage.getItem('zentra-ui-theme') || 'cyberpunk';
  let zTheme = savedTheme;
  if (autoTheme) {
    zTheme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'cyberpunk' : 'light';
  }
  const isLight = (zTheme === 'light') || document.documentElement.classList.contains('theme-light') || document.body.classList.contains('theme-light');
  console.log('[Zentra Editor] Auto:', autoTheme, 'Saved:', savedTheme, 'Actual:', zTheme, 'isLight:', isLight);
  
  // Zentra Light Profile
  monaco.editor.defineTheme('zentra-light', {
    base: 'vs',
    inherit: true,
    rules: [],
    colors: {
      'editor.background': '#ffffff',
      'editor.lineHighlightBackground': '#f8fafc',
      'editorLineNumber.foreground': '#94a3b8',
      'editorLineNumber.activeForeground': '#2563eb',
      'editor.selectionBackground': '#e2e8f0',
      'editorWidget.background': '#ffffff',
      'editorWidget.border': '#e2e8f0',
      'input.background': '#ffffff',
    }
  });

  // Zentra Dark Profile (Default)
  monaco.editor.defineTheme('zentra-dark', {
    base: 'vs-dark',
    inherit: true,
    rules: [],
    colors: {
      'editor.background': '#0f1117',
      'editor.lineHighlightBackground': '#1a1d27',
      'editorLineNumber.foreground': '#484f58',
      'editorLineNumber.activeForeground': '#6c8cff',
      'editor.selectionBackground': '#264f78',
      'editorWidget.background': '#1a1d27',
      'editorWidget.border': '#2d3351',
      'input.background': '#0f1117',
    }
  });

  const activeTheme = isLight ? 'zentra-light' : 'zentra-dark';
  console.log('[Zentra Editor] Active theme:', activeTheme);

  // 2. Create editor
  editor = monaco.editor.create(document.getElementById('monaco-editor'), {
    value: 'Loading file…',
    language: window.LANGUAGE,
    theme: activeTheme,
    fontFamily: "'JetBrains Mono', 'Fira Code', 'Consolas', monospace",
    fontSize: 14,
    lineHeight: 22,
    minimap: { enabled: true, maxColumn: 80 },
    wordWrap: window.WORD_WRAP,
    automaticLayout: true,
    scrollBeyondLastLine: false,
    renderLineHighlight: 'all',
    cursorBlinking: 'smooth',
    cursorSmoothCaretAnimation: 'on',
    smoothScrolling: true,
    bracketPairColorization: { enabled: true },
    guides: { bracketPairs: true, indentation: true },
    renderWhitespace: 'trailing',
    tabSize: 4,
    insertSpaces: true,
    folding: true,
    foldingHighlight: true,
    showFoldingControls: 'always',
    glyphMargin: true,
    overviewRulerBorder: false,
    scrollbar: {
      vertical: 'auto',
      horizontal: 'auto',
      useShadows: false,
    }
  });

  // 3. Load file content via REST
  fetch(`/drive/api/editor/read?path=${encodeURIComponent(window.FILE_PATH)}`)
    .then(r => r.json())
    .then(data => {
      if (!data.ok) {
        editor.setValue(`// ERROR loading file:\n// ${data.error}`);
        showToast(data.error, true);
        return;
      }
      originalContent = data.content;
      editor.setValue(data.content);
      // Update language if server disagrees
      if (data.language !== window.LANGUAGE) {
        monaco.editor.setModelLanguage(editor.getModel(), data.language);
        document.getElementById('lang-badge').textContent = data.language;
        document.getElementById('status-lang').textContent = data.language;
      }
      setMsg('');
    })
    .catch(e => {
      editor.setValue(`// Connection error: ${e}`);
      showToast('Connection error', true);
    });

  // 4. Track modifications
  editor.onDidChangeModelContent(() => {
    const changed = editor.getValue() !== originalContent;
    if (changed !== isModified) {
      isModified = changed;
      document.getElementById('file-tab').classList.toggle('modified', changed);
      document.getElementById('save-btn').disabled = !changed;
      // Note: relying on document.title string manipulation without jinja template variable
      const baseTitle = document.title.replace('● ', '');
      document.title = (changed ? '● ' : '') + baseTitle;
    }
  });

  // 5. Cursor position in status bar
  editor.onDidChangeCursorPosition(e => {
    const pos = e.position;
    document.getElementById('status-cursor').textContent = `Ln ${pos.lineNumber}, Col ${pos.column}`;
  });

  // 6. Ctrl+S save keybinding
  editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS, saveFile);

  // 7. Spell check overlay (browser native, minimal impact)
  if (window.SPELL_CHK) {
    const ta = editor.getDomNode().querySelector('textarea');
    if (ta) { ta.spellcheck = true; ta.lang = 'en'; }
  }
});

// ── Save ──────────────────────────────────────────────────────────────
function saveFile() {
  if (!editor || !isModified) return;
  const content = editor.getValue();
  document.getElementById('save-btn').disabled = true;
  setMsg('Saving…', 'saving');

  fetch('/drive/api/editor/save', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path: window.FILE_PATH, content })
  })
  .then(r => r.json())
  .then(data => {
    if (data.ok) {
      originalContent = content;
      isModified = false;
      document.getElementById('file-tab').classList.remove('modified');
      
      const baseTitle = document.title.replace('● ', '');
      document.title = baseTitle;
      
      showToast('✓ File saved successfully.');
      setMsg('Saved ✓', 'ok');
      setTimeout(() => setMsg(''), 3000);
    } else {
      showToast(data.error || 'Save failed', true);
      setMsg('Save failed!', 'err');
      document.getElementById('save-btn').disabled = false;
    }
  })
  .catch(e => {
    showToast('Network error: ' + e, true);
    setMsg('Error', 'err');
    document.getElementById('save-btn').disabled = false;
  });
}

document.getElementById('save-btn').addEventListener('click', saveFile);

// ── Helpers ───────────────────────────────────────────────────────────
function setMsg(text, cls = '') {
  const el = document.getElementById('status-msg');
  if (el) {
    el.textContent = text;
    el.className = cls;
  }
}

function showToast(msg, isError = false) {
  const t = document.getElementById('toast');
  if (!t) return;
  t.textContent = msg;
  t.className = isError ? 'error' : '';
  void t.offsetWidth; // force reflow
  t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), 3200);
}

// ── Warn before leaving with unsaved changes ──────────────────────────
window.addEventListener('beforeunload', e => {
  if (isModified) {
    e.preventDefault();
    e.returnValue = 'You have unsaved changes. Are you sure?';
  }
});
