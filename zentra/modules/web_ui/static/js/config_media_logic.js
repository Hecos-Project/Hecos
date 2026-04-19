/**
 * Zentra Core WebUI - Media Configuration Logic
 * Handles image generation settings and Media Vault.
 */

function populateMediaUI() {
    const igen = (mediaConfig && mediaConfig.image_gen) ? mediaConfig.image_gen : {};

    // --- Dynamic Image Providers Population ---
    const imgProvSelect = document.getElementById('igen-provider');
    if (imgProvSelect && cfg.llm && cfg.llm.providers) {
        imgProvSelect.innerHTML = '';
        const globalProviders = Object.keys(cfg.llm.providers);
        globalProviders.push("ollama");
        const extraImageProviders = ["pollinations", "airforce", "stability", "gemini_native", "huggingface"];
        
        // Merge without duplicates
        const allSet = new Set([...globalProviders, ...extraImageProviders]);
        
        const labels = {
            "pollinations": "Pollinations.ai (Free)",
            "airforce": "Airforce API (Free/Experimental)",
            "gemini": "Google Gemini Imagen",
            "gemini_native": "Google Gemini (Studio Multi-Modality)",
            "openai": "OpenAI DALL-E",
            "stability": "Stability.ai",
            "huggingface": "Hugging Face Inference API",
            "groq": "Groq (Testo - Non supporta immagini)",
            "anthropic": "Anthropic (Testo - Non supporta immagini)",
            "ollama": "Ollama (Testo - Non supporta immagini)",
            "lmstudio": "LM Studio (Testo - Non supporta immagini)"
        };

        allSet.forEach(prov => {
            const opt = document.createElement('option');
            opt.value = prov;
            opt.textContent = labels[prov] || (prov.charAt(0).toUpperCase() + prov.slice(1));
            imgProvSelect.appendChild(opt);
        });
    }

    setCheck('igen-enabled', igen.enabled !== false);
    setVal('igen-provider', igen.provider || 'pollinations');
    setVal('igen-width', igen.width  || 1024);
    setVal('igen-height', igen.height || 1024);
    setCheck('igen-nologo', igen.nologo ?? true);
    // New Advanced Fields
    setCheck('igen-use-neg-prompt', igen.enable_negative_prompt ?? true);
    setVal('igen-neg-prompt', igen.negative_prompt || '');
    setVal('igen-guidance', igen.guidance_scale || 7.5);
    setVal('igen-steps', igen.num_inference_steps || 30);
    setCheck('igen-auto-enrich', igen.auto_enrich ?? true);
    setVal('igen-enrich-keywords', igen.enrich_keywords || '');
    setVal('igen-style', igen.style || 'none');
    setCheck('igen-optimize-flux', igen.optimize_for_flux ?? true);
    setVal('igen-flux-instructions', igen.flux_refiner_instructions || '');

    // Sync Slider Labels
    const gVal = document.getElementById('igen-guidance-val');
    if (gVal) gVal.textContent = igen.guidance_scale || 7.5;
    const sVal = document.getElementById('igen-steps-val');
    if (sVal) sVal.textContent = igen.num_inference_steps || 30;

    refreshImageModels(igen.model || 'flux');
    onProviderChanged();
}

function buildMediaPayload() {
    return {
        image_gen: {
            enabled: document.getElementById('igen-enabled').checked,
            provider: document.getElementById('igen-provider').value,
            model: document.getElementById('igen-model').value,
            width: parseInt(document.getElementById('igen-width').value) || 1024,
            height: parseInt(document.getElementById('igen-height').value) || 1024,
            nologo: document.getElementById('igen-nologo').checked,
            enable_negative_prompt: document.getElementById('igen-use-neg-prompt').checked,
            negative_prompt: document.getElementById('igen-neg-prompt').value.trim(),
            guidance_scale: parseFloat(document.getElementById('igen-guidance').value) || 7.5,
            num_inference_steps: parseInt(document.getElementById('igen-steps').value) || 30,
            auto_enrich: document.getElementById('igen-auto-enrich').checked,
            enrich_keywords: document.getElementById('igen-enrich-keywords').value.trim(),
            style: document.getElementById('igen-style').value,
            optimize_for_flux: document.getElementById('igen-optimize-flux').checked,
            flux_refiner_instructions: document.getElementById('igen-flux-instructions').value.trim()
        }
    };
}

