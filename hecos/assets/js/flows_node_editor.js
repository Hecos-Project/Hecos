// ── Node Editor Modal ────────────────────────────────────────────────────────
// opens on double-click of a node on the canvas

let _editingNode = null;

function openNodeEditor(node) {
  if (!node) return;
  _editingNode = node;
  
  const modal = document.getElementById('node-editor-modal-bg');
  const actionSel = document.getElementById('ne-action');
  
  // ensure catalog is loaded for the select dropdown
  if (!_paletteCatalog && typeof initPalette === 'function') {
    // If palette wasn't opened yet, init it silently
    fetch('/api/flows/actions/catalog').then(r=>r.json()).then(d=>{
      if(d.ok) {
        _paletteCatalog = d.catalog;
        _populateEditorSelect(actionSel);
        _applyNodeData(node);
      }
    });
  } else {
    _populateEditorSelect(actionSel);
    _applyNodeData(node);
  }
  
  if (modal) modal.style.display = 'flex';
}

function _populateEditorSelect(selectEl) {
  if (!selectEl || !_paletteCatalog) return;
  selectEl.innerHTML = '';
  const sortedCats = Object.keys(_paletteCatalog).sort();
  for (const cat of sortedCats) {
    const group = document.createElement('optgroup');
    group.label = cat;
    for (const a of _paletteCatalog[cat]) {
      const opt = document.createElement('option');
      opt.value = a.name;
      opt.textContent = a.name.replace(/^[^_]+__/, '');
      group.appendChild(opt);
    }
    selectEl.appendChild(group);
  }
}

function _applyNodeData(node) {
  const props = node.properties || {};
  document.getElementById('ne-orig-id').value = node.title || '';
  document.getElementById('ne-id').value = node.title || '';
  document.getElementById('ne-action').value = props.action || '';
  
  let paramsStr = props.params || '{}';
  try {
    let obj = typeof paramsStr === 'string' ? JSON.parse(paramsStr) : paramsStr;
    paramsStr = Object.keys(obj).length ? jsyaml.dump(obj) : '';
  } catch(e) {}
  document.getElementById('ne-params').value = paramsStr;
  
  document.getElementById('ne-output').value = props.output_as || '';
  
  // Convert depends_on which is a list in YAML but comma-sep string in node editor
  let deps = props.depends_on || [];
  if (Array.isArray(deps)) {
      deps = deps.map(d => {
          if (typeof d === 'object' && d.node) return `${d.node} (${d.branch || 'out'})`;
          return d;
      }).join(', ');
  }
  document.getElementById('ne-depends').value = deps;

  // Hide/show 'Output As' depending on action type
  const outputRow = document.getElementById('ne-output').closest('div[style]');
  const action = props.action || '';
  if (outputRow) {
    outputRow.style.display = action === 'LOGIC__set_variable' ? 'none' : '';
  }
  
  // Rebuild the dynamic form based on the selected action schema
  buildDynamicForm();
}

// ── Variable Discovery ────────────────────────────────────────────────────────
// Scans the current flow YAML to find all variables defined by set_variable
// and output_as fields. Returns a sorted, unique array of variable names.
function getAvailableVariables() {
  const vars = new Set();
  const yamlEl = document.getElementById('yaml-editor');
  let yamlText = yamlEl ? yamlEl.value : '';
  // Try CodeMirror instance if present
  if (!yamlText && window._cmEditor) yamlText = window._cmEditor.getValue();
  
  let parsed = null;
  try { parsed = jsyaml.load(yamlText); } catch(e) {}
  
  if (parsed && Array.isArray(parsed.pipeline)) {
    for (const step of parsed.pipeline) {
      if (step.output_as) vars.add(step.output_as);
      if (step.action === 'LOGIC__set_variable' && step.params && step.params.name) {
        vars.add(step.params.name);
      }
    }
  }
  return Array.from(vars).sort();
}

function closeNodeEditor() {
  const modal = document.getElementById('node-editor-modal-bg');
  if (modal) modal.style.display = 'none';
  _editingNode = null;
}

