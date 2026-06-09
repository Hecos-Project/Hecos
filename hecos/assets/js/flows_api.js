// ── Flows API Calls ───────────────────────────────────────────────

async function loadFlowsList() {
  try {
    const res = await fetch('/api/flows/list');
    const d = await res.json();
    if (!d.ok) throw new Error(d.error);
    renderSidebar(d.flows);
  } catch(e) { toast('error','Could not load flows: '+e.message); }
}

function renderSidebar(flows) {
  const list = document.getElementById('flows-list');
  const empty = document.getElementById('flows-sidebar-empty');
  if(!list) return;
  list.innerHTML = '';
  if (!flows.length) { 
      if(empty) empty.style.display='flex'; 
      list.appendChild(empty);
      return; 
  }
  if(empty) empty.style.display = 'none';
  flows.forEach(f => {
    const el = document.createElement('div');
    el.className = 'flow-item' + (f.id === currentFlowId ? ' active' : '');
    el.dataset.id = f.id;
    el.innerHTML = `
      <div class="flow-item-name">
        <span class="flow-status-dot ${f.enabled?'enabled':'disabled'}"></span>
        ${f.name}
      </div>
      <div class="flow-item-meta">
        <span><i class="fas fa-bolt" style="font-size:.6rem"></i> ${f.trigger_type}${f.trigger_expr?' ('+f.trigger_expr+')':''}</span>
        <span>${f.step_count} steps</span>
        <button class="flow-item-del" title="Elimina flusso" data-flow-id="${f.id}"><i class="fas fa-trash"></i></button>
      </div>`;
    el.querySelector('.flow-item-del').addEventListener('click', e => {
      e.stopPropagation();
      deleteFlowById(f.id, f.name);
    });
    el.addEventListener('click', () => selectFlow(f.id));
    list.appendChild(el);
  });
}

async function selectFlow(flowId) {
  try {
    const res = await fetch(`/api/flows/${flowId}`);
    const d = await res.json();
    if (!d.ok) throw new Error(d.error);
    currentFlowId = flowId;
    currentFlowData = d.flow;

    // Update sidebar selection
    document.querySelectorAll('.flow-item').forEach(el => {
      el.classList.toggle('active', el.dataset.id === flowId);
    });

    // Populate toolbar
    const tlInput = document.getElementById('flow-title');
    if (tlInput) tlInput.value = d.flow.name || flowId;
    
    ['btn-run','btn-save','btn-delete','btn-palette'].forEach(id => {
      const btn = document.getElementById(id);
      if (btn) btn.disabled = false;
    });

    // Set YAML editor
    if (cmEditor) cmEditor.setValue(d.yaml || '');

    // Render canvas nodes via ReactFlow bridge (flows_canvas_shim.js)
    if (typeof renderCanvasFromFlow === 'function') renderCanvasFromFlow(d.flow);

    // Render timeline (from flows_canvas_shim.js)
    if (typeof renderTimeline === 'function') renderTimeline(d.flow);

    // Sync run button state from backend
    try {
      const sres = await fetch(`/api/flows/${flowId}/status`);
      const sd = await sres.json();
      if (sd.ok && sd.running) setRunningState(true, sd.run_id);
      else setRunningState(false);
    } catch { setRunningState(false); }

  } catch(e) { toast('error','Could not load flow: '+e.message); }
}

