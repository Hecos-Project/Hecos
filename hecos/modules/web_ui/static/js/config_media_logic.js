/**
 * Hecos WebUI - Media Configuration Logic
 * Handles image generation settings and Media Vault.
 */

function populateMediaUI() {
    const igen = (mediaConfig && mediaConfig.image_gen) ? mediaConfig.image_gen : {};
    window.igen_custom_hf_models = igen.custom_hf_models || [];

    // --- Dynamic Image Providers Population ---
    const imgProvSelect = document.getElementById('igen-provider');
    if (imgProvSelect && cfg.llm && cfg.llm.providers) {
        imgProvSelect.innerHTML = '';
        const globalProviders = Object.keys(cfg.llm.providers);
        globalProviders.push("ollama");
        const extraImageProviders = ["pollinations", "airforce", "stability", "gemini_native", "huggingface"];
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

    setCheck('igen-enabled',          igen.enabled !== false);
    setVal('igen-provider',           igen.provider || 'pollinations');
    setVal('igen-aspect-ratio',       igen.aspect_ratio || '1:1');
    setVal('igen-width',              igen.width  || 1024);
    setVal('igen-height',             igen.height || 1024);
    setVal('igen-seed',               igen.seed ?? -1);
    setVal('igen-sampler',            igen.sampler || 'euler_a');
    setVal('igen-scheduler',          igen.scheduler || 'euler');
    setCheck('igen-nologo',           igen.nologo ?? true);
    setCheck('igen-use-neg-prompt',   igen.enable_negative_prompt ?? true);
    setVal('igen-neg-prompt',         igen.negative_prompt || '');
    setVal('igen-guidance',           igen.guidance_scale || 7.5);
    setVal('igen-steps',              igen.num_inference_steps || 30);
    setCheck('igen-auto-enrich',      igen.auto_enrich ?? true);
    setVal('igen-enrich-keywords',    igen.enrich_keywords || '');
    setVal('igen-style',              igen.style || 'none');
    setCheck('igen-optimize-flux',    igen.optimize_for_flux ?? true);
    setVal('igen-flux-instructions',  igen.flux_refiner_instructions || '');
    setCheck('igen-show-metadata',    igen.show_metadata_in_chat ?? false);

    // Sync slider display values
    const gVal = document.getElementById('igen-guidance-val');
    if (gVal) gVal.textContent = igen.guidance_scale || 7.5;
    const sVal = document.getElementById('igen-steps-val');
    if (sVal) sVal.textContent = igen.num_inference_steps || 30;

    // Show/hide custom dimension inputs
    if (typeof onAspectRatioChanged === 'function') onAspectRatioChanged();

    // Load preset list
    if (typeof loadIgenPresets === 'function') loadIgenPresets();
    if (igen.active_preset) {
        const ps = document.getElementById('igen-preset');
        if (ps) ps.value = igen.active_preset;
    }

    refreshImageModels(igen.model || 'flux');
    onProviderChanged();
}

function buildMediaPayload() {
    const aspectRatio = (document.getElementById('igen-aspect-ratio') || {}).value || '1:1';
    return {
        image_gen: {
            enabled:               document.getElementById('igen-enabled').checked,
            provider:              document.getElementById('igen-provider').value,
            model:                 document.getElementById('igen-model').value,
            aspect_ratio:          aspectRatio,
            width:                 parseInt((document.getElementById('igen-width') || {}).value) || 1024,
            height:                parseInt((document.getElementById('igen-height') || {}).value) || 1024,
            seed:                  parseInt(document.getElementById('igen-seed').value) || -1,
            sampler:               document.getElementById('igen-sampler').value || 'euler_a',
            scheduler:             document.getElementById('igen-scheduler').value || 'euler',
            nologo:                document.getElementById('igen-nologo').checked,
            enable_negative_prompt:document.getElementById('igen-use-neg-prompt').checked,
            negative_prompt:       document.getElementById('igen-neg-prompt').value.trim(),
            guidance_scale:        parseFloat(document.getElementById('igen-guidance').value) || 7.5,
            num_inference_steps:   parseInt(document.getElementById('igen-steps').value) || 30,
            auto_enrich:           document.getElementById('igen-auto-enrich').checked,
            enrich_keywords:       document.getElementById('igen-enrich-keywords').value.trim(),
            style:                 document.getElementById('igen-style').value,
            optimize_for_flux:     document.getElementById('igen-optimize-flux').checked,
            flux_refiner_instructions: document.getElementById('igen-flux-instructions').value.trim(),
            show_metadata_in_chat: document.getElementById('igen-show-metadata').checked,
            active_preset:         (document.getElementById('igen-preset') || {}).value || '',
            custom_hf_models:      window.igen_custom_hf_models || []
        }
    };
}

function onProviderChanged() {
  const prov = (document.getElementById('igen-provider') || {}).value;
  const hfWrapper = document.getElementById('igen-hf-explorer-wrapper');
  if (hfWrapper) {
    hfWrapper.style.display = (prov === 'huggingface') ? 'block' : 'none';
  }
}

async function refreshImageModels(restoreValue) {
  const provEl = document.getElementById('igen-provider');
  const provider = provEl ? provEl.value : 'pollinations';
  const sel     = document.getElementById('igen-model');
  const status  = document.getElementById('igen-model-status');
  if (!sel) return;
  if (status) status.textContent = 'Loading...';
  try {
    const r = await fetch(`/hecos/api/media/models?provider=${encodeURIComponent(provider)}`);
    const d = await r.json();
    if (d.ok && Array.isArray(d.models) && d.models.length) {
      sel.innerHTML = '';
      d.models.forEach(m => {
        const opt = document.createElement('option');
        opt.value = m; opt.textContent = m;
        if (restoreValue && m === restoreValue) opt.selected = true;
        sel.appendChild(opt);
      });
      // Ensure custom models in HF are restored even if not in backend list yet
      if (restoreValue && provider === 'huggingface' && !d.models.includes(restoreValue)) {
        const opt = document.createElement('option');
        opt.value = restoreValue; opt.textContent = restoreValue;
        opt.selected = true;
        sel.appendChild(opt);
      }
      if (status) status.textContent = `${d.models.length + (window.igen_custom_hf_models||[]).length} models`;
      if (typeof checkCustomModelSelect === 'function') checkCustomModelSelect();
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
    const res = await fetch('/hecos/api/media/open', { method: 'POST' });
    const data = await res.json();
    if (!data.ok) {
      alert('❌ Impossibile aprire la cartella: ' + (data.error || 'Errore sconosciuto'));
    }
  } catch(e) {
    console.warn('openMediaVault error:', e);
    alert('❌ Errore di connessione al server.');
  }
}

async function clearMediaVault() {
  const confirmed = confirm(
    'Sei sicuro? Questa operazione ELIMINERÀ DEFINITIVAMENTE tutte le immagini, audio e video generati da Hecos.\n\nVuoi procedere?'
  );
  if (!confirmed) return;
  try {
    const res = await fetch('/hecos/api/media/clear', { method: 'POST' });
    const data = await res.json();
    if (data.ok) {
      alert(`✅ Media Vault svuotato con successo.\nFile eliminati: ${data.deleted}`);
    } else {
      alert("❌ Errore durante l'eliminazione: " + (data.error || 'Errore sconosciuto'));
    }
  } catch(e) {
    alert('❌ Errore di connessione al server.');
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
        const res = await fetch('/hecos/api/media/refine-prompt', {
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

// Make checkCustomModelSelect and removeSelectedHFModel available globally
window.checkCustomModelSelect = function() {
    const sel = document.getElementById('igen-model');
    const btn = document.getElementById('igen-model-remove-btn');
    if (!sel || !btn) return;
    
    // Check if current selected model is in the custom HF models list
    const isCustom = (window.igen_custom_hf_models || []).includes(sel.value);
    btn.style.display = isCustom ? 'inline-block' : 'none';
};

window.removeSelectedHFModel = async function() {
    const sel = document.getElementById('igen-model');
    const modelId = sel.value;
    if (!window.igen_custom_hf_models.includes(modelId)) return;
    
    // Remove from array
    window.igen_custom_hf_models = window.igen_custom_hf_models.filter(m => m !== modelId);
    
    // Auto-save the update
    if (typeof window.saveConfig === 'function') {
        await window.saveConfig(true); 
    }
    
    // Refresh models list, fallback to first generic model
    refreshImageModels("black-forest-labs/FLUX.1-schnell");
};

// Auto-add model to custom list when picked from HuggingFace Explorer
const originalUseHFModel = window.useHFModel;
if (typeof originalUseHFModel !== 'undefined') {
    // Override slightly to push to global list
    window.useHFModel = async function(modelId) {
        if (!window.igen_custom_hf_models) window.igen_custom_hf_models = [];
        if (!window.igen_custom_hf_models.includes(modelId)) {
            window.igen_custom_hf_models.push(modelId);
        }
        
        // Execute original UI injection logic mapped in HTML if exists
        const sel = document.getElementById('igen-model');
        if (sel) {
            let exists = Array.from(sel.options).some(o => o.value === modelId);
            if (!exists) {
                const opt = document.createElement('option');
                opt.value = modelId; opt.textContent = modelId;
                sel.appendChild(opt);
            }
            sel.value = modelId;
            sel.style.transition = "border-color 0.2s, box-shadow 0.2s";
            sel.style.borderColor = "var(--accent)";
            sel.style.boxShadow = "0 0 5px var(--accent)";
            setTimeout(() => { sel.style.borderColor = ""; sel.style.boxShadow = ""; }, 800);
            
            window.checkCustomModelSelect();
            
            // Critical: Automatically save the configuration in the background!
            if (typeof window.saveConfig === 'function') {
                await window.saveConfig(true); // save silently
            }
        }
    };
}

// Preset & dimension helpers defined in config_igen.html (inline scripts)
// but exported here for any external callers
if (typeof loadIgenPresets !== 'undefined') window.loadIgenPresets = loadIgenPresets;
if (typeof saveIgenPreset !== 'undefined') window.saveIgenPreset = saveIgenPreset;
if (typeof deleteIgenPreset !== 'undefined') window.deleteIgenPreset = deleteIgenPreset;
if (typeof onAspectRatioChanged !== 'undefined') window.onAspectRatioChanged = onAspectRatioChanged;

// Slider event listeners (also handled inline in HTML for immediate feedback,
// kept here as a safety net for dynamically injected elements)
document.addEventListener('input', (e) => {
  if (e.target.id === 'igen-guidance') {
    const val = document.getElementById('igen-guidance-val');
    if (val) val.textContent = parseFloat(e.target.value).toFixed(1);
  }
  if (e.target.id === 'igen-steps') {
    const val = document.getElementById('igen-steps-val');
    if (val) val.textContent = e.target.value;
  }
});
