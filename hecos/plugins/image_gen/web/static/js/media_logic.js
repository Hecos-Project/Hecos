/**
 * Autonomous logic to connect the image_gen HTML panel to the plugin API.
 */

document.addEventListener('DOMContentLoaded', async () => {
    // 1. Fetch initial config from the plugin API
    try {
        const res = await fetch('/hecos/api/plugins/image_gen/config');
        const data = await res.json();
        const cfg = data.image_gen || {};
        
        // 2. Load presets (wait for it to populate the select)
        await window.loadIgenPresets(cfg.active_preset);
        
        // 3. Apply the config to the UI
        window.applyIgenConfig(cfg);
        
        // 4. Populate providers
        await window.onProviderChanged(false);

    } catch (e) {
        console.error("[ImageGen] Bootstrap error:", e);
    }
});

window.onProviderChanged = async function(userTriggered = false) {
    const provSel = document.getElementById('igen-provider');
    const modelSel = document.getElementById('igen-model');
    if (!provSel || !modelSel) return;

    // List of autonomous providers we support
    const providers = [
        { id: "pollinations", name: "Pollinations (Free, Fast)" },
        { id: "gemini", name: "Google Gemini" },
        { id: "gemini_native", name: "Google Gemini Native (Flash)" },
        { id: "openai", name: "OpenAI DALL-E" },
        { id: "stability", name: "Stability AI" },
        { id: "airforce", name: "Airforce (Free)" },
        { id: "huggingface", name: "Hugging Face Inference API" }
    ];

    // Populate providers if empty
    if (provSel.options.length === 0) {
        providers.forEach(p => {
            let opt = document.createElement('option');
            opt.value = p.id;
            opt.textContent = p.name;
            provSel.appendChild(opt);
        });
        // Restore value if it was set before options were added
        const cfgProvider = document.getElementById('igen-provider').getAttribute('data-initial-val') || 'pollinations';
        provSel.value = cfgProvider;
    }

    // Toggle HF explorer
    const hfWrap = document.getElementById('igen-hf-explorer-wrapper');
    if (hfWrap) hfWrap.style.display = (provSel.value === 'huggingface') ? 'block' : 'none';

    // Fetch models for the selected provider
    try {
        const res = await fetch(`/hecos/api/plugins/image_gen/models?provider=${provSel.value}`);
        const data = await res.json();
        
        // Save current selection if we're just refreshing, else reset
        const currentSelection = userTriggered ? '' : modelSel.value;
        
        modelSel.innerHTML = '';
        if (data.ok && data.models) {
            data.models.forEach(m => {
                let opt = document.createElement('option');
                opt.value = m;
                opt.textContent = m;
                modelSel.appendChild(opt);
            });
            if (currentSelection && data.models.includes(currentSelection)) {
                modelSel.value = currentSelection;
            }
        }
    } catch (e) {
        console.error("[ImageGen] Fetch models error:", e);
    }
};

window.saveIgenConfig = async function() {
    const btn = document.getElementById('igen-main-save-btn');
    if (btn) btn.textContent = 'Saving...';

    const cfg = window.collectIgenConfig();
    const activePreset = document.getElementById('igen-preset') ? document.getElementById('igen-preset').value : '';
    cfg.active_preset = activePreset;

    try {
        const res = await fetch('/hecos/api/plugins/image_gen/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image_gen: cfg })
        });
        const data = await res.json();
        if (data.ok) {
            if (btn) {
                btn.textContent = '✅ Saved';
                setTimeout(() => { btn.textContent = 'Save Configuration'; }, 1500);
            }
        } else {
            alert("Save failed: " + data.error);
            if (btn) btn.textContent = 'Save Configuration';
        }
    } catch (e) {
        console.error("[ImageGen] Save config error:", e);
        if (btn) btn.textContent = 'Save Configuration';
    }
};

window.saveKeyToEnv = async function() {
    const keyInput = document.getElementById('igen-api-key');
    const provSel = document.getElementById('igen-provider');
    if (!keyInput || !provSel) return;
    
    const key = keyInput.value.trim();
    if (!key) {
        alert("Please enter a key to save globally.");
        return;
    }
    
    if (!confirm("Save this API key to the global .env file (and Keys Manager) for " + provSel.value + "?")) return;
    
    try {
        const res = await fetch('/hecos/api/plugins/image_gen/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image_gen: { 
                _internal_save_to_env: true, 
                api_key: key, 
                provider: provSel.value,
                api_key_comment: "ImageGen Panel"
            } })
        });
        const data = await res.json();
        if (data.ok) {
            alert("Key saved globally.");
            keyInput.value = ""; // clear local input since it's now global
            window.saveIgenConfig();
        } else {
            alert("Error saving key: " + data.error);
        }
    } catch(e) {
        console.error(e);
        alert("Network error.");
    }
};
