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
  if (Array.isArray(deps)) deps = deps.join(', ');
  document.getElementById('ne-depends').value = deps;
  
  // Rebuild the dynamic form based on the selected action schema
  buildDynamicForm();
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
  _editingNode.properties = {
    action: action,
    params: Object.keys(parsedObj).length ? JSON.stringify(parsedObj) : '{}',
    output_as: outputAs,
    depends_on: dependsStr ? dependsStr.split(',').map(s=>s.trim()).filter(s=>s) : []
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

