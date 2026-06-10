// ── Flows API Calls ───────────────────────────────────────────────

// ── Sidebar order persistence ─────────────────────────────────────
const FLOWS_ORDER_KEY = 'hecos_flows_order';

function getSavedOrder() {
  try { return JSON.parse(localStorage.getItem(FLOWS_ORDER_KEY)) || []; }
  catch { return []; }
}

function saveOrder(ids) {
  localStorage.setItem(FLOWS_ORDER_KEY, JSON.stringify(ids));
}

function sortFlowsByOrder(flows) {
  const order = getSavedOrder();
  if (!order.length) return flows;
  const ranked = [];
  const remaining = [...flows];
  order.forEach(id => {
    const idx = remaining.findIndex(f => f.id === id);
    if (idx !== -1) ranked.push(remaining.splice(idx, 1)[0]);
  });
  return [...ranked, ...remaining]; // unseen flows go to end
}

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
  
  // Rimuove solo i flow-item per non distruggere l'elemento "empty" dal DOM
  list.querySelectorAll('.flow-item').forEach(el => el.remove());

  if (!flows.length) {
    if(empty) empty.style.display='flex';
    return;
  }
  if(empty) empty.style.display = 'none';

  // Apply saved order
  const sorted = sortFlowsByOrder(flows);

  sorted.forEach(f => {
    const el = document.createElement('div');
    el.className = 'flow-item' + (f.id === currentFlowId ? ' active' : '');
    el.dataset.id = f.id;
    el.draggable = true;
    el.innerHTML = `
      <span class="flow-drag-handle" title="${window.t('flows_drag_to_reorder')}">⠿</span>
      <div class="flow-item-name">
        <span class="flow-status-dot ${f.enabled?'enabled':'disabled'}"></span>
        ${f.name}
      </div>
      <div class="flow-item-meta">
        <span><i class="fas fa-bolt" style="font-size:.6rem"></i> ${f.trigger_type}${f.trigger_expr?' ('+f.trigger_expr+')':''}</span>
        <span>${f.step_count} steps</span>
        <button class="flow-item-del" title="${window.t('flows_delete_flow')}" data-flow-id="${f.id}"><i class="fas fa-trash"></i></button>
      </div>`;
    el.querySelector('.flow-item-del').addEventListener('click', e => {
      e.stopPropagation();
      deleteFlowById(f.id, f.name);
    });
    el.addEventListener('click', e => {
      if (e.target.closest('.flow-drag-handle') || e.target.closest('.flow-item-del')) return;
      selectFlow(f.id);
    });
    list.appendChild(el);
  });

  initSidebarDragSort();
}

