// ── NLP Modal ─────────────────────────────────────────────────────
function openNlpModal() {
  compiledYaml = null;
  const nInput = document.getElementById('nlp-name-input');
  const tArea = document.getElementById('nlp-textarea');
  if(nInput) nInput.value='';
  if(tArea) tArea.value='';
  const card = document.getElementById('nlp-summary-card');
  const prog = document.getElementById('nlp-compile-progress');
  const btnSave = document.getElementById('btn-save-compiled');
  if(card) card.className='';
  if(prog) prog.className='';
  if(btnSave) btnSave.style.display='none';
  const modal = document.getElementById('nlp-modal-bg');
  if(modal) modal.classList.add('open');
  if(tArea) tArea.focus();
}

function closeNlpModal() {
  const modal = document.getElementById('nlp-modal-bg');
  if(modal) modal.classList.remove('open');
  if (isRecording) stopVoiceInput();
}

async function compileFlow() {
  const ta = document.getElementById('nlp-textarea');
  const na = document.getElementById('nlp-name-input');
  if (!ta) return;
  const desc = ta.value.trim();
  const name = na ? na.value.trim() : '';
  if (!desc) { toast('error','Please describe the flow first.'); return; }

  const prog = document.getElementById('nlp-compile-progress');
  const card = document.getElementById('nlp-summary-card');
  const saveBtn = document.getElementById('btn-save-compiled');
  
  if (prog) prog.className='show';
  if (card) card.className='';
  if (saveBtn) saveBtn.style.display='none';

  try {
    const res = await fetch('/api/flows/compile',{
      method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({description:desc,flow_name:name||undefined})
    });
    const d = await res.json();
    if (!d.ok) throw new Error(d.error);

    compiledYaml = d.yaml;
    if (card) {
      card.className='show'; 
      card.textContent=d.summary;
    }
    if (saveBtn) saveBtn.style.display='block';
    toast('ok','Flow compiled successfully!');
  } catch(e) {
    toast('error','Compilation failed: '+e.message);
  } finally {
    if (prog) prog.className='';
  }
}

async function saveCompiledFlow() {
  if (!compiledYaml) return;
  try {
    const res = await fetch('/api/flows/save',{
      method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({yaml:compiledYaml})
    });
    const d = await res.json();
    if (!d.ok) throw new Error((d.errors||[d.error]).join('; '));
    closeNlpModal();
    toast('ok','Flow saved!');
    if (typeof loadFlowsList === 'function') await loadFlowsList();
    if (typeof selectFlow === 'function') selectFlow(d.flow_id);
  } catch(e) { toast('error','Save failed: '+e.message); }
}

// ── Voice input ───────────────────────────────────────────────────
function toggleVoiceInput() {
  isRecording ? stopVoiceInput() : startVoiceInput();
}

async function startVoiceInput() {
  if (!navigator.mediaDevices) { toast('error','Microphone not available.'); return; }
  const btn = document.getElementById('nlp-voice-btn');
  if (btn) {
    btn.classList.add('recording');
    btn.innerHTML='<i class="fas fa-stop-circle"></i> Stop recording';
  }
  isRecording = true;

  const stream = await navigator.mediaDevices.getUserMedia({audio:true});
  const chunks = [];
  mediaRecorder = new MediaRecorder(stream);
  mediaRecorder.ondataavailable = e => chunks.push(e.data);
  mediaRecorder.onstop = async () => {
    stream.getTracks().forEach(t => t.stop());
    const blob = new Blob(chunks, {type:'audio/webm'});
    // Use Hecos STT endpoint if available
    try {
      const fd = new FormData();
      fd.append('audio', blob, 'audio.webm');
      const res = await fetch('/audio/stt', {method:'POST', body:fd});
      const d = await res.json();
      const ta = document.getElementById('nlp-textarea');
      if (d.text && ta) ta.value = d.text;
    } catch {
      toast('info','Voice transcription unavailable — type your description instead.');
    }
  };
  mediaRecorder.start();
}

function stopVoiceInput() {
  isRecording = false;
  if (mediaRecorder && mediaRecorder.state !== 'inactive') mediaRecorder.stop();
  const btn = document.getElementById('nlp-voice-btn');
  if(btn) {
    btn.classList.remove('recording');
    btn.innerHTML='<i class="fas fa-microphone"></i> Speak your flow';
  }
}
