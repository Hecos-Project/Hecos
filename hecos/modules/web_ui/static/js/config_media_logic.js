/**
 * Hecos WebUI - Media Configuration Logic
 * Handles image generation settings and Media Vault.
 */

async function populateMediaUI() {
    const igen = (mediaConfig && mediaConfig.image_gen) ? mediaConfig.image_gen : (window.cfg?.plugins?.IMAGE_GEN || {});
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
    setVal('igen-sampler',            igen.sampler || 'euler');
    setVal('igen-scheduler',          igen.scheduler || 'simple');
    setCheck('igen-nologo',           igen.nologo ?? true);
    setCheck('igen-use-neg-prompt',   igen.enable_negative_prompt ?? false);
    setVal('igen-neg-prompt',         igen.negative_prompt || '');
    // Use ?? instead of || so that 0.0 is preserved (not replaced by 7.5)
    setVal('igen-guidance',           igen.guidance_scale ?? 0.0);
    setVal('igen-steps',              igen.num_inference_steps || 4);
    setCheck('igen-auto-enrich',      igen.auto_enrich ?? false);
    setVal('igen-enrich-keywords',    igen.enrich_keywords || '');
    setVal('igen-style',              igen.style || 'none');
    setCheck('igen-optimize-flux',    igen.optimize_for_flux ?? true);
    setVal('igen-flux-instructions',  igen.flux_refiner_instructions || '');
    setCheck('igen-show-metadata',    igen.show_metadata_in_chat ?? false);

    // Sync slider display values — use ?? so 0.0 is shown correctly
    const gVal = document.getElementById('igen-guidance-val');
    if (gVal) gVal.textContent = parseFloat(igen.guidance_scale ?? 0.0).toFixed(1);
    const sVal = document.getElementById('igen-steps-val');
    if (sVal) sVal.textContent = igen.num_inference_steps || 4;

    // Show/hide custom dimension inputs
    if (typeof onAspectRatioChanged === 'function') onAspectRatioChanged();

    // ── Preset list: AWAIT so the dropdown is fully populated before we set the active value ──
    if (typeof loadIgenPresets === 'function') {
        await loadIgenPresets();   // waits for the fetch to complete and the <option>s to be inserted
    }
    // Now the dropdown has all options — safely set the active preset
    if (igen.active_preset) {
        const ps = document.getElementById('igen-preset');
        if (ps) {
            ps.value = igen.active_preset;
            if (typeof checkIgenPresetUI === 'function') checkIgenPresetUI();
        }
    }

    refreshImageModels(igen.model || 'flux');
    onProviderChanged();
}

function buildMediaPayload() {
    // ALWAYS read from DOM first. Only fall back to window.mediaConfig for fields
    // that have no DOM representation (e.g. presets dict, custom_hf_models, api_key).
    // This prevents stale/null mediaConfig from overwriting user changes.
    const stored = (window.mediaConfig && window.mediaConfig.image_gen) ? window.mediaConfig.image_gen : {};

    // Helper: read from DOM if element exists, else use stored value, else use hardcoded default
    const domV  = (id, fallback) => { const el = document.getElementById(id); return (el !== null) ? el.value    : fallback; };
    const domC  = (id, fallback) => { const el = document.getElementById(id); return (el !== null) ? el.checked : fallback; };

    // Use ?? for numeric fields so that 0 / 0.0 is preserved (|| would replace 0 with fallback)
    const guidanceRaw = domV('igen-guidance', stored.guidance_scale ?? 0.0);
    const stepsRaw    = domV('igen-steps',    stored.num_inference_steps ?? 4);

    return {
        image_gen: {
            enabled:                   domC('igen-enabled',          stored.enabled               !== false),
            provider:                  domV('igen-provider',         stored.provider               || 'pollinations'),
            model:                     domV('igen-model',            stored.model                  || 'flux'),
            aspect_ratio:              domV('igen-aspect-ratio',     stored.aspect_ratio           || '1:1'),
            width:                     parseInt(domV('igen-width',   stored.width                  || 1024)),
            height:                    parseInt(domV('igen-height',  stored.height                 || 1024)),
            seed:                      parseInt(domV('igen-seed',    stored.seed                   ?? -1)),
            sampler:                   domV('igen-sampler',          stored.sampler                || 'euler'),
            scheduler:                 domV('igen-scheduler',        stored.scheduler              || 'simple'),
            nologo:                    domC('igen-nologo',           stored.nologo                 ?? true),
            enable_negative_prompt:    domC('igen-use-neg-prompt',  stored.enable_negative_prompt ?? false),
            negative_prompt:          (domV('igen-neg-prompt',       stored.negative_prompt        || '')).trim(),
            guidance_scale:            parseFloat(guidanceRaw),
            num_inference_steps:       parseInt(stepsRaw),
            auto_enrich:               domC('igen-auto-enrich',      stored.auto_enrich            ?? false),
            enrich_keywords:          (domV('igen-enrich-keywords',  stored.enrich_keywords        || '')).trim(),
            style:                     domV('igen-style',            stored.style                  || 'none'),
            optimize_for_flux:         domC('igen-optimize-flux',    stored.optimize_for_flux      ?? true),
            flux_refiner_instructions:(domV('igen-flux-instructions',stored.flux_refiner_instructions || '')).trim(),
            show_metadata_in_chat:     domC('igen-show-metadata',   stored.show_metadata_in_chat  ?? false),
            active_preset:             domV('igen-preset',           stored.active_preset          || ''),
            // Non-DOM fields: preserve from stored config
            // CRITICAL: presets must never revert to {} — always use stored.presets
            custom_hf_models:          window.igen_custom_hf_models || stored.custom_hf_models || [],
            api_key:                   stored.api_key               || '',
            api_key_comment:           stored.api_key_comment       || '',
            last_seed:                 stored.last_seed             ?? -1,
            presets:                   stored.presets               || {},
        }
    };
}

function onProviderChanged(isManual = false) {
  const prov = (document.getElementById('igen-provider') || {}).value;
  const hfWrapper = document.getElementById('igen-hf-explorer-wrapper');
  if (hfWrapper) {
    hfWrapper.style.display = (prov === 'huggingface') ? 'block' : 'none';
  }
  if (isManual) {
      // Refresh models matching the new provider. Uses setTimeout to not block UI thread during the "change" event save fired by config_core
      setTimeout(async () => {
          await refreshImageModels();
          if (typeof window.saveConfig === 'function') window.saveConfig(true);
      }, 100);
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
