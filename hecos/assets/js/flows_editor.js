// ── Init CodeMirror ───────────────────────────────────────────────
function initEditor() {
  const el = document.getElementById('yaml-editor');
  if (!el || typeof CodeMirror === 'undefined') return;
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
  if(!cmEditor) return;
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
  if(!cmEditor || typeof jsyaml === 'undefined') return;
  const yaml = cmEditor.getValue();
  try {
    const flow = jsyaml.load(yaml);
    if (flow && flow.pipeline && typeof renderCanvasFromFlow === 'function') {
      renderCanvasFromFlow(flow);
    }
  } catch(e) { toast('error','YAML parse error: '+e.message); }
}

function formatYaml() {
  if(!cmEditor || typeof jsyaml === 'undefined') return;
  try {
    const parsed = jsyaml.load(cmEditor.getValue());
    cmEditor.setValue(jsyaml.dump(parsed, {indent:2,lineWidth:-1}));
  } catch(e) { toast('error','Cannot format: invalid YAML'); }
}

function syncCanvasToYaml() {
  if (!cmEditor || !lgraph || typeof jsyaml === 'undefined') return;
  let flowObj;
  try {
    flowObj = jsyaml.load(cmEditor.getValue()) || {};
  } catch(e) { flowObj = { name: 'Flow', trigger: {type: 'manual'} }; }
  
  if (!flowObj.id && typeof currentFlowId !== 'undefined' && currentFlowId) {
    flowObj.id = currentFlowId;
  }
  
  flowObj.pipeline = [];
  
  // Sort nodes roughly by X/Y position for a readable linear YAML order
  const nodes = lgraph._nodes.slice().sort((a,b) => {
    if (Math.abs(a.pos[1] - b.pos[1]) > 100) return a.pos[1] - b.pos[1];
    return a.pos[0] - b.pos[0];
  });
  
  // Build a nodeId → title map for connection lookup
  const idToTitle = {};
  for (const node of nodes) {
    idToTitle[node.id] = node.title || 'step';
  }

  for (const node of nodes) {
    const props = node.properties || {};
    const step = {
      id: node.title || 'step',
      action: props.action || 'LOGIC__delay',
    };
    if (props.params && props.params !== '{}') {
      try {
         const p = JSON.parse(props.params);
         if (Object.keys(p).length) step.params = p;
      } catch(e){}
    }
    if (props.output_as) step.output_as = props.output_as;
    
    // Read actual canvas link connections to derive depends_on
    const deps = [];
    if (node.inputs) {
      for (const input of node.inputs) {
        if (input.link != null) {
          const link = lgraph.links[input.link];
          if (link) {
            const srcTitle = idToTitle[link.origin_id];
            if (srcTitle) deps.push(srcTitle);
          }
        }
      }
    }
    if (deps.length) step.depends_on = deps;
    
    flowObj.pipeline.push(step);
  }
  
  const newYaml = jsyaml.dump(flowObj, {indent: 2, lineWidth: -1});
  const scrollInfo = cmEditor.getScrollInfo();
  cmEditor.setValue(newYaml);
  cmEditor.scrollTo(scrollInfo.left, scrollInfo.top);
}