async function saveCurrentFlow() {
  if (!currentFlowId && (!cmEditor || !cmEditor.getValue().trim())) return;
  if (typeof syncCanvasToYaml === 'function' && document.getElementById('tab-canvas').classList.contains('active')) {
    syncCanvasToYaml(); // Sync canvas to YAML before reading the value if we're on the canvas tab
  }
  let yaml = cmEditor.getValue();

  // Auto-deduplicate step IDs
  if (typeof jsyaml !== 'undefined') {
    try {
      const flowObj = jsyaml.load(yaml);
      if (flowObj && Array.isArray(flowObj.pipeline)) {
        let changed = false;
        let seen = new Set();
        flowObj.pipeline.forEach((step, idx) => {
          if (!step.id) { step.id = 'step_' + idx; changed = true; }
          if (seen.has(step.id)) {
            let baseId = String(step.id).replace(/(_copy\d*|\s\(\d+\)|\s\d+)$/, '').trim();
            let count = 1;
            let newId = baseId + ' ' + count;
            while(seen.has(newId)) { count++; newId = baseId + ' ' + count; }
            step.id = newId;
            changed = true;
          }
          seen.add(step.id);
        });
        if (changed) {
          yaml = jsyaml.dump(flowObj, { indent: 2, lineWidth: -1 });
          const scrollInfo = cmEditor.getScrollInfo();
          cmEditor.setValue(yaml);
          cmEditor.scrollTo(scrollInfo.left, scrollInfo.top);
          if (typeof renderCanvasFromFlow === 'function') renderCanvasFromFlow(flowObj);
          toast('info', 'Auto-corrected duplicate step IDs.');
        }
      }
    } catch(e) { console.warn("Deduplication error:", e); }
  }
  try {
    const res = await fetch('/api/flows/save', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({yaml})
    });
    const d = await res.json();
    if (!d.ok) {
      // Show each validation error on its own line for clarity
      const errs = d.errors || [d.error || 'Unknown error'];
      toast('error', '❌ Save failed:\n' + errs.map((e,i) => `${i+1}. ${e}`).join('\n'));
      // Also log details to console for debugging
      console.warn('[Flows] Save validation errors:', errs);
      return;
    }
    toast('ok','Flow saved ✓');
    currentFlowId = d.flow_id;
    loadFlowsList();
  } catch(e) { toast('error','Save failed: '+e.message); }
}

// ── Run state helpers ────────────────────────────────────────────
let _currentRunId = null;

function setRunningState(running, runId) {
  _currentRunId = running ? runId : null;
  const btn = document.getElementById('btn-run');
  if (!btn) return;
  if (running) {
    btn.classList.add('running');
    btn.innerHTML = '<i class="fas fa-stop-circle"></i> Stop';
    btn.title = 'Click to stop the running flow';
  } else {
    btn.classList.remove('running');
    btn.innerHTML = '<i class="fas fa-play"></i> Run';
    btn.title = 'Execute this flow';
  }
}

async function runCurrentFlow() {
  if (!currentFlowId) return;

  // If already running — act as STOP
  if (_currentRunId) {
    try {
      const res = await fetch(`/api/flows/${currentFlowId}/stop`, { method: 'POST' });
      const d = await res.json();
      if (d.ok) {
        toast('info', '⏹ Stop signal sent — flow will halt after current step.');
      } else {
        toast('error', 'Could not stop: ' + (d.error || 'unknown'));
      }
    } catch(e) { toast('error', 'Stop failed: ' + e.message); }
    return;
  }

  try {
    const res = await fetch(`/api/flows/${currentFlowId}/run`, { method: 'POST' });
    const d = await res.json();

    // 409 = already running
    if (res.status === 409) {
      toast('info', '⚠️ Flow is already running (run: ' + d.run_id + ')');
      // Reconnect to existing stream
      setRunningState(true, d.run_id);
      const logTabBtn = document.querySelector('.tab-btn[data-tab="log"]');
      if (logTabBtn) logTabBtn.click();
      if (typeof startLogStream === 'function') startLogStream(d.run_id);
      return;
    }

    if (!d.ok) throw new Error(d.error);

    setRunningState(true, d.run_id);
    toast('info', `▶ Flow started (run: ${d.run_id})`);

    // Switch to log tab
    const logTabBtn = document.querySelector('.tab-btn[data-tab="log"]');
    if (logTabBtn) logTabBtn.click();

    if (typeof startLogStream === 'function') startLogStream(d.run_id, () => setRunningState(false));
  } catch(e) { toast('error', 'Run failed: ' + e.message); }
}

