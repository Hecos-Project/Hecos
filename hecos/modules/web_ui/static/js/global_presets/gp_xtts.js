/* ⚡ SOUL FORGE: gp_xtts.js */

window.sfSaveNewXttsInferencePreset = function() {
    window.hecosPrompt("Enter the name for the new XTTS Inference Preset:", async function(name) {
        if (!name) return;
        
        const getNum = (id) => { const v = document.getElementById(id).value; return v ? parseFloat(v) : null; };
        const p = {
            temperature: getNum('sf-xtts-temp'),
            speed: getNum('sf-xtts-speed'),
            top_k: parseInt(getNum('sf-xtts-topk')),
            repetition_penalty: getNum('sf-xtts-reppen'),
            top_p: getNum('sf-xtts-topp'),
            length_penalty: getNum('sf-xtts-length-penalty')
        };
        
        window.sfState.xttsInferencePresets[name] = p;
        
        try {
            const res = await fetch('/api/audio/config', {
                method: 'POST',
                headers: {'Content-Type':'application/json'},
                body: JSON.stringify({ xtts_inference_presets: window.sfState.xttsInferencePresets })
            });
            if (res.ok) {
                await window.sfLoadData();
                document.getElementById('sf-xtts-inference-preset-select').value = name;
            }
        } catch(e) {}
    });
};


window.sfOverwriteXttsInferencePreset = function() {
    const name = document.getElementById('sf-xtts-inference-preset-select').value;
    if (!name) {
        if (window.showToast) window.showToast("No XTTS Inference Preset selected for overwrite.", "error");
        return;
    }
    
    window.hecosConfirm(`Do you really want to overwrite the XTTS Inference Preset "${name}"?`, async function() {
        const getNum = (id) => { const v = document.getElementById(id).value; return v ? parseFloat(v) : null; };
        const p = {
            temperature: getNum('sf-xtts-temp'),
            speed: getNum('sf-xtts-speed'),
            top_k: parseInt(getNum('sf-xtts-topk')),
            repetition_penalty: getNum('sf-xtts-reppen'),
            top_p: getNum('sf-xtts-topp'),
            length_penalty: getNum('sf-xtts-length-penalty')
        };
        
        window.sfState.xttsInferencePresets[name] = p;
        
        try {
            const res = await fetch('/api/audio/config', {
                method: 'POST',
                headers: {'Content-Type':'application/json'},
                body: JSON.stringify({ xtts_inference_presets: window.sfState.xttsInferencePresets })
            });
            if (res.ok) {
                await window.sfLoadData();
                document.getElementById('sf-xtts-inference-preset-select').value = name;
            }
        } catch(e) {}
    });
};


window.sfDeleteXttsInferencePreset = function() {
    const name = document.getElementById('sf-xtts-inference-preset-select').value;
    if (!name) {
        if (window.showToast) window.showToast("No XTTS Inference Preset selected to delete.", "error");
        return;
    }
    
    window.hecosConfirm(`Are you sure you want to delete the XTTS Inference Preset "${name}"?`, async function() {
        delete window.sfState.xttsInferencePresets[name];
        
        try {
            const res = await fetch('/api/audio/config', {
                method: 'POST',
                headers: {'Content-Type':'application/json'},
                body: JSON.stringify({ xtts_inference_presets: window.sfState.xttsInferencePresets })
            });
            if (res.ok) {
                await window.sfLoadData();
                document.getElementById('sf-xtts-inference-preset-select').value = "";
            }
        } catch(e) {}
    });
};


