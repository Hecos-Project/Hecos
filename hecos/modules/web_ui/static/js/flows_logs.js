// ── SSE Log stream ────────────────────────────────────────────────
function startLogStream(runId) {
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
    }
  };
  sseSource.onerror = () => { 
    if (status) status.textContent = 'Stream ended'; 
    sseSource.close(); 
  };
}

function appendLog(ev) {
  const log = document.getElementById('log-output');
  if (!log) return;
  const empty = log.querySelector('.log-empty');
  if (empty) empty.remove();

  let cls='info', icon='fa-circle', text='';
  const ts = ev.ts ? ev.ts.slice(11,19) : '';
  
  if (ev.type==='flow_start')  { cls='start'; icon='fa-play-circle';   text=`▶ Flow started: ${ev.flow_id}`; }
  else if (ev.type==='flow_done')  { cls='ok';    icon='fa-check-circle';  text=`✅ Flow completed`; }
  else if (ev.type==='flow_error') { cls='error'; icon='fa-times-circle';  text=`❌ Flow error: ${ev.error}`; }
  else if (ev.type==='step_start') { cls='info';  icon='fa-cog';           text=`  → ${ev.step_id} (${ev.action})`; }
  else if (ev.type==='step_ok')    { cls='ok';    icon='fa-check';         text=`  ✓ ${ev.step_id}${ev.output?' → '+ev.output.slice(0,80):''}`.replace('  ✓','  ✓'); }
  else if (ev.type==='step_error') { cls='error'; icon='fa-exclamation';   text=`  ✗ ${ev.step_id}: ${ev.error}`; }
  else if (ev.type==='connected')  { cls='info';  icon='fa-link';          text=`Connected to run ${ev.run_id}`; }
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
