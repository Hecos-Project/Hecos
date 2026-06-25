/**
 * image_gen — combined panel JS
 * Contains: onProviderChanged, saveIgenConfig, saveKeyToEnv (media_logic)
 *           + preset management, collectIgenConfig, applyIgenConfig (igen_panel)
 */

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
                btn.textContent = 'âœ… Saved';
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


// ── Preset & Panel Logic ──────────────────────────────────────────────────────
/**
 * image_gen autonomous panel JS
 */

async function loadIgenPresets(restoreValue) {
    try {
        const r = await fetch('/hecos/api/plugins/image_gen/presets');
        const d = await r.json();
        if (!d.ok) return;

        const sel = document.getElementById('igen-preset');
        if (!sel) return;

        const targetValue = restoreValue !== undefined ? restoreValue : sel.value;
        sel.innerHTML = '<option value="">â€” Select a preset â€”</option>';
        (d.presets || []).forEach(p => {
            const opt = document.createElement('option');
            opt.value = p.name;
            opt.textContent = (p.builtin ? '' : 'ðŸ‘¤ ') + p.name;
            opt.dataset.builtin = String(p.builtin);
            sel.appendChild(opt);
        });

        if (targetValue) sel.value = targetValue;
        checkIgenPresetUI();
    } catch (err) {
        console.warn('[igen] loadIgenPresets error:', err);
    }
}

function checkIgenPresetUI() {
    const sel = document.getElementById('igen-preset');
    const updateBtn = document.getElementById('igen-preset-update-btn');
    const deleteBtn = document.getElementById('igen-preset-delete-btn');
    if (!sel) return;

    const selectedOpt = sel.options[sel.selectedIndex];
    const isEmpty = !sel.value;
    const isBuiltin = selectedOpt ? (selectedOpt.dataset.builtin === 'true') : true;

    const show = !isEmpty && !isBuiltin;
    if (updateBtn) updateBtn.style.display = show ? 'inline-block' : 'none';
    if (deleteBtn) deleteBtn.style.display = show ? 'inline-block' : 'none';
}

async function loadIgenPreset() {
    const sel = document.getElementById('igen-preset');
    const name = sel ? sel.value : '';
    if (!name) {
        checkIgenPresetUI();
        return;
    }
    try {
        const r = await fetch('/hecos/api/plugins/image_gen/presets/load/' + encodeURIComponent(name));
        const d = await r.json();
        if (!d.ok) {
            alert('Error loading preset: ' + d.error);
            return;
        }
        applyIgenConfig(d.config);
        if (sel) sel.value = name;
        checkIgenPresetUI();
    } catch (err) {
        console.error('[igen] preset load error', err);
    }
}

async function saveIgenPreset() {
    const name = prompt('Name for this preset:');
    if (!name || !name.trim()) return;
    const config = collectIgenConfig();
    const r = await fetch('/hecos/api/plugins/image_gen/presets/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: name.trim(), config })
    });
    const d = await r.json();
    if (d.ok) {
        await loadIgenPresets(name.trim());
    } else {
        alert('Save failed: ' + d.error);
    }
}

async function updateIgenPreset() {
    const sel = document.getElementById('igen-preset');
    const name = sel ? sel.value : '';
    if (!name) return;
    const config = collectIgenConfig();
    const r = await fetch('/hecos/api/plugins/image_gen/presets/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, config })
    });
    const d = await r.json();
    if (d.ok) {
        const btn = document.getElementById('igen-preset-update-btn');
        if (btn) {
            btn.innerHTML = 'âœ… Saved!';
            setTimeout(() => { btn.innerHTML = 'ðŸ”„ Update'; }, 1500);
        }
    } else {
        alert('Update failed: ' + d.error);
    }
}