function onProviderChanged() {
  // Provider UI toggles if any future ones are needed
}

async function refreshImageModels(restoreValue) {
  const provEl = document.getElementById('igen-provider');
  const provider = provEl ? provEl.value : 'pollinations';
  const sel     = document.getElementById('igen-model');
  const status  = document.getElementById('igen-model-status');
  if (!sel) return;
  if (status) status.textContent = 'Loading...';
  try {
    const r = await fetch(`/zentra/api/media/models?provider=${encodeURIComponent(provider)}`);
    const d = await r.json();
    if (d.ok && Array.isArray(d.models) && d.models.length) {
      sel.innerHTML = '';
      d.models.forEach(m => {
        const opt = document.createElement('option');
        opt.value = m; opt.textContent = m;
        if (restoreValue && m === restoreValue) opt.selected = true;
        sel.appendChild(opt);
      });
      if (status) status.textContent = `${d.models.length} models`;
    } else {
      if (status) status.textContent = 'Using defaults';
    }
  } catch(e) {
    if (status) status.textContent = 'Could not fetch';
    console.warn('refreshImageModels error:', e);
  }
}

async function openMediaVault() {
  try {
    const res = await fetch('/zentra/api/media/open-folder', { method: 'POST' });
    if (!res.ok) alert('Impossibile aprire la cartella.');
  } catch(e) { console.error(e); }
}

async function clearMediaVault() {
  if (!confirm('Sei sicuro? Questa operazione ELIMINERÀ DEFINITIVAMENTE tutte le immagini salvate in locale.\n\nVuoi procedere?')) return;
  try {
    const res = await fetch('/zentra/api/media/clear', { method: 'POST' });
    const data = await res.json();
    if (data.ok) {
      alert(`Media Vault svuotato con successo.\nFile eliminati: ${data.deleted}`);
    } else {
      alert("Errore durante l'eliminazione: " + data.error);
    }
  } catch(e) {
    alert('Errore di connessione al server.');
  }
}

async function refineDraftPrompt(btn) {
    const draft = document.getElementById('igen-flux-draft').value.trim();
    if (!draft) return;
    const instructions = document.getElementById('igen-flux-instructions').value.trim();
    const origText = btn.innerHTML;
    btn.innerHTML = '&#8987; ...';
    btn.disabled = true;
    
    try {
        const res = await fetch('/zentra/api/media/refine-prompt', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ prompt: draft, instructions: instructions })
        });
        const data = await res.json();
        if (data.ok && data.refined) {
            document.getElementById('igen-flux-result').value = data.refined;
        } else {
            alert("Error: " + (data.error || "Unknown error"));
        }
    } catch(e) {
        console.error(e);
        alert("Network error.");
    } finally {
        btn.innerHTML = origText;
        btn.disabled = false;
    }
}

function sendPromptToChat() {
    const res = document.getElementById('igen-flux-result').value.trim();
    if (!res) return;
    
    // Inject into the chat input window (assuming we are in an iframe inside the main UI)
    const chatInput = window.parent.document.getElementById('chat-input');
    if (chatInput) {
        chatInput.value = "/img " + res;
        chatInput.focus();
    } else {
        alert("Chat input not found. Copy the prompt manually.");
    }
}

// Exports for Global Scope
window.populateMediaUI = populateMediaUI;
window.buildMediaPayload = buildMediaPayload;
window.onProviderChanged = onProviderChanged;
window.refreshImageModels = refreshImageModels;
window.openMediaVault = openMediaVault;
window.clearMediaVault = clearMediaVault;
window.refineDraftPrompt = refineDraftPrompt;
window.sendPromptToChat = sendPromptToChat;

// --- Event Listeners for Sliders ---
document.addEventListener('input', (e) => {
  if (e.target.id === 'igen-guidance') {
    const val = document.getElementById('igen-guidance-val');
    if (val) val.textContent = e.target.value;
  }
  if (e.target.id === 'igen-steps') {
    const val = document.getElementById('igen-steps-val');
    if (val) val.textContent = e.target.value;
  }
});
