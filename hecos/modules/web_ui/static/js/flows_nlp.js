// ── NLP Modal ─────────────────────────────────────────────────────
function openNlpModal() {
  compiledYaml = null;
  document.getElementById('nlp-name-input').value='';
  document.getElementById('nlp-textarea').value='';
  document.getElementById('nlp-summary-card').className='';
  document.getElementById('nlp-compile-progress').className='';
  document.getElementById('btn-save-compiled').style.display='none';
  document.getElementById('nlp-modal-bg').classList.add('open');
  document.getElementById('nlp-textarea').focus();
}

function closeNlpModal() {
  document.getElementById('nlp-modal-bg').classList.remove('open');
  if (isRecording) stopVoiceInput();
}

async function compileFlow() {
  const desc = document.getElementById('nlp-textarea').value.trim();
  const name = document.getElementById('nlp-name-input').value.trim();
  if (!desc) { toast('error','Please describe the flow first.'); return; }

  document.getElementById('nlp-compile-progress').className='show';
  document.getElementById('nlp-summary-card').className='';
  document.getElementById('btn-save-compiled').style.display='none';

  try {
    const res = await fetch('/api/flows/compile',{
      method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({description:desc,flow_name:name||undefined})
    });
    const d = await res.json();
    if (!d.ok) throw new Error(d.error);

    compiledYaml = d.yaml;
    const card = document.getElementById('nlp-summary-card');
    card.className='show'; card.textContent=d.summary;
    document.getElementById('btn-save-compiled').style.display='block';
    toast('ok','Flow compiled successfully!');
  } catch(e) {
    toast('error','Compilation failed: '+e.message);
  } finally {
    document.getElementById('nlp-compile-progress').className='';
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
  btn.classList.add('recording');
  btn.innerHTML='<i class="fas fa-stop-circle"></i> Stop recording';
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
      if (d.text) document.getElementById('nlp-textarea').value = d.text;
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
