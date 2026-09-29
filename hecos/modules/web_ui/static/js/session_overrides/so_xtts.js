/* ⚡ SOUL FORGE: gp_xtts.js */

window.soSaveNewXttsInferencePreset = function() {
    window.hecosPrompt("Enter the name for the new XTTS Inference Preset:", async function(name) {
        if (!name) return;
        
        const getNum = (id) => { const v = document.getElementById(id).value; return v ? parseFloat(v) : null; };
        const p = {
            temperature: getNum('so-xtts-temp'),
            speed: getNum('so-xtts-speed'),
            top_k: parseInt(getNum('so-xtts-topk')),
            repetition_penalty: getNum('so-xtts-reppen'),
            top_p: getNum('so-xtts-topp'),
            length_penalty: getNum('so-xtts-length-penalty')
        };
        
        window.soState.xttsInferencePresets[name] = p;
        
        try {
            const res = await fetch('/api/audio/config', {
                method: 'POST',
                headers: {'Content-Type':'application/json'},
                body: JSON.stringify({ xtts_inference_presets: window.soState.xttsInferencePresets })
            });
            if (res.ok) {
                await window.soLoadData();
                document.getElementById('so-xtts-inference-preset-select').value = name;
            }
        } catch(e) {}
    });
};


window.soOverwriteXttsInferencePreset = function() {
    const name = document.getElementById('so-xtts-inference-preset-select').value;
    if (!name) {
        if (window.showToast) window.showToast("No XTTS Inference Preset selected for overwrite.", "error");
        return;
    }
    
    window.hecosConfirm(`Do you really want to overwrite the XTTS Inference Preset "${name}"?`, async function() {
        const getNum = (id) => { const v = document.getElementById(id).value; return v ? parseFloat(v) : null; };
        const p = {
            temperature: getNum('so-xtts-temp'),
            speed: getNum('so-xtts-speed'),
            top_k: parseInt(getNum('so-xtts-topk')),
            repetition_penalty: getNum('so-xtts-reppen'),
            top_p: getNum('so-xtts-topp'),
            length_penalty: getNum('so-xtts-length-penalty')
        };
        
        window.soState.xttsInferencePresets[name] = p;
        
        try {
            const res = await fetch('/api/audio/config', {
                method: 'POST',
                headers: {'Content-Type':'application/json'},
                body: JSON.stringify({ xtts_inference_presets: window.soState.xttsInferencePresets })
            });
            if (res.ok) {
                await window.soLoadData();
                document.getElementById('so-xtts-inference-preset-select').value = name;
            }
        } catch(e) {}
    });
};


window.soDeleteXttsInferencePreset = function() {
    const name = document.getElementById('so-xtts-inference-preset-select').value;
    if (!name) {
        if (window.showToast) window.showToast("No XTTS Inference Preset selected to delete.", "error");
        return;
    }
    
    window.hecosConfirm(`Are you sure you want to delete the XTTS Inference Preset "${name}"?`, async function() {
        delete window.soState.xttsInferencePresets[name];
        
        try {
            const res = await fetch('/api/audio/config', {
                method: 'POST',
                headers: {'Content-Type':'application/json'},
                body: JSON.stringify({ xtts_inference_presets: window.soState.xttsInferencePresets })
            });
            if (res.ok) {
                await window.soLoadData();
                document.getElementById('so-xtts-inference-preset-select').value = "";
            }
        } catch(e) {}
    });
};