function saveNodeEditor() {
  if (!_editingNode) return;
  
  const stepId = document.getElementById('ne-id').value.trim();
  const action = document.getElementById('ne-action').value;
  const paramsStr = document.getElementById('ne-params').value.trim();
  const outputAs = document.getElementById('ne-output').value.trim();
  const dependsStr = document.getElementById('ne-depends').value.trim();
  
  // Validate YAML params
  let parsedObj = {};
  if (paramsStr) {
    try {
      parsedObj = jsyaml.load(paramsStr) || {};
      if (typeof parsedObj !== 'object' || Array.isArray(parsedObj)) {
        throw new Error('Params must be an object/dict');
      }
    } catch(e) {
      if(typeof toast === 'function') toast('error', 'Invalid YAML in Params');
      return;
    }
  }
  
  // Update node
  _editingNode.title = stepId;
    let newDeps = [];
    if (dependsStr) {
        newDeps = dependsStr.split(',').map(s => {
            s = s.trim();
            if (!s) return null;
            let m = s.match(/^(.*?)\s*\((.*?)\)$/);
            if (m) return { node: m[1].trim(), branch: m[2].trim() };
            return s;
        }).filter(s => s);
    }

    _editingNode.properties = {
      action: action,
      params: Object.keys(parsedObj).length ? JSON.stringify(parsedObj) : '{}',
      output_as: outputAs,
      depends_on: newDeps
    };
  
  // Update _nodeMap key if ID changed (LiteGraph legacy — no-op with ReactFlow bridge)
  const origId = document.getElementById('ne-orig-id').value;
  if (origId && origId !== stepId && typeof _nodeMap !== 'undefined') {
    _nodeMap[stepId] = _nodeMap[origId];
    delete _nodeMap[origId];
    if(typeof _nodeOrigColors !== 'undefined') {
       _nodeOrigColors[stepId] = _nodeOrigColors[origId];
       delete _nodeOrigColors[origId];
    }
  }
  
  // Sync canvas via ReactFlow bridge (replaces lgcanvas.draw)
  if (typeof syncCanvasToYaml === 'function') syncCanvasToYaml();
  
  closeNodeEditor();
  if (typeof toast === 'function') toast('ok', 'Node updated');
}

// ── Smart Dynamic Form Builder ───────────────────────────────────────────────

function toggleRawYaml() {
  const wrap = document.getElementById('ne-params-wrap');
  wrap.style.display = wrap.style.display === 'none' ? 'flex' : 'none';
}

function getActionSchema(actionName) {
  if (!_paletteCatalog) return null;
  for (const cat of Object.values(_paletteCatalog)) {
    for (const a of cat) {
      if (a.name === actionName) return a;
    }
  }
  return null;
}