async function deleteIgenPreset() {
    const name = document.getElementById('igen-preset') ? document.getElementById('igen-preset').value : '';
    if (!name) return;
    if (!confirm('Delete preset "' + name + '"?')) return;
    const r = await fetch('/hecos/api/plugins/image_gen/presets/delete/' + encodeURIComponent(name), { method: 'DELETE' });
    const d = await r.json();
    if (d.ok) {
        await loadIgenPresets('');
    } else {
        alert('Delete failed: ' + d.error);
    }
}

function onAspectRatioChanged() {
    const val = document.getElementById('igen-aspect-ratio').value;
    document.getElementById('igen-custom-dims').style.display = (val === 'custom') ? 'block' : 'none';
}

function collectIgenConfig() {
    const get = (id, def) => { const el = document.getElementById(id); return el ? el.value : def; };
    const chk = (id, def) => { const el = document.getElementById(id); return el ? el.checked : def; };
    return {
        provider: get('igen-provider', 'pollinations'),
        model: get('igen-model', 'flux'),
        aspect_ratio: get('igen-aspect-ratio', '1:1'),
        width: parseInt(get('igen-width', 1024)),
        height: parseInt(get('igen-height', 1024)),
        seed: parseInt(get('igen-seed', -1)),
        sampler: get('igen-sampler', 'euler'),
        scheduler: get('igen-scheduler', 'simple'),
        guidance_scale: parseFloat(get('igen-guidance', 0.0)),
        num_inference_steps: parseInt(get('igen-steps', 4)),
        enable_negative_prompt: chk('igen-use-neg-prompt', false),
        negative_prompt: get('igen-neg-prompt', ''),
        auto_enrich: chk('igen-auto-enrich', false),
        enrich_keywords: get('igen-enrich-keywords', ''),
        style: get('igen-style', 'none'),
        nologo: chk('igen-nologo', true),
        optimize_for_flux: chk('igen-optimize-flux', true),
        show_metadata_in_chat: chk('igen-show-metadata', false),
        enabled: chk('igen-enabled', true),
        api_key: get('igen-api-key', ''),
    };
}

function applyIgenConfig(cfg) {
    const set = (id, val) => { const el = document.getElementById(id); if (el) el.value = val; };
    const chk = (id, val) => { const el = document.getElementById(id); if (el) el.checked = !!val; };

    set('igen-provider', cfg.provider || 'pollinations');
    set('igen-model', cfg.model || 'flux');
    set('igen-aspect-ratio', cfg.aspect_ratio || '1:1');
    set('igen-width', cfg.width || 1024);
    set('igen-height', cfg.height || 1024);
    set('igen-seed', cfg.seed ?? -1);
    set('igen-sampler', cfg.sampler || 'euler');
    set('igen-scheduler', cfg.scheduler || 'simple');
    set('igen-api-key', cfg.api_key || '');

    const guidance = cfg.guidance_scale ?? 0.0;
    set('igen-guidance', guidance);
    const gValEl = document.getElementById('igen-guidance-val');
    if (gValEl) gValEl.textContent = parseFloat(guidance).toFixed(1);

    const steps = cfg.num_inference_steps || 4;
    set('igen-steps', steps);
    const sValEl = document.getElementById('igen-steps-val');
    if (sValEl) sValEl.textContent = steps;

    chk('igen-use-neg-prompt', cfg.enable_negative_prompt);
    set('igen-neg-prompt', cfg.negative_prompt || '');
    chk('igen-auto-enrich', cfg.auto_enrich);
    set('igen-enrich-keywords', cfg.enrich_keywords || '');
    set('igen-style', cfg.style || 'none');
    chk('igen-nologo', cfg.nologo ?? true);
    chk('igen-optimize-flux', cfg.optimize_for_flux ?? true);
    chk('igen-show-metadata', cfg.show_metadata_in_chat ?? false);
    chk('igen-enabled', cfg.enabled ?? true);

    onAspectRatioChanged();
    if (cfg.provider && typeof window.onProviderChanged === 'function') window.onProviderChanged();
}