// ── Sidebar drag-to-reorder ───────────────────────────────────────
function initSidebarDragSort() {
  const list = document.getElementById('flows-list');
  if (!list) return;

  let dragSrc = null;

  list.querySelectorAll('.flow-item[draggable]').forEach(item => {
    item.addEventListener('dragstart', e => {
      dragSrc = item;
      item.classList.add('dragging');
      e.dataTransfer.effectAllowed = 'move';
      e.dataTransfer.setData('text/plain', item.dataset.id);
    });

    item.addEventListener('dragend', () => {
      item.classList.remove('dragging');
      list.querySelectorAll('.flow-item').forEach(el => {
        el.classList.remove('drag-over-top', 'drag-over-bottom');
      });
      dragSrc = null;
      // Save the new order
      const ids = [...list.querySelectorAll('.flow-item[data-id]')].map(el => el.dataset.id);
      saveOrder(ids);
    });

    item.addEventListener('dragover', e => {
      e.preventDefault();
      if (!dragSrc || dragSrc === item) return;
      e.dataTransfer.dropEffect = 'move';
      list.querySelectorAll('.flow-item').forEach(el => {
        el.classList.remove('drag-over-top', 'drag-over-bottom');
      });
      const rect = item.getBoundingClientRect();
      const mid  = rect.top + rect.height / 2;
      if (e.clientY < mid) {
        item.classList.add('drag-over-top');
      } else {
        item.classList.add('drag-over-bottom');
      }
    });

    item.addEventListener('dragleave', () => {
      item.classList.remove('drag-over-top', 'drag-over-bottom');
    });

    item.addEventListener('drop', e => {
      e.preventDefault();
      if (!dragSrc || dragSrc === item) return;
      const rect = item.getBoundingClientRect();
      const mid  = rect.top + rect.height / 2;
      if (e.clientY < mid) {
        list.insertBefore(dragSrc, item);
      } else {
        item.after(dragSrc);
      }
      item.classList.remove('drag-over-top', 'drag-over-bottom');
    });
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

    ['btn-run','btn-save','btn-delete','btn-palette','btn-export'].forEach(id => {
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

async function saveCurrentFlow(silent = false) {
  if (!currentFlowId && (!cmEditor || !cmEditor.getValue().trim())) return;
  // Always sync canvas → YAML before reading cmEditor, regardless of active tab.
  // This is the ONLY place where canvas positions are flushed to disk.
  if (typeof syncCanvasToYaml === 'function') {
    syncCanvasToYaml(); 
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
          if (!silent) toast('info', 'Auto-corrected duplicate step IDs.');
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
      if (!silent) {
        const errs = d.errors || [d.error || 'Unknown error'];
        toast('error', '❌ Save failed:\n' + errs.map((e,i) => `${i+1}. ${e}`).join('\n'));
      }
      console.warn('[Flows] Save validation errors:', d.errors || d.error);
      return;
    }
    if (!silent) {
      toast('ok','✓ Synced');
      loadFlowsList();
    }
    currentFlowId = d.flow_id;
  } catch(e) { 
    if (!silent) toast('error','Save failed: '+e.message); 
  }
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
  await saveCurrentFlow(true); // Ensure latest changes are saved before running

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
  if (!currentFlowId) { toast('info', window.t('flows_select_first')); return; }
  await deleteFlowById(currentFlowId, currentFlowData?.name || currentFlowId);
}

async function deleteFlowById(flowId, flowName) {
  const bg = document.getElementById('confirm-modal-bg');
  const text = document.getElementById('confirm-modal-text');
  const yesBtn = document.getElementById('confirm-modal-yes');
  
  if(bg && text && yesBtn) {
    text.innerText = window.t('flows_confirm_delete_text').replace('{name}', flowName);
    bg.style.display = 'flex';
    yesBtn.onclick = async () => {
      bg.style.display = 'none';
      await _doDeleteFlowById(flowId);
    };
  } else {
    if (!confirm(window.t('flows_confirm_delete_text').replace('{name}', flowName))) return;
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
      ['btn-run','btn-save','btn-delete','btn-export'].forEach(id => {
        const btn = document.getElementById(id);
        if (btn) btn.disabled=true;
      });
      if (typeof renderTimeline === 'function') renderTimeline(null);
    }

    toast('ok', window.t('flows_deleted_toast'));
    loadFlowsList();
  } catch(e) { toast('error', window.t('flows_delete_failed_toast').replace('{error}', e.message)); }
}

// ── Export / Import ──────────────────────────────────────────────

/**
 * Inject the Hecos flow type marker into a YAML string.
 * Adds \`_type: hecos_flow\` after the first line (or at top if missing).
 */
function _injectFlowTypeMarker(yaml) {
  if (yaml.includes('_type: hecos_flow')) return yaml;
  // Insert after first non-empty line
  const lines = yaml.split('\n');
  const insertAt = lines.findIndex(l => l.trim() !== '');
  if (insertAt === -1) return '_type: hecos_flow\n' + yaml;
  lines.splice(insertAt + 1, 0, '_type: hecos_flow');
  return lines.join('\n');
}

/**
 * Export the current flow as a .heflow file.
 * Uses the native OS Save-As dialog (File System Access API) when available,
 * falling back to a standard browser download.
 * The exported file is a YAML with an injected \`_type: hecos_flow\` marker
 * so it can be reliably distinguished from generic YAML files.
 */
async function exportCurrentFlow() {
  if (!currentFlowId && (!cmEditor || !cmEditor.getValue().trim())) {
    toast('info', window.t('flows_export_select_first'));
    return;
  }
  const rawYaml = cmEditor ? cmEditor.getValue() : '';
  if (!rawYaml.trim()) { toast('error', window.t('flows_export_empty')); return; }

  // Inject type marker so the file is self-identifying
  const yamlToSave = _injectFlowTypeMarker(rawYaml);

  // Suggested filename: <flow_id>.heflow
  const suggestedName = (currentFlowId || 'flow_export') + '.heflow';

  // ── Strategy 1: native OS Save-As dialog (Chrome/Edge) ───────────────
  if (typeof window.showSaveFilePicker === 'function') {
    try {
      const fileHandle = await window.showSaveFilePicker({
        suggestedName,
        types: [{
          description: 'Hecos Flow File',
          accept: { 'text/plain': ['.heflow'] },
        }],
      });
      const writable = await fileHandle.createWritable();
      await writable.write(yamlToSave);
      await writable.close();
      toast('ok', window.t('flows_export_saved').replace('{name}', fileHandle.name));
      return;
    } catch (err) {
      // User cancelled the dialog — do nothing
      if (err.name === 'AbortError') return;
      // Unexpected error — fall through to download fallback
      console.warn('[Flows] showSaveFilePicker failed, falling back to download:', err);
    }
  }

  // ── Strategy 2: standard browser download (fallback) ───────────────
  const blob = new Blob([yamlToSave], { type: 'text/plain' });
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement('a');
  a.href     = url;
  a.download = suggestedName;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
  toast('ok', window.t('flows_export_done').replace('{name}', suggestedName));
}

/**
 * Import a .heflow (or .yaml) file from disk into the YAML editor.
 * Validates that the file is a genuine Hecos flow before loading.
 * Fires after the user picks a file from the hidden <input type="file">.
 * Does NOT auto-save — the user must click Save after review.
 */
function importFlowFromFile(inputEl) {
  const file = inputEl.files[0];
  if (!file) return;
  inputEl.value = '';

  const reader = new FileReader();
  reader.onload = e => {
    const yaml = e.target.result;
    if (!yaml || !yaml.trim()) {
      toast('error', window.t('flows_import_empty_file'));
      return;
    }

    // ── Validation: is this actually a Hecos flow? ──────────────────
    const isHeflowExt = file.name.toLowerCase().endsWith('.heflow');
    let parsed = null;
    try {
      if (typeof jsyaml !== 'undefined') parsed = jsyaml.load(yaml);
    } catch(parseErr) {
      toast('error', window.t('flows_import_yaml_invalid').replace('{error}', parseErr.message));
      return;
    }

    // Must have either .heflow extension OR _type marker OR pipeline field
    const hasTypeMarker = parsed && parsed._type === 'hecos_flow';
    const hasPipeline   = parsed && Array.isArray(parsed.pipeline);
    if (!isHeflowExt && !hasTypeMarker && !hasPipeline) {
      toast('error', window.t('flows_import_invalid_file'));
      return;
    }

    // ── Extract name / id ───────────────────────────────────────
    let flowName = file.name.replace(/\.(heflow|ya?ml)$/i, '');
    let flowId   = flowName;
    if (parsed) {
      if (parsed.name) flowName = parsed.name;
      if (parsed.id)   flowId   = parsed.id;
    }

    // Load into editor
    if (cmEditor) cmEditor.setValue(yaml);
    currentFlowId   = flowId;
    currentFlowData = null;

    // Update toolbar
    const tlInput = document.getElementById('flow-title');
    if (tlInput) { tlInput.value = flowName; tlInput.disabled = false; }
    ['btn-save','btn-export'].forEach(id => {
      const btn = document.getElementById(id);
      if (btn) btn.disabled = false;
    });
    ['btn-run','btn-delete'].forEach(id => {
      const btn = document.getElementById(id);
      if (btn) btn.disabled = true;
    });

    // Mark in sidebar
    const _list = document.getElementById('flows-list');
    if (_list) {
      _list.querySelectorAll('.flow-item').forEach(el => el.classList.remove('active'));
      const existing = _list.querySelector(`.flow-item[data-id="${CSS.escape(flowId)}"]`);
      if (existing) {
        existing.classList.add('active');
      } else {
        const prev = _list.querySelector('.flow-item-unsaved');
        if (prev) prev.remove();
        const newEl = document.createElement('div');
        newEl.className = 'flow-item active flow-item-unsaved';
        newEl.innerHTML = `
          <span class="flow-drag-handle">⠿</span>
          <div class="flow-item-name">
            <span class="flow-status-dot disabled"></span>
            ↑ ${flowName} <em style="font-size:.7rem;opacity:.6">(imported)</em>
          </div>
          <div class="flow-item-meta"><span>manual</span><span>—</span></div>`;
        _list.prepend(newEl);
      }
    }

    const stepCount = hasPipeline ? parsed.pipeline.length : '?';
    toast('ok', window.t('flows_import_done').replace('{name}', flowName).replace('{count}', stepCount));
    const yamlTabBtn = document.querySelector('.tab-btn[data-tab="yaml"]');
    if (yamlTabBtn) yamlTabBtn.click();
  };
  reader.onerror = () => toast('error', window.t('flows_import_read_error'));
  reader.readAsText(file);
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

// ── Autosave Interval ─────────────────────────────────────────────
let autosaveTimer = null;

async function initFlowsAutosave() {
  try {
    const res = await fetch('/hecos/config');
    const cfg = await res.json();
    const flowsCfg = cfg?.plugins?.FLOWS || {};
    // Default: autosave enabled every 1 minute unless config says otherwise
    const enabled = flowsCfg.autosave_enabled !== false; // true by default
    const intervalMinutes = flowsCfg.autosave_interval_minutes || 1;
    if (enabled) {
      const ms = intervalMinutes * 60000;
      autosaveTimer = setInterval(() => {
        const saveBtn = document.getElementById('btn-save');
        if (currentFlowId && saveBtn && !saveBtn.disabled) {
          saveCurrentFlow(true);
        }
      }, ms);
      console.log(`[Flows] Autosave enabled: every ${intervalMinutes} min`);
    } else {
      console.log('[Flows] Autosave disabled by config.');
    }
  } catch(e) {
    console.warn('[Flows] Could not init autosave', e);
    // Fallback: enable autosave every 1 min even if config fetch fails
    autosaveTimer = setInterval(() => {
      const saveBtn = document.getElementById('btn-save');
      if (currentFlowId && saveBtn && !saveBtn.disabled) {
        saveCurrentFlow(true);
      }
    }, 60000);
  }
}

document.addEventListener('DOMContentLoaded', () => {
  setTimeout(initFlowsAutosave, 1000);
});