function buildDynamicForm() {
  const container = document.getElementById('ne-dynamic-form');
  const actionName = document.getElementById('ne-action').value;
  const rawYaml = document.getElementById('ne-params').value.trim();
  
  // Hide Output As for set_variable (it uses 'name' param directly)
  const outputRow = document.getElementById('ne-output')?.closest('div[style]');
  if (outputRow) {
    outputRow.style.display = (actionName === 'LOGIC__set_variable') ? 'none' : '';
  }

  container.innerHTML = ''; // reset
  const schema = getActionSchema(actionName);
  
  if (!schema || !schema.params || Object.keys(schema.params).length === 0) {
    container.innerHTML = '<div style="color:var(--flows-muted); font-size: 0.85em;"><i>No parameters required for this action.</i></div>';
    return;
  }
  
  let currentVals = {};
  if (rawYaml) {
    try { currentVals = jsyaml.load(rawYaml) || {}; } catch(e) {}
  }

  for (const [key, desc] of Object.entries(schema.params)) {
    const descLower = String(desc).toLowerCase();
    const val = currentVals[key];
    
    // Wrapper for a single field
    const fieldWrap = document.createElement('div');
    fieldWrap.className = 'dynamic-field';
    fieldWrap.style = "display: flex; flex-direction: column; gap: 4px; border: 1px solid rgba(255,255,255,0.1); padding: 8px 12px; border-radius: 6px; background: rgba(0,0,0,0.2);";
    
    // Label and description
    const labelRow = document.createElement('div');
    labelRow.innerHTML = `<label style="margin:0; color:var(--text); font-weight: 500;">${key}</label>
                          <div style="font-size:0.75rem; color:var(--flows-muted);">${desc}</div>`;
    fieldWrap.appendChild(labelRow);
    
    // Base ID for mapping
    const elId = 'dyn_fld_' + key;
    
    // Determine the type of UI to show
    
    if (descLower.includes('bool')) {
      // Toggle Switch
      const tgglWrap = document.createElement('div');
      tgglWrap.style = "display:flex; align-items:center; gap: 10px; margin-top: 5px;";
      
      const switchLbl = document.createElement('label');
      switchLbl.className = 'switch-small';
      const chk = document.createElement('input');
      chk.type = 'checkbox';
      chk.id = elId;
      if (val === true || val === 'true') chk.checked = true;
      else if (val === undefined && descLower.includes('default true')) chk.checked = true;
      chk.onchange = syncYamlFromDynamicForm;
      
      const thumb = document.createElement('span');
      thumb.className = 'slider-small round';
      switchLbl.appendChild(chk);
      switchLbl.appendChild(thumb);
      
      tgglWrap.appendChild(switchLbl);
      fieldWrap.appendChild(tgglWrap);
      
    } else if (key === 'sound' || descLower.includes('sound file')) {
      // File Picker specific to sounds
      const flex = document.createElement('div');
      flex.style = "display:flex; gap: 8px; margin-top: 5px;";
      
      const inp = document.createElement('select');
      inp.id = elId;
      inp.style.flex = "1";
      inp.onchange = syncYamlFromDynamicForm;
      
      const loadingOpt = document.createElement('option');
      loadingOpt.text = "Loading sounds...";
      inp.appendChild(loadingOpt);
      
      fetch('/api/system/explorer/ls', {
         method: 'POST',
         body: JSON.stringify({ path: 'C:\\Hecos\\hecos\\assets\\sounds' })
      }).then(r => r.json()).then(data => {
         inp.innerHTML = '';
         const emptyOpt = document.createElement('option');
         emptyOpt.value = '';
         emptyOpt.text = '-- Select a sound --';
         inp.appendChild(emptyOpt);
         
         if(data.ok && data.entries) {
            data.entries.forEach(e => {
               if(e.type === 'file' && e.name.match(/\.(wav|mp3|ogg)$/i)) {
                  const opt = document.createElement('option');
                  opt.value = e.name;
                  opt.text = e.name;
                  inp.appendChild(opt);
               }
            });
         }
         
         if(val !== undefined) {
             inp.value = val;
             if(inp.value !== val) {
                 const customOpt = document.createElement('option');
                 customOpt.value = val;
                 customOpt.text = val;
                 inp.appendChild(customOpt);
                 inp.value = val;
             }
         }
      }).catch(e => {
         console.error('Failed to load sounds:', e);
         loadingOpt.text = "Failed to load sounds";
      });
      
      const btn = document.createElement('button');
      btn.className = 'tb-btn';
      btn.type = 'button';
      btn.innerHTML = '<i class="fas fa-folder-open"></i> Browse';
      btn.onclick = async () => {
         try {
            btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
            const res = await fetch("/api/system/explorer/pick-native", {
               method: "POST",
               body: JSON.stringify({
                  title: "Hecos — Select Sound File",
                  initialdir: "C:\\Hecos\\hecos\\assets\\sounds",
                  filetypes: [["Audio Files", "*.wav *.mp3 *.ogg"], ["All Files", "*.*"]]
               })
            });
            const data = await res.json();
            if (data.ok && data.path) {
               let base = data.path.split('\\\\').pop().split('/').pop();
               let exists = Array.from(inp.options).some(o => o.value === base);
               if(!exists) {
                   const customOpt = document.createElement('option');
                   customOpt.value = base;
                   customOpt.text = base;
                   inp.appendChild(customOpt);
               }
               inp.value = base;
               syncYamlFromDynamicForm();
            }
         } catch(e) {
            console.error("Native pick error:", e);
         } finally {
            btn.innerHTML = '<i class="fas fa-folder-open"></i> Browse';
         }
      };
      
      const playBtn = document.createElement('button');
      playBtn.className = 'tb-btn';
      playBtn.type = 'button';
      playBtn.style.padding = '0 10px';
      playBtn.title = 'Preview Audio';
      playBtn.innerHTML = '<i class="fas fa-play"></i>';
      playBtn.onclick = () => {
         if(!inp.value) return;
         const audio = new Audio('/assets/sounds/' + inp.value);
         audio.play().catch(e => console.warn("Failed to play preview:", e));
      };
      
      flex.appendChild(inp);
      flex.appendChild(playBtn);
      flex.appendChild(btn);
      fieldWrap.appendChild(flex);

    } else if (descLower.includes('int') || descLower.includes('float') || descLower.includes('time') || descLower.includes('seconds') || descLower.includes('temperature')) {
      // Range slider + number input
      const flex = document.createElement('div');
      flex.style = "display:flex; gap: 10px; align-items:center; margin-top: 5px;";
      
      const sld = document.createElement('input');
      sld.type = 'range';
      sld.id = elId + '_range';
      sld.style.flex = "1";
      sld.style.accentColor = 'var(--accent)';
      
      // Determine step/max
      if (descLower.includes('float') || descLower.includes('temperature')) {
          sld.min = 0; sld.max = 2; sld.step = 0.1;
      } else if (descLower.includes('seconds')) {
          sld.min = 0; sld.max = 300; sld.step = 1;
      } else {
          sld.min = 0; sld.max = 100; sld.step = 1;
      }
      
      const num = document.createElement('input');
      num.type = 'number';
      num.id = elId;
      num.style.width = "80px";
      
      const parsedVal = parseFloat(val);
      if (!isNaN(parsedVal)) {
          sld.value = parsedVal;
          num.value = parsedVal;
      }
      
      sld.oninput = (e) => { num.value = e.target.value; syncYamlFromDynamicForm(); };
      num.oninput = (e) => { sld.value = e.target.value; syncYamlFromDynamicForm(); };
      
      flex.appendChild(sld);
      flex.appendChild(num);
      fieldWrap.appendChild(flex);
      
    } else if (descLower.includes('dict') || descLower.includes('action + params') || descLower.includes('action to run') || descLower.includes('action definition') || key === 'true_branch' || key === 'false_branch' || key === 'on_success' || key === 'on_fail' || key === 'body' || key === 'branches' || key === 'default') {
      // Nested dict/action parameter — render as a YAML textarea
      const ta = document.createElement('textarea');
      ta.id = elId;
      ta.rows = 5;
      ta.style = "margin-top: 5px; width: 100%; font-family: monospace; font-size: 0.82rem; resize: vertical; background: rgba(0,0,0,0.3); color: var(--text); border: 1px solid rgba(255,255,255,0.15); border-radius: 4px; padding: 6px;";
      ta.placeholder = 'action: AUDIO__speak\nparams:\n  text: \'{{ variabile }}\'\n';
      if (val !== undefined && val !== null) {
        try {
          ta.value = typeof val === 'object' ? jsyaml.dump(val).trimEnd() : String(val);
        } catch(e) { ta.value = String(val); }
      }
      ta.oninput = syncYamlFromDynamicForm;
      fieldWrap.appendChild(ta);
    } else if (key === 'condition' && actionName === 'LOGIC__if_else') {
      // ── Logic Builder ───────────────────────────────────────────────────────
      const builderWrap = document.createElement('div');
      builderWrap.style = 'display:flex; flex-direction:column; gap:8px; margin-top:5px;';

      // Row 1: Dropdowns for structured building
      const row = document.createElement('div');
      row.style = 'display:flex; gap:6px; flex-wrap:wrap; align-items:center;';

      const availVars = getAvailableVariables();

      // Variabile dropdown
      const selVar = document.createElement('select');
      selVar.id = 'logic_var';
      selVar.style = 'flex:2; min-width:100px;';
      const emptyVarOpt = document.createElement('option');
      emptyVarOpt.value = ''; emptyVarOpt.textContent = '— variabile —';
      selVar.appendChild(emptyVarOpt);
      // also option for manual entry
      if (availVars.length === 0) {
        const hint = document.createElement('option');
        hint.value = ''; hint.textContent = '(nessuna variabile trovata)';
        hint.disabled = true;
        selVar.appendChild(hint);
      } else {
        availVars.forEach(v => {
          const o = document.createElement('option');
          o.value = v; o.textContent = v;
          selVar.appendChild(o);
        });
      }

      // Tipo (cast) dropdown
      const selType = document.createElement('select');
      selType.id = 'logic_type';
      selType.style = 'flex:1; min-width:80px;';
      [['', 'as-is'], ['| int', 'intero'], ['| float', 'decimale'], ['| lower', 'testo']].forEach(([v,l]) => {
        const o = document.createElement('option'); o.value = v; o.textContent = l;
        selType.appendChild(o);
      });

      // Operatore dropdown
      const selOp = document.createElement('select');
      selOp.id = 'logic_op';
      selOp.style = 'flex:1; min-width:80px;';
      [['>', '>'], ['<', '<'], ['==', '=='], ['!=', '!='], ['>=', '>='], ['<=', '<='], ['in', 'contiene'], ['not in', 'non contiene']].forEach(([v,l]) => {
        const o = document.createElement('option'); o.value = v; o.textContent = l;
        selOp.appendChild(o);
      });

      // Valore input
      const inpVal = document.createElement('input');
      inpVal.type = 'text';
      inpVal.id = 'logic_cmpval';
      inpVal.placeholder = 'valore...';
      inpVal.style = 'flex:2; min-width:80px;';

      row.appendChild(selVar);
      row.appendChild(selType);
      row.appendChild(selOp);
      row.appendChild(inpVal);
      builderWrap.appendChild(row);

      // Preview / raw expression
      const previewLabel = document.createElement('div');
      previewLabel.style = 'font-size:0.7rem; color:var(--flows-muted); margin-bottom:2px;';
      previewLabel.textContent = 'Espressione generata (modificabile a mano):';
      builderWrap.appendChild(previewLabel);

      const rawInp = document.createElement('input');
      rawInp.type = 'text';
      rawInp.id = elId;
      rawInp.value = val !== undefined ? val : '';
      rawInp.style = 'width:100%; font-family:monospace; font-size:0.88rem; background:rgba(0,212,255,0.05); border:1px solid rgba(0,212,255,0.3); color:var(--text); border-radius:4px; padding:5px 8px; margin-top:2px;';
      rawInp.placeholder = 'es: variabile1 | int > 5';
      rawInp.oninput = syncYamlFromDynamicForm;
      builderWrap.appendChild(rawInp);

      // Wire up builder → raw expression
      function _updateExprFromBuilder() {
        const v = selVar.value;
        const t = selType.value;
        const op = selOp.value;
        const cmp = inpVal.value.trim();
        if (!v) return;
        const varPart = t ? `${v} ${t}` : v;
        // quote string comparisons if type is not int/float
        let cmpPart = cmp;
        if ((t === '' || t === '| lower') && cmp !== '' && isNaN(Number(cmp)) && !cmp.startsWith("'") && !cmp.startsWith('"')) {
          cmpPart = `'${cmp}'`;
        }
        rawInp.value = `${varPart} ${op} ${cmpPart}`;
        syncYamlFromDynamicForm();
      }
      selVar.onchange = _updateExprFromBuilder;
      selType.onchange = _updateExprFromBuilder;
      selOp.onchange = _updateExprFromBuilder;
      inpVal.oninput = _updateExprFromBuilder;

      // Pre-fill dropdowns by parsing existing condition string
      if (val) {
        // Try to parse: 'name | cast op value'
        const m = String(val).trim().match(/^(\S+)(?:\s+(\|\s*\w+))?\s*(>|<|==|!=|>=|<=|in|not in)\s*(.+)$/);
        if (m) {
          selVar.value = m[1].trim() || '';
          selType.value = m[2] ? m[2].trim() : '';
          selOp.value = m[3].trim();
          inpVal.value = m[4].trim().replace(/^['"]|['"]$/g, '');
        }
      }

      fieldWrap.appendChild(builderWrap);
    } else {
      // Normal String input
      const inp = document.createElement('input');
      inp.type = 'text';
      inp.id = elId;
      inp.value = val !== undefined ? val : '';
      inp.style = "margin-top: 5px; width: 100%;";
      inp.oninput = syncYamlFromDynamicForm;
      fieldWrap.appendChild(inp);
    }
    
    container.appendChild(fieldWrap);
  }
}

function syncYamlFromDynamicForm() {
  const actionName = document.getElementById('ne-action').value;
  const schema = getActionSchema(actionName);
  if (!schema || !schema.params) return;
  
  let newObj = {};
  for (const [key, desc] of Object.entries(schema.params)) {
    const elId = 'dyn_fld_' + key;
    const el = document.getElementById(elId);
    if (!el) continue;
    
    if (el.type === 'checkbox') {
        newObj[key] = el.checked;
    } else if (el.type === 'number' || el.tagName.toLowerCase() === 'number') {
        const v = parseFloat(el.value);
        if (!isNaN(v)) newObj[key] = v;
    } else if (el.tagName.toLowerCase() === 'textarea') {
        // Dict/nested YAML param
        const raw = el.value.trim();
        if (raw !== '') {
            try {
                const parsed = jsyaml.load(raw);
                if (parsed !== null && parsed !== undefined) newObj[key] = parsed;
            } catch(e) {
                // Keep as raw string if YAML parse fails
                newObj[key] = raw;
            }
        }
    } else {
        if (el.value.trim() !== '') {
            newObj[key] = el.value.trim();
        }
    }
  }
  
  const yamlArea = document.getElementById('ne-params');
  if (Object.keys(newObj).length > 0) {
      yamlArea.value = jsyaml.dump(newObj);
  } else {
      yamlArea.value = '';
  }
}

function syncDynamicFormFromYaml() {
  buildDynamicForm();
}