// HF Explorer
async function searchHFHub() {
    const qEl = document.getElementById('igen-hf-search-q');
    const q = qEl ? qEl.value.trim() : '';
    const resContainer = document.getElementById('igen-hf-results');
    if (!resContainer) return;
    resContainer.innerHTML = '<div style="padding:10px; text-align:center; color:var(--muted); font-size:12px;">Searching...</div>';
    try {
        const res = await fetch('/hecos/api/plugins/image_gen/hf-search?q=' + encodeURIComponent(q));
        const data = await res.json();
        if (!data.ok) {
            resContainer.innerHTML = `<div style="padding:10px; color:var(--error, #e74c3c); font-size:12px;">Error: ${data.error}</div>`;
            return;
        }
        if (!data.models || data.models.length === 0) {
            resContainer.innerHTML = '<div style="padding:10px; text-align:center; color:var(--muted); font-size:12px;">No models found.</div>';
            return;
        }
        let html = '<div style="display:flex; flex-direction:column;">';
        data.models.forEach(m => {
            html += `<div style="display:flex;justify-content:space-between;padding:8px 10px;border-bottom:1px solid var(--border);">
                <div><strong>${m.id}</strong><br><small>â¬‡ï¸ ${m.downloads} | â¤ï¸ ${m.likes}</small></div>
                <button onclick="useHFModel('${m.id}')" style="padding:4px 10px;font-size:11px;border-radius:5px;cursor:pointer;">âž• Use</button>
            </div>`;
        });
        html += '</div>';
        resContainer.innerHTML = html;
    } catch (err) {
        resContainer.innerHTML = `<div style="padding:10px; color:#e74c3c; font-size:12px;">Network Error: ${err.message}</div>`;
    }
}

function useHFModel(modelId) {
    const sel = document.getElementById('igen-model');
    if (!sel) return;
    let exists = false;
    for (let opt of sel.options) { if (opt.value === modelId) { exists = true; break; } }
    if (!exists) {
        const opt = document.createElement('option');
        opt.value = modelId;
        opt.textContent = modelId;
        sel.appendChild(opt);
    }
    sel.value = modelId;
}

