// ── SSE Log stream ────────────────────────────────────────────────
function startLogStream(runId, onDone) {
  if (sseSource) sseSource.close();
  const log = document.getElementById('log-output');
  if (!log) return;
  log.innerHTML = '';
  const status = document.getElementById('log-status');
  if (status) status.textContent = `Run: ${runId}`;

  sseSource = new EventSource(`/api/flows/${currentFlowId}/log/stream?run_id=${runId}`);
  sseSource.onmessage = e => {
    const ev = JSON.parse(e.data);
    appendLog(ev);
    if (ev.type === 'stream_end') { 
      sseSource.close();
      if (status) status.textContent = 'Done';
      if (typeof onDone === 'function') onDone();
    }
  };
  sseSource.onerror = () => { 
    if (status) status.textContent = 'Stream ended'; 
    sseSource.close();
    if (typeof onDone === 'function') onDone();
  };
}

function appendLog(ev) {
  const log = document.getElementById('log-output');
  if (!log) return;
  const empty = log.querySelector('.log-empty');
  if (empty) empty.remove();

  let cls='info', icon='fa-circle', text='';
  const ts = ev.ts ? ev.ts.slice(11,19) : '';
  
  if (ev.type==='flow_start')    { cls='start'; icon='fa-play-circle';   text=`▶ Flow started: ${ev.flow_id}`;
    if (typeof resetNodeStates === 'function') resetNodeStates();
  }
  else if (ev.type==='flow_done')    { cls='ok';    icon='fa-check-circle';  text=`✅ Flow completed`; }
  else if (ev.type==='flow_aborted') { cls='abort';  icon='fa-ban';           text=`⛔ Flow aborted by user`;
    if (typeof resetNodeStates === 'function') resetNodeStates();
  }
  else if (ev.type==='flow_error')   { cls='error';  icon='fa-times-circle';  text=`❌ Flow error: ${ev.error}`; }
  else if (ev.type==='step_start')   { cls='info';   icon='fa-cog';           text=`  → ${ev.step_id} (${ev.action})`;
    if (typeof setNodeState === 'function') setNodeState(ev.step_id, 'running');
  }
  else if (ev.type==='step_ok')      { cls='ok';     icon='fa-check';         text=`  ✓ ${ev.step_id}${ev.output?' → '+ev.output.slice(0,80):''}`.trim();
    if (typeof setNodeState === 'function') setNodeState(ev.step_id, 'done');
  }
  else if (ev.type==='step_error')   { cls='error';  icon='fa-exclamation';   text=`  ✗ ${ev.step_id}: ${ev.error}`;
    if (typeof setNodeState === 'function') setNodeState(ev.step_id, 'error');
  }
  else if (ev.type==='connected')    { cls='info';   icon='fa-link';          text=`Connected to run ${ev.run_id}`; }
  else if (ev.type==='toast')        {
    if (typeof window.toast === 'function') window.toast(ev.level || 'info', ev.message);
    return;
  }
  else if (ev.type==='step_waiting_input') {
    if (typeof window.toast === 'function') window.toast('info', '⏳ Flow is waiting for your input...');
    
    const line = document.createElement('div');
    line.className = `log-line info`;
    line.innerHTML = `<span class="ts">${ts}</span><span class="evt"><i class="fas fa-microphone"></i> <strong>Waiting for input:</strong> ${ev.prompt}</span>`;
    
    const inputDiv = document.createElement('div');
    inputDiv.style.padding = '8px';
    inputDiv.style.marginTop = '4px';
    inputDiv.style.background = 'rgba(0,0,0,0.2)';
    inputDiv.style.borderRadius = '4px';
    inputDiv.style.display = 'flex';
    inputDiv.style.gap = '8px';
    
    const inputField = document.createElement('input');
    inputField.type = 'text';
    inputField.placeholder = ev.intercept_mode === 'explicit' ? 'Type @flow [your answer]' : 'Type your answer...';
    inputField.style.flex = '1';
    inputField.style.background = 'rgba(255,255,255,0.05)';
    inputField.style.border = '1px solid rgba(255,255,255,0.1)';
    inputField.style.color = '#fff';
    inputField.style.padding = '6px 10px';
    inputField.style.borderRadius = '4px';
    
    const btn = document.createElement('button');
    btn.textContent = 'Send';
    btn.className = 'hc-btn primary';
    btn.style.padding = '4px 12px';
    
    const submit = () => {
      let text = inputField.value.trim();
      if (!text) return;
      if (ev.intercept_mode === 'explicit' && !text.toLowerCase().startsWith('@flow ')) {
        text = '@flow ' + text;
      }
      btn.disabled = true;
      inputField.disabled = true;
      fetch(`/api/flows/run/${ev.run_id}/input`, {
        method: 'POST',
        body: JSON.stringify({ text })
      }).then(r => r.json()).then(d => {
        if (!d.ok && typeof window.toast === 'function') window.toast('error', d.error);
        else {
          btn.textContent = 'Sent';
          btn.style.background = 'var(--flows-ok)';
        }
      });
    };
    
    btn.onclick = submit;
    inputField.onkeydown = e => { if (e.key === 'Enter') submit(); };
    
    inputDiv.appendChild(inputField);
    inputDiv.appendChild(btn);
    line.appendChild(inputDiv);
    
    log.appendChild(line);
    log.scrollTop = log.scrollHeight;
    
    // Auto focus the input field
    setTimeout(() => inputField.focus(), 100);
    return;
  }
  else return;

  const line = document.createElement('div');
  line.className = `log-line ${cls}`;
  line.innerHTML = `<span class="ts">${ts}</span><span class="evt"><i class="fas ${icon}"></i> ${text}</span>`;
  log.appendChild(line);
  log.scrollTop = log.scrollHeight;
}

function clearLog() {
  const log = document.getElementById('log-output');
  if (log) log.innerHTML = '<div class="log-empty">Log cleared.</div>';
}