async function deleteCurrentFlow() {
  if (!currentFlowId) { toast('info','Seleziona prima un flusso.'); return; }
  await deleteFlowById(currentFlowId, currentFlowData?.name || currentFlowId);
}

async function deleteFlowById(flowId, flowName) {
  const bg = document.getElementById('confirm-modal-bg');
  const text = document.getElementById('confirm-modal-text');
  const yesBtn = document.getElementById('confirm-modal-yes');
  
  if(bg && text && yesBtn) {
    text.innerText = `Eliminare il flusso "${flowName}"?`;
    bg.style.display = 'flex';
    yesBtn.onclick = async () => {
      bg.style.display = 'none';
      await _doDeleteFlowById(flowId);
    };
  } else {
    if (!confirm(`Eliminare il flusso "${flowName}"?`)) return;
    await _doDeleteFlowById(flowId);
  }
}

async function _doDeleteFlowById(flowId) {
  try {
    const res = await fetch(`/api/flows/${flowId}`, {method:'DELETE'});
    const d = await res.json();
    if (!d.ok) throw new Error(d.error);

    if (currentFlowId === flowId) {
      currentFlowId = null;
      currentFlowData = null;
      if (cmEditor) cmEditor.setValue('');
      // Clear ReactFlow canvas via bridge
      if (typeof renderCanvasFromFlow === 'function') renderCanvasFromFlow({ pipeline: [] });
      const tlInput = document.getElementById('flow-title');
      if (tlInput) tlInput.value='';
      ['btn-run','btn-save','btn-delete'].forEach(id => {
        const btn = document.getElementById(id);
        if (btn) btn.disabled=true;
      });
      if (typeof renderTimeline === 'function') renderTimeline(null);
    }

    toast('ok','Flusso eliminato.');
    loadFlowsList();
  } catch(e) { toast('error','Eliminazione fallita: '+e.message); }
}

// ── Manual Flow Creation ──────────────────────────────────────────

function newEmptyCanvas() {
  currentFlowId = 'new_flow_' + Date.now().toString(36);
  currentFlowData = { name: 'New Flow', trigger: { type: 'manual' }, pipeline: [] };
  
  const tlInput = document.getElementById('flow-title');
  if (tlInput) {
    tlInput.value = 'New Flow';
    tlInput.disabled = false;
  }
  
  if (typeof renderCanvasFromFlow === 'function') renderCanvasFromFlow(currentFlowData);
  if (cmEditor) cmEditor.setValue(`id: ${currentFlowId}\nname: New Flow\ntrigger:\n  type: manual\npipeline: []`);
  
  // Add a temporary unsaved entry to the sidebar so the new flow is visible
  document.querySelectorAll('.flow-item').forEach(el => el.classList.remove('active'));
  const _list = document.getElementById('flows-list');
  const _emptyHint = document.getElementById('flows-sidebar-empty');
  if (_emptyHint) _emptyHint.style.display = 'none';
  if (_list) {
    const prev = _list.querySelector('.flow-item-unsaved');
    if (prev) prev.remove();
    const newEl = document.createElement('div');
    newEl.className = 'flow-item active flow-item-unsaved';
    newEl.innerHTML = `
      <div class="flow-item-name">
        <span class="flow-status-dot disabled"></span>
        ✦ New Flow <em style="font-size:.7rem;opacity:.6">(unsaved)</em>
      </div>
      <div class="flow-item-meta"><span><i class="fas fa-bolt" style="font-size:.6rem"></i> manual</span><span>0 steps</span></div>`;
    _list.prepend(newEl);
  }
  
  // Enable save and palette, disable run/delete for now
  ['btn-save', 'btn-palette'].forEach(id => {
    const btn = document.getElementById(id);
    if (btn) btn.disabled = false;
  });
  ['btn-run', 'btn-delete'].forEach(id => {
    const btn = document.getElementById(id);
    if (btn) btn.disabled = true;
  });
  
  if (typeof renderTimeline === 'function') renderTimeline(currentFlowData);
}