window.searchHFHub = searchHFHub;
window.useHFModel = useHFModel;
window.collectIgenConfig = collectIgenConfig;
window.applyIgenConfig = applyIgenConfig;
window.loadIgenPresets = loadIgenPresets;
window.loadIgenPreset = loadIgenPreset;
window.saveIgenPreset = saveIgenPreset;
window.updateIgenPreset = updateIgenPreset;
window.deleteIgenPreset = deleteIgenPreset;
window.checkIgenPresetUI = checkIgenPresetUI;
window.onAspectRatioChanged = onAspectRatioChanged;
/ * *  
   *   A u t o n o m o u s   l o g i c   t o   c o n n e c t   t h e   i m a g e _ g e n   H T M L   p a n e l   t o   t h e   p l u g i n   A P I .  
   * /  
  
 d o c u m e n t . a d d E v e n t L i s t e n e r ( ' D O M C o n t e n t L o a d e d ' ,   a s y n c   ( )   = >   {  
         / /   1 .   F e t c h   i n i t i a l   c o n f i g   f r o m   t h e   p l u g i n   A P I  
         t r y   {  
                 c o n s t   r e s   =   a w a i t   f e t c h ( ' / h e c o s / a p i / p l u g i n s / i m a g e _ g e n / c o n f i g ' ) ;  
                 c o n s t   d a t a   =   a w a i t   r e s . j s o n ( ) ;  
                 c o n s t   c f g   =   d a t a . i m a g e _ g e n   | |   { } ;  
                  
                 / /   2 .   L o a d   p r e s e t s   ( w a i t   f o r   i t   t o   p o p u l a t e   t h e   s e l e c t )  
                 a w a i t   w i n d o w . l o a d I g e n P r e s e t s ( c f g . a c t i v e _ p r e s e t ) ;  
                  
                 / /   3 .   A p p l y   t h e   c o n f i g   t o   t h e   U I  
                 w i n d o w . a p p l y I g e n C o n f i g ( c f g ) ;  
                  
                 / /   4 .   P o p u l a t e   p r o v i d e r s  
                 a w a i t   w i n d o w . o n P r o v i d e r C h a n g e d ( f a l s e ) ;  
  
         }   c a t c h   ( e )   {  
                 c o n s o l e . e r r o r ( " [ I m a g e G e n ]   B o o t s t r a p   e r r o r : " ,   e ) ;  
         }  
 } ) ;  
  
 w i n d o w . o n P r o v i d e r C h a n g e d   =   a s y n c   f u n c t i o n ( u s e r T r i g g e r e d   =   f a l s e )   {  
         c o n s t   p r o v S e l   =   d o c u m e n t . g e t E l e m e n t B y I d ( ' i g e n - p r o v i d e r ' ) ;  
         c o n s t   m o d e l S e l   =   d o c u m e n t . g e t E l e m e n t B y I d ( ' i g e n - m o d e l ' ) ;  
         i f   ( ! p r o v S e l   | |   ! m o d e l S e l )   r e t u r n ;  
  
         / /   L i s t   o f   a u t o n o m o u s   p r o v i d e r s   w e   s u p p o r t  
         c o n s t   p r o v i d e r s   =   [  
                 {   i d :   " p o l l i n a t i o n s " ,   n a m e :   " P o l l i n a t i o n s   ( F r e e ,   F a s t ) "   } ,  
                 {   i d :   " g e m i n i " ,   n a m e :   " G o o g l e   G e m i n i "   } ,  
                 {   i d :   " g e m i n i _ n a t i v e " ,   n a m e :   " G o o g l e   G e m i n i   N a t i v e   ( F l a s h ) "   } ,  
                 {   i d :   " o p e n a i " ,   n a m e :   " O p e n A I   D A L L - E "   } ,  
                 {   i d :   " s t a b i l i t y " ,   n a m e :   " S t a b i l i t y   A I "   } ,  
                 {   i d :   " a i r f o r c e " ,   n a m e :   " A i r f o r c e   ( F r e e ) "   } ,  
                 {   i d :   " h u g g i n g f a c e " ,   n a m e :   " H u g g i n g   F a c e   I n f e r e n c e   A P I "   }  
         ] ;  
  
         / /   P o p u l a t e   p r o v i d e r s   i f   e m p t y  
         i f   ( p r o v S e l . o p t i o n s . l e n g t h   = = =   0 )   {  
                 p r o v i d e r s . f o r E a c h ( p   = >   {  
                         l e t   o p t   =   d o c u m e n t . c r e a t e E l e m e n t ( ' o p t i o n ' ) ;  
                         o p t . v a l u e   =   p . i d ;  
                         o p t . t e x t C o n t e n t   =   p . n a m e ;  
                         p r o v S e l . a p p e n d C h i l d ( o p t ) ;  
                 } ) ;  
                 / /   R e s t o r e   v a l u e   i f   i t   w a s   s e t   b e f o r e   o p t i o n s   w e r e   a d d e d  
                 c o n s t   c f g P r o v i d e r   =   d o c u m e n t . g e t E l e m e n t B y I d ( ' i g e n - p r o v i d e r ' ) . g e t A t t r i b u t e ( ' d a t a - i n i t i a l - v a l ' )   | |   ' p o l l i n a t i o n s ' ;  
                 p r o v S e l . v a l u e   =   c f g P r o v i d e r ;  
         }  
  
         / /   T o g g l e   H F   e x p l o r e r  
         c o n s t   h f W r a p   =   d o c u m e n t . g e t E l e m e n t B y I d ( ' i g e n - h f - e x p l o r e r - w r a p p e r ' ) ;  
         i f   ( h f W r a p )   h f W r a p . s t y l e . d i s p l a y   =   ( p r o v S e l . v a l u e   = = =   ' h u g g i n g f a c e ' )   ?   ' b l o c k '   :   ' n o n e ' ;  
  
         / /   F e t c h   m o d e l s   f o r   t h e   s e l e c t e d   p r o v i d e r  
         t r y   {  
                 c o n s t   r e s   =   a w a i t   f e t c h ( ` / h e c o s / a p i / p l u g i n s / i m a g e _ g e n / m o d e l s ? p r o v i d e r = $ { p r o v S e l . v a l u e } ` ) ;  
                 c o n s t   d a t a   =   a w a i t   r e s . j s o n ( ) ;  
                  
                 / /   S a v e   c u r r e n t   s e l e c t i o n   i f   w e ' r e   j u s t   r e f r e s h i n g ,   e l s e   r e s e t  
                 c o n s t   c u r r e n t S e l e c t i o n   =   u s e r T r i g g e r e d   ?   ' '   :   m o d e l S e l . v a l u e ;  
                  
                 m o d e l S e l . i n n e r H T M L   =   ' ' ;  
                 i f   ( d a t a . o k   & &   d a t a . m o d e l s )   {  
                         d a t a . m o d e l s . f o r E a c h ( m   = >   {  
                                 l e t   o p t   =   d o c u m e n t . c r e a t e E l e m e n t ( ' o p t i o n ' ) ;  
                                 o p t . v a l u e   =   m ;  
                                 o p t . t e x t C o n t e n t   =   m ;  
                                 m o d e l S e l . a p p e n d C h i l d ( o p t ) ;  
                         } ) ;  
                         i f   ( c u r r e n t S e l e c t i o n   & &   d a t a . m o d e l s . i n c l u d e s ( c u r r e n t S e l e c t i o n ) )   {  
                                 m o d e l S e l . v a l u e   =   c u r r e n t S e l e c t i o n ;  
                         }  
                 }  
         }   c a t c h   ( e )   {  
                 c o n s o l e . e r r o r ( " [ I m a g e G e n ]   F e t c h   m o d e l s   e r r o r : " ,   e ) ;  
         }  
 } ;  
  
 w i n d o w . s a v e I g e n C o n f i g   =   a s y n c   f u n c t i o n ( )   {  
         c o n s t   b t n   =   d o c u m e n t . g e t E l e m e n t B y I d ( ' i g e n - m a i n - s a v e - b t n ' ) ;  
         i f   ( b t n )   b t n . t e x t C o n t e n t   =   ' S a v i n g . . . ' ;  
  
         c o n s t   c f g   =   w i n d o w . c o l l e c t I g e n C o n f i g ( ) ;  
         c o n s t   a c t i v e P r e s e t   =   d o c u m e n t . g e t E l e m e n t B y I d ( ' i g e n - p r e s e t ' )   ?   d o c u m e n t . g e t E l e m e n t B y I d ( ' i g e n - p r e s e t ' ) . v a l u e   :   ' ' ;  
         c f g . a c t i v e _ p r e s e t   =   a c t i v e P r e s e t ;  
  
         t r y   {  
                 c o n s t   r e s   =   a w a i t   f e t c h ( ' / h e c o s / a p i / p l u g i n s / i m a g e _ g e n / c o n f i g ' ,   {  
                         m e t h o d :   ' P O S T ' ,  
                         h e a d e r s :   {   ' C o n t e n t - T y p e ' :   ' a p p l i c a t i o n / j s o n '   } ,  
                         b o d y :   J S O N . s t r i n g i f y ( {   i m a g e _ g e n :   c f g   } )  
                 } ) ;  
                 c o n s t   d a t a   =   a w a i t   r e s . j s o n ( ) ;  
                 i f   ( d a t a . o k )   {  
                         i f   ( b t n )   {  
                                 b t n . t e x t C o n t e n t   =   ' â S&   S a v e d ' ;  
                                 s e t T i m e o u t ( ( )   = >   {   b t n . t e x t C o n t e n t   =   ' S a v e   C o n f i g u r a t i o n ' ;   } ,   1 5 0 0 ) ;  
                         }  
                 }   e l s e   {  
                         a l e r t ( " S a v e   f a i l e d :   "   +   d a t a . e r r o r ) ;  
                         i f   ( b t n )   b t n . t e x t C o n t e n t   =   ' S a v e   C o n f i g u r a t i o n ' ;  
                 }  
         }   c a t c h   ( e )   {  
                 c o n s o l e . e r r o r ( " [ I m a g e G e n ]   S a v e   c o n f i g   e r r o r : " ,   e ) ;  
                 i f   ( b t n )   b t n . t e x t C o n t e n t   =   ' S a v e   C o n f i g u r a t i o n ' ;  
         }  
 } ;  
  
 w i n d o w . s a v e K e y T o E n v   =   a s y n c   f u n c t i o n ( )   {  
         c o n s t   k e y I n p u t   =   d o c u m e n t . g e t E l e m e n t B y I d ( ' i g e n - a p i - k e y ' ) ;  
         c o n s t   p r o v S e l   =   d o c u m e n t . g e t E l e m e n t B y I d ( ' i g e n - p r o v i d e r ' ) ;  
         i f   ( ! k e y I n p u t   | |   ! p r o v S e l )   r e t u r n ;  
          
         c o n s t   k e y   =   k e y I n p u t . v a l u e . t r i m ( ) ;  
         i f   ( ! k e y )   {  
                 a l e r t ( " P l e a s e   e n t e r   a   k e y   t o   s a v e   g l o b a l l y . " ) ;  
                 r e t u r n ;  
         }  
          
         i f   ( ! c o n f i r m ( " S a v e   t h i s   A P I   k e y   t o   t h e   g l o b a l   . e n v   f i l e   ( a n d   K e y s   M a n a g e r )   f o r   "   +   p r o v S e l . v a l u e   +   " ? " ) )   r e t u r n ;  
          
         t r y   {  
                 c o n s t   r e s   =   a w a i t   f e t c h ( ' / h e c o s / a p i / p l u g i n s / i m a g e _ g e n / c o n f i g ' ,   {  
                         m e t h o d :   ' P O S T ' ,  
                         h e a d e r s :   {   ' C o n t e n t - T y p e ' :   ' a p p l i c a t i o n / j s o n '   } ,  
                         b o d y :   J S O N . s t r i n g i f y ( {   i m a g e _ g e n :   {    
                                 _ i n t e r n a l _ s a v e _ t o _ e n v :   t r u e ,    
                                 a p i _ k e y :   k e y ,    
                                 p r o v i d e r :   p r o v S e l . v a l u e ,  
                                 a p i _ k e y _ c o m m e n t :   " I m a g e G e n   P a n e l "  
                         }   } )  
                 } ) ;  
                 c o n s t   d a t a   =   a w a i t   r e s . j s o n ( ) ;  
                 i f   ( d a t a . o k )   {  
                         a l e r t ( " K e y   s a v e d   g l o b a l l y . " ) ;  
                         k e y I n p u t . v a l u e   =   " " ;   / /   c l e a r   l o c a l   i n p u t   s i n c e   i t ' s   n o w   g l o b a l  
                         w i n d o w . s a v e I g e n C o n f i g ( ) ;  
                 }   e l s e   {  
                         a l e r t ( " E r r o r   s a v i n g   k e y :   "   +   d a t a . e r r o r ) ;  
                 }  
         }   c a t c h ( e )   {  
                 c o n s o l e . e r r o r ( e ) ;  
                 a l e r t ( " N e t w o r k   e r r o r . " ) ;  
         }  
 } ;  
 
