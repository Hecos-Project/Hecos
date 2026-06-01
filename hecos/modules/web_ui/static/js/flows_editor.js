// ── Init CodeMirror ───────────────────────────────────────────────
function initEditor() {
  const el = document.getElementById('yaml-editor');
  if (!el) return;
  cmEditor = CodeMirror.fromTextArea(el, {
    mode: 'yaml', 
    theme: 'material-darker',
    lineNumbers: true, 
    lineWrapping: false,
    indentUnit: 2, 
    tabSize: 2,
    extraKeys: { Tab: cm => cm.execCommand('insertSoftTab') },
  });
  cmEditor.on('change', debounce(onYamlChange, 800));
}

// ── YAML editor sync ──────────────────────────────────────────────
function onYamlChange() {
  const yaml = cmEditor.getValue();
  validateYaml(yaml);
}

async function validateYaml(yaml) {
  const el = document.getElementById('yaml-validation');
  if (!el) return;
  if (!yaml.trim()) { el.className=''; el.style.display='none'; return; }
  try {
    const res = await fetch('/api/flows/validate',{
      method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({yaml})
    });
    const d = await res.json();
    if (d.valid) {
      el.className='ok'; el.textContent='✓ Valid';
    } else {
      el.className='err'; el.textContent='✗ '+d.errors[0];
    }
  } catch { el.className=''; }
}

function applyYamlToCanvas() {
  const yaml = cmEditor.getValue();
  try {
    const flow = jsyaml.load(yaml);
    if (flow && flow.pipeline && typeof renderCanvasFromFlow === 'function') {
      renderCanvasFromFlow(flow);
    }
  } catch(e) { toast('error','YAML parse error: '+e.message); }
}

function formatYaml() {
  try {
    const parsed = jsyaml.load(cmEditor.getValue());
    cmEditor.setValue(jsyaml.dump(parsed, {indent:2,lineWidth:-1}));
  } catch(e) { toast('error','Cannot format: invalid YAML'); }
}
